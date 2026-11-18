"""The live trend bot on the Deribit testnet (Lecture 24 §7): the plumbing around one strategy.

Three jobs run side by side:
  - the market feed (connectors/deribit_public_feed.py): heartbeat, reconnects, gap checks;
  - the heartbeat of the bot itself, once a minute: equity, feed health, a manual stop file;
  - the decisions, once an hour at `decision_minute` past the hour plus a random delay.

What protects the account, each a separate guard:
  - **Start-up reconciliation.** Our leftover open orders are cancelled; the exchange's position must equal
    the one our recorded fills add up to. If not, the bot refuses to trade and says why: a person decides.
  - **No double orders.** Each decision's order label contains its hour (cap-YYYYMMDDHH); after a crash and
    restart, an order already recorded for that hour is never sent again.
  - **Plumbing kill switch.** Trading pauses on a silent feed or an invalid book, on stale prices, on drift
    between our records and the exchange, after repeated order errors, or when the file data/STOP exists.
    There is deliberately no drawdown stop: a trend follower's drawdowns are how it earns.
  - **Hard limit.** The position never exceeds max_position_x_equity x equity, whatever the signal.
  - **No late decisions.** A decision more than 10 minutes late (the computer slept) is skipped, not acted on.
On Ctrl+C the bot stops cleanly and leaves the position as it is; the next start reconciles it.

Usage:  python -m capstone.run_bot [--dry-run] [--hours N] [--once]
  --dry-run  compute and record every decision, send no order
  --hours N  stop after N decisions
  --once     decide immediately on the last finished hour, then stop (for testing the plumbing)
"""
import argparse
import asyncio
import hashlib
import logging
import random
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import numpy as np

from capstone.configs.settings import load_env
from capstone.connectors import deribit_rest
from capstone.connectors.deribit_public_feed import PublicFeed
from capstone.connectors.history import MinuteCloses
from capstone.database.connection import DB
from capstone.database.migrate import migrate
from capstone.database import store
from capstone.executors.gateway import Gateway
from capstone.security.redact import install_log_scrubbing, scrub
from capstone.strategies.trend import params as P
from capstone.strategies.trend.signal import targets

STOP_FILE = Path(__file__).resolve().parent / "data" / "STOP"
CONTRACT = Decimal(10)
log = logging.getLogger("bot")


class Bot:
    def __init__(self, dry_run: bool):
        load_env()
        self.p = P.load()                                   # invalid settings: refuse to start
        self.params_hash = hashlib.sha256(P.FILE.read_bytes()).hexdigest()[:12]
        self.dry = dry_run
        self.db = DB(); migrate(self.db)
        self.gw = Gateway()                                 # testnet only, by construction
        self.inst = deribit_rest.instrument(self.gw.env, self.p.instrument)
        self.feed = PublicFeed(self.p.instrument, "mainnet", inverse=self.inst.instrument_type == "reversed")
        self.paused_reason: str | None = None
        self.order_errors = 0

    # ---- events: everything the bot does is written down -------------------------------------------
    def event(self, level: str, kind: str, detail: str = ""):
        store.bot_event(self.db, level, kind, scrub(detail)); self.db.commit()
        getattr(log, "warning" if level != "info" else "info")("%s: %s", kind, detail)

    def pause(self, reason: str):
        if self.paused_reason is None:
            self.paused_reason = reason
            self.event("critical", "paused", reason + " -- trading stops until a person restarts the bot")

    # ---- §6 reconciliation: trust the exchange, never accept a silent difference ---------------------
    def reconcile(self, at_start: bool = False) -> bool:
        if at_start:
            for o in self.gw.open_orders(self.p.instrument):
                if (o["client_order_id"] or "").startswith("cap-"):
                    if not self.dry:
                        o = self.gw.cancel(o["exchange_order_id"])
                    self.event("warning", "leftover_order", f"{o['client_order_id']} cancelled at start")
        pos = self.gw.position(self.p.instrument)["size_usd"]
        ledger = store.ledger_position(self.db, self.p.instrument)
        drift = store.reconcile(self.db, self.p.instrument, self.gw.open_orders(self.p.instrument), pos, ledger)
        self.db.commit()
        if drift:
            self.pause("reconciliation drift: " + "; ".join(drift))
            return False
        return True

    # ---- the bot's own heartbeat, once a minute ------------------------------------------------------
    async def heartbeat(self):
        while True:
            try:
                s = await asyncio.to_thread(self.gw.account_summary, "BTC")
                pos = (await asyncio.to_thread(self.gw.position, self.p.instrument))["size_usd"]
                store.record_equity(self.db, s["equity"], self.feed.book.mid(), pos); self.db.commit()
                h = self.feed.health()
                store.bot_event(self.db, "info", "heartbeat", f"equity {s['equity']} BTC, position {pos} USD, feed "
                                f"{'ok' if h['book_valid'] else 'NOT valid'}, {h['seconds_since_message']} s since message, "
                                f"reconnects {h['reconnects']}, gaps {h['gaps']}"); self.db.commit()
                if STOP_FILE.exists():
                    self.pause("manual stop: data/STOP exists")
            except Exception as e:                          # a failed heartbeat is recorded, never fatal
                self.event("warning", "heartbeat_failed", f"{type(e).__name__}: {e}")
            await asyncio.sleep(60)

    # ---- one decision ---------------------------------------------------------------------------------
    def decide(self, minutes: MinuteCloses, decision_time: datetime):
        p = self.p
        h = self.feed.health()
        if not h["book_valid"] or h["seconds_since_message"] is None or h["seconds_since_message"] > p.max_feed_silence_s:
            self.event("warning", "skip", f"unhealthy feed: {h}"); return
        minutes.update()
        hourly = minutes.hourly(p.decision_minute)
        if hourly.index[-1] < decision_time:                 # the price we need has not arrived: never trade on stale data
            self.event("warning", "skip", f"stale prices: last close {hourly.index[-1]}, decision {decision_time}"); return
        hourly = hourly[hourly.index <= decision_time]
        sig = targets(hourly, p)
        tx = float(sig["target_x_equity"].iloc[-1])
        if np.isnan(tx):
            self.event("info", "skip", "not enough history for the signal yet"); return
        eq = (self.gw.account_summary("BTC"))["equity"]
        price = Decimal(str(hourly.iloc[-1])); mid = self.feed.book.mid() or price
        target = Decimal(str(tx)) * eq * price
        cap = Decimal(str(p.max_position_x_equity)) * eq * price
        target = max(-cap, min(cap, target))                 # hard limit: a guard against bugs
        band = Decimal(str(p.buffer * float(sig["target_x_equity"].abs().expanding().mean().iloc[-1]))) * eq * price
        pos = self.gw.position(p.instrument)["size_usd"]
        new = (target / CONTRACT).to_integral_value() * CONTRACT
        trade = new - pos
        label = f"cap-{decision_time:%Y%m%d%H}"
        if abs(target - pos) <= band or trade == 0:
            store.record_decision(self.db, "trend", p.instrument, int(np.sign(tx)), "hold", target, mid, f"within buffer {band:.0f}", self.params_hash)
            self.db.commit(); log.info("hold: target %.0f USD, position %s, buffer %.0f", target, pos, band); return
        if store.order_exists(self.db, label):               # restart after a crash: never send the same hour twice
            self.event("warning", "duplicate_avoided", label); return
        side = "buy" if trade > 0 else "sell"
        store.record_decision(self.db, "trend", p.instrument, int(np.sign(tx)), side, target, mid, f"trade {trade} USD", self.params_hash)
        self.db.commit()
        if self.dry:
            log.info("DRY RUN: would %s %s USD (target %.0f, position %s)", side, abs(trade), target, pos); return
        try:
            o = self.gw.submit(p.instrument, side, abs(trade), label, order_type="market", allow_market=True)
            store.record_order(self.db, o, reason="trend"); self.db.commit()
            for _ in range(10):                              # a market order fills at once, possibly in pieces
                fills = self.gw.fills_of_order(o["exchange_order_id"])
                if sum(f["amount"] for f in fills) >= abs(trade):
                    break
                time.sleep(0.5)
            for f in fills:
                store.record_fill(self.db, f)
            store.record_order(self.db, self.gw.order_state(o["exchange_order_id"])); self.db.commit()
            avg = sum(f["price"] * f["amount"] for f in fills) / sum(f["amount"] for f in fills)
            log.info("%s %s USD: average %s, arrival mid %s, slippage %.2f bp", side, abs(trade), avg, mid,
                     float((avg / mid - 1) * (1 if side == "buy" else -1) * 10000))
            self.order_errors = 0
        except Exception as e:
            self.order_errors += 1
            self.event("critical", "order_failed", f"{type(e).__name__}: {e}")
            if self.order_errors >= p.max_order_errors:
                self.pause(f"{self.order_errors} failed orders in a row")
        self.reconcile()

    # ---- the schedule ---------------------------------------------------------------------------------
    async def decisions(self, n_hours: int | None, once: bool):
        minutes = await asyncio.to_thread(MinuteCloses, self.p.instrument, "mainnet", int(self.p.vol_window_days * 2) + 60)
        done = 0
        while n_hours is None or done < n_hours:
            now = datetime.now(timezone.utc)
            if once:
                decision_time = now.replace(minute=self.p.decision_minute, second=0, microsecond=0)
                if decision_time > now:
                    decision_time -= timedelta(hours=1)
            else:
                decision_time = now.replace(minute=self.p.decision_minute, second=0, microsecond=0)
                if decision_time <= now:
                    decision_time += timedelta(hours=1)
                wait = (decision_time - now).total_seconds() + random.uniform(0, self.p.jitter_seconds)
                log.info("next decision %s (+ random delay), in %.0f s", decision_time.isoformat(), wait)
                await asyncio.sleep(wait)
            await asyncio.sleep(2)                           # let the decision minute's candle close
            late = (datetime.now(timezone.utc) - decision_time).total_seconds()
            if not once and late > 600 + self.p.jitter_seconds:   # e.g. the PC slept: never act on an old decision
                self.event("warning", "skip", f"decision for {decision_time:%H:%M} is {late / 60:.0f} min late (did the computer sleep?)")
                continue
            if self.paused_reason:
                log.warning("paused (%s): no decision", self.paused_reason)
            else:
                await asyncio.to_thread(self.decide, minutes, decision_time)
            done += 1
            if once:
                break
        self.feed.stop()

    async def run(self, n_hours, once):
        self.event("info", "start", f"{'dry run' if self.dry else 'live'} on the {self.gw.env}, settings {self.params_hash}")
        if not self.reconcile(at_start=True):
            log.error("refusing to trade: %s", self.paused_reason); return
        feed = asyncio.create_task(self.feed.run())
        beat = asyncio.create_task(self.heartbeat())
        await asyncio.sleep(5)                               # give the feed time for a snapshot
        try:
            await self.decisions(n_hours, once)
        finally:
            beat.cancel(); self.feed.stop()
            await asyncio.gather(feed, return_exceptions=True)
            self.event("info", "stop", "stopped cleanly; the position is left as it is")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--hours", type=int); ap.add_argument("--once", action="store_true")
    a = ap.parse_args()
    bot = Bot(a.dry_run)
    try:
        asyncio.run(bot.run(a.hours, a.once))
    except KeyboardInterrupt:
        bot.event("info", "stop", "Ctrl+C: stopped; the position is left as it is")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    install_log_scrubbing()
    main()
