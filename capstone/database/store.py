"""Small write and read helpers for the tables. Each function does one thing; nothing decides here."""
from datetime import datetime, timezone
from decimal import Decimal

from capstone.database.connection import DB


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def upsert_bar(db: DB, symbol: str, bar: dict, source: str) -> None:
    db.execute("DELETE FROM bars_1m WHERE symbol = ? AND start_ms = ?", (symbol, bar["start_ms"]))
    db.execute("INSERT INTO bars_1m (symbol, start_ms, open, high, low, close, volume, trades, source) VALUES (?,?,?,?,?,?,?,?,?)",
               (symbol, bar["start_ms"], bar["open"], bar["high"], bar["low"], bar["close"], bar["volume"], bar.get("trades"), source))


def bot_event(db: DB, level: str, kind: str, detail: str = "") -> None:
    db.execute("INSERT INTO bot_events (at, level, kind, detail) VALUES (?,?,?,?)", (now_iso(), level, kind, detail))


def record_order(db: DB, o: dict, reason: str = "", detail: str = "") -> None:
    """Insert or update an order's current state, and append the change to its history if the state changed."""
    now = now_iso()
    row = db.query("SELECT status FROM orders WHERE client_order_id = ?", (o["client_order_id"],))
    if not row:
        db.execute("INSERT INTO orders (client_order_id, exchange_order_id, symbol, side, order_type, time_in_force, price, qty, "
                   "reduce_only, status, reason, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                   (o["client_order_id"], o.get("exchange_order_id"), o["instrument"], o["side"], o["order_type"],
                    "post_only" if o.get("post_only") else "GTC", o.get("price"), o["amount"], int(o.get("reduce_only", False)),
                    o["state"], reason, now, now))
        changed = True
    else:
        changed = row[0][0] != o["state"] or bool(detail)
        db.execute("UPDATE orders SET exchange_order_id = COALESCE(?, exchange_order_id), price = ?, qty = ?, status = ?, updated_at = ? "
                   "WHERE client_order_id = ?", (o.get("exchange_order_id"), o.get("price"), o["amount"], o["state"], now, o["client_order_id"]))
    if changed:
        db.execute("INSERT INTO order_status_history (client_order_id, status, at, detail) VALUES (?,?,?,?)",
                   (o["client_order_id"], o["state"], now, detail))


def open_orders_in_db(db: DB, symbol: str) -> set[str]:
    return {r[0] for r in db.query("SELECT client_order_id FROM orders WHERE symbol = ? AND status IN ('open', 'untriggered')", (symbol,))}


def reconcile(db: DB, symbol: str, exchange_open: list[dict], exchange_position: Decimal, ledger_position: Decimal) -> list[str]:
    """Compare our records with the exchange: open orders by label, and the position. Records the result;
    returns the differences found (empty = in agreement). Never changes anything on the exchange."""
    ours, theirs = open_orders_in_db(db, symbol), {o["client_order_id"] for o in exchange_open if o["client_order_id"]}
    drift = []
    if ours != theirs:
        drift.append(f"open orders: ours {sorted(ours)} vs exchange {sorted(theirs)}")
    if ledger_position != exchange_position:
        drift.append(f"position: ours {ledger_position} vs exchange {exchange_position}")
    now = now_iso()
    db.execute("INSERT INTO reconciliation_events (at, kind, status, ours, theirs, action) VALUES (?,?,?,?,?,?)",
               (now, "open_orders", "drift" if ours != theirs else "ok", ",".join(sorted(ours)), ",".join(sorted(theirs)), "none"))
    db.execute("INSERT INTO reconciliation_events (at, kind, status, ours, theirs, action) VALUES (?,?,?,?,?,?)",
               (now, "position", "drift" if ledger_position != exchange_position else "ok", str(ledger_position), str(exchange_position), "none"))
    return drift
