from __future__ import annotations

from goldmine.db.connection import Database, row_to_dict, rows_to_dicts
from goldmine.exceptions import NotFoundError, ValidationError
from goldmine.security.passwords import hash_password
from goldmine.security.permissions import ROLE_EMPLOYEE, ROLE_OWNER, CurrentUser, require_owner
from goldmine.services.audit import AuditService
from goldmine.util import now_iso


class UserService:
    def __init__(self, db: Database, audit: AuditService) -> None:
        self.db = db
        self.audit = audit

    def list(self, user: CurrentUser) -> list[dict]:
        require_owner(user)
        rows = self.db.fetchall(
            """
            SELECT id, username, full_name, role, is_active, created_at
            FROM users ORDER BY role, username
            """
        )
        return rows_to_dicts(rows)

    def create_employee(self, user: CurrentUser, username: str, password: str, full_name: str) -> dict:
        require_owner(user)
        username = username.strip()
        full_name = full_name.strip()
        if not username or not full_name:
            raise ValidationError("Username and full name are required.")
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters.")
        exists = self.db.fetchone("SELECT id FROM users WHERE username = ? COLLATE NOCASE", (username,))
        if exists:
            raise ValidationError("That username is already taken.")
        self.db.execute(
            """
            INSERT INTO users (username, password_hash, full_name, role, is_active, created_at, created_by)
            VALUES (?, ?, ?, ?, 1, ?, ?)
            """,
            (username, hash_password(password), full_name, ROLE_EMPLOYEE, now_iso(), user.id),
        )
        self.db.commit()
        created = row_to_dict(
            self.db.fetchone(
                "SELECT id, username, full_name, role, is_active, created_at FROM users WHERE username = ? COLLATE NOCASE",
                (username,),
            )
        )
        self.audit.record(user, "user.create", entity_type="user", entity_id=created["id"], new=created)
        return created

    def set_active(self, user: CurrentUser, target_id: int, active: bool) -> None:
        require_owner(user)
        target = self.db.fetchone("SELECT * FROM users WHERE id = ?", (target_id,))
        if not target:
            raise NotFoundError("User not found.")
        if target["role"] == ROLE_OWNER and not active:
            raise ValidationError("The owner account cannot be deactivated.")
        if target_id == user.id and not active:
            raise ValidationError("You cannot deactivate your own account.")
        self.db.execute("UPDATE users SET is_active = ? WHERE id = ?", (1 if active else 0, target_id))
        self.db.commit()
        self.audit.record(
            user,
            "user.status",
            entity_type="user",
            entity_id=target_id,
            previous={"is_active": bool(target["is_active"])},
            new={"is_active": active},
        )

    def reset_password(self, user: CurrentUser, target_id: int, new_password: str) -> None:
        require_owner(user)
        if len(new_password) < 8:
            raise ValidationError("Password must be at least 8 characters.")
        target = self.db.fetchone("SELECT * FROM users WHERE id = ?", (target_id,))
        if not target:
            raise NotFoundError("User not found.")
        self.db.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (hash_password(new_password), target_id),
        )
        self.db.commit()
        self.audit.record(user, "password.reset", entity_type="user", entity_id=target_id)
