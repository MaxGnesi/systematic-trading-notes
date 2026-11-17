"""Record the live market into the database: step 1 of the capstone, no account needed.

It fills the last few hours of one-minute candles from Bybit's REST API (one question, one answer), then
keeps the public WebSocket open (a line that stays open) for the chosen time, builds one-minute bars from
the trades, and writes them next to the candles. Disconnects, reconnects and book gaps are written to
bot_events, so the dashboard can show how healthy the feed was.

Usage:  python -m capstone.tools.record_market --minutes 5 [--env mainnet|testnet] [--backfill 240]
"""
import argparse
import asyncio
import logging

from capstone.connectors import bybit_rest
from capstone.connectors.bars import BarBuilder
from capstone.connectors.bybit_public_feed import PublicFeed
from capstone.database.connection import DB
from capstone.database.migrate import migrate
from capstone.database.store import bot_event, upsert_bar
from capstone.security.redact import install_log_scrubbing

log = logging.getLogger("record_market")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="BTCUSDT")
    ap.add_argument("--env", default="mainnet", choices=["mainnet", "testnet"])
    ap.add_argument("--minutes", type=float, default=5)
    ap.add_argument("--backfill", type=int, default=240, help="minutes of past candles to fetch first")
    a = ap.parse_args()

    db = DB(); migrate(db)
    inst = bybit_rest.instrument(a.env, a.symbol)
    log.info("%s %s: tick %s, quantity step %s, minimum %s", a.env, inst.symbol, inst.tick_size, inst.qty_step, inst.min_qty)

    for b in bybit_rest.klines(a.env, a.symbol, "1", min(a.backfill, 1000))[:-1]:   # the last candle is still open
        upsert_bar(db, a.symbol, b, "rest")
    db.commit()

    n_bars = 0

    def on_bar(bar):
        nonlocal n_bars
        upsert_bar(db, a.symbol, bar, "live"); db.commit(); n_bars += 1
        log.info("bar %s  O %s H %s L %s C %s  vol %s  trades %s", bar["start_ms"], bar["open"], bar["high"], bar["low"],
                 bar["close"], bar["volume"], bar["trades"])

    builder = BarBuilder(on_bar)
    feed = PublicFeed(a.symbol, a.env, on_trade=builder.add_trade)
    bot_event(db, "info", "recorder_start", f"{a.env} {a.symbol} for {a.minutes} min"); db.commit()
    asyncio.run(feed.run(duration_s=a.minutes * 60))
    h = feed.health()
    bot_event(db, "info" if h["gaps"] == 0 and h["reconnects"] == 0 else "warning", "recorder_stop",
              f"connects {h['connects']} reconnects {h['reconnects']} gaps {h['gaps']} trades {h['trades']} "
              f"book updates {h['book_updates']} bad messages {h['bad_messages']}")
    db.commit()
    log.info("done: %s live bars; feed health %s", n_bars, h)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    install_log_scrubbing()
    main()
