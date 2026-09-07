from __future__ import annotations

import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from goldmine.db.connection import Database
from goldmine.exceptions import PermissionDenied, ValidationError
from goldmine.security.permissions import CurrentUser
from goldmine.services.audit import AuditService
from goldmine.services.auth import AuthService
from goldmine.services.customers import CustomerService
from goldmine.services.loans import LoanService
from goldmine.util import now, now_iso


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.tmp.name) / "t.db")
        self.audit = AuditService(self.db)
        self.auth = AuthService(self.db, self.audit)
        self.customers = CustomerService(self.db, self.audit)
        self.loans = LoanService(self.db, self.audit)
        self.owner = self.auth.create_owner("owner", "password123", "Owner", "Test Shop")
        self.emp = CurrentUser(id=2, username="ram", full_name="Ram", role="employee")
        self.db.execute(
            "INSERT INTO users (username, password_hash, full_name, role, is_active, created_at) VALUES (?,?,?,?,1,?)",
            ("ram", "x", "Ram", "employee", now_iso()),
        )
        self.db.commit()
        self.emp = CurrentUser(
            id=self.db.fetchone("SELECT id FROM users WHERE username='ram'")["id"],
            username="ram",
            full_name="Ram",
            role="employee",
        )

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def test_login_and_password_not_plain(self):
        user = self.auth.login("owner", "password123")
        self.assertEqual(user.role, "owner")
        row = self.db.fetchone("SELECT password_hash FROM users WHERE username='owner'")
        self.assertNotEqual(row["password_hash"], "password123")
        self.assertTrue(row["password_hash"].startswith("$2"))

    def test_employee_cannot_close_loan(self):
        cust = self.customers.create(self.emp, {"name": "Asha", "phone": "9876543210"})
        loan = self.loans.create(
            self.emp,
            {
                "customer_id": cust["id"],
                "gold_description": "Chain",
                "gold_weight": 10,
                "loan_amount": 50000,
                "interest_rate": 2.0,
                "start_date": now().date().isoformat(),
            },
        )
        with self.assertRaises(PermissionDenied):
            self.loans.close(
                self.emp,
                loan["id"],
                closing_date=now().date().isoformat(),
                interest_collected=100,
                total_received=50100,
                remarks="",
            )

    def test_locked_loan_blocks_employee(self):
        cust = self.customers.create(self.emp, {"name": "Asha", "phone": "9876543210"})
        loan = self.loans.create(
            self.emp,
            {
                "customer_id": cust["id"],
                "gold_description": "Chain",
                "gold_weight": 10,
                "loan_amount": 50000,
                "interest_rate": 2.0,
                "start_date": now().date().isoformat(),
            },
        )
        self.db.execute(
            "UPDATE loans SET created_at = ? WHERE id = ?",
            ((now() - timedelta(minutes=6)).replace(microsecond=0).isoformat(), loan["id"]),
        )
        self.db.commit()
        with self.assertRaises(PermissionDenied):
            self.loans.update(self.emp, loan["id"], {**loan, "loan_amount": 1})

    def test_audit_cannot_be_deleted(self):
        self.audit.record(self.owner, "login", entity_type="user", entity_id=1)
        with self.assertRaises(Exception):
            self.db.execute("DELETE FROM audit_log")
            self.db.commit()

    def test_interest_must_be_predefined(self):
        cust = self.customers.create(self.emp, {"name": "Asha", "phone": "9876543210"})
        with self.assertRaises(ValidationError):
            self.loans.create(
                self.emp,
                {
                    "customer_id": cust["id"],
                    "gold_description": "Ring",
                    "gold_weight": 5,
                    "loan_amount": 10000,
                    "interest_rate": 9.99,
                    "start_date": now().date().isoformat(),
                },
            )


if __name__ == "__main__":
    unittest.main()
