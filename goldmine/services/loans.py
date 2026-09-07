from __future__ import annotations

from datetime import datetime, timedelta

from goldmine.db.connection import Database, row_to_dict, rows_to_dicts
from goldmine.exceptions import NotFoundError, PermissionDenied, ValidationError
from goldmine.paths import EDIT_WINDOW_SECONDS
from goldmine.security.permissions import CurrentUser, require_owner, require_user
from goldmine.services.audit import AuditService
from goldmine.util import now, now_iso, parse_dt


def _loan_with_customer(row) -> dict | None:
    data = row_to_dict(row)
    if not data:
        return None
    data["is_locked"] = loan_is_locked(data)
    data["seconds_remaining"] = loan_seconds_remaining(data)
    return data


def loan_is_locked(loan: dict) -> bool:
    created = parse_dt(loan["created_at"])
    return now() - created > timedelta(seconds=EDIT_WINDOW_SECONDS)


def loan_seconds_remaining(loan: dict) -> int:
    created = parse_dt(loan["created_at"])
    remaining = EDIT_WINDOW_SECONDS - int((now() - created).total_seconds())
    return max(0, remaining)


LOAN_SELECT = """
    SELECT l.*,
           c.name AS customer_name,
           c.phone AS customer_phone,
           c.address AS customer_address,
           c.government_id AS customer_government_id
    FROM loans l
    JOIN customers c ON c.id = l.customer_id
"""


class LoanService:
    def __init__(self, db: Database, audit: AuditService) -> None:
        self.db = db
        self.audit = audit

    def get(self, loan_id: int) -> dict:
        row = self.db.fetchone(LOAN_SELECT + " WHERE l.id = ?", (loan_id,))
        data = _loan_with_customer(row)
        if not data:
            raise NotFoundError("Loan not found.")
        data["items"] = rows_to_dicts(
            self.db.fetchall("SELECT * FROM loan_items WHERE loan_id = ? ORDER BY id", (loan_id,))
        )
        return data

    def get_by_number(self, loan_number: str) -> dict:
        row = self.db.fetchone(LOAN_SELECT + " WHERE l.loan_number = ?", (loan_number.strip(),))
        data = _loan_with_customer(row)
        if not data:
            raise NotFoundError("Loan not found.")
        return data

    def search(self, query: str, status: str = "") -> list[dict]:
        q = (query or "").strip()
        clauses = ["1=1"]
        params: list = []
        today = now().date().isoformat()
        soon = (now().date() + timedelta(days=7)).isoformat()
        if status == "open":
            clauses.append("l.status = 'open'")
        elif status == "closed":
            clauses.append("l.status = 'closed'")
        elif status == "overdue":
            clauses.append("l.status = 'open' AND l.due_date IS NOT NULL AND l.due_date < ?")
            params.append(today)
        elif status == "due soon":
            clauses.append("l.status = 'open' AND l.due_date IS NOT NULL AND l.due_date >= ? AND l.due_date <= ?")
            params.extend([today, soon])
        if q:
            clauses.append(
                "(l.loan_number LIKE ? OR c.name LIKE ? COLLATE NOCASE OR c.phone LIKE ? OR l.locker_no LIKE ? OR l.gold_description LIKE ?)"
            )
            like = f"%{q}%"
            params.extend([like, like, like, like, like])
        rows = self.db.fetchall(
            LOAN_SELECT
            + f" WHERE {' AND '.join(clauses)} ORDER BY l.id DESC LIMIT 400",
            tuple(params),
        )
        return [_loan_with_customer(r) for r in rows]

    def list_due_soon(self, days: int) -> list[dict]:
        today = now().date().isoformat()
        until = (now().date() + timedelta(days=days)).isoformat()
        rows = self.db.fetchall(
            LOAN_SELECT
            + """
            WHERE l.status = 'open' AND l.due_date IS NOT NULL
              AND l.due_date >= ? AND l.due_date <= ?
            ORDER BY l.due_date ASC
            """,
            (today, until),
        )
        return [_loan_with_customer(r) for r in rows]

    def active_rates(self) -> list[dict]:
        return rows_to_dicts(
            self.db.fetchall(
                "SELECT * FROM interest_rates WHERE is_active = 1 ORDER BY sort_order, rate"
            )
        )

    def _next_loan_number(self, conn) -> str:
        year = now().year
        prefix = f"GL-{year}-"
        row = conn.execute(
            "SELECT loan_number FROM loans WHERE loan_number LIKE ? ORDER BY loan_number DESC LIMIT 1",
            (prefix + "%",),
        ).fetchone()
        if row is None:
            seq = 1
        else:
            try:
                seq = int(str(row["loan_number"]).split("-")[-1]) + 1
            except ValueError:
                seq = 1
        return f"{prefix}{seq:05d}"

    def _assert_rate_allowed(self, rate: float, *, allow_inactive: bool = False) -> float:
        if allow_inactive:
            row = self.db.fetchone("SELECT rate FROM interest_rates WHERE rate = ?", (rate,))
        else:
            row = self.db.fetchone(
                "SELECT rate FROM interest_rates WHERE rate = ? AND is_active = 1",
                (rate,),
            )
        if row is None:
            raise ValidationError("Interest rate must be selected from the configured options.")
        return float(row["rate"])

    def _validate_payload(self, data: dict, *, creating: bool) -> dict:
        desc = (data.get("gold_description") or "").strip()
        purity = (data.get("gold_purity") or "").strip() or None
        remarks = (data.get("remarks") or "").strip() or None
        try:
            weight = float(data.get("gold_weight"))
            amount = float(data.get("loan_amount"))
            rate = float(data.get("interest_rate"))
        except (TypeError, ValueError):
            raise ValidationError("Weight, loan amount, and interest rate must be numbers.")
        if not desc:
            raise ValidationError("Gold description is required.")
        if weight <= 0:
            raise ValidationError("Gold weight must be greater than zero.")
        if amount <= 0:
            raise ValidationError("Loan amount must be greater than zero.")
        start = (data.get("start_date") or "").strip()
        due = (data.get("due_date") or "").strip() or None
        try:
            datetime.strptime(start, "%Y-%m-%d")
        except ValueError:
            raise ValidationError("Start date must be a valid date.")
        if due:
            try:
                datetime.strptime(due, "%Y-%m-%d")
            except ValueError:
                raise ValidationError("Due date must be a valid date.")
            if due < start:
                raise ValidationError("Due date cannot be before the start date.")
        customer_id = data.get("customer_id")
        if creating and not customer_id:
            raise ValidationError("Select or create a customer first.")
        locker = (data.get("locker_no") or "").strip() or None
        try:
            est = float(data["estimated_value"]) if data.get("estimated_value") not in (None, "") else None
            ltv = float(data["ltv_percent"]) if data.get("ltv_percent") not in (None, "") else None
        except (TypeError, ValueError):
            raise ValidationError("Estimated value and LTV must be numbers.")
        return {
            "customer_id": int(customer_id) if customer_id else None,
            "gold_description": desc,
            "gold_weight": round(weight, 3),
            "gold_purity": purity,
            "loan_amount": round(amount, 2),
            "interest_rate": rate,
            "start_date": start,
            "due_date": due,
            "remarks": remarks,
            "locker_no": locker,
            "estimated_value": round(est, 2) if est is not None else None,
            "ltv_percent": round(ltv, 2) if ltv is not None else None,
        }

    def create(self, user: CurrentUser, data: dict) -> dict:
        require_user(user)
        payload = self._validate_payload(data, creating=True)
        payload["interest_rate"] = self._assert_rate_allowed(payload["interest_rate"])
        customer = self.db.fetchone("SELECT id FROM customers WHERE id = ?", (payload["customer_id"],))
        if not customer:
            raise ValidationError("Customer not found.")
        with self.db.transaction() as conn:
            number = self._next_loan_number(conn)
            conn.execute(
                """
                INSERT INTO loans (
                    loan_number, customer_id, gold_description, gold_weight, gold_purity,
                    loan_amount, interest_rate, start_date, due_date, remarks,
                    locker_no, estimated_value, ltv_percent, notice_status,
                    status, created_at, created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Not sent', 'open', ?, ?)
                """,
                (
                    number,
                    payload["customer_id"],
                    payload["gold_description"],
                    payload["gold_weight"],
                    payload["gold_purity"],
                    payload["loan_amount"],
                    payload["interest_rate"],
                    payload["start_date"],
                    payload["due_date"],
                    payload["remarks"],
                    payload["locker_no"],
                    payload["estimated_value"],
                    payload["ltv_percent"],
                    now_iso(),
                    user.id,
                ),
            )
            loan_id = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
        created = self.get(loan_id)
        self.audit.record(user, "loan.create", entity_type="loan", entity_id=created["loan_number"], new=created)
        return created

    def update(
        self,
        user: CurrentUser,
        loan_id: int,
        data: dict,
        *,
        owner_password: str | None = None,
        reason: str | None = None,
        auth_service=None,
    ) -> dict:
        require_user(user)
        current = self.get(loan_id)
        locked = current["is_locked"]
        if current["status"] == "closed" and not user.is_owner:
            raise PermissionDenied("Closed loans cannot be edited.")

        if user.is_employee:
            if locked:
                raise PermissionDenied("This loan is locked. Employees cannot edit it after 5 minutes.")
            if current["status"] == "closed":
                raise PermissionDenied("Closed loans cannot be edited.")
        else:
            if locked or current["status"] == "closed":
                if not owner_password or auth_service is None:
                    raise PermissionDenied("Owner password is required to change a locked loan.")
                auth_service.verify_owner_password(user, owner_password)
                if not (reason or "").strip():
                    raise ValidationError("A reason is required for owner overrides.")

        payload = self._validate_payload({**data, "customer_id": data.get("customer_id", current["customer_id"])}, creating=False)
        payload["customer_id"] = int(data.get("customer_id") or current["customer_id"])
        if payload["customer_id"] != current["customer_id"] and user.is_employee and locked:
            raise PermissionDenied("Cannot change the customer on a locked loan.")
        allow_inactive = user.is_owner and locked
        payload["interest_rate"] = self._assert_rate_allowed(payload["interest_rate"], allow_inactive=allow_inactive)

        self.db.execute(
            """
            UPDATE loans SET
                customer_id = ?, gold_description = ?, gold_weight = ?, gold_purity = ?,
                loan_amount = ?, interest_rate = ?, start_date = ?, due_date = ?, remarks = ?,
                locker_no = ?, estimated_value = ?, ltv_percent = ?,
                updated_at = ?, updated_by = ?
            WHERE id = ?
            """,
            (
                payload["customer_id"],
                payload["gold_description"],
                payload["gold_weight"],
                payload["gold_purity"],
                payload["loan_amount"],
                payload["interest_rate"],
                payload["start_date"],
                payload["due_date"],
                payload["remarks"],
                payload["locker_no"],
                payload["estimated_value"],
                payload["ltv_percent"],
                now_iso(),
                user.id,
                loan_id,
            ),
        )
        self.db.commit()
        updated = self.get(loan_id)
        action = "loan.owner_override" if user.is_owner and locked else "loan.update"
        self.audit.record(
            user,
            action,
            entity_type="loan",
            entity_id=updated["loan_number"],
            previous=current,
            new=updated,
            reason=reason,
        )
        return updated

    def close(
        self,
        user: CurrentUser,
        loan_id: int,
        *,
        closing_date: str,
        interest_collected: float,
        total_received: float,
        remarks: str | None,
        close_type: str = "Redeemed",
    ) -> dict:
        require_owner(user)
        current = self.get(loan_id)
        if current["status"] != "open":
            raise ValidationError("Only open loans can be closed.")
        from goldmine.catalog import CLOSE_TYPES

        if close_type not in CLOSE_TYPES:
            raise ValidationError("Choose how this loan was closed.")
        try:
            datetime.strptime(closing_date, "%Y-%m-%d")
            interest = float(interest_collected)
            total = float(total_received)
        except (TypeError, ValueError):
            raise ValidationError("Enter a valid closing date, interest, and total received.")
        if interest < 0 or total < 0:
            raise ValidationError("Amounts cannot be negative.")
        if closing_date < current["start_date"]:
            raise ValidationError("Closing date cannot be before the loan start date.")
        notes = (remarks or "").strip() or None
        self.db.execute(
            """
            UPDATE loans SET
                status = 'closed',
                closed_at = ?,
                closing_date = ?,
                interest_collected = ?,
                total_received = ?,
                closing_remarks = ?,
                closed_by = ?,
                close_type = ?,
                updated_at = ?,
                updated_by = ?
            WHERE id = ?
            """,
            (
                now_iso(),
                closing_date,
                round(interest, 2),
                round(total, 2),
                notes,
                user.id,
                close_type,
                now_iso(),
                user.id,
                loan_id,
            ),
        )
        self.db.commit()
        updated = self.get(loan_id)
        self.audit.record(
            user,
            "loan.close",
            entity_type="loan",
            entity_id=updated["loan_number"],
            previous={"status": current["status"]},
            new={
                "status": "closed",
                "close_type": close_type,
                "closing_date": closing_date,
                "interest_collected": interest,
                "total_received": total,
            },
            reason=notes,
        )
        return updated

    def reopen(self, user: CurrentUser, loan_id: int, reason: str) -> dict:
        require_owner(user)
        current = self.get(loan_id)
        if current["status"] != "closed":
            raise ValidationError("Only closed loans can be reopened.")
        if not (reason or "").strip():
            raise ValidationError("A reason is required to reopen a loan.")
        self.db.execute(
            """
            UPDATE loans SET
                status = 'open',
                closed_at = NULL,
                closing_date = NULL,
                interest_collected = NULL,
                total_received = NULL,
                closing_remarks = NULL,
                closed_by = NULL,
                updated_at = ?,
                updated_by = ?
            WHERE id = ?
            """,
            (now_iso(), user.id, loan_id),
        )
        self.db.commit()
        updated = self.get(loan_id)
        self.audit.record(
            user,
            "loan.reopen",
            entity_type="loan",
            entity_id=updated["loan_number"],
            previous=current,
            new={"status": "open"},
            reason=reason.strip(),
        )
        return updated
