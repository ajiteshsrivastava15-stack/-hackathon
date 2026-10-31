"""Database layer, schema initializer, and seed data generator for Brightloop."""

import sqlite3
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
from auth import hash_password

DB_PATH = Path(__file__).parent / "brightloop.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"

def get_db(db_file: Optional[Path] = None) -> sqlite3.Connection:
    """Returns a sqlite3 connection configured with dict-like row factories."""
    target_db = db_file or DB_PATH
    conn = sqlite3.connect(str(target_db))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db(db_file: Optional[Path] = None, force_reseed: bool = False):
    """Initializes the database schema and seeds initial data if empty or forced."""
    target_db = db_file or DB_PATH
    
    conn = get_db(target_db)
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()

    # Check if users exist
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as cnt FROM users")
    count = cursor.fetchone()["cnt"]

    if count == 0 or force_reseed:
        seed_data(conn)
    
    conn.close()

def seed_data(conn: sqlite3.Connection):
    """Seeds realistic demo data covering all 7 specification scenes."""
    cur = conn.cursor()

    # Clear existing demo data
    tables = [
        "discount_usages", "payments", "invoice_lines", "invoices",
        "subscription_lines", "subscriptions", "quotation_template_lines",
        "quotation_templates", "product_variants", "products", "plans",
        "discounts", "taxes", "users"
    ]
    for tbl in tables:
        cur.execute(f"DELETE FROM {tbl};")

    # 1. Users (Admin, Staff, Customers)
    users_data = [
        ("admin@brightloop.com", "BrightAdmin2026!", "Arthur Dent (Admin)", "Brightloop Software HQ", "admin"),
        ("sarah.sales@brightloop.com", "BrightStaff2026!", "Sarah Connor (Sales Lead)", "Brightloop Software", "staff"),
        ("alex@acmecorp.com", "AcmeCustomer2026!", "Alex Mercer", "Acme Corporation", "customer"),
        ("maria@techwave.io", "TechWave2026!", "Maria Santos", "TechWave Media", "customer"),
        ("david@retailpro.com", "RetailPro2026!", "David Miller", "RetailPro Solutions", "customer"),
    ]

    user_ids = {}
    for email, pwd, name, comp, role in users_data:
        h, salt = hash_password(pwd)
        cur.execute("""
            INSERT INTO users (email, password_hash, salt, full_name, company_name, role)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (email, h, salt, name, comp, role))
        user_ids[email] = cur.lastrowid

    # 2. Taxes
    taxes_data = [
        ("Standard Sales Tax (10%)", 0.10),
        ("VAT (20%)", 0.20),
        ("Tax Exempt (0%)", 0.0),
    ]
    tax_ids = {}
    for name, rate in taxes_data:
        cur.execute("INSERT INTO taxes (name, rate) VALUES (?, ?)", (name, rate))
        tax_ids[name] = cur.lastrowid

    # 3. Products & Variants (e.g. Brand with Odoo variant adding 560 to price)
    products_data = [
        ("Brightloop Cloud Suite", "Software", 1200.0, 350.0, "Core business cloud application suite."),
        ("AI Insights & Automation Engine", "Add-on", 450.0, 80.0, "Predictive intelligence add-on."),
        ("Dedicated Priority Support", "Service", 600.0, 200.0, "24/7 dedicated engineer SLA."),
        ("Custom API Integration Seat", "Software", 150.0, 20.0, "High-throughput API token seat.")
    ]
    prod_ids = {}
    for name, ptype, s_price, c_price, notes in products_data:
        cur.execute("""
            INSERT INTO products (name, type, sales_price, cost_price, notes)
            VALUES (?, ?, ?, ?, ?)
        """, (name, ptype, s_price, c_price, notes))
        prod_ids[name] = cur.lastrowid

    # Variants
    variants_data = [
        # Odoo Brand variant: adds 560 to the price!
        (prod_ids["Brightloop Cloud Suite"], "Brand", "Standard Edition", 0.0),
        (prod_ids["Brightloop Cloud Suite"], "Brand", "Odoo Brand Integration", 560.0),
        (prod_ids["Brightloop Cloud Suite"], "Brand", "Enterprise White-label", 950.0),
        (prod_ids["AI Insights & Automation Engine"], "Tier", "Standard Tier", 0.0),
        (prod_ids["AI Insights & Automation Engine"], "Tier", "Unlimited Quota", 250.0),
    ]
    variant_ids = {}
    for pid, attr, val, surcharge in variants_data:
        cur.execute("""
            INSERT INTO product_variants (product_id, attribute_name, attribute_value, price_surcharge)
            VALUES (?, ?, ?, ?)
        """, (pid, attr, val, surcharge))
        variant_ids[f"{pid}_{val}"] = cur.lastrowid

    # 4. Plans (Daily, Weekly, Monthly, Yearly + Policies)
    today = datetime.now().date()
    plans_data = [
        ("Starter Monthly", "PLAN-START-M", 299.0, "monthly", 1, "2026-01-01", "2026-12-31", 0, 1, 1, 1),
        ("Growth Weekly", "PLAN-GROW-W", 89.0, "weekly", 1, "2026-01-01", "2026-12-31", 0, 1, 1, 1),
        ("Enterprise Annual", "PLAN-ENT-Y", 8500.0, "yearly", 5, "2026-01-01", "2027-12-31", 0, 0, 0, 1),
        ("Pilot Project 30-Day (Auto-Close)", "PLAN-PILOT", 199.0, "monthly", 1, "2026-01-01", "2026-12-31", 1, 1, 0, 0),
        ("Dev Daily Flex", "PLAN-DEV-D", 25.0, "daily", 1, "2026-01-01", "2026-12-31", 0, 1, 1, 1),
    ]
    plan_ids = {}
    for name, code, price, freq, min_q, af, at, ac, ce, ap, ar in plans_data:
        cur.execute("""
            INSERT INTO plans (name, code, base_price, billing_frequency, min_quantity, available_from, available_to, auto_close, allow_close_early, allow_pause, allow_renewal)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (name, code, price, freq, min_q, af, at, ac, ce, ap, ar))
        plan_ids[name] = cur.lastrowid

    # 5. Quotation Templates
    templates_data = [
        ("Standard SaaS Package (30 Days)", plan_ids["Starter Monthly"], 30),
        ("Enterprise Odoo Brand Rollout (15 Days)", plan_ids["Enterprise Annual"], 15),
    ]
    tmpl_ids = {}
    for name, pid, vdays in templates_data:
        cur.execute("""
            INSERT INTO quotation_templates (name, plan_id, validity_days)
            VALUES (?, ?, ?)
        """, (name, pid, vdays))
        tmpl_ids[name] = cur.lastrowid

    # Template Lines
    cur.execute("""
        INSERT INTO quotation_template_lines (template_id, product_id, variant_id, quantity, notes)
        VALUES (?, ?, ?, 1, 'Standard SaaS Suite')
    """, (tmpl_ids["Standard SaaS Package (30 Days)"], prod_ids["Brightloop Cloud Suite"], variant_ids[f"{prod_ids['Brightloop Cloud Suite']}_Standard Edition"]))

    cur.execute("""
        INSERT INTO quotation_template_lines (template_id, product_id, variant_id, quantity, notes)
        VALUES (?, ?, ?, 5, 'Includes 5 seats and Odoo brand customization')
    """, (tmpl_ids["Enterprise Odoo Brand Rollout (15 Days)"], prod_ids["Brightloop Cloud Suite"], variant_ids[f"{prod_ids['Brightloop Cloud Suite']}_Odoo Brand Integration"]))

    cur.execute("""
        INSERT INTO quotation_template_lines (template_id, product_id, variant_id, quantity, notes)
        VALUES (?, ?, NULL, 1, 'Enterprise 24/7 Support Addon')
    """, (tmpl_ids["Enterprise Odoo Brand Rollout (15 Days)"], prod_ids["Dedicated Priority Support"]))

    # 6. Discounts (Fixed, Percentage, Product/Subscription scopes, seat thresholds)
    discounts_data = [
        ("SEATPOWER15", "Volume Discount (15% for 5+ seats)", "percentage", 0.15, 0.0, 5, "2026-01-01", "2026-12-31", 50, 4, "subscription", None),
        ("WELCOME50", "Welcome Credit ($50 Off)", "fixed", 50.0, 200.0, 1, "2026-01-01", "2026-12-31", 100, 15, "subscription", None),
        ("ODOOSAVE100", "Odoo Brand Special ($100 Off Product)", "fixed", 100.0, 0.0, 1, "2026-01-01", "2026-12-31", 30, 2, "product", prod_ids["Brightloop Cloud Suite"]),
    ]
    disc_ids = {}
    for code, name, dtype, val, min_p, min_q, sd, ed, ulimit, tused, scope, target_p in discounts_data:
        cur.execute("""
            INSERT INTO discounts (code, name, discount_type, value, min_purchase_amount, min_quantity, start_date, end_date, usage_limit, times_used, scope, target_product_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (code, name, dtype, val, min_p, min_q, sd, ed, ulimit, tused, scope, target_p))
        disc_ids[code] = cur.lastrowid

    # 7. Subscriptions
    subs_data = [
        # Sub 1: Acme Corp, Starter Monthly, Active, Due for billing today
        ("SUB-2026-0001", user_ids["alex@acmecorp.com"], plan_ids["Starter Monthly"], "active", 
         (today - timedelta(days=60)).isoformat(), (today + timedelta(days=300)).isoformat(), "net_30", today.isoformat(), (today - timedelta(days=30)).isoformat(), "Acme main subscription"),
        # Sub 2: TechWave Media, Enterprise Annual, Active
        ("SUB-2026-0002", user_ids["maria@techwave.io"], plan_ids["Enterprise Annual"], "active",
         (today - timedelta(days=90)).isoformat(), (today + timedelta(days=275)).isoformat(), "net_30", (today + timedelta(days=275)).isoformat(), (today - timedelta(days=90)).isoformat(), "TechWave enterprise contract"),
        # Sub 3: RetailPro Solutions, Pilot Project (Auto-close), Active
        ("SUB-2026-0003", user_ids["david@retailpro.com"], plan_ids["Pilot Project 30-Day (Auto-Close)"], "active",
         (today - timedelta(days=25)).isoformat(), (today + timedelta(days=5)).isoformat(), "immediate", (today + timedelta(days=5)).isoformat(), (today - timedelta(days=25)).isoformat(), "Pilot project trial"),
        # Sub 4: Acme Corp, Growth Weekly, Quotation stage
        ("SUB-2026-0004", user_ids["alex@acmecorp.com"], plan_ids["Growth Weekly"], "quotation",
         today.isoformat(), (today + timedelta(days=180)).isoformat(), "net_15", today.isoformat(), None, "Pending customer approval"),
        # Sub 5: RetailPro, Starter Monthly, Draft stage
        ("SUB-2026-0005", user_ids["david@retailpro.com"], plan_ids["Starter Monthly"], "draft",
         (today + timedelta(days=7)).isoformat(), (today + timedelta(days=365)).isoformat(), "net_30", None, None, "Draft proposal"),
    ]

    sub_ids = {}
    for s_num, cid, pid, st, sdate, edate, pterms, n_bill, l_bill, notes in subs_data:
        cur.execute("""
            INSERT INTO subscriptions (subscription_number, customer_id, plan_id, status, start_date, expiry_date, payment_terms, next_billing_date, last_billed_date, notes, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (s_num, cid, pid, st, sdate, edate, pterms, n_bill, l_bill, notes, user_ids["sarah.sales@brightloop.com"]))
        sub_ids[s_num] = cur.lastrowid

    # Sub Lines for SUB-2026-0001 (Acme)
    # 1 x Brightloop Cloud Suite (Standard) @ $1200 + 10% tax = $1320
    tax_10 = tax_ids["Standard Sales Tax (10%)"]
    cur.execute("""
        INSERT INTO subscription_lines (subscription_id, product_id, variant_id, quantity, unit_price, tax_id, line_subtotal, line_total)
        VALUES (?, ?, ?, 1, 1200.0, ?, 1200.0, 1320.0)
    """, (sub_ids["SUB-2026-0001"], prod_ids["Brightloop Cloud Suite"], variant_ids[f"{prod_ids['Brightloop Cloud Suite']}_Standard Edition"], tax_10))

    # Sub Lines for SUB-2026-0002 (TechWave: 5x Odoo Brand = 5 * (1200 + 560 = 1760) = 8800 + Support 600 = 9400 - 15% volume discount)
    unit_p = 1200.0 + 560.0 # 1760.0
    subtotal = unit_p * 5   # 8800.0
    tax_20 = tax_ids["VAT (20%)"]
    disc_15 = disc_ids["SEATPOWER15"]
    cur.execute("""
        INSERT INTO subscription_lines (subscription_id, product_id, variant_id, quantity, unit_price, tax_id, discount_id, line_subtotal, line_total)
        VALUES (?, ?, ?, 5, ?, ?, ?, ?, ?)
    """, (sub_ids["SUB-2026-0002"], prod_ids["Brightloop Cloud Suite"], variant_ids[f"{prod_ids['Brightloop Cloud Suite']}_Odoo Brand Integration"], unit_p, tax_20, disc_15, subtotal, subtotal * 1.20))

    # 8. Invoices
    # INV-1: Acme Corp, Confirmed, OVERDUE! (due 15 days ago, balance $1320.00)
    inv1_issue = (today - timedelta(days=45)).isoformat()
    inv1_due = (today - timedelta(days=15)).isoformat()
    cur.execute("""
        INSERT INTO invoices (invoice_number, subscription_id, customer_id, issue_date, due_date, subtotal, tax_amount, discount_amount, total_amount, amount_paid, balance_due, status, billing_period_start, billing_period_end, notes)
        VALUES ('INV-2026-0001', ?, ?, ?, ?, 1200.0, 120.0, 0.0, 1320.0, 0.0, 1320.0, 'confirmed', ?, ?, 'Overdue recurring invoice')
    """, (sub_ids["SUB-2026-0001"], user_ids["alex@acmecorp.com"], inv1_issue, inv1_due, (today - timedelta(days=60)).isoformat(), (today - timedelta(days=30)).isoformat()))
    inv1_id = cur.lastrowid

    cur.execute("""
        INSERT INTO invoice_lines (invoice_id, product_id, description, quantity, unit_price, tax_rate, tax_amount, discount_amount, total)
        VALUES (?, ?, 'Brightloop Cloud Suite (Standard Edition)', 1, 1200.0, 0.10, 120.0, 0.0, 1320.0)
    """, (inv1_id, prod_ids["Brightloop Cloud Suite"]))

    # INV-2: TechWave Media, Paid, $10,560.00 total
    inv2_issue = (today - timedelta(days=90)).isoformat()
    inv2_due = (today - timedelta(days=60)).isoformat()
    cur.execute("""
        INSERT INTO invoices (invoice_number, subscription_id, customer_id, issue_date, due_date, subtotal, tax_amount, discount_amount, total_amount, amount_paid, balance_due, status, billing_period_start, billing_period_end, notes)
        VALUES ('INV-2026-0002', ?, ?, ?, ?, 8800.0, 1760.0, 0.0, 10560.0, 10560.0, 0.0, 'paid', ?, ?, 'Enterprise Annual Initial Invoice')
    """, (sub_ids["SUB-2026-0002"], user_ids["maria@techwave.io"], inv2_issue, inv2_due, (today - timedelta(days=90)).isoformat(), (today + timedelta(days=275)).isoformat()))
    inv2_id = cur.lastrowid

    cur.execute("""
        INSERT INTO invoice_lines (invoice_id, product_id, description, quantity, unit_price, tax_rate, tax_amount, discount_amount, total)
        VALUES (?, ?, 'Brightloop Cloud Suite (Odoo Brand Integration) - 5 Seats', 5, 1760.0, 0.20, 1760.0, 0.0, 10560.0)
    """, (inv2_id, prod_ids["Brightloop Cloud Suite"]))

    # 9. Payment for INV-2
    cur.execute("""
        INSERT INTO payments (payment_number, invoice_id, customer_id, payment_method, amount, payment_date, note)
        VALUES ('PAY-2026-0001', ?, ?, 'Bank Transfer', 10560.0, ?, 'Wire transfer ref #TX-9844012')
    """, (inv2_id, user_ids["maria@techwave.io"], (today - timedelta(days=70)).isoformat()))

    conn.commit()
    print("Brightloop demo database seeded successfully.")

if __name__ == "__main__":
    init_db(force_reseed=True)
