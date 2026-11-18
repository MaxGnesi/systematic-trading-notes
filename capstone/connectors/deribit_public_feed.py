"""Deribit's public WebSocket: a line that stays open and streams the book and the trades (Lecture 24 §2, §7).

What keeps it trustworthy, each a separate mechanism:

- **Heartbeat.** We ask Deribit to check on us every `heartbeat_s` seconds (public/set_heartbeat); it sends
  a "test_request" and we must answer with public/test, or it closes the line. Independently, if no message
  at all arrives for `stale_after_s`, we treat the line as dead even if it looks open, and reconnect.
- **Reconnect with backoff.** After a drop we wait 1 s, then 2, 4, ... up to 30 s between attempts, so a
  struggling exchange is not hammered, and we resubscribe on every new connection.
- **Gap check.** Each book change names the change before it (prev_change_id). If that is not the last one
  we applied, a change was lost: the book is marked invalid and we reconnect for a fresh snapshot.
- **One bad message never kills the loop.** Each message is handled inside its own try/except.

The connector translates Deribit's formats into the bot's own, so nothing above it knows the exchange:
book levels [action, price, amount] become (price, size) with size 0 for 'delete'; a trade's amount,
in USD for an inverse contract, is also given in BTC (amount / price), the unit of Deribit's candles.

Verified live (17 November 2026, mainnet): JSON-RPC replies to set_heartbeat and subscribe; book snapshot
then 'change' messages whose prev_change_id equalled the previous change_id over 77 messages; levels
['new' | 'change' | 'delete', price, amount]; heartbeat type 'test_request' answered by public/test.
"""
import asyncio
import json
import logging
import time
from decimal import Decimal

import websockets

from .order_book import BookGap, OrderBook

URL = {"mainnet": "wss://www.deribit.com/ws/api/v2", "testnet": "wss://test.deribit.com/ws/api/v2"}
log = logging.getLogger(__name__)


def _levels(rows):
    """Deribit's [action, price, amount] -> (price, size), size 0 for a deletion."""
    return [(p, 0 if action == "delete" else q) for action, p, q in rows]


class PublicFeed:
    def __init__(self, instrument: str, env: str = "mainnet", on_trade=None, on_book=None,
                 heartbeat_s: int = 10, stale_after_s: float = 30, inverse: bool = True):
        self.instrument, self.env, self.inverse = instrument, env, inverse
        self.book = OrderBook(instrument)
        self.on_trade, self.on_book = on_trade, on_book
        self.heartbeat_s, self.stale_after_s = heartbeat_s, stale_after_s
        self.stats = dict(connects=0, reconnects=0, gaps=0, bad_messages=0, trades=0, book_updates=0, heartbeats=0,
                          last_message_at=None, connected=False)
        self._stop = asyncio.Event()
        self._id = 0

    def health(self) -> dict:
        """What the dashboard shows: is the line alive, is the book trustworthy, how often did it break."""
        last = self.stats["last_message_at"]
        return {**self.stats, "seconds_since_message": None if last is None else round(time.time() - last, 1),
                "book_valid": self.book.valid and not self.book.crossed()}

    def stop(self):
        self._stop.set()

    async def run(self, duration_s: float | None = None):
        """Keep the feed alive until stop() or `duration_s` seconds, reconnecting as needed."""
        t_end = None if duration_s is None else time.time() + duration_s
        backoff = 1
        while not self._stop.is_set() and (t_end is None or time.time() < t_end):
            try:
                await self._session(t_end)
                backoff = 1
            except (OSError, websockets.ConnectionClosed, asyncio.TimeoutError, BookGap) as e:
                self.stats["connected"] = False; self.stats["reconnects"] += 1
                log.warning("public feed: %s; reconnecting in %s s", type(e).__name__, backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30)
        self.stats["connected"] = False

    async def _call(self, ws, method: str, params: dict):
        self._id += 1
        await ws.send(json.dumps({"jsonrpc": "2.0", "id": self._id, "method": method, "params": params}))

    async def _session(self, t_end):
        channels = [f"book.{self.instrument}.100ms", f"trades.{self.instrument}.100ms"]
        async with websockets.connect(URL[self.env], ping_interval=None, open_timeout=10, max_size=2**23) as ws:
            self.stats["connects"] += 1; self.stats["connected"] = True
            self.book = OrderBook(self.instrument)            # a new connection always starts from a snapshot
            await self._call(ws, "public/set_heartbeat", {"interval": self.heartbeat_s})
            await self._call(ws, "public/subscribe", {"channels": channels})
            while not self._stop.is_set() and (t_end is None or time.time() < t_end):
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=self.stale_after_s)
                except asyncio.TimeoutError:
                    log.warning("public feed: no message for %s s, treating the line as dead", self.stale_after_s)
                    raise
                self.stats["last_message_at"] = time.time()
                try:
                    m = json.loads(raw)
                    if m.get("method") == "heartbeat":
                        self.stats["heartbeats"] += 1
                        if m["params"].get("type") == "test_request":
                            await self._call(ws, "public/test", {})
                        continue
                    if "error" in m:
                        raise RuntimeError(f"exchange error: {m['error'].get('message')}")
                    if m.get("method") == "subscription":
                        self._handle(m["params"]["channel"], m["params"]["data"])
                except BookGap:
                    self.stats["gaps"] += 1
                    raise                                     # reconnect: the fresh snapshot repairs the book
                except Exception:                             # one bad message must never stop the feed
                    self.stats["bad_messages"] += 1
                    log.exception("public feed: bad message skipped")

    def _handle(self, channel: str, d):
        if channel.startswith("book."):
            if d["type"] == "snapshot":
                self.book.snapshot(_levels(d["bids"]), _levels(d["asks"]), d["change_id"], d.get("timestamp"))
            else:
                self.book.change(_levels(d["bids"]), _levels(d["asks"]), d["change_id"], d["prev_change_id"], d.get("timestamp"))
            self.stats["book_updates"] += 1
            if self.on_book and self.book.valid:
                self.on_book(self.book)
        elif channel.startswith("trades."):
            for t in d:
                self.stats["trades"] += 1
                price, amount = Decimal(str(t["price"])), Decimal(str(t["amount"]))
                qty = amount / price if self.inverse else amount     # bars in BTC, like Deribit's candles
                if self.on_trade:
                    self.on_trade(dict(ts_ms=int(t["timestamp"]), side=t["direction"], price=price, qty=qty,
                                       amount=amount, trade_id=str(t["trade_id"])))
