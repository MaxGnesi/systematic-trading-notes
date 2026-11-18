"""Safe order test on the testnet (step 2b): an order that cannot fill, followed through its whole life.

1. Read the price band and the best bid; price a post-only buy of the minimum size about 2.5% below the
   best bid: inside the band (so it is accepted), far from the market (so it does not fill in seconds).
2. Submit it with our own label, and record it.          -> expect state 'open', also in the exchange's list
3. Amend it a little lower (amount and price together).   -> expect 'open', new price
4. Cancel it.                                             -> expect 'cancelled'
5. Reconcile: our open orders and position against the exchange's. -> expect agreement, flat position
No market order is ever sent. Usage: python -m capstone.tools.safe_order_test
"""
import logging
import secrets
import time
from decimal import Decimal

from capstone.configs.settings import load_env
from capstone.connectors import deribit_rest
from capstone.connectors.deribit_rest import _get
from capstone.database.connection import DB
from capstone.database.migrate import migrate
from capstone.database.store import bot_event, reconcile, record_order
from capstone.executors.gateway import Gateway
from capstone.security.redact import install_log_scrubbing

INSTRUMENT = "BTC-PERPETUAL"
log = logging.getLogger("safe_order_test")


def main():
    load_env()
    g, db = Gateway(), DB(); migrate(db)
    inst = deribit_rest.instrument(g.env, INSTRUMENT)
    t = _get(g.env, "public/ticker", {"instrument_name": INSTRUMENT})
    bid, lo = Decimal(str(t["best_bid_price"])), Decimal(str(t["min_price"]))
    price = inst.round_price(bid * Decimal("0.975"))
    if price <= lo:
        price = inst.round_price(lo + 10 * inst.tick_size)
    assert price < bid * Decimal("0.98"), "the test price must stay far below the market"
    label = f"cap-test-{int(time.time())}-{secrets.token_hex(3)}"
    log.info("best bid %s, band floor %s: post-only buy of %s USD at %s (%.2f%% below the bid), label %s",
             bid, lo, inst.min_amount, price, float(100 * (1 - price / bid)), label)

    o = g.submit(INSTRUMENT, "buy", inst.min_amount, label, price=price, post_only=True)
    record_order(db, o, reason="safe_test"); db.commit()
    seen = [x["client_order_id"] for x in g.open_orders(INSTRUMENT)]
    log.info("1. submitted: state %s, price %s; in the exchange's open orders: %s", o["state"], o["price"], label in seen)

    new_price = price - 2 * inst.tick_size
    o = g.edit(o["exchange_order_id"], inst.min_amount, new_price)
    record_order(db, o, detail=f"amended to {new_price}"); db.commit()
    log.info("2. amended: state %s, price %s", o["state"], o["price"])

    o = g.cancel(o["exchange_order_id"])
    record_order(db, o); db.commit()
    log.info("3. cancelled: state %s", o["state"])

    pos = g.position(INSTRUMENT)["size_usd"]
    drift = reconcile(db, INSTRUMENT, g.open_orders(INSTRUMENT), pos, Decimal("0"))
    bot_event(db, "info" if not drift else "critical", "safe_order_test", "; ".join(drift) or "in agreement"); db.commit()
    log.info("4. reconciliation: %s; position %s USD", "in agreement" if not drift else drift, pos)

    hist = db.query("SELECT status, detail FROM order_status_history WHERE client_order_id = ? ORDER BY id", (label,))
    log.info("history in our database: %s", hist)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    install_log_scrubbing()
    main()
