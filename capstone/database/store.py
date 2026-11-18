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


def record_fill(db: DB, f: dict) -> bool:
    """Record one execution; the exchange's execution id makes it impossible to count a fill twice."""
    if db.query("SELECT 1 FROM fills WHERE exec_id = ?", (f["exec_id"],)):
        return False
    from datetime import datetime, timezone
    at = datetime.fromtimestamp(f["ts_ms"] / 1000, timezone.utc).isoformat(timespec="milliseconds")
    db.execute("INSERT INTO fills (exec_id, client_order_id, exchange_order_id, symbol, side, price, qty, fee, fee_currency, is_maker, at) "
               "VALUES (?,?,?,?,?,?,?,?,?,?,?)", (f["exec_id"], f["client_order_id"], f["exchange_order_id"], f["instrument"], f["side"],
                                                   f["price"], f["amount"], f["fee"], f["fee_currency"], int(f["is_maker"]), at))
    return True


def ledger_position(db: DB, symbol: str) -> Decimal:
    """Our position as our own recorded fills add up to: buys minus sells, in USD for an inverse contract."""
    total = Decimal(0)
    for side, qty in db.query("SELECT side, qty FROM fills WHERE symbol = ?", (symbol,)):
        total += Decimal(str(qty)) if side == "buy" else -Decimal(str(qty))
    return total


def record_equity(db: DB, equity_btc: Decimal, price: Decimal | None, position_usd: Decimal | None) -> None:
    db.execute("INSERT INTO equity_snapshots (at, equity_btc, price, position_usd) VALUES (?,?,?,?)", (now_iso(), equity_btc, price, position_usd))


def record_decision(db: DB, strategy: str, symbol: str, signal: int, action: str, target_qty, arrival_price, reason: str, params_hash: str) -> None:
    db.execute("INSERT INTO decisions (at, strategy, symbol, signal, action, target_qty, arrival_price, reason, params_hash) VALUES (?,?,?,?,?,?,?,?,?)",
               (now_iso(), strategy, symbol, signal, action, target_qty, arrival_price, reason, params_hash))


def order_exists(db: DB, client_order_id: str) -> bool:
    return bool(db.query("SELECT 1 FROM orders WHERE client_order_id = ?", (client_order_id,)))
