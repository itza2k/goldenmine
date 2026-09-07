from __future__ import annotations

import time

from goldmine.db.connection import Database, row_to_dict
from goldmine.exceptions import AuthError, ValidationError
from goldmine.security.passwords import hash_password, verify_password
from goldmine.security.permissions import CurrentUser, ROLE_OWNER
from goldmine.services.audit import AuditService
from goldmine.util import now_iso


MAX_FAILED = 5
LOCKOUT_SECONDS = 300


class AuthService:
    def __init__(self, db: Database, audit: AuditService) -> None:
        self.db = db
        self.audit = audit
        self._failures: dict[str, list[float]] = {}

    def _locked(self, username: str) -> bool:
        now = time.time()
        stamps = [t for t in self._failures.get(username.lower(), []) if now - t < LOCKOUT_SECONDS]
        self._failures[username.lower()] = stamps
        return len(stamps) >= MAX_FAILED

    def _fail(self, username: str) -> None:
        self._failures.setdefault(username.lower(), []).append(time.time())

    def _clear(self, username: str) -> None:
        self._failures.pop(username.lower(), None)

    def login(self, username: str, password: str) -> CurrentUser:
        username = (username or "").strip()
        if not username or not password:
            raise AuthError("Enter username and password.")
        if self._locked(username):
            raise AuthError("Too many failed attempts. Try again in 5 minutes.")

        row = self.db.fetchone(
            "SELECT * FROM users WHERE username = ? COLLATE NOCASE",
            (username,),
        )
        if row is None or not row["is_active"]:
            self._fail(username)
            raise AuthError("Invalid username or password.")
        if not verify_password(password, row["password_hash"]):
            self._fail(username)
            self.audit.record(
                None,
                "login.failed",
                entity_type="user",
                entity_id=row["id"],
                username=row["username"],
            )
            raise AuthError("Invalid username or password.")

        self._clear(username)
        user = CurrentUser(
            id=row["id"],
            username=row["username"],
            full_name=row["full_name"],
            role=row["role"],
        )
        self.audit.record(user, "login", entity_type="user", entity_id=user.id)
        return user

    def logout(self, user: CurrentUser) -> None:
        self.audit.record(user, "logout", entity_type="user", entity_id=user.id)

    def verify_owner_password(self, user: CurrentUser, password: str) -> None:
        if user.role != ROLE_OWNER:
            raise AuthError("Owner authentication is required.")
        row = self.db.fetchone("SELECT password_hash FROM users WHERE id = ?", (user.id,))
        if row is None or not verify_password(password, row["password_hash"]):
            raise AuthError("Password is incorrect.")

    def change_password(self, user: CurrentUser, current: str, new: str) -> None:
        if len(new) < 8:
            raise ValidationError("New password must be at least 8 characters.")
        row = self.db.fetchone("SELECT password_hash FROM users WHERE id = ?", (user.id,))
        if row is None or not verify_password(current, row["password_hash"]):
            raise AuthError("Current password is incorrect.")
        self.db.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (hash_password(new), user.id),
        )
        self.db.commit()
        self.audit.record(user, "password.change", entity_type="user", entity_id=user.id)

    def create_owner(self, username: str, password: str, full_name: str, shop_name: str) -> CurrentUser:
        username = username.strip()
        full_name = full_name.strip()
        shop_name = shop_name.strip()
        if not username or not full_name or not shop_name:
            raise ValidationError("All setup fields are required.")
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters.")
        existing = self.db.fetchone("SELECT id FROM users WHERE role = 'owner'")
        if existing:
            raise ValidationError("An owner account already exists.")
        self.db.execute(
            """
            INSERT INTO users (username, password_hash, full_name, role, is_active, created_at)
            VALUES (?, ?, ?, 'owner', 1, ?)
            """,
            (username, hash_password(password), full_name, now_iso()),
        )
        self.db.execute("UPDATE settings SET value = ? WHERE key = 'shop_name'", (shop_name,))
        self.db.execute("UPDATE settings SET value = '1' WHERE key = 'setup_complete'", ())
        self.db.commit()
        row = self.db.fetchone("SELECT * FROM users WHERE username = ? COLLATE NOCASE", (username,))
        user = CurrentUser(id=row["id"], username=row["username"], full_name=row["full_name"], role=row["role"])
        self.audit.record(user, "setup.complete", entity_type="user", entity_id=user.id, new={"shop_name": shop_name})
        return user
