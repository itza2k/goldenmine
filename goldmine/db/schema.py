from __future__ import annotations

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL COLLATE NOCASE UNIQUE,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('owner', 'employee')),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at TEXT NOT NULL,
    created_by INTEGER
);

CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    address TEXT,
    government_id TEXT,
    created_at TEXT NOT NULL,
    created_by INTEGER,
    updated_at TEXT,
    updated_by INTEGER,
    FOREIGN KEY (created_by) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_customers_phone ON customers(phone);
CREATE INDEX IF NOT EXISTS idx_customers_name ON customers(name COLLATE NOCASE);

CREATE TABLE IF NOT EXISTS loans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    loan_number TEXT NOT NULL UNIQUE,
    customer_id INTEGER NOT NULL,
    gold_description TEXT NOT NULL,
    gold_weight REAL NOT NULL CHECK (gold_weight > 0),
    gold_purity TEXT,
    loan_amount REAL NOT NULL CHECK (loan_amount > 0),
    interest_rate REAL NOT NULL CHECK (interest_rate >= 0),
    start_date TEXT NOT NULL,
    due_date TEXT,
    remarks TEXT,
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'closed')),
    created_at TEXT NOT NULL,
    created_by INTEGER NOT NULL,
    updated_at TEXT,
    updated_by INTEGER,
    closed_at TEXT,
    closing_date TEXT,
    interest_collected REAL,
    total_received REAL,
    closing_remarks TEXT,
    closed_by INTEGER,
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    FOREIGN KEY (created_by) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_loans_customer ON loans(customer_id);
CREATE INDEX IF NOT EXISTS idx_loans_status ON loans(status);
CREATE INDEX IF NOT EXISTS idx_loans_start ON loans(start_date);
CREATE INDEX IF NOT EXISTS idx_loans_number ON loans(loan_number);

CREATE TABLE IF NOT EXISTS interest_rates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rate REAL NOT NULL UNIQUE CHECK (rate >= 0),
    label TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    sort_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    username TEXT NOT NULL,
    action TEXT NOT NULL,
    entity_type TEXT,
    entity_id TEXT,
    previous_value TEXT,
    new_value TEXT,
    reason TEXT
);

CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_log(created_at);
CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log(action);

CREATE TRIGGER IF NOT EXISTS audit_log_no_update
BEFORE UPDATE ON audit_log
BEGIN
    SELECT RAISE(ABORT, 'Audit records cannot be modified');
END;

CREATE TRIGGER IF NOT EXISTS audit_log_no_delete
BEFORE DELETE ON audit_log
BEGIN
    SELECT RAISE(ABORT, 'Audit records cannot be deleted');
END;

CREATE TRIGGER IF NOT EXISTS loans_no_delete
BEFORE DELETE ON loans
BEGIN
    SELECT RAISE(ABORT, 'Loans cannot be deleted');
END;

CREATE TABLE IF NOT EXISTS loan_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    loan_id INTEGER NOT NULL,
    jewellery_type TEXT NOT NULL,
    description TEXT,
    purity TEXT,
    gross_weight REAL NOT NULL DEFAULT 0,
    stone_weight REAL NOT NULL DEFAULT 0,
    net_weight REAL NOT NULL DEFAULT 0,
    condition_label TEXT,
    estimated_value REAL,
    FOREIGN KEY (loan_id) REFERENCES loans(id)
);

CREATE INDEX IF NOT EXISTS idx_items_loan ON loan_items(loan_id);

CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    loan_id INTEGER NOT NULL,
    payment_date TEXT NOT NULL,
    amount REAL NOT NULL CHECK (amount > 0),
    kind TEXT NOT NULL,
    method TEXT NOT NULL,
    remarks TEXT,
    created_at TEXT NOT NULL,
    created_by INTEGER NOT NULL,
    FOREIGN KEY (loan_id) REFERENCES loans(id)
);

CREATE INDEX IF NOT EXISTS idx_payments_loan ON payments(loan_id);

CREATE TRIGGER IF NOT EXISTS payments_no_delete
BEFORE DELETE ON payments
BEGIN
    SELECT RAISE(ABORT, 'Payments cannot be deleted');
END;

CREATE TABLE IF NOT EXISTS gold_rates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rate_date TEXT NOT NULL UNIQUE,
    rate_22k REAL NOT NULL,
    rate_24k REAL NOT NULL,
    set_by INTEGER,
    created_at TEXT NOT NULL
);
"""

DEFAULT_INTEREST_RATES = [
    (1.0, "1.0% per month", 1),
    (1.5, "1.5% per month", 2),
    (2.0, "2.0% per month", 3),
    (2.5, "2.5% per month", 4),
    (3.0, "3.0% per month", 5),
]

DEFAULT_SETTINGS = {
    "shop_name": "Goldmine",
    "shop_address": "",
    "shop_phone": "",
    "currency_symbol": "₹",
    "backup_retain_count": "14",
    "appearance_mode": "light",
    "due_soon_days": "7",
    "receipt_footer": "Thank you for your business. Ornaments released only against this ticket.",
    "setup_complete": "0",
    "default_ltv": "75",
    "gold_rate_22k": "0",
    "gold_rate_24k": "0",
    "min_interest_days": "15",
}
