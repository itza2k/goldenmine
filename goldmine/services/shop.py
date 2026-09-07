from __future__ import annotations

import math
from datetime import datetime, timedelta

from goldmine.catalog import CLOSE_TYPES, PAYMENT_KINDS, PAYMENT_METHODS, fine_factor
from goldmine.db.connection import Database, rows_to_dicts
from goldmine.exceptions import PermissionDenied, ValidationError
from goldmine.security.permissions import CurrentUser, require_owner, require_user
from goldmine.services.audit import AuditService
from goldmine.util import now, now_iso


class ShopService:
    def __init__(self, db: Database, audit: AuditService, settings) -> None:
        self.db = db
        self.audit = audit
        self.settings = settings

    def gold_rate(self) -> dict:
        row = self.db.fetchone("SELECT * FROM gold_rates ORDER BY rate_date DESC, id DESC LIMIT 1")
        if row:
            return {"rate_22k": row["rate_22k"], "rate_24k": row["rate_24k"], "rate_date": row["rate_date"]}
        return {
            "rate_22k": float(self.settings.get("gold_rate_22k", "0") or 0),
            "rate_24k": float(self.settings.get("gold_rate_24k", "0") or 0),
            "rate_date": now().date().isoformat(),
        }

    def set_gold_rate(self, user: CurrentUser, rate_22k: float, rate_24k: float) -> dict:
        require_owner(user)
        try:
            k22 = float(rate_22k)
            k24 = float(rate_24k)
        except (TypeError, ValueError):
            raise ValidationError("Enter valid gold rates.")
        if k22 <= 0 or k24 <= 0:
            raise ValidationError("Gold rates must be greater than zero.")
        today = now().date().isoformat()
        self.db.execute(
            """
            INSERT INTO gold_rates (rate_date, rate_22k, rate_24k, set_by, created_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(rate_date) DO UPDATE SET rate_22k = excluded.rate_22k, rate_24k = excluded.rate_24k, set_by = excluded.set_by
            """,
            (today, k22, k24, user.id, now_iso()),
        )
        self.db.execute("UPDATE settings SET value = ? WHERE key = 'gold_rate_22k'", (str(k22),))
        self.db.execute("UPDATE settings SET value = ? WHERE key = 'gold_rate_24k'", (str(k24),))
        self.db.commit()
        self.audit.record(user, "gold_rate.set", entity_type="gold_rate", new={"22k": k22, "24k": k24})
        return self.gold_rate()

    def estimate(self, net_weight: float, purity: str, ltv: float | None = None) -> dict:
        try:
            weight = float(net_weight)
        except (TypeError, ValueError):
            raise ValidationError("Enter a valid net weight.")
        if weight <= 0:
            raise ValidationError("Net weight must be greater than zero.")
        rates = self.gold_rate()
        factor = fine_factor(purity)
        fine = weight * factor
        value_24 = fine * float(rates["rate_24k"] or 0)
        # If 24K rate missing, scale from 22K
        if value_24 <= 0 and rates["rate_22k"]:
            value_24 = (weight * factor / 0.916) * float(rates["rate_22k"])
        ltv = float(ltv if ltv is not None else self.settings.get("default_ltv", "75") or 75)
        max_loan = round(value_24 * ltv / 100, 2)
        return {
            "net_weight": round(weight, 3),
            "fine_gold": round(fine, 3),
            "estimated_value": round(value_24, 2),
            "ltv": ltv,
            "max_loan": max_loan,
            "rate_22k": rates["rate_22k"],
            "rate_24k": rates["rate_24k"],
        }

    def charged_months(self, start_date: str, as_of: str | None = None) -> int:
        as_of_d = datetime.strptime(as_of or now().date().isoformat(), "%Y-%m-%d").date()
        start = datetime.strptime(start_date[:10], "%Y-%m-%d").date()
        days = max((as_of_d - start).days, 0)
        min_days = int(self.settings.get("min_interest_days", "15") or 15)
        days = max(days, min_days)
        return max(1, math.ceil(days / 30))

    def settlement(self, loan: dict, as_of: str | None = None) -> dict:
        as_of = as_of or now().date().isoformat()
        months = self.charged_months(loan["start_date"], as_of)
        principal = float(loan["loan_amount"] or 0)
        rate = float(loan["interest_rate"] or 0)
        interest = round(principal * rate / 100 * months, 2)
        paid = self.db.fetchone(
            "SELECT COALESCE(SUM(amount),0) AS s FROM payments WHERE loan_id = ?",
            (loan["id"],),
        )["s"]
        total_due = round(principal + interest, 2)
        outstanding = round(max(total_due - paid, 0), 2)
        due = loan.get("due_date")
        overdue_days = 0
        if due and loan.get("status") == "open" and due < as_of:
            overdue_days = (datetime.strptime(as_of, "%Y-%m-%d").date() - datetime.strptime(due, "%Y-%m-%d").date()).days
        return {
            "months": months,
            "interest_accrued": interest,
            "principal": principal,
            "paid": paid,
            "total_due": total_due,
            "outstanding": outstanding,
            "overdue_days": overdue_days,
        }

    def items(self, loan_id: int) -> list[dict]:
        return rows_to_dicts(
            self.db.fetchall("SELECT * FROM loan_items WHERE loan_id = ? ORDER BY id", (loan_id,))
        )

    def replace_items(self, user: CurrentUser, loan_id: int, items: list[dict]) -> None:
        require_user(user)
        cleaned = []
        for it in items:
            jtype = (it.get("jewellery_type") or "").strip()
            if not jtype:
                continue
            try:
                gross = float(it.get("gross_weight") or 0)
                stone = float(it.get("stone_weight") or 0)
            except (TypeError, ValueError):
                raise ValidationError("Ornament weights must be numbers.")
            net = max(gross - stone, 0)
            cleaned.append(
                {
                    "jewellery_type": jtype,
                    "description": (it.get("description") or "").strip() or None,
                    "purity": it.get("purity") or None,
                    "gross_weight": round(gross, 3),
                    "stone_weight": round(stone, 3),
                    "net_weight": round(net, 3),
                    "condition_label": it.get("condition_label") or None,
                    "estimated_value": it.get("estimated_value"),
                }
            )
        self.db.execute("DELETE FROM loan_items WHERE loan_id = ?", (loan_id,))
        for it in cleaned:
            self.db.execute(
                """
                INSERT INTO loan_items (
                    loan_id, jewellery_type, description, purity, gross_weight, stone_weight,
                    net_weight, condition_label, estimated_value
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    loan_id,
                    it["jewellery_type"],
                    it["description"],
                    it["purity"],
                    it["gross_weight"],
                    it["stone_weight"],
                    it["net_weight"],
                    it["condition_label"],
                    it["estimated_value"],
                ),
            )
        self.db.commit()

    def payments(self, loan_id: int) -> list[dict]:
        return rows_to_dicts(
            self.db.fetchall("SELECT * FROM payments WHERE loan_id = ? ORDER BY id DESC", (loan_id,))
        )

    def record_payment(
        self,
        user: CurrentUser,
        loan_id: int,
        *,
        amount,
        kind: str,
        method: str,
        payment_date: str,
        remarks: str | None,
    ) -> dict:
        require_user(user)
        loan = self.db.fetchone("SELECT * FROM loans WHERE id = ?", (loan_id,))
        if not loan:
            raise ValidationError("Loan not found.")
        if loan["status"] != "open":
            raise ValidationError("Payments can only be recorded on open loans.")
        if kind not in PAYMENT_KINDS or method not in PAYMENT_METHODS:
            raise ValidationError("Choose a valid payment type and method.")
        try:
            datetime.strptime(payment_date, "%Y-%m-%d")
            amt = float(amount)
        except (TypeError, ValueError):
            raise ValidationError("Enter a valid date and amount.")
        if amt <= 0:
            raise ValidationError("Amount must be greater than zero.")
        self.db.execute(
            """
            INSERT INTO payments (loan_id, payment_date, amount, kind, method, remarks, created_at, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (loan_id, payment_date, round(amt, 2), kind, method, (remarks or "").strip() or None, now_iso(), user.id),
        )
        self.db.commit()
        self.audit.record(
            user,
            "payment.create",
            entity_type="loan",
            entity_id=loan["loan_number"],
            new={"amount": amt, "kind": kind, "method": method},
        )
        return {"amount": amt, "kind": kind, "method": method}

    def vault(self) -> list[dict]:
        return rows_to_dicts(
            self.db.fetchall(
                """
                SELECT i.*, l.loan_number, l.locker_no, l.status, c.name AS customer_name, c.phone
                FROM loan_items i
                JOIN loans l ON l.id = i.loan_id
                JOIN customers c ON c.id = l.customer_id
                WHERE l.status = 'open'
                ORDER BY l.loan_number, i.id
                """
            )
        )

    def overdue(self) -> list[dict]:
        today = now().date().isoformat()
        return rows_to_dicts(
            self.db.fetchall(
                """
                SELECT l.*, c.name AS customer_name, c.phone AS customer_phone
                FROM loans l JOIN customers c ON c.id = l.customer_id
                WHERE l.status = 'open' AND l.due_date IS NOT NULL AND l.due_date < ?
                ORDER BY l.due_date
                """,
                (today,),
            )
        )

    def set_notice(self, user: CurrentUser, loan_id: int, status: str) -> None:
        require_user(user)
        self.db.execute("UPDATE loans SET notice_status = ? WHERE id = ?", (status, loan_id))
        self.db.commit()
        self.audit.record(user, "loan.notice", entity_type="loan", entity_id=loan_id, new={"notice_status": status})

    def renew(self, user: CurrentUser, loan_id: int, new_due: str, reason: str) -> None:
        require_owner(user)
        if not (reason or "").strip():
            raise ValidationError("A reason is required to renew.")
        datetime.strptime(new_due, "%Y-%m-%d")
        loan = self.db.fetchone("SELECT * FROM loans WHERE id = ?", (loan_id,))
        if not loan or loan["status"] != "open":
            raise ValidationError("Only open loans can be renewed.")
        prev = loan["due_date"]
        self.db.execute(
            "UPDATE loans SET due_date = ?, updated_at = ?, updated_by = ? WHERE id = ?",
            (new_due, now_iso(), user.id, loan_id),
        )
        self.db.commit()
        self.audit.record(
            user,
            "loan.renew",
            entity_type="loan",
            entity_id=loan["loan_number"],
            previous={"due_date": prev},
            new={"due_date": new_due},
            reason=reason.strip(),
        )
