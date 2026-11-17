"""Bybit's public WebSocket: a line that stays open and streams the book and the trades (Lecture 24 §2, §7).

What keeps it trustworthy, each a separate mechanism:

- **Heartbeat.** Every 20 s we send {"op": "ping"}; the exchange answers "pong". If no message at all
  arrives for `stale_after_s`, the line is treated as dead even if it looks open, and we reconnect.
- **Reconnect with backoff.** After a drop we wait 1 s, then 2, 4, ... up to 30 s between attempts, so a
  struggling exchange is not hammered, and we resubscribe on every new connection.
- **Gap check.** The book's update numbers must rise by one (see order_book.py). A gap marks the book
  invalid and forces a reconnect, which brings a fresh snapshot.
- **One bad message never kills the loop.** Each message is handled inside its own try/except.

Verified live (17 November 2026): topics orderbook.50.SYMBOL and publicTrade.SYMBOL, snapshot then deltas,
ping answered with ret_msg "pong". The testnet's feed works the same way, but its book is a different,
much quieter market: use it for the plumbing, not for realistic fills.
"""
import asyncio
import json
import logging
import time
from decimal import Decimal

import websockets

from .order_book import BookGap, OrderBook

URL = {"mainnet": "wss://stream.bybit.com/v5/public/linear", "testnet": "wss://stream-testnet.bybit.com/v5/public/linear"}
log = logging.getLogger(__name__)


class PublicFeed:
    def __init__(self, symbol: str, env: str = "mainnet", depth: int = 50, on_trade=None, on_book=None,
                 ping_every_s: float = 20, stale_after_s: float = 30):
        self.symbol, self.env, self.depth = symbol, env, depth
        self.book = OrderBook(symbol)
        self.on_trade, self.on_book = on_trade, on_book
        self.ping_every_s, self.stale_after_s = ping_every_s, stale_after_s
        self.stats = dict(connects=0, reconnects=0, gaps=0, bad_messages=0, trades=0, book_updates=0,
                          last_message_at=None, last_pong_at=None, connected=False)
        self._stop = asyncio.Event()

    def health(self) -> dict:
        """What the dashboard shows: is the line alive, is the book trustworthy, how often did it break."""
        now = time.time(); last = self.stats["last_message_at"]
        return {**self.stats, "seconds_since_message": None if last is None else round(now - last, 1),
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

    async def _session(self, t_end):
        topics = [f"orderbook.{self.depth}.{self.symbol}", f"publicTrade.{self.symbol}"]
        async with websockets.connect(URL[self.env], ping_interval=None, open_timeout=10) as ws:
            self.stats["connects"] += 1; self.stats["connected"] = True
            self.book = OrderBook(self.symbol)                # a new connection always starts from a snapshot
            await ws.send(json.dumps({"op": "subscribe", "args": topics}))
            last_ping = time.time()
            while not self._stop.is_set() and (t_end is None or time.time() < t_end):
                if time.time() - last_ping >= self.ping_every_s:
                    await ws.send(json.dumps({"op": "ping"})); last_ping = time.time()
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=self.stale_after_s)
                except asyncio.TimeoutError:
                    log.warning("public feed: no message for %s s, treating the line as dead", self.stale_after_s)
                    raise
                self.stats["last_message_at"] = time.time()
                try:
                    self._handle(json.loads(raw))
                except BookGap:
                    self.stats["gaps"] += 1
                    raise                                     # reconnect: the fresh snapshot repairs the book
                except Exception:                             # one bad message must never stop the feed
                    self.stats["bad_messages"] += 1
                    log.exception("public feed: bad message skipped")

    def _handle(self, m: dict):
        if m.get("op") == "ping" or m.get("ret_msg") == "pong":
            self.stats["last_pong_at"] = time.time(); return
        if m.get("op") == "subscribe":
            if not m.get("success"):
                raise RuntimeError(f"subscription refused: {m.get('ret_msg')}")
            return
        topic = m.get("topic", "")
        if topic.startswith("orderbook."):
            self.book.apply(m["type"], m["data"], m.get("cts") or m.get("ts"))
            self.stats["book_updates"] += 1
            if self.on_book and self.book.valid:
                self.on_book(self.book)
        elif topic.startswith("publicTrade."):
            for t in m["data"]:
                self.stats["trades"] += 1
                if self.on_trade:
                    self.on_trade(dict(ts_ms=int(t["T"]), side=t["S"], price=Decimal(t["p"]), qty=Decimal(t["v"]), trade_id=t["i"]))
