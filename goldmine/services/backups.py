from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from goldmine.db.connection import Database
from goldmine.exceptions import ValidationError
from goldmine.paths import backups_dir, database_path
from goldmine.security.permissions import CurrentUser, require_owner
from goldmine.services.audit import AuditService
from goldmine.util import now, now_iso


class BackupService:
    def __init__(self, db: Database, audit: AuditService, settings) -> None:
        self.db = db
        self.audit = audit
        self.settings = settings

    def list_backups(self) -> list[dict]:
        files = sorted(backups_dir().glob("goldmine-*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
        out = []
        for f in files:
            out.append(
                {
                    "name": f.name,
                    "path": str(f),
                    "size": f.stat().st_size,
                    "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(timespec="seconds"),
                }
            )
        return out

    def create(self, user: CurrentUser | None, *, automatic: bool = False) -> Path:
        if not automatic:
            require_owner(user)
        self.db.commit()
        stamp = now().strftime("%Y%m%d-%H%M%S")
        kind = "auto" if automatic else "manual"
        dest = backups_dir() / f"goldmine-{kind}-{stamp}.db"
        src = Path(self.db.path)
        # Safe snapshot via SQLite backup API
        import sqlite3

        dst_conn = sqlite3.connect(str(dest))
        try:
            self.db.conn.backup(dst_conn)
        finally:
            dst_conn.close()
        self._prune()
        if user:
            self.audit.record(
                user,
                "backup.create",
                entity_type="backup",
                new={"path": dest.name, "automatic": automatic},
            )
        return dest

    def restore(self, user: CurrentUser, backup_path: str) -> dict:
        require_owner(user)
        path = Path(backup_path)
        if not path.exists():
            raise ValidationError("Backup file not found.")
        # Keep a pre-restore copy
        safety = self.create(user, automatic=True)
        self.db.conn.close()
        shutil.copy2(path, database_path())
        return {"safety_copy": safety.name, "restored": path.name}

    def maybe_daily_backup(self) -> Path | None:
        today = now().date().isoformat()
        marker = backups_dir() / f".last-auto-{today}"
        if marker.exists():
            return None
        dest = self.create(None, automatic=True)
        marker.write_text(now_iso(), encoding="utf-8")
        # Remove old day markers
        for old in backups_dir().glob(".last-auto-*"):
            if old != marker:
                try:
                    old.unlink()
                except OSError:
                    pass
        return dest

    def _prune(self) -> None:
        keep = self.settings.int_value("backup_retain_count", 14)
        files = sorted(backups_dir().glob("goldmine-*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
        for stale in files[keep:]:
            try:
                stale.unlink()
            except OSError:
                pass
