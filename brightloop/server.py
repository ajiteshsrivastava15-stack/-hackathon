"""Full-stack REST API Server for Brightloop Software Subscription Management."""

import http.server
import socketserver
import json
import urllib.parse
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional, List

from db import get_db, init_db, DB_PATH
from auth import (
    validate_password_complexity, hash_password, verify_password,
    create_session, get_session_user, destroy_session, generate_reset_token, SESSIONS
)
from billing_engine import run_billing_engine, compute_due_date, compute_next_billing_date

PORT = 8080
STATIC_DIR = Path(__file__).parent / "static"

class BrightloopHandler(http.server.SimpleHTTPRequestHandler):
    """Custom HTTP request handler with REST API routing and static file serving."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def send_json(self, data: Any, status: int = 200):
        """Sends a JSON response with CORS headers."""
        response_bytes = json.dumps(data, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Auth-Token, X-Demo-Role")
        self.end_headers()
        self.wfile.write(response_bytes)

    def parse_body(self) -> Dict[str, Any]:
        """Parses JSON request body."""
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return {}
        raw_body = self.rfile.read(content_length).decode("utf-8")
        try:
            return json.loads(raw_body)
        except Exception:
            return {}

    def get_current_user(self) -> Optional[Dict[str, Any]]:
        """Extracts user from auth token or demo header/query parameter."""
        # 1. Bearer / X-Auth-Token
        auth_header = self.headers.get("Authorization", "")
        token = None
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
        elif "X-Auth-Token" in self.headers:
            token = self.headers.get("X-Auth-Token")

        if token:
            user = get_session_user(token)
            if user:
                return user

        # 2. Support demo role override for rapid testing
        demo_role = self.headers.get("X-Demo-Role")
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)

        target_email = None
        if demo_role == "admin" or "demo_admin" in query:
            target_email = "admin@brightloop.com"
        elif demo_role == "staff" or "demo_staff" in query:
            target_email = "sarah.sales@brightloop.com"
        elif demo_role == "customer" or "demo_customer" in query:
            target_email = "alex@acmecorp.com"

        if target_email:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("SELECT id, email, full_name, company_name, role FROM users WHERE email = ?", (target_email,))
            row = cur.fetchone()
            conn.close()
            if row:
                return dict(row)

        return None

    def do_OPTIONS(self):
        """Handles CORS preflight."""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Auth-Token, X-Demo-Role")
        self.end_headers()

    # ========================== GET ROUTER ==========================
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if not path.startswith("/api/"):
            # Static files
            return super().do_GET()

        user = self.get_current_user()

        # Public endpoints
        if path == "/api/auth/me":
            if not user:
                return self.send_json({"authenticated": False, "user": None})
            return self.send_json({"authenticated": True, "user": user})

        # Protected endpoints
        if not user:
            return self.send_json({"error": "Unauthorized. Please log in."}, 401)

        conn = get_db()
        cur = conn.cursor()

        try:
            # 1. Staff Members (Admin only)
            if path == "/api/staff":
                if user["role"] != "admin":
                    return self.send_json({"error": "Only admins can view staff management."}, 403)
                cur.execute("SELECT id, email, full_name, company_name, role, created_at FROM users WHERE role IN ('admin', 'staff') ORDER BY id ASC")
                staff_list = [dict(r) for r in cur.fetchall()]
                return self.send_json(staff_list)

            # 2. Customers List (Admin/Staff only)
            elif path == "/api/customers":
                if user["role"] == "customer":
                    return self.send_json({"error": "Forbidden"}, 403)
                cur.execute("SELECT id, email, full_name, company_name, role, created_at FROM users WHERE role = 'customer' ORDER BY full_name ASC")
                return self.send_json([dict(r) for r in cur.fetchall()])

            # 3. Products & Variants
            elif path == "/api/products":
                cur.execute("SELECT * FROM products WHERE is_active = 1 ORDER BY name ASC")
                products = [dict(r) for r in cur.fetchall()]
                for p in products:
                    cur.execute("SELECT * FROM product_variants WHERE product_id = ?", (p["id"],))
                    p["variants"] = [dict(v) for v in cur.fetchall()]
                return self.send_json(products)

            # 4. Plans
            elif path == "/api/plans":
                cur.execute("SELECT * FROM plans WHERE is_active = 1 ORDER BY base_price ASC")
                return self.send_json([dict(r) for r in cur.fetchall()])

            # 5. Quotation Templates
            elif path == "/api/templates":
                cur.execute("""
                    SELECT qt.*, p.name as plan_name, p.billing_frequency, p.base_price
                    FROM quotation_templates qt
                    LEFT JOIN plans p ON qt.plan_id = p.id
                    ORDER BY qt.id ASC
                """)
                templates = [dict(r) for r in cur.fetchall()]
                for t in templates:
                    cur.execute("""
                        SELECT qtl.*, prod.name as product_name, pv.attribute_name, pv.attribute_value, pv.price_surcharge
                        FROM quotation_template_lines qtl
                        JOIN products prod ON qtl.product_id = prod.id
                        LEFT JOIN product_variants pv ON qtl.variant_id = pv.id
                        WHERE qtl.template_id = ?
                    """, (t["id"],))
                    t["lines"] = [dict(l) for l in cur.fetchall()]
                return self.send_json(templates)

            # 6. Taxes
            elif path == "/api/taxes":
                cur.execute("SELECT * FROM taxes WHERE is_active = 1")
                return self.send_json([dict(r) for r in cur.fetchall()])

            # 7. Discounts
            elif path == "/api/discounts":
                cur.execute("SELECT * FROM discounts ORDER BY id DESC")
                return self.send_json([dict(r) for r in cur.fetchall()])

            # 8. Subscriptions
            elif path == "/api/subscriptions":
                sql = """
                    SELECT s.*, u.full_name as customer_name, u.email as customer_email, u.company_name,
                           p.name as plan_name, p.billing_frequency, p.base_price, p.auto_close, p.allow_pause, p.allow_close_early, p.allow_renewal
                    FROM subscriptions s
                    JOIN users u ON s.customer_id = u.id
                    JOIN plans p ON s.plan_id = p.id
                """
                params = []
                if user["role"] == "customer":
                    sql += " WHERE s.customer_id = ?"
                    params.append(user["id"])
                elif "status" in query:
                    sql += " WHERE s.status = ?"
                    params.append(query["status"][0])

                sql += " ORDER BY s.id DESC"
                cur.execute(sql, params)
                subs = [dict(r) for r in cur.fetchall()]
                for s in subs:
                    cur.execute("""
                        SELECT sl.*, prod.name as product_name, pv.attribute_value, pv.price_surcharge, t.name as tax_name, t.rate as tax_rate
                        FROM subscription_lines sl
                        JOIN products prod ON sl.product_id = prod.id
                        LEFT JOIN product_variants pv ON sl.variant_id = pv.id
                        LEFT JOIN taxes t ON sl.tax_id = t.id
                        WHERE sl.subscription_id = ?
                    """, (s["id"],))
                    s["lines"] = [dict(l) for l in cur.fetchall()]
                return self.send_json(subs)

            elif path.startswith("/api/subscriptions/"):
                sub_id = int(path.split("/")[3])
                cur.execute("""
                    SELECT s.*, u.full_name as customer_name, u.email as customer_email, u.company_name,
                           p.name as plan_name, p.billing_frequency, p.base_price, p.auto_close, p.allow_pause, p.allow_close_early, p.allow_renewal
                    FROM subscriptions s
                    JOIN users u ON s.customer_id = u.id
                    JOIN plans p ON s.plan_id = p.id
                    WHERE s.id = ?
                """, (sub_id,))
                sub = cur.fetchone()
                if not sub:
                    return self.send_json({"error": "Subscription not found"}, 404)
                
                sub_dict = dict(sub)
                if user["role"] == "customer" and sub_dict["customer_id"] != user["id"]:
                    return self.send_json({"error": "Access denied"}, 403)

                cur.execute("""
                    SELECT sl.*, prod.name as product_name, pv.attribute_value, pv.price_surcharge, t.name as tax_name, t.rate as tax_rate
                    FROM subscription_lines sl
                    JOIN products prod ON sl.product_id = prod.id
                    LEFT JOIN product_variants pv ON sl.variant_id = pv.id
                    LEFT JOIN taxes t ON sl.tax_id = t.id
                    WHERE sl.subscription_id = ?
                """, (sub_id,))
                sub_dict["lines"] = [dict(l) for l in cur.fetchall()]

                cur.execute("SELECT * FROM invoices WHERE subscription_id = ? ORDER BY id DESC", (sub_id,))
                sub_dict["invoices"] = [dict(i) for r in cur.fetchall() for i in [r]]
                return self.send_json(sub_dict)

            # 9. Invoices
            elif path == "/api/invoices":
                sql = """
                    SELECT i.*, u.full_name as customer_name, u.email as customer_email, u.company_name, s.subscription_number
                    FROM invoices i
                    JOIN users u ON i.customer_id = u.id
                    LEFT JOIN subscriptions s ON i.subscription_id = s.id
                """
                params = []
                where_clauses = []
                if user["role"] == "customer":
                    where_clauses.append("i.customer_id = ?")
                    params.append(user["id"])
                
                if "status" in query:
                    where_clauses.append("i.status = ?")
                    params.append(query["status"][0])

                if "overdue_only" in query:
                    today_str = date.today().isoformat()
                    where_clauses.append("i.status = 'confirmed' AND i.due_date < ? AND i.balance_due > 0")
                    params.append(today_str)

                if where_clauses:
                    sql += " WHERE " + " AND ".join(where_clauses)

                sql += " ORDER BY i.id DESC"
                cur.execute(sql, params)
                invoices = [dict(r) for r in cur.fetchall()]
                return self.send_json(invoices)

            elif path.startswith("/api/invoices/"):
                inv_id = int(path.split("/")[3])
                cur.execute("""
                    SELECT i.*, u.full_name as customer_name, u.email as customer_email, u.company_name, s.subscription_number
                    FROM invoices i
                    JOIN users u ON i.customer_id = u.id
                    LEFT JOIN subscriptions s ON i.subscription_id = s.id
                    WHERE i.id = ?
                """, (inv_id,))
                inv = cur.fetchone()
                if not inv:
                    return self.send_json({"error": "Invoice not found"}, 404)
                inv_dict = dict(inv)
                if user["role"] == "customer" and inv_dict["customer_id"] != user["id"]:
                    return self.send_json({"error": "Access denied"}, 403)

                cur.execute("SELECT * FROM invoice_lines WHERE invoice_id = ?", (inv_id,))
                inv_dict["lines"] = [dict(l) for l in cur.fetchall()]

                cur.execute("SELECT * FROM payments WHERE invoice_id = ? ORDER BY id DESC", (inv_id,))
                inv_dict["payments"] = [dict(p) for p in cur.fetchall()]
                return self.send_json(inv_dict)

            # 10. Payments
            elif path == "/api/payments":
                sql = """
                    SELECT p.*, i.invoice_number, u.full_name as customer_name, u.email as customer_email
                    FROM payments p
                    JOIN invoices i ON p.invoice_id = i.id
                    JOIN users u ON p.customer_id = u.id
                """
                params = []
                if user["role"] == "customer":
                    sql += " WHERE p.customer_id = ?"
                    params.append(user["id"])
                sql += " ORDER BY p.id DESC"
                cur.execute(sql, params)
                return self.send_json([dict(r) for r in cur.fetchall()])

            # 11. Finance Reports Dashboard (<50ms performance)
            elif path == "/api/reports/dashboard":
                today_str = date.today().isoformat()
                
                # Active Subscriptions Count
                cur.execute("SELECT COUNT(*) as count FROM subscriptions WHERE status = 'active'")
                active_subs_count = cur.fetchone()["count"]

                # Total Revenue Collected (from all payments)
                cur.execute("SELECT COALESCE(SUM(amount), 0.0) as rev FROM payments")
                total_revenue = cur.fetchone()["rev"]

                # Outstanding / Owed Revenue (confirmed invoices balance_due)
                cur.execute("SELECT COALESCE(SUM(balance_due), 0.0) as owed FROM invoices WHERE status = 'confirmed' AND balance_due > 0")
                outstanding_revenue = cur.fetchone()["owed"]

                # Overdue Invoices
                cur.execute("""
                    SELECT COUNT(*) as cnt, COALESCE(SUM(balance_due), 0.0) as amount 
                    FROM invoices 
                    WHERE status = 'confirmed' AND due_date < ? AND balance_due > 0
                """, (today_str,))
                od = cur.fetchone()
                overdue_count = od["cnt"]
                overdue_amount = od["amount"]

                # Overdue Invoices List (for chasing)
                cur.execute("""
                    SELECT i.id, i.invoice_number, i.due_date, i.total_amount, i.balance_due, u.full_name as customer_name, u.email as customer_email
                    FROM invoices i
                    JOIN users u ON i.customer_id = u.id
                    WHERE i.status = 'confirmed' AND i.due_date < ? AND i.balance_due > 0
                    ORDER BY i.due_date ASC
                """, (today_str,))
                overdue_list = [dict(r) for r in cur.fetchall()]

                # MRR / ARR calculation across active subscriptions
                cur.execute("""
                    SELECT s.id, p.billing_frequency,
                           COALESCE((SELECT SUM(sl.unit_price * sl.quantity) FROM subscription_lines sl WHERE sl.subscription_id = s.id), p.base_price) as sub_total
                    FROM subscriptions s
                    JOIN plans p ON s.plan_id = p.id
                    WHERE s.status = 'active'
                """)
                mrr = 0.0
                for row in cur.fetchall():
                    freq = row["billing_frequency"]
                    st = row["sub_total"] or 0.0
                    if freq == "monthly":
                        mrr += st
                    elif freq == "yearly":
                        mrr += (st / 12.0)
                    elif freq == "weekly":
                        mrr += (st * 4.33)
                    elif freq == "daily":
                        mrr += (st * 30.0)
                
                arr = mrr * 12.0

                # Subscriptions by Status
                cur.execute("SELECT status, COUNT(*) as cnt FROM subscriptions GROUP BY status")
                status_counts = {r["status"]: r["cnt"] for r in cur.fetchall()}

                # Recent Payments
                cur.execute("""
                    SELECT p.*, i.invoice_number, u.full_name as customer_name
                    FROM payments p
                    JOIN invoices i ON p.invoice_id = i.id
                    JOIN users u ON p.customer_id = u.id
                    ORDER BY p.id DESC LIMIT 6
                """)
                recent_payments = [dict(r) for r in cur.fetchall()]

                return self.send_json({
                    "active_subscriptions": active_subs_count,
                    "total_revenue": round(total_revenue, 2),
                    "mrr": round(mrr, 2),
                    "arr": round(arr, 2),
                    "outstanding_revenue": round(outstanding_revenue, 2),
                    "overdue_count": overdue_count,
                    "overdue_amount": round(overdue_amount, 2),
                    "overdue_invoices": overdue_list,
                    "status_breakdown": status_counts,
                    "recent_payments": recent_payments
                })

            else:
                return self.send_json({"error": "Endpoint not found"}, 404)

        finally:
            conn.close()

    # ========================== POST ROUTER ==========================
    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        body = self.parse_body()
        user = self.get_current_user()

        conn = get_db()
        cur = conn.cursor()

        try:
            # 1. Register Account
            if path == "/api/auth/register":
                email = (body.get("email") or "").strip().lower()
                password = body.get("password") or ""
                full_name = (body.get("full_name") or "").strip()
                company_name = (body.get("company_name") or "").strip()

                if not email or not full_name:
                    return self.send_json({"error": "Email and Full Name are required."}, 400)

                valid, err_msg = validate_password_complexity(password)
                if not valid:
                    return self.send_json({"error": err_msg}, 400)

                # Check unique email
                cur.execute("SELECT id FROM users WHERE email = ?", (email,))
                if cur.fetchone():
                    return self.send_json({"error": "An account with this email address already exists."}, 409)

                pwd_hash, salt = hash_password(password)
                cur.execute("""
                    INSERT INTO users (email, password_hash, salt, full_name, company_name, role)
                    VALUES (?, ?, ?, ?, ?, 'customer')
                """, (email, pwd_hash, salt, full_name, company_name))
                user_id = cur.lastrowid
                conn.commit()

                user_dict = {
                    "id": user_id,
                    "email": email,
                    "full_name": full_name,
                    "company_name": company_name,
                    "role": "customer"
                }
                token = create_session(user_dict)
                return self.send_json({"token": token, "user": user_dict}, 201)

            # 2. Login
            elif path == "/api/auth/login":
                email = (body.get("email") or "").strip().lower()
                password = body.get("password") or ""

                cur.execute("SELECT * FROM users WHERE email = ?", (email,))
                row = cur.fetchone()
                if not row or not verify_password(password, row["password_hash"], row["salt"]):
                    return self.send_json({"error": "Invalid email or password."}, 401)

                user_dict = {
                    "id": row["id"],
                    "email": row["email"],
                    "full_name": row["full_name"],
                    "company_name": row["company_name"],
                    "role": row["role"]
                }
                token = create_session(user_dict)
                return self.send_json({"token": token, "user": user_dict})

            # 3. Forgot Password
            elif path == "/api/auth/forgot-password":
                email = (body.get("email") or "").strip().lower()
                cur.execute("SELECT id FROM users WHERE email = ?", (email,))
                row = cur.fetchone()
                if not row:
                    # Generic success message for privacy
                    return self.send_json({"message": "If the email is registered, a password reset link has been dispatched."})

                token, expiry = generate_reset_token()
                cur.execute("UPDATE users SET reset_token = ?, reset_token_expiry = ? WHERE id = ?", (token, expiry, row["id"]))
                conn.commit()
                reset_link = f"/reset-password?token={token}"
                return self.send_json({
                    "message": "Password reset link generated and dispatched to registered email.",
                    "reset_link": reset_link,
                    "token": token
                })

            # 4. Reset Password
            elif path == "/api/auth/reset-password":
                token = body.get("token") or ""
                new_password = body.get("new_password") or ""

                valid, err_msg = validate_password_complexity(new_password)
                if not valid:
                    return self.send_json({"error": err_msg}, 400)

                cur.execute("SELECT id, reset_token_expiry FROM users WHERE reset_token = ?", (token,))
                row = cur.fetchone()
                if not row:
                    return self.send_json({"error": "Invalid or expired reset token."}, 400)

                if row["reset_token_expiry"] and datetime.fromisoformat(row["reset_token_expiry"]) < datetime.now():
                    return self.send_json({"error": "Reset token has expired."}, 400)

                pwd_hash, salt = hash_password(new_password)
                cur.execute("UPDATE users SET password_hash = ?, salt = ?, reset_token = NULL, reset_token_expiry = NULL WHERE id = ?", (pwd_hash, salt, row["id"]))
                conn.commit()
                return self.send_json({"message": "Password has been successfully updated. You can now log in."})

            # 5. Add Staff Member (Admin only!)
            elif path == "/api/staff":
                if not user or user["role"] != "admin":
                    return self.send_json({"error": "Only administrators can add new staff members."}, 403)

                email = (body.get("email") or "").strip().lower()
                password = body.get("password") or ""
                full_name = (body.get("full_name") or "").strip()
                role = body.get("role") or "staff"

                if role not in ("staff", "admin"):
                    return self.send_json({"error": "Invalid role."}, 400)

                valid, err_msg = validate_password_complexity(password)
                if not valid:
                    return self.send_json({"error": err_msg}, 400)

                cur.execute("SELECT id FROM users WHERE email = ?", (email,))
                if cur.fetchone():
                    return self.send_json({"error": "An account with this email already exists."}, 409)

                pwd_hash, salt = hash_password(password)
                cur.execute("""
                    INSERT INTO users (email, password_hash, salt, full_name, company_name, role)
                    VALUES (?, ?, ?, ?, 'Brightloop Software', ?)
                """, (email, pwd_hash, salt, full_name, role))
                conn.commit()
                return self.send_json({"message": f"Staff member {full_name} created successfully.", "id": cur.lastrowid}, 201)

            # Protected write endpoints below
            if not user:
                return self.send_json({"error": "Unauthorized"}, 401)

            # 6. Create Product (Admin only)
            if path == "/api/products":
                if user["role"] != "admin":
                    return self.send_json({"error": "Only admins can add products."}, 403)
                cur.execute("""
                    INSERT INTO products (name, type, sales_price, cost_price, notes)
                    VALUES (?, ?, ?, ?, ?)
                """, (body.get("name"), body.get("type", "Software"), float(body.get("sales_price", 0)), float(body.get("cost_price", 0)), body.get("notes")))
                prod_id = cur.lastrowid

                # Optional variants
                for v in body.get("variants", []):
                    cur.execute("""
                        INSERT INTO product_variants (product_id, attribute_name, attribute_value, price_surcharge)
                        VALUES (?, ?, ?, ?)
                    """, (prod_id, v.get("attribute_name", "Variant"), v.get("attribute_value", "Standard"), float(v.get("price_surcharge", 0))))

                conn.commit()
                return self.send_json({"id": prod_id, "message": "Product created successfully"}, 201)

            # 7. Create Plan (Admin only)
            elif path == "/api/plans":
                if user["role"] != "admin":
                    return self.send_json({"error": "Only admins can add plans."}, 403)
                cur.execute("""
                    INSERT INTO plans (name, code, base_price, billing_frequency, min_quantity, available_from, available_to, auto_close, allow_close_early, allow_pause, allow_renewal)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    body.get("name"), body.get("code"), float(body.get("base_price", 0)),
                    body.get("billing_frequency", "monthly"), int(body.get("min_quantity", 1)),
                    body.get("available_from", date.today().isoformat()), body.get("available_to"),
                    int(body.get("auto_close", 0)), int(body.get("allow_close_early", 1)),
                    int(body.get("allow_pause", 1)), int(body.get("allow_renewal", 1))
                ))
                conn.commit()
                return self.send_json({"id": cur.lastrowid, "message": "Plan created successfully"}, 201)

            # 8. Create Quote from Template (1-Click Quotation)
            elif path.startswith("/api/templates/") and path.endswith("/create-quote"):
                tmpl_id = int(path.split("/")[3])
                customer_id = body.get("customer_id")
                if not customer_id:
                    if user["role"] == "customer":
                        customer_id = user["id"]
                    else:
                        return self.send_json({"error": "customer_id is required."}, 400)

                cur.execute("SELECT * FROM quotation_templates WHERE id = ?", (tmpl_id,))
                tmpl = cur.fetchone()
                if not tmpl:
                    return self.send_json({"error": "Template not found"}, 404)

                cur.execute("SELECT * FROM quotation_template_lines WHERE template_id = ?", (tmpl_id,))
                tmpl_lines = cur.fetchall()

                # Generate Sub Number
                cur.execute("SELECT COUNT(*) as cnt FROM subscriptions")
                sub_count = cur.fetchone()["cnt"] + 1
                sub_num = f"SUB-{date.today().year}-{sub_count:04d}"

                validity_days = tmpl["validity_days"] or 30
                start_d = date.today()
                expiry_d = start_d + timedelta(days=validity_days)

                cur.execute("""
                    INSERT INTO subscriptions (subscription_number, customer_id, plan_id, status, start_date, expiry_date, payment_terms, created_by)
                    VALUES (?, ?, ?, 'quotation', ?, ?, 'net_30', ?)
                """, (sub_num, customer_id, tmpl["plan_id"], start_d.isoformat(), expiry_d.isoformat(), user["id"]))
                sub_id = cur.lastrowid

                # Insert lines
                for tl in tmpl_lines:
                    cur.execute("SELECT sales_price FROM products WHERE id = ?", (tl["product_id"],))
                    prod_row = cur.fetchone()
                    base_p = prod_row["sales_price"] if prod_row else 0.0

                    surcharge = 0.0
                    if tl["variant_id"]:
                        cur.execute("SELECT price_surcharge FROM product_variants WHERE id = ?", (tl["variant_id"],))
                        var_row = cur.fetchone()
                        if var_row:
                            surcharge = var_row["price_surcharge"] or 0.0

                    effective_price = base_p + surcharge
                    line_sub = effective_price * tl["quantity"]

                    # Default tax (10% standard)
                    cur.execute("SELECT id, rate FROM taxes WHERE is_active = 1 LIMIT 1")
                    tax_row = cur.fetchone()
                    tax_id = tax_row["id"] if tax_row else None
                    tax_rate = tax_row["rate"] if tax_row else 0.0
                    line_tot = line_sub * (1.0 + tax_rate)

                    cur.execute("""
                        INSERT INTO subscription_lines (subscription_id, product_id, variant_id, quantity, unit_price, tax_id, line_subtotal, line_total)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (sub_id, tl["product_id"], tl["variant_id"], tl["quantity"], effective_price, tax_id, line_sub, line_tot))

                conn.commit()
                return self.send_json({"id": sub_id, "subscription_number": sub_num, "message": "Quotation created from template."}, 201)

            # 9. Create Subscription / Quote Directly
            elif path == "/api/subscriptions":
                customer_id = body.get("customer_id") or user["id"]
                plan_id = body.get("plan_id")
                status = body.get("status", "draft")
                start_date_str = body.get("start_date") or date.today().isoformat()
                expiry_date_str = body.get("expiry_date")
                payment_terms = body.get("payment_terms", "net_30")

                cur.execute("SELECT COUNT(*) as cnt FROM subscriptions")
                sub_count = cur.fetchone()["cnt"] + 1
                sub_num = f"SUB-{date.today().year}-{sub_count:04d}"

                next_b = start_date_str if status == "active" else None

                cur.execute("""
                    INSERT INTO subscriptions (subscription_number, customer_id, plan_id, status, start_date, expiry_date, payment_terms, next_billing_date, created_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (sub_num, customer_id, plan_id, status, start_date_str, expiry_date_str, payment_terms, next_b, user["id"]))
                sub_id = cur.lastrowid

                # Insert lines
                for l in body.get("lines", []):
                    prod_id = l.get("product_id")
                    var_id = l.get("variant_id")
                    qty = int(l.get("quantity", 1))
                    unit_p = float(l.get("unit_price", 0.0))
                    tax_id = l.get("tax_id")
                    sub_tot = unit_p * qty
                    cur.execute("""
                        INSERT INTO subscription_lines (subscription_id, product_id, variant_id, quantity, unit_price, tax_id, line_subtotal, line_total)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (sub_id, prod_id, var_id, qty, unit_p, tax_id, sub_tot, sub_tot))

                conn.commit()
                return self.send_json({"id": sub_id, "subscription_number": sub_num, "message": "Subscription created successfully."}, 201)

            # 10. Update Subscription Status (Lifecycle check against Plan Policies!)
            elif path.startswith("/api/subscriptions/") and path.endswith("/status"):
                sub_id = int(path.split("/")[3])
                target_status = body.get("status")

                cur.execute("""
                    SELECT s.*, p.allow_pause, p.allow_close_early, p.allow_renewal, p.auto_close
                    FROM subscriptions s
                    JOIN plans p ON s.plan_id = p.id
                    WHERE s.id = ?
                """, (sub_id,))
                sub = cur.fetchone()
                if not sub:
                    return self.send_json({"error": "Subscription not found"}, 404)

                # Check customer permissions
                if user["role"] == "customer" and sub["customer_id"] != user["id"]:
                    return self.send_json({"error": "Access denied"}, 403)

                # Policy Enforcement
                if target_status == "paused" and not sub["allow_pause"]:
                    return self.send_json({"error": "This plan's policy does not allow pausing."}, 400)
                if target_status == "closed" and not sub["allow_close_early"] and sub["expiry_date"] and date.today().isoformat() < sub["expiry_date"]:
                    return self.send_json({"error": "This plan's policy does not permit early closure."}, 400)

                # Next billing date initialization when activating
                next_b = sub["next_billing_date"]
                if target_status == "active" and not next_b:
                    next_b = date.today().isoformat()

                cur.execute("UPDATE subscriptions SET status = ?, next_billing_date = ?, updated_at = datetime('now') WHERE id = ?", (target_status, next_b, sub_id))
                conn.commit()
                return self.send_json({"message": f"Subscription status updated to {target_status}."})

            # 11. Run Billing Batch Engine
            elif path == "/api/billing/run":
                if user["role"] == "customer":
                    return self.send_json({"error": "Only staff or admins can trigger billing."}, 403)
                as_of_date = body.get("as_of_date")
                result = run_billing_engine(conn, as_of_date)
                return self.send_json(result)

            # 12. Confirm / Cancel Invoice Status
            elif path.startswith("/api/invoices/") and path.endswith("/status"):
                inv_id = int(path.split("/")[3])
                new_status = body.get("status")
                if user["role"] == "customer":
                    return self.send_json({"error": "Customers cannot modify invoice statuses."}, 403)

                cur.execute("UPDATE invoices SET status = ? WHERE id = ?", (new_status, inv_id))
                conn.commit()
                return self.send_json({"message": f"Invoice updated to {new_status}."})

            # 13. Send Invoice (Simulation)
            elif path.startswith("/api/invoices/") and path.endswith("/send"):
                inv_id = int(path.split("/")[3])
                now_str = datetime.now().isoformat()
                cur.execute("UPDATE invoices SET sent_at = ? WHERE id = ?", (now_str, inv_id))
                conn.commit()
                return self.send_json({"message": "Invoice sent to customer registered email address.", "sent_at": now_str})

            # 14. Record Payment against Invoice
            elif path == "/api/payments":
                inv_id = body.get("invoice_id")
                amount = float(body.get("amount", 0.0))
                method = body.get("payment_method", "Credit Card")
                note = body.get("note", "")

                cur.execute("SELECT * FROM invoices WHERE id = ?", (inv_id,))
                inv = cur.fetchone()
                if not inv:
                    return self.send_json({"error": "Invoice not found"}, 404)

                if user["role"] == "customer" and inv["customer_id"] != user["id"]:
                    return self.send_json({"error": "Access denied"}, 403)

                if amount <= 0:
                    return self.send_json({"error": "Payment amount must be greater than 0."}, 400)

                # Generate Payment Number
                cur.execute("SELECT COUNT(*) as cnt FROM payments")
                p_cnt = cur.fetchone()["cnt"] + 1
                pay_num = f"PAY-{date.today().year}-{p_cnt:04d}"
                pay_date = body.get("payment_date") or date.today().isoformat()

                cur.execute("""
                    INSERT INTO payments (payment_number, invoice_id, customer_id, payment_method, amount, payment_date, note)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (pay_num, inv_id, inv["customer_id"], method, amount, pay_date, note))

                # Update invoice paid & balance due
                new_paid = round(inv["amount_paid"] + amount, 2)
                new_balance = max(0.0, round(inv["total_amount"] - new_paid, 2))
                new_inv_status = "paid" if new_balance <= 0.0 else "confirmed"

                cur.execute("""
                    UPDATE invoices SET amount_paid = ?, balance_due = ?, status = ? WHERE id = ?
                """, (new_paid, new_balance, new_inv_status, inv_id))

                conn.commit()
                return self.send_json({
                    "payment_number": pay_num,
                    "amount_paid": amount,
                    "new_balance_due": new_balance,
                    "invoice_status": new_inv_status,
                    "message": "Payment recorded successfully."
                }, 201)

            # 15. Create Discount Rule (Admin only!)
            elif path == "/api/discounts":
                if user["role"] != "admin":
                    return self.send_json({"error": "Only admins can create discount rules."}, 403)

                code = (body.get("code") or "").strip().upper()
                name = (body.get("name") or "").strip()
                dtype = body.get("discount_type", "percentage")
                val = float(body.get("value", 0.0))
                min_p = float(body.get("min_purchase_amount", 0.0))
                min_q = int(body.get("min_quantity", 0))
                s_date = body.get("start_date")
                e_date = body.get("end_date")
                ulimit = int(body.get("usage_limit", 0))
                scope = body.get("scope", "subscription")
                target_p = body.get("target_product_id")

                cur.execute("""
                    INSERT INTO discounts (code, name, discount_type, value, min_purchase_amount, min_quantity, start_date, end_date, usage_limit, times_used, scope, target_product_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
                """, (code, name, dtype, val, min_p, min_q, s_date, e_date, ulimit, scope, target_p))
                conn.commit()
                return self.send_json({"id": cur.lastrowid, "message": "Discount rule created successfully."}, 201)

            # 16. Create Tax Rule (Admin only!)
            elif path == "/api/taxes":
                if user["role"] != "admin":
                    return self.send_json({"error": "Only admins can create tax rules."}, 403)

                name = body.get("name")
                rate = float(body.get("rate", 0.0))
                cur.execute("INSERT INTO taxes (name, rate) VALUES (?, ?)", (name, rate))
                conn.commit()
                return self.send_json({"id": cur.lastrowid, "message": "Tax rule created successfully."}, 201)

            # 17. Reseed Demo Database
            elif path == "/api/admin/reseed":
                if user["role"] != "admin":
                    return self.send_json({"error": "Only admins can reseed database."}, 403)
                init_db(force_reseed=True)
                return self.send_json({"message": "Demo database reseeded successfully."})

            else:
                return self.send_json({"error": "Endpoint not found"}, 404)

        except Exception as e:
            return self.send_json({"error": str(e)}, 500)
        finally:
            conn.close()

def run_server(port: int = PORT):
    init_db()
    server_address = ("", port)
    httpd = socketserver.TCPServer(server_address, BrightloopHandler)
    print(f"Brightloop Subscription Platform running at http://localhost:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
        httpd.server_close()

if __name__ == "__main__":
    run_server()
