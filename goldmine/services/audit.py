from __future__ import annotations

from goldmine.db.connection import Database
from goldmine.security.permissions import CurrentUser
from goldmine.util import now_iso, to_json


class AuditService:
    def __init__(self, db: Database) -> None:
        self.db = db

    def record(
        self,
        user: CurrentUser | None,
        action: str,
        *,
        entity_type: str | None = None,
        entity_id: str | int | None = None,
        previous=None,
        new=None,
        reason: str | None = None,
        username: str | None = None,
    ) -> None:
        name = username or (user.username if user else "system")
        prev_s = None if previous is None else (previous if isinstance(previous, str) else to_json(previous))
        new_s = None if new is None else (new if isinstance(new, str) else to_json(new))
        self.db.execute(
            """
            INSERT INTO audit_log
                (created_at, username, action, entity_type, entity_id, previous_value, new_value, reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                now_iso(),
                name,
                action,
                entity_type,
                None if entity_id is None else str(entity_id),
                prev_s,
                new_s,
                reason,
            ),
        )
        self.db.commit()

    def list(
        self,
        *,
        search: str = "",
        action: str = "",
        limit: int = 500,
        offset: int = 0,
    ) -> list[dict]:
        clauses = ["1=1"]
        params: list = []
        if search:
            clauses.append("(username LIKE ? OR action LIKE ? OR entity_id LIKE ? OR reason LIKE ?)")
            q = f"%{search}%"
            params.extend([q, q, q, q])
        if action:
            clauses.append("action = ?")
            params.append(action)
        params.extend([limit, offset])
        rows = self.db.fetchall(
            f"""
            SELECT * FROM audit_log
            WHERE {' AND '.join(clauses)}
            ORDER BY id DESC
            LIMIT ? OFFSET ?
            """,
            tuple(params),
        )
        return [{k: r[k] for k in r.keys()} for r in rows]

    def distinct_actions(self) -> list[str]:
        rows = self.db.fetchall("SELECT DISTINCT action FROM audit_log ORDER BY action")
        return [r["action"] for r in rows]
