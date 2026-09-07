from __future__ import annotations

from goldmine.db.connection import Database, rows_to_dicts
from goldmine.exceptions import ValidationError
from goldmine.security.permissions import CurrentUser, require_owner
from goldmine.services.audit import AuditService


class SettingsService:
    def __init__(self, db: Database, audit: AuditService) -> None:
        self.db = db
        self.audit = audit

    def all(self) -> dict[str, str]:
        rows = self.db.fetchall("SELECT key, value FROM settings")
        return {r["key"]: r["value"] for r in rows}

    def get(self, key: str, default: str = "") -> str:
        row = self.db.fetchone("SELECT value FROM settings WHERE key = ?", (key,))
        return row["value"] if row else default

    def int_value(self, key: str, default: int) -> int:
        try:
            return int(self.get(key, str(default)))
        except ValueError:
            return default

    def update_many(self, user: CurrentUser, values: dict[str, str]) -> None:
        require_owner(user)
        previous = self.all()
        allowed = {
            "shop_name",
            "shop_address",
            "shop_phone",
            "currency_symbol",
            "backup_retain_count",
            "appearance_mode",
            "due_soon_days",
            "receipt_footer",
            "default_ltv",
            "gold_rate_22k",
            "gold_rate_24k",
            "min_interest_days",
        }
        for key, value in values.items():
            if key not in allowed:
                raise ValidationError(f"Unknown setting: {key}")
            if key in ("backup_retain_count", "due_soon_days", "min_interest_days", "default_ltv"):
                try:
                    n = int(float(value))
                except ValueError:
                    raise ValidationError(f"{key} must be a number.")
                if key == "default_ltv" and (n < 1 or n > 100):
                    raise ValidationError("LTV must be between 1 and 100.")
                if key != "default_ltv" and (n < 1 or n > 365):
                    raise ValidationError(f"{key} must be between 1 and 365.")
            if key == "shop_name" and not str(value).strip():
                raise ValidationError("Shop name is required.")
            if key == "appearance_mode" and value not in ("light", "dark", "system"):
                raise ValidationError("Invalid appearance mode.")
            self.db.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, str(value).strip()),
            )
        self.db.commit()
        self.audit.record(user, "settings.update", entity_type="settings", previous=previous, new=self.all())

    def list_rates(self, user: CurrentUser | None = None, *, active_only: bool = False) -> list[dict]:
        if active_only:
            sql = "SELECT * FROM interest_rates WHERE is_active = 1 ORDER BY sort_order, rate"
        else:
            sql = "SELECT * FROM interest_rates ORDER BY sort_order, rate"
        return rows_to_dicts(self.db.fetchall(sql))

    def add_rate(self, user: CurrentUser, rate: float, label: str) -> None:
        require_owner(user)
        try:
            rate = float(rate)
        except (TypeError, ValueError):
            raise ValidationError("Enter a valid interest rate.")
        if rate < 0 or rate > 100:
            raise ValidationError("Rate must be between 0 and 100.")
        label = (label or "").strip() or f"{rate:g}% per month"
        exists = self.db.fetchone("SELECT id FROM interest_rates WHERE rate = ?", (rate,))
        if exists:
            raise ValidationError("That rate already exists.")
        max_order = self.db.fetchone("SELECT COALESCE(MAX(sort_order), 0) AS m FROM interest_rates")["m"]
        self.db.execute(
            "INSERT INTO interest_rates (rate, label, is_active, sort_order) VALUES (?, ?, 1, ?)",
            (rate, label, max_order + 1),
        )
        self.db.commit()
        self.audit.record(user, "rates.add", entity_type="interest_rate", new={"rate": rate, "label": label})

    def set_rate_active(self, user: CurrentUser, rate_id: int, active: bool) -> None:
        require_owner(user)
        row = self.db.fetchone("SELECT * FROM interest_rates WHERE id = ?", (rate_id,))
        if not row:
            raise ValidationError("Rate not found.")
        if not active:
            active_count = self.db.fetchone(
                "SELECT COUNT(*) AS c FROM interest_rates WHERE is_active = 1 AND id != ?",
                (rate_id,),
            )["c"]
            if active_count < 1:
                raise ValidationError("At least one interest rate must remain active.")
        self.db.execute("UPDATE interest_rates SET is_active = ? WHERE id = ?", (1 if active else 0, rate_id))
        self.db.commit()
        self.audit.record(
            user,
            "rates.update",
            entity_type="interest_rate",
            entity_id=rate_id,
            previous={"is_active": bool(row["is_active"])},
            new={"is_active": active},
        )
