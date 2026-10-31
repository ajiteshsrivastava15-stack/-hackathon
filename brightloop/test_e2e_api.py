"""End-to-end API integration tests verifying all 7 Brightloop business scenes."""

import unittest
import json
import io
from server import BrightloopHandler, init_db, get_db

class MockServerRequest:
    def __init__(self, method, path, headers=None, body=None):
        self.method = method
        self.path = path
        self.headers = headers or {}
        self.body_bytes = json.dumps(body).encode('utf-8') if body else b""

class MockSocket:
    def __init__(self, request_bytes):
        self.rfile = io.BytesIO(request_bytes)
        self.output = io.BytesIO()

    def makefile(self, mode, *args, **kwargs):
        if 'r' in mode:
            return self.rfile
        return self.output

    def sendall(self, b):
        self.output.write(b)

class TestBrightloopE2E(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_db(force_reseed=True)

    def execute_request(self, method, path, headers=None, body=None):
        req_headers = headers or {}
        body_bytes = json.dumps(body).encode('utf-8') if body else b""
        if body_bytes:
            req_headers["Content-Length"] = str(len(body_bytes))
            req_headers["Content-Type"] = "application/json"

        # Format HTTP 1.1 request
        header_lines = [f"{method} {path} HTTP/1.1"]
        for k, v in req_headers.items():
            header_lines.append(f"{k}: {v}")
        header_lines.append("\r\n")

        full_req = "\r\n".join(header_lines).encode("utf-8") + body_bytes
        sock = MockSocket(full_req)

        # Initialize handler without listening socket
        handler = BrightloopHandler(sock, ("127.0.0.1", 8080), None)
        
        # Parse output
        output_bytes = sock.output.getvalue()
        parts = output_bytes.split(b"\r\n\r\n", 1)
        headers_raw = parts[0].decode('utf-8')
        body_raw = parts[1].decode('utf-8') if len(parts) > 1 else ""

        status_line = headers_raw.splitlines()[0]
        status_code = int(status_line.split()[1])

        try:
            json_body = json.loads(body_raw) if body_raw else None
        except Exception:
            json_body = body_raw

        return status_code, json_body

    # Scene 1: A new customer signs up & RBAC
    def test_scene_1_customer_signup_and_rbac(self):
        # 1. Invalid weak password (<=8 characters)
        status, res = self.execute_request("POST", "/api/auth/register", body={
            "email": "newuser@test.com",
            "password": "Weak1!",
            "full_name": "Test User",
            "company_name": "Test Co"
        })
        self.assertEqual(status, 400)
        self.assertIn("more than 8", res["error"])

        # 2. Valid password signup
        status, res = self.execute_request("POST", "/api/auth/register", body={
            "email": "newuser@test.com",
            "password": "ValidStrongPass2026!",
            "full_name": "Test User",
            "company_name": "Test Co"
        })
        self.assertEqual(status, 201)
        self.assertIn("token", res)
        self.assertEqual(res["user"]["role"], "customer")

        # 3. Duplicate email rejection
        status, res = self.execute_request("POST", "/api/auth/register", body={
            "email": "newuser@test.com",
            "password": "ValidStrongPass2026!",
            "full_name": "Another User"
        })
        self.assertEqual(status, 409)
        self.assertIn("already exists", res["error"])

        # 4. Forgot password reset link
        status, res = self.execute_request("POST", "/api/auth/forgot-password", body={
            "email": "newuser@test.com"
        })
        self.assertEqual(status, 200)
        self.assertIn("reset_link", res)
        self.assertIn("token", res)

        # 5. Staff creation by Customer (should be REJECTED 403)
        status, res = self.execute_request("POST", "/api/staff", headers={"X-Demo-Role": "customer"}, body={
            "full_name": "Illegal Staff",
            "email": "illegal@brightloop.com",
            "password": "ValidStrongPass2026!"
        })
        self.assertEqual(status, 403)

        # 6. Staff creation by Admin (should SUCCEED 201)
        status, res = self.execute_request("POST", "/api/staff", headers={"X-Demo-Role": "admin"}, body={
            "full_name": "James Bond",
            "email": "james.sales@brightloop.com",
            "role": "staff",
            "password": "ValidStrongPass2026!"
        })
        self.assertEqual(status, 201)

    # Scene 2: Launching a new plan with variants & lifecycle policies
    def test_scene_2_launching_plan_and_variants(self):
        # Admin creates product with variant (+560 surcharge)
        status, res = self.execute_request("POST", "/api/products", headers={"X-Demo-Role": "admin"}, body={
            "name": "Custom ERP Module",
            "type": "Software",
            "sales_price": 2000.0,
            "cost_price": 500.0,
            "variants": [
                {"attribute_name": "Brand", "attribute_value": "Odoo Integration", "price_surcharge": 560.0}
            ]
        })
        self.assertEqual(status, 201)

        # Admin creates Plan with lifecycle policies
        status, res = self.execute_request("POST", "/api/plans", headers={"X-Demo-Role": "admin"}, body={
            "name": "Custom Plan Monthly",
            "code": "PLAN-CUSTOM-M",
            "base_price": 2560.0,
            "billing_frequency": "monthly",
            "min_quantity": 1,
            "auto_close": 0,
            "allow_close_early": 1,
            "allow_pause": 1,
            "allow_renewal": 1
        })
        self.assertEqual(status, 201)

    # Scene 3: Turning a quote into a subscription
    def test_scene_3_turning_quote_into_subscription(self):
        # 1. Fetch templates
        status, templates = self.execute_request("GET", "/api/templates", headers={"X-Demo-Role": "staff"})
        self.assertEqual(status, 200)
        self.assertGreater(len(templates), 0)
        tmpl_id = templates[0]["id"]

        # 2. Instantiate quote from template
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE role = 'customer' LIMIT 1")
        customer_row = cur.fetchone()
        cust_id = customer_row["id"]
        conn.close()

        status, res = self.execute_request("POST", f"/api/templates/{tmpl_id}/create-quote", headers={"X-Demo-Role": "staff"}, body={
            "customer_id": cust_id
        })
        if status != 201:
            print("ERROR IN TEMPLATE CREATE QUOTE:", res)
        self.assertEqual(status, 201)
        sub_id = res["id"]
        self.assertIn("SUB-", res["subscription_number"])

        # 3. Advance Quote through stages: Quotation -> Confirmed -> Active
        status, res = self.execute_request("POST", f"/api/subscriptions/{sub_id}/status", headers={"X-Demo-Role": "staff"}, body={
            "status": "confirmed"
        })
        self.assertEqual(status, 200)

        status, res = self.execute_request("POST", f"/api/subscriptions/{sub_id}/status", headers={"X-Demo-Role": "staff"}, body={
            "status": "active"
        })
        self.assertEqual(status, 200)

    # Scene 4 & 5: Billing day, taxes, and automatic discounts
    def test_scene_4_and_5_billing_day_and_discounts(self):
        # Trigger recurring billing
        status, res = self.execute_request("POST", "/api/billing/run", headers={"X-Demo-Role": "staff"}, body={
            "as_of_date": "2026-10-31"
        })
        self.assertEqual(status, 200)
        self.assertIn("invoices_created", res)
        self.assertIn("skipped_count", res)

    # Scene 6: Payments & overdue receivables
    def test_scene_6_payments_and_overdue(self):
        # Get invoices
        status, invoices = self.execute_request("GET", "/api/invoices?status=confirmed", headers={"X-Demo-Role": "staff"})
        self.assertEqual(status, 200)
        self.assertGreater(len(invoices), 0)

        target_inv = invoices[0]
        # Record partial payment of $50
        status, res = self.execute_request("POST", "/api/payments", headers={"X-Demo-Role": "staff"}, body={
            "invoice_id": target_inv["id"],
            "amount": 50.0,
            "payment_method": "Credit Card",
            "note": "Partial test payment"
        })
        self.assertEqual(status, 201)
        self.assertEqual(res["amount_paid"], 50.0)
        self.assertGreater(res["new_balance_due"], 0)

    # Scene 7: Finance lead dashboard (<50ms)
    def test_scene_7_finance_dashboard(self):
        status, res = self.execute_request("GET", "/api/reports/dashboard", headers={"X-Demo-Role": "admin"})
        self.assertEqual(status, 200)
        self.assertIn("active_subscriptions", res)
        self.assertIn("mrr", res)
        self.assertIn("arr", res)
        self.assertIn("total_revenue", res)
        self.assertIn("outstanding_revenue", res)
        self.assertIn("overdue_invoices", res)
        self.assertGreater(res["active_subscriptions"], 0)

if __name__ == "__main__":
    unittest.main()
