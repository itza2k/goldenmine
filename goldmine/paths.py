from __future__ import annotations

import os
import sys
from pathlib import Path


APP_NAME = "Goldmine"
EDIT_WINDOW_SECONDS = 300  # 5-minute employee edit window


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def app_root() -> Path:
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def data_dir() -> Path:
    if is_frozen():
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
        path = base / APP_NAME
    else:
        path = app_root() / "data"
    path.mkdir(parents=True, exist_ok=True)
    return path


def database_path() -> Path:
    return data_dir() / "goldmine.db"


def backups_dir() -> Path:
    path = data_dir() / "backups"
    path.mkdir(parents=True, exist_ok=True)
    return path


def exports_dir() -> Path:
    path = data_dir() / "exports"
    path.mkdir(parents=True, exist_ok=True)
    return path


def receipts_dir() -> Path:
    path = data_dir() / "receipts"
    path.mkdir(parents=True, exist_ok=True)
    return path
