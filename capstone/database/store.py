"""Small write and read helpers for the tables. Each function does one thing; nothing decides here."""
from datetime import datetime, timezone

from capstone.database.connection import DB


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def upsert_bar(db: DB, symbol: str, bar: dict, source: str) -> None:
    db.execute("DELETE FROM bars_1m WHERE symbol = ? AND start_ms = ?", (symbol, bar["start_ms"]))
    db.execute("INSERT INTO bars_1m (symbol, start_ms, open, high, low, close, volume, trades, source) VALUES (?,?,?,?,?,?,?,?,?)",
               (symbol, bar["start_ms"], bar["open"], bar["high"], bar["low"], bar["close"], bar["volume"], bar.get("trades"), source))


def bot_event(db: DB, level: str, kind: str, detail: str = "") -> None:
    db.execute("INSERT INTO bot_events (at, level, kind, detail) VALUES (?,?,?,?)", (now_iso(), level, kind, detail))
