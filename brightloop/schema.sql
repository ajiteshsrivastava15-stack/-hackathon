-- Brightloop Subscription Management System Schema
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    salt TEXT NOT NULL,
    full_name TEXT NOT NULL,
    company_name TEXT,
    role TEXT NOT NULL CHECK(role IN ('admin', 'staff', 'customer')),
    reset_token TEXT,
    reset_token_expiry TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    type TEXT NOT NULL DEFAULT 'Software',
    sales_price REAL NOT NULL DEFAULT 0.0,
    cost_price REAL NOT NULL DEFAULT 0.0,
    notes TEXT,
    is_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS product_variants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    attribute_name TEXT NOT NULL,
    attribute_value TEXT NOT NULL,
    price_surcharge REAL NOT NULL DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    code TEXT UNIQUE NOT NULL,
    base_price REAL NOT NULL DEFAULT 0.0,
    billing_frequency TEXT NOT NULL CHECK(billing_frequency IN ('daily', 'weekly', 'monthly', 'yearly')),
    min_quantity INTEGER NOT NULL DEFAULT 1,
    available_from TEXT NOT NULL,
    available_to TEXT,
    auto_close INTEGER NOT NULL DEFAULT 0,
    allow_close_early INTEGER NOT NULL DEFAULT 1,
    allow_pause INTEGER NOT NULL DEFAULT 1,
    allow_renewal INTEGER NOT NULL DEFAULT 1,
    is_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS quotation_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    plan_id INTEGER REFERENCES plans(id) ON DELETE SET NULL,
    validity_days INTEGER NOT NULL DEFAULT 30
);

CREATE TABLE IF NOT EXISTS quotation_template_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    template_id INTEGER NOT NULL REFERENCES quotation_templates(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    variant_id INTEGER REFERENCES product_variants(id) ON DELETE SET NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS taxes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    rate REAL NOT NULL, -- e.g. 0.10 for 10%
    is_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS discounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    discount_type TEXT NOT NULL CHECK(discount_type IN ('fixed', 'percentage')),
    value REAL NOT NULL, -- e.g. 50.0 for $50 or 0.15 for 15%
    min_purchase_amount REAL DEFAULT 0.0,
    min_quantity INTEGER DEFAULT 0,
    start_date TEXT,
    end_date TEXT,
    usage_limit INTEGER DEFAULT 0, -- 0 = unlimited
    times_used INTEGER NOT NULL DEFAULT 0,
    scope TEXT NOT NULL CHECK(scope IN ('subscription', 'product')),
    target_product_id INTEGER REFERENCES products(id) ON DELETE SET NULL,
    is_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subscription_number TEXT UNIQUE NOT NULL,
    customer_id INTEGER NOT NULL REFERENCES users(id),
    plan_id INTEGER NOT NULL REFERENCES plans(id),
    status TEXT NOT NULL CHECK(status IN ('draft', 'quotation', 'confirmed', 'active', 'paused', 'closed')),
    start_date TEXT NOT NULL,
    expiry_date TEXT,
    payment_terms TEXT NOT NULL DEFAULT 'net_30' CHECK(payment_terms IN ('immediate', 'net_15', 'net_30', 'net_60')),
    next_billing_date TEXT,
    last_billed_date TEXT,
    notes TEXT,
    created_by INTEGER REFERENCES users(id),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS subscription_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subscription_id INTEGER NOT NULL REFERENCES subscriptions(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id),
    variant_id INTEGER REFERENCES product_variants(id),
    quantity INTEGER NOT NULL DEFAULT 1,
    unit_price REAL NOT NULL DEFAULT 0.0,
    tax_id INTEGER REFERENCES taxes(id),
    discount_id INTEGER REFERENCES discounts(id),
    line_subtotal REAL NOT NULL DEFAULT 0.0,
    line_total REAL NOT NULL DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_number TEXT UNIQUE NOT NULL,
    subscription_id INTEGER REFERENCES subscriptions(id) ON DELETE SET NULL,
    customer_id INTEGER NOT NULL REFERENCES users(id),
    issue_date TEXT NOT NULL,
    due_date TEXT NOT NULL,
    subtotal REAL NOT NULL DEFAULT 0.0,
    tax_amount REAL NOT NULL DEFAULT 0.0,
    discount_amount REAL NOT NULL DEFAULT 0.0,
    total_amount REAL NOT NULL DEFAULT 0.0,
    amount_paid REAL NOT NULL DEFAULT 0.0,
    balance_due REAL NOT NULL DEFAULT 0.0,
    status TEXT NOT NULL CHECK(status IN ('draft', 'confirmed', 'paid', 'cancelled')),
    sent_at TEXT,
    billing_period_start TEXT,
    billing_period_end TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS invoice_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id INTEGER NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    product_id INTEGER REFERENCES products(id),
    description TEXT NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    unit_price REAL NOT NULL DEFAULT 0.0,
    tax_rate REAL NOT NULL DEFAULT 0.0,
    tax_amount REAL NOT NULL DEFAULT 0.0,
    discount_amount REAL NOT NULL DEFAULT 0.0,
    total REAL NOT NULL DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    payment_number TEXT UNIQUE NOT NULL,
    invoice_id INTEGER NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    customer_id INTEGER NOT NULL REFERENCES users(id),
    payment_method TEXT NOT NULL CHECK(payment_method IN ('Credit Card', 'Bank Transfer', 'Cash', 'Check', 'Online / Stripe')),
    amount REAL NOT NULL,
    payment_date TEXT NOT NULL,
    note TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS discount_usages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    discount_id INTEGER NOT NULL REFERENCES discounts(id) ON DELETE CASCADE,
    subscription_id INTEGER REFERENCES subscriptions(id) ON DELETE SET NULL,
    invoice_id INTEGER REFERENCES invoices(id) ON DELETE SET NULL,
    applied_amount REAL NOT NULL,
    applied_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Optimized Indexes for sub-2s query speeds
CREATE INDEX IF NOT EXISTS idx_subs_customer ON subscriptions(customer_id);
CREATE INDEX IF NOT EXISTS idx_subs_status ON subscriptions(status);
CREATE INDEX IF NOT EXISTS idx_subs_next_billing ON subscriptions(next_billing_date);
CREATE INDEX IF NOT EXISTS idx_invoices_customer ON invoices(customer_id);
CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(status);
CREATE INDEX IF NOT EXISTS idx_invoices_due ON invoices(due_date);
CREATE INDEX IF NOT EXISTS idx_invoices_sub ON invoices(subscription_id);
CREATE INDEX IF NOT EXISTS idx_payments_invoice ON payments(invoice_id);
