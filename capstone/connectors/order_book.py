"""A local copy of the exchange's order book, kept from a snapshot and its updates.

How it works (Lecture 24 §2): the exchange first sends a **snapshot**, the whole book, then only
**updates** ("deltas"): the new size at each price that changed; a size of zero removes the level.
Every message carries an update number `u` that rises by exactly one. If a number is skipped, an update
was lost and our copy is wrong: we must not trade on it, and we ask for a fresh snapshot (resubscribe).

Verified live on Bybit's public feed (17 November 2026): snapshot then deltas, `u` consecutive.
Prices and sizes are kept as `Decimal`, never `float`, so they are exact.
"""
from dataclasses import dataclass, field
from decimal import Decimal


class BookGap(Exception):
    """An update number was skipped: the local book can no longer be trusted."""


@dataclass
class OrderBook:
    symbol: str
    bids: dict = field(default_factory=dict)   # price -> size
    asks: dict = field(default_factory=dict)
    last_u: int | None = None                  # update number of the last message applied
    ts_ms: int | None = None                   # exchange time of the last message
    valid: bool = False                        # False until a snapshot arrives, and after a gap

    def apply(self, msg_type: str, data: dict, ts_ms: int | None = None) -> None:
        """Apply one book message. Raises BookGap if an update was missed."""
        u = int(data["u"])
        if msg_type == "snapshot" or u == 1:      # Bybit resends a snapshot (u = 1) after a service restart
            self.bids = {Decimal(p): Decimal(q) for p, q in data.get("b", []) if Decimal(q) > 0}
            self.asks = {Decimal(p): Decimal(q) for p, q in data.get("a", []) if Decimal(q) > 0}
            self.valid = True
        else:
            if not self.valid:
                return                              # waiting for a snapshot; ignore deltas
            if self.last_u is not None and u != self.last_u + 1:
                self.valid = False
                raise BookGap(f"{self.symbol}: update {self.last_u} followed by {u}")
            for side, levels in (("b", self.bids), ("a", self.asks)):
                for p, q in data.get(side, []):
                    p, q = Decimal(p), Decimal(q)
                    if q == 0:
                        levels.pop(p, None)
                    else:
                        levels[p] = q
        self.last_u = u
        self.ts_ms = ts_ms

    def best_bid(self):
        return max(self.bids) if self.bids else None

    def best_ask(self):
        return min(self.asks) if self.asks else None

    def mid(self):
        b, a = self.best_bid(), self.best_ask()
        return (b + a) / 2 if b is not None and a is not None else None

    def depth(self, side: str, n: int = 5):
        """The best n levels of one side, best first, as (price, size)."""
        levels = self.bids if side == "b" else self.asks
        return sorted(levels.items(), reverse=(side == "b"))[:n]

    def crossed(self) -> bool:
        """A best bid at or above the best ask means the copy is broken."""
        b, a = self.best_bid(), self.best_ask()
        return b is not None and a is not None and b >= a
