from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path

from goldmine.db.schema import DEFAULT_INTEREST_RATES, DEFAULT_SETTINGS, SCHEMA_SQL
from goldmine.paths import database_path


NEW_COLUMNS = [
    ("customers", "title", "TEXT"),
    ("customers", "id_proof_type", "TEXT"),
    ("customers", "nominee_name", "TEXT"),
    ("loans", "locker_no", "TEXT"),
    ("loans", "estimated_value", "REAL"),
    ("loans", "ltv_percent", "REAL"),
    ("loans", "close_type", "TEXT"),
    ("loans", "notice_status", "TEXT"),
]


class Database:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or database_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self.conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA journal_mode = WAL")
        self.conn.execute("PRAGMA busy_timeout = 5000")
        self.conn.execute("PRAGMA synchronous = NORMAL")
        self.initialize()

    def initialize(self) -> None:
        with self._lock:
            self.conn.executescript(SCHEMA_SQL)
            self._migrate()
            for rate, label, order in DEFAULT_INTEREST_RATES:
                self.conn.execute(
                    """
                    INSERT OR IGNORE INTO interest_rates (rate, label, is_active, sort_order)
                    VALUES (?, ?, 1, ?)
                    """,
                    (rate, label, order),
                )
            for key, value in DEFAULT_SETTINGS.items():
                self.conn.execute(
                    "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                    (key, value),
                )
            self.conn.commit()

    def _migrate(self) -> None:
        for table, column, coltype in NEW_COLUMNS:
            info = self.conn.execute(f"PRAGMA table_info({table})").fetchall()
            names = {row[1] for row in info}
            if column not in names:
                self.conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}")

    def execute(self, sql: str, params: tuple | list = ()) -> sqlite3.Cursor:
        with self._lock:
            cur = self.conn.execute(sql, params)
            return cur

    def executemany(self, sql: str, seq: list) -> sqlite3.Cursor:
        with self._lock:
            return self.conn.executemany(sql, seq)

    def fetchone(self, sql: str, params: tuple | list = ()) -> sqlite3.Row | None:
        with self._lock:
            return self.conn.execute(sql, params).fetchone()

    def fetchall(self, sql: str, params: tuple | list = ()) -> list[sqlite3.Row]:
        with self._lock:
            return self.conn.execute(sql, params).fetchall()

    def commit(self) -> None:
        with self._lock:
            self.conn.commit()

    def rollback(self) -> None:
        with self._lock:
            self.conn.rollback()

    @contextmanager
    def transaction(self):
        with self._lock:
            try:
                yield self.conn
                self.conn.commit()
            except Exception:
                self.conn.rollback()
                raise

    def close(self) -> None:
        with self._lock:
            self.conn.close()


def row_to_dict(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    return {k: row[k] for k in row.keys()}


def rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict]:
    return [{k: r[k] for k in r.keys()} for r in rows]


def seed_needed(db: Database) -> bool:
    setup = db.fetchone("SELECT value FROM settings WHERE key = 'setup_complete'")
    if setup and setup["value"] == "1":
        return False
    owners = db.fetchone("SELECT COUNT(*) AS c FROM users WHERE role = 'owner'")
    return not owners or owners["c"] == 0
