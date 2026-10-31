"""Recurring Billing Engine, Tax Calculation, and Discount Evaluation for Brightloop."""

import sqlite3
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional, Tuple

def parse_date(d_str: Optional[str]) -> Optional[date]:
    if not d_str:
        return None
    try:
        return datetime.fromisoformat(d_str.split("T")[0]).date()
    except Exception:
        return None

def compute_next_billing_date(current_date: date, frequency: str) -> date:
    """Computes the next billing date based on frequency."""
    freq = frequency.lower()
    if freq == "daily":
        return current_date + timedelta(days=1)
    elif freq == "weekly":
        return current_date + timedelta(days=7)
    elif freq == "yearly":
        # Approximate or leap-safe year addition
        try:
            return current_date.replace(year=current_date.year + 1)
        except ValueError:
            return current_date + timedelta(days=365)
    else: # monthly (default)
        month = current_date.month + 1
        year = current_date.year
        if month > 12:
            month = 1
            year += 1
        day = min(current_date.day, 28)
        return date(year, month, day)

def compute_due_date(issue_date: date, payment_terms: str) -> date:
    """Calculates invoice due date from payment terms."""
    terms = (payment_terms or "net_30").lower()
    if terms == "immediate":
        return issue_date
    elif terms == "net_15":
        return issue_date + timedelta(days=15)
    elif terms == "net_60":
        return issue_date + timedelta(days=60)
    else: # net_30
        return issue_date + timedelta(days=30)

def generate_invoice_number(conn: sqlite3.Connection) -> str:
    """Generates sequential invoice number e.g. INV-2026-0005."""
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as cnt FROM invoices")
    count = cur.fetchone()["cnt"] + 1
    year = date.today().year
    return f"INV-{year}-{count:04d}"

def evaluate_discounts_for_subscription(
    conn: sqlite3.Connection,
    subscription_id: int,
    subtotal: float,
    total_quantity: int,
    lines: List[Dict[str, Any]],
    as_of: date
) -> Tuple[float, Optional[int]]:
    """
    Evaluates discount rules:
    - Checks start and end date
    - Checks usage limits
    - Checks min_purchase_amount and min_quantity
    Returns (discount_amount, discount_id)
    """
    cur = conn.cursor()
    
    # First check if the subscription explicitly references a discount
    cur.execute("""
        SELECT sl.discount_id 
        FROM subscription_lines sl
        WHERE sl.subscription_id = ? AND sl.discount_id IS NOT NULL
        LIMIT 1
    """, (subscription_id,))
    assigned = cur.fetchone()
    
    candidates = []
    if assigned and assigned["discount_id"]:
        cur.execute("SELECT * FROM discounts WHERE id = ? AND is_active = 1", (assigned["discount_id"],))
        candidates = cur.fetchall()
    else:
        # Check all active discounts
        cur.execute("SELECT * FROM discounts WHERE is_active = 1")
        candidates = cur.fetchall()

    best_discount_amount = 0.0
    best_discount_id = None

    for d in candidates:
        # Date eligibility
        s_date = parse_date(d["start_date"])
        e_date = parse_date(d["end_date"])
        if s_date and as_of < s_date:
            continue
        if e_date and as_of > e_date:
            continue

        # Usage limit check
        if d["usage_limit"] and d["usage_limit"] > 0 and d["times_used"] >= d["usage_limit"]:
            continue

        # Minimum thresholds
        if d["min_purchase_amount"] and subtotal < d["min_purchase_amount"]:
            continue
        if d["min_quantity"] and total_quantity < d["min_quantity"]:
            continue

        # Calculate discount value
        amount = 0.0
        if d["scope"] == "product" and d["target_product_id"]:
            # Apply to specific product lines only
            matching_subtotal = sum(l["line_subtotal"] for l in lines if l.get("product_id") == d["target_product_id"])
            if matching_subtotal > 0:
                if d["discount_type"] == "percentage":
                    amount = matching_subtotal * d["value"]
                else:
                    amount = min(d["value"], matching_subtotal)
        else:
            # Whole subscription
            if d["discount_type"] == "percentage":
                amount = subtotal * d["value"]
            else:
                amount = min(d["value"], subtotal)

        if amount > best_discount_amount:
            best_discount_amount = amount
            best_discount_id = d["id"]

    return round(best_discount_amount, 2), best_discount_id

def run_billing_engine(conn: sqlite3.Connection, as_of_date_str: Optional[str] = None) -> Dict[str, Any]:
    """
    Executes recurring billing:
    - Finds active subscriptions due on or before as_of_date.
    - Idempotency: Prevents duplicate billing for the same billing cycle.
    - Generates invoices with customer details, lines, automatic taxes, and discounts.
    - Updates next_billing_date and last_billed_date.
    - Closes expired subscriptions if auto_close is enabled on their plan.
    """
    as_of = parse_date(as_of_date_str) or date.today()
    cur = conn.cursor()

    # Query active subscriptions due
    cur.execute("""
        SELECT s.*, p.billing_frequency, p.auto_close, p.allow_renewal, u.email as customer_email, u.full_name as customer_name
        FROM subscriptions s
        JOIN plans p ON s.plan_id = p.id
        JOIN users u ON s.customer_id = u.id
        WHERE s.status = 'active'
          AND s.next_billing_date IS NOT NULL
          AND date(s.next_billing_date) <= date(?)
    """, (as_of.isoformat(),))
    
    due_subscriptions = cur.fetchall()
    
    created_invoices = []
    skipped_count = 0
    auto_closed_count = 0

    for sub in due_subscriptions:
        sub_id = sub["id"]
        customer_id = sub["customer_id"]
        billing_start = sub["next_billing_date"]
        billing_freq = sub["billing_frequency"]
        p_terms = sub["payment_terms"] or "net_30"

        # Check expiry and auto_close
        expiry = parse_date(sub["expiry_date"])
        start_d = parse_date(billing_start) or as_of
        
        if sub["auto_close"] and expiry and start_d >= expiry:
            # Auto-close subscription
            cur.execute("UPDATE subscriptions SET status = 'closed', updated_at = datetime('now') WHERE id = ?", (sub_id,))
            auto_closed_count += 1
            continue

        # Idempotency check: check if an invoice already exists for this subscription and billing_period_start
        cur.execute("""
            SELECT id, invoice_number FROM invoices 
            WHERE subscription_id = ? AND billing_period_start = ?
        """, (sub_id, billing_start))
        existing = cur.fetchone()
        if existing:
            # Already billed for this period!
            skipped_count += 1
            continue

        # Calculate next billing date
        next_b_date = compute_next_billing_date(start_d, billing_freq)
        billing_end = (next_b_date - timedelta(days=1)).isoformat()

        # Fetch lines for subscription
        cur.execute("""
            SELECT sl.*, p.name as product_name, pv.attribute_name, pv.attribute_value, pv.price_surcharge, t.rate as tax_rate
            FROM subscription_lines sl
            JOIN products p ON sl.product_id = p.id
            LEFT JOIN product_variants pv ON sl.variant_id = pv.id
            LEFT JOIN taxes t ON sl.tax_id = t.id
            WHERE sl.subscription_id = ?
        """, (sub_id,))
        lines_data = cur.fetchall()

        if not lines_data:
            # Empty subscription, skip
            continue

        # Calculate line amounts and taxes
        subtotal = 0.0
        tax_total = 0.0
        total_quantity = 0
        computed_lines = []

        for row in lines_data:
            qty = row["quantity"]
            total_quantity += qty
            base_p = row["unit_price"]
            surcharge = row["price_surcharge"] or 0.0
            effective_unit_price = base_p + surcharge
            line_sub = effective_unit_price * qty
            subtotal += line_sub

            t_rate = row["tax_rate"] if row["tax_rate"] is not None else 0.0
            line_tax = round(line_sub * t_rate, 2)
            tax_total += line_tax

            desc = row["product_name"]
            if row["attribute_value"]:
                desc += f" ({row['attribute_name']}: {row['attribute_value']})"

            computed_lines.append({
                "product_id": row["product_id"],
                "description": desc,
                "quantity": qty,
                "unit_price": effective_unit_price,
                "tax_rate": t_rate,
                "tax_amount": line_tax,
                "discount_amount": 0.0,
                "line_subtotal": line_sub,
                "total": line_sub + line_tax
            })

        # Evaluate discounts
        discount_amount, discount_id = evaluate_discounts_for_subscription(
            conn, sub_id, subtotal, total_quantity, computed_lines, as_of
        )

        final_total = max(0.0, round(subtotal + tax_total - discount_amount, 2))
        inv_num = generate_invoice_number(conn)
        due_d = compute_due_date(as_of, p_terms).isoformat()

        # Create Invoice in 'draft' or 'confirmed'
        cur.execute("""
            INSERT INTO invoices (
                invoice_number, subscription_id, customer_id, issue_date, due_date,
                subtotal, tax_amount, discount_amount, total_amount, amount_paid, balance_due,
                status, billing_period_start, billing_period_end, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0.0, ?, 'draft', ?, ?, ?)
        """, (
            inv_num, sub_id, customer_id, as_of.isoformat(), due_d,
            subtotal, tax_total, discount_amount, final_total, final_total,
            billing_start, billing_end, f"Automated billing for period {billing_start} to {billing_end}"
        ))
        inv_id = cur.lastrowid

        # Insert lines
        for cl in computed_lines:
            cur.execute("""
                INSERT INTO invoice_lines (
                    invoice_id, product_id, description, quantity, unit_price,
                    tax_rate, tax_amount, discount_amount, total
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                inv_id, cl["product_id"], cl["description"], cl["quantity"],
                cl["unit_price"], cl["tax_rate"], cl["tax_amount"], 0.0, cl["total"]
            ))

        # Record discount usage if applied
        if discount_id and discount_amount > 0:
            cur.execute("""
                INSERT INTO discount_usages (discount_id, subscription_id, invoice_id, applied_amount)
                VALUES (?, ?, ?, ?)
            """, (discount_id, sub_id, inv_id, discount_amount))
            cur.execute("UPDATE discounts SET times_used = times_used + 1 WHERE id = ?", (discount_id,))

        # Update Subscription next and last billing dates
        new_status = "active"
        if sub["auto_close"] and expiry and next_b_date >= expiry:
            new_status = "closed"

        cur.execute("""
            UPDATE subscriptions 
            SET last_billed_date = ?, next_billing_date = ?, status = ?, updated_at = datetime('now')
            WHERE id = ?
        """, (as_of.isoformat(), next_b_date.isoformat(), new_status, sub_id))

        created_invoices.append({
            "id": inv_id,
            "invoice_number": inv_num,
            "customer_name": sub["customer_name"],
            "subscription_number": sub["subscription_number"],
            "total_amount": final_total,
            "due_date": due_d
        })

    conn.commit()

    return {
        "as_of_date": as_of.isoformat(),
        "total_due_found": len(due_subscriptions),
        "invoices_created": created_invoices,
        "created_count": len(created_invoices),
        "skipped_count": skipped_count,
        "auto_closed_count": auto_closed_count
    }
