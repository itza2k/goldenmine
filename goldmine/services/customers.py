from __future__ import annotations

import re

from goldmine.db.connection import Database, row_to_dict, rows_to_dicts
from goldmine.exceptions import NotFoundError, PermissionDenied, ValidationError
from goldmine.security.permissions import CurrentUser, require_user
from goldmine.services.audit import AuditService
from goldmine.util import now_iso


PHONE_RE = re.compile(r"^[0-9+\-\s()]{7,20}$")


class CustomerService:
    def __init__(self, db: Database, audit: AuditService) -> None:
        self.db = db
        self.audit = audit

    def get(self, customer_id: int) -> dict:
        row = self.db.fetchone("SELECT * FROM customers WHERE id = ?", (customer_id,))
        data = row_to_dict(row)
        if not data:
            raise NotFoundError("Customer not found.")
        return data

    def search(self, query: str) -> list[dict]:
        q = (query or "").strip()
        if not q:
            rows = self.db.fetchall(
                "SELECT * FROM customers ORDER BY created_at DESC LIMIT 200"
            )
        else:
            like = f"%{q}%"
            rows = self.db.fetchall(
                """
                SELECT * FROM customers
                WHERE name LIKE ? COLLATE NOCASE OR phone LIKE ?
                ORDER BY name COLLATE NOCASE
                LIMIT 200
                """,
                (like, like),
            )
        return rows_to_dicts(rows)

    def has_locked_loans(self, customer_id: int, edit_window_seconds: int) -> bool:
        from datetime import timedelta

        from goldmine.util import now, parse_dt

        rows = self.db.fetchall("SELECT created_at FROM loans WHERE customer_id = ?", (customer_id,))
        cutoff = now()
        for row in rows:
            created = parse_dt(row["created_at"])
            if cutoff - created > timedelta(seconds=edit_window_seconds):
                return True
        return False

    def create(self, user: CurrentUser, data: dict) -> dict:
        require_user(user)
        payload = self._validate(data, creating=True)
        existing = self.db.fetchone("SELECT id FROM customers WHERE phone = ?", (payload["phone"],))
        if existing:
            raise ValidationError("A customer with this phone number already exists. Search and reuse that profile.")
        self.db.execute(
            """
            INSERT INTO customers (name, phone, address, government_id, title, id_proof_type, nominee_name, created_at, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["name"],
                payload["phone"],
                payload["address"],
                payload["government_id"],
                payload["title"],
                payload["id_proof_type"],
                payload["nominee_name"],
                now_iso(),
                user.id,
            ),
        )
        self.db.commit()
        customer_id = self.db.fetchone("SELECT last_insert_rowid() AS id")["id"]
        created = self.get(customer_id)
        self.audit.record(user, "customer.create", entity_type="customer", entity_id=customer_id, new=created)
        return created

    def update(self, user: CurrentUser, customer_id: int, data: dict, *, edit_window_seconds: int) -> dict:
        require_user(user)
        current = self.get(customer_id)
        if user.is_employee and self.has_locked_loans(customer_id, edit_window_seconds):
            raise PermissionDenied(
                "This customer has a locked loan. Employees cannot change customer details after the 5-minute window."
            )
        payload = self._validate(data, creating=False)
        if payload["phone"] != current["phone"]:
            clash = self.db.fetchone(
                "SELECT id FROM customers WHERE phone = ? AND id != ?",
                (payload["phone"], customer_id),
            )
            if clash:
                raise ValidationError("Another customer already uses this phone number.")
        self.db.execute(
            """
            UPDATE customers
            SET name = ?, phone = ?, address = ?, government_id = ?, title = ?, id_proof_type = ?, nominee_name = ?, updated_at = ?, updated_by = ?
            WHERE id = ?
            """,
            (
                payload["name"],
                payload["phone"],
                payload["address"],
                payload["government_id"],
                payload["title"],
                payload["id_proof_type"],
                payload["nominee_name"],
                now_iso(),
                user.id,
                customer_id,
            ),
        )
        self.db.commit()
        updated = self.get(customer_id)
        self.audit.record(
            user,
            "customer.update",
            entity_type="customer",
            entity_id=customer_id,
            previous=current,
            new=updated,
        )
        return updated

    def _validate(self, data: dict, creating: bool) -> dict:
        name = (data.get("name") or "").strip()
        phone = re.sub(r"\s+", "", (data.get("phone") or "").strip())
        address = (data.get("address") or "").strip() or None
        gov = (data.get("government_id") or "").strip() or None
        title = (data.get("title") or "Mr").strip()
        id_type = (data.get("id_proof_type") or "").strip() or None
        nominee = (data.get("nominee_name") or "").strip() or None
        if not name:
            raise ValidationError("Customer name is required.")
        if len(name) < 2:
            raise ValidationError("Enter a valid customer name.")
        if not phone:
            raise ValidationError("Phone number is required.")
        if not PHONE_RE.match(phone):
            raise ValidationError("Enter a valid phone number (7–20 digits).")
        return {
            "name": name,
            "phone": phone,
            "address": address,
            "government_id": gov,
            "title": title,
            "id_proof_type": id_type,
            "nominee_name": nominee,
        }
