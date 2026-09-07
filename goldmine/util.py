from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo
import json


def local_tz():
    try:
        return datetime.now().astimezone().tzinfo
    except Exception:
        return ZoneInfo("UTC")


def now() -> datetime:
    return datetime.now().astimezone()


def now_iso() -> str:
    return now().replace(microsecond=0).isoformat()


def parse_dt(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=now().tzinfo)
    return dt


def to_json(value) -> str:
    return json.dumps(value, ensure_ascii=False, default=str, sort_keys=True)


def money(amount: float | None, symbol: str = "₹") -> str:
    if amount is None:
        return "—"
    return f"{symbol}{amount:,.2f}"


def format_dt(value: str | None) -> str:
    if not value:
        return "—"
    try:
        dt = parse_dt(value)
        return dt.strftime("%d %b %Y %H:%M")
    except Exception:
        return value


def format_date(value: str | None) -> str:
    if not value:
        return "—"
    try:
        return parse_dt(value).strftime("%d %b %Y")
    except Exception:
        return value[:10]
