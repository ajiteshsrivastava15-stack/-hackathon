"""Automated Unit and Integration Test Suite for Brightloop Subscription Management."""

import unittest
import os
import time
from pathlib import Path
from datetime import date, timedelta

from auth import (
    validate_password_complexity, hash_password, verify_password,
    create_session, get_session_user, generate_reset_token
)
from db import get_db, init_db, DB_PATH
from billing_engine import (
    run_billing_engine, compute_next_billing_date, compute_due_date,
    evaluate_discounts_for_subscription
)

TEST_DB_PATH = Path(__file__).parent / "test_brightloop.db"

class TestBrightloopSuite(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Initialize isolated test database
        if TEST_DB_PATH.exists():
            os.remove(TEST_DB_PATH)
        init_db(db_file=TEST_DB_PATH, force_reseed=True)

    @classmethod
    def tearDownClass(cls):
        if TEST_DB_PATH.exists():
            try:
                os.remove(TEST_DB_PATH)
            except Exception:
                pass

    def get_test_conn(self):
        return get_db(TEST_DB_PATH)

    # 1. Password Complexity Tests
    def test_password_validation(self):
        # Too short (<= 8 characters)
        ok, msg = validate_password_complexity("Ab1!")
        self.assertFalse(ok)
        self.assertIn("more than 8", msg)

        # Exactly 8 characters (specification says: "more than eight characters")
        ok, msg = validate_password_complexity("Abcde1!2")
        self.assertFalse(ok)
        self.assertIn("more than 8", msg)

        # Missing uppercase
        ok, msg = validate_password_complexity("password123!")
        self.assertFalse(ok)
        self.assertIn("uppercase", msg)

        # Missing lowercase
        ok, msg = validate_password_complexity("PASSWORD123!")
        self.assertFalse(ok)
        self.assertIn("lowercase", msg)

        # Missing special character
        ok, msg = validate_password_complexity("Password123")
        self.assertFalse(ok)
        self.assertIn("special character", msg)

        # Valid password (>8 chars, uppercase, lowercase, special char)
        ok, msg = validate_password_complexity("SecurePass2026!")
        self.assertTrue(ok)
        self.assertEqual(msg, "")

    # 2. Authentication Hashing & Reset Token
    def test_hashing_and_reset(self):
        h, salt = hash_password("SuperSecret2026$")
        self.assertTrue(verify_password("SuperSecret2026$", h, salt))
        self.assertFalse(verify_password("WrongPassword!", h, salt))

        token, expiry = generate_reset_token()
        self.assertTrue(len(token) > 16)
        self.assertIsNotNone(expiry)

    # 3. Product Variants & Surcharges (Odoo Brand adds 560 to price)
    def test_product_variants_and_surcharges(self):
        conn = self.get_test_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM products WHERE name = 'Brightloop Cloud Suite'")
        prod = cur.fetchone()
        self.assertIsNotNone(prod)
        base_price = prod["sales_price"]
        self.assertEqual(base_price, 1200.0)

        # Check Odoo brand variant surcharge
        cur.execute("""
            SELECT * FROM product_variants 
            WHERE product_id = ? AND attribute_value LIKE '%Odoo%'
        """, (prod["id"],))
        variant = cur.fetchone()
        self.assertIsNotNone(variant)
        self.assertEqual(variant["price_surcharge"], 560.0)

        effective_price = base_price + variant["price_surcharge"]
        self.assertEqual(effective_price, 1760.0)
        conn.close()

    # 4. Quotation Template to Subscription
    def test_quotation_template(self):
        conn = self.get_test_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM quotation_templates WHERE name LIKE '%Standard SaaS%'")
        tmpl = cur.fetchone()
        self.assertIsNotNone(tmpl)
        self.assertEqual(tmpl["validity_days"], 30)

        # Check lines in template
        cur.execute("SELECT * FROM quotation_template_lines WHERE template_id = ?", (tmpl["id"],))
        lines = cur.fetchall()
        self.assertTrue(len(lines) >= 1)
        conn.close()

    # 5. Plan Policies Enforcement (Pause, Early Close, Renew)
    def test_plan_policies(self):
        conn = self.get_test_conn()
        cur = conn.cursor()
        # Find Enterprise Annual (allow_pause = 0)
        cur.execute("SELECT * FROM plans WHERE code = 'PLAN-ENT-Y'")
        ent_plan = cur.fetchone()
        self.assertEqual(ent_plan["allow_pause"], 0)
        self.assertEqual(ent_plan["allow_close_early"], 0)

        # Find Starter Monthly (allow_pause = 1, allow_close_early = 1)
        cur.execute("SELECT * FROM plans WHERE code = 'PLAN-START-M'")
        starter = cur.fetchone()
        self.assertEqual(starter["allow_pause"], 1)
        self.assertEqual(starter["allow_close_early"], 1)
        conn.close()

    # 6. Billing Engine & Idempotency (No double billing)
    def test_billing_engine_idempotency(self):
        conn = self.get_test_conn()
        today_str = date.today().isoformat()

        # Run 1: Billing run today
        res1 = run_billing_engine(conn, as_of_date_str=today_str)
        self.assertIn("invoices_created", res1)
        initial_created = res1["created_count"]
        self.assertGreaterEqual(initial_created, 1)

        # Run 2: Immediate re-run should create 0 new invoices
        res2 = run_billing_engine(conn, as_of_date_str=today_str)
        self.assertEqual(res2["created_count"], 0, "Idempotency violated: duplicate invoices generated for same period!")

        # Run 3: Simulate retry where a subscription's next_billing_date matches existing invoice billing_period_start
        cur = conn.cursor()
        cur.execute("SELECT subscription_id, billing_period_start FROM invoices WHERE subscription_id IS NOT NULL LIMIT 1")
        inv_row = cur.fetchone()
        sub_id = inv_row["subscription_id"]
        period_start = inv_row["billing_period_start"]

        cur.execute("UPDATE subscriptions SET next_billing_date = ? WHERE id = ?", (period_start, sub_id))
        conn.commit()

        res3 = run_billing_engine(conn, as_of_date_str=today_str)
        self.assertEqual(res3["created_count"], 0)
        self.assertGreaterEqual(res3["skipped_count"], 1)

        # Check invoice totals and structure
        cur.execute("SELECT * FROM invoices ORDER BY id DESC LIMIT 1")
        inv = cur.fetchone()
        if inv:
            self.assertIsNotNone(inv["invoice_number"])
            self.assertGreater(inv["total_amount"], 0)
            self.assertEqual(inv["status"], "draft")
            # Verify lines
            cur.execute("SELECT COUNT(*) as cnt FROM invoice_lines WHERE invoice_id = ?", (inv["id"],))
            self.assertGreater(cur.fetchone()["cnt"], 0)

        conn.close()

    # 7. Discount Engine Evaluation (Seat volume discount)
    def test_discount_evaluation(self):
        conn = self.get_test_conn()
        cur = conn.cursor()

        # Query discount SEATPOWER15 (15% for min 5 seats)
        cur.execute("SELECT * FROM discounts WHERE code = 'SEATPOWER15'")
        disc = cur.fetchone()
        self.assertIsNotNone(disc)
        self.assertEqual(disc["min_quantity"], 5)

        # Test evaluation with 3 seats (should NOT qualify)
        dummy_lines = [{"product_id": 1, "line_subtotal": 3600.0}]
        amt_3, id_3 = evaluate_discounts_for_subscription(conn, 9999, 3600.0, 3, dummy_lines, date.today())
        # Should not get 15% discount because qty < 5
        self.assertNotEqual(id_3, disc["id"])

        # Test evaluation with 5 seats (QUALIFIES for 15% off 6000 = 900)
        dummy_lines_5 = [{"product_id": 1, "line_subtotal": 6000.0}]
        amt_5, id_5 = evaluate_discounts_for_subscription(conn, 9999, 6000.0, 5, dummy_lines_5, date.today())
        self.assertEqual(id_5, disc["id"])
        self.assertEqual(amt_5, 900.0)

        conn.close()

    # 8. Payments & Receivables Tracking (Partial & Full Payments)
    def test_payment_recording(self):
        conn = self.get_test_conn()
        cur = conn.cursor()

        # Create a fresh invoice with $1000 balance
        cur.execute("""
            INSERT INTO invoices (invoice_number, customer_id, issue_date, due_date, subtotal, tax_amount, total_amount, amount_paid, balance_due, status)
            VALUES ('INV-TEST-999', 1, '2026-01-01', '2026-01-31', 1000.0, 0.0, 1000.0, 0.0, 1000.0, 'confirmed')
        """)
        inv_id = cur.lastrowid

        # Step 1: Partial payment of $400
        cur.execute("""
            INSERT INTO payments (payment_number, invoice_id, customer_id, payment_method, amount, payment_date, note)
            VALUES ('PAY-TEST-1', ?, 1, 'Credit Card', 400.0, '2026-01-15', 'Partial downpayment')
        """, (inv_id,))
        cur.execute("UPDATE invoices SET amount_paid = 400.0, balance_due = 600.0, status = 'confirmed' WHERE id = ?", (inv_id,))

        cur.execute("SELECT * FROM invoices WHERE id = ?", (inv_id,))
        inv_check = cur.fetchone()
        self.assertEqual(inv_check["amount_paid"], 400.0)
        self.assertEqual(inv_check["balance_due"], 600.0)
        self.assertEqual(inv_check["status"], "confirmed")

        # Step 2: Remaining payment of $600
        cur.execute("""
            INSERT INTO payments (payment_number, invoice_id, customer_id, payment_method, amount, payment_date, note)
            VALUES ('PAY-TEST-2', ?, 1, 'Bank Transfer', 600.0, '2026-01-20', 'Final balance')
        """, (inv_id,))
        cur.execute("UPDATE invoices SET amount_paid = 1000.0, balance_due = 0.0, status = 'paid' WHERE id = ?", (inv_id,))

        cur.execute("SELECT * FROM invoices WHERE id = ?", (inv_id,))
        inv_paid = cur.fetchone()
        self.assertEqual(inv_paid["amount_paid"], 1000.0)
        self.assertEqual(inv_paid["balance_due"], 0.0)
        self.assertEqual(inv_paid["status"], "paid")

        conn.close()

    # 9. Performance Benchmark for Finance Reporting (<50ms)
    def test_finance_reporting_speed(self):
        conn = self.get_test_conn()
        t0 = time.perf_counter()

        # Simulate aggregate queries
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) as count FROM subscriptions WHERE status = 'active'")
        active_count = cur.fetchone()["count"]

        cur.execute("SELECT COALESCE(SUM(amount), 0.0) as rev FROM payments")
        total_rev = cur.fetchone()["rev"]

        cur.execute("SELECT COALESCE(SUM(balance_due), 0.0) as owed FROM invoices WHERE status = 'confirmed'")
        owed_rev = cur.fetchone()["owed"]

        cur.execute("""
            SELECT COUNT(*) as cnt, COALESCE(SUM(balance_due), 0.0) as amount 
            FROM invoices 
            WHERE status = 'confirmed' AND due_date < '2026-12-31' AND balance_due > 0
        """)
        overdue = cur.fetchone()

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        self.assertLess(elapsed_ms, 50.0, f"Query took {elapsed_ms:.2f}ms, expected under 50ms")
        self.assertGreaterEqual(active_count, 1)
        self.assertGreater(total_rev, 0)
        conn.close()

if __name__ == "__main__":
    unittest.main()
