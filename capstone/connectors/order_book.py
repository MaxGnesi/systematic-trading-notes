"""A local copy of the exchange's order book, kept from a snapshot and its changes. Exchange-neutral.

How it works (Lecture 24 §2): the exchange first sends a **snapshot**, the whole book, then only
**changes**: the new size at each price that changed; a size of zero removes the level. Every change
carries its own id and the id of the change before it. If the two do not chain, a change was lost and
our copy is wrong: we must not trade on it, and we ask for a fresh snapshot.

This class knows nothing about any exchange. Each connector translates its exchange's messages into
`snapshot(bids, asks, change_id)` and `change(bids, asks, change_id, prev_change_id)`, with levels as
(price, size) and size 0 meaning "delete". That is what lets the rest of the bot stay the same when the
exchange changes. Prices and sizes are kept as `Decimal`, never `float`, so they are exact.
"""
from dataclasses import dataclass, field
from decimal import Decimal


class BookGap(Exception):
    """A change was lost: the local book can no longer be trusted."""


@dataclass
class OrderBook:
    instrument: str
    bids: dict = field(default_factory=dict)   # price -> size
    asks: dict = field(default_factory=dict)
    last_id: int | None = None                 # id of the last change applied
    ts_ms: int | None = None                   # exchange time of the last message
    valid: bool = False                        # False until a snapshot arrives, and after a gap

    def snapshot(self, bids, asks, change_id: int, ts_ms: int | None = None) -> None:
        self.bids = {Decimal(str(p)): Decimal(str(q)) for p, q in bids if Decimal(str(q)) > 0}
        self.asks = {Decimal(str(p)): Decimal(str(q)) for p, q in asks if Decimal(str(q)) > 0}
        self.last_id, self.ts_ms, self.valid = change_id, ts_ms, True

    def change(self, bids, asks, change_id: int, prev_change_id: int, ts_ms: int | None = None) -> None:
        """Apply one change. Raises BookGap if it does not follow the last one."""
        if not self.valid:
            return                                  # waiting for a snapshot
        if prev_change_id != self.last_id:
            self.valid = False
            raise BookGap(f"{self.instrument}: expected a change after {self.last_id}, got one after {prev_change_id}")
        for levels, updates in ((self.bids, bids), (self.asks, asks)):
            for p, q in updates:
                p, q = Decimal(str(p)), Decimal(str(q))
                if q == 0:
                    levels.pop(p, None)
                else:
                    levels[p] = q
        self.last_id, self.ts_ms = change_id, ts_ms

    def best_bid(self):
        return max(self.bids) if self.bids else None

    def best_ask(self):
        return min(self.asks) if self.asks else None

    def mid(self):
        b, a = self.best_bid(), self.best_ask()
        return (b + a) / 2 if b is not None and a is not None else None

    def depth(self, side: str, n: int = 5):
        """The best n levels of one side ('b' or 'a'), best first, as (price, size)."""
        levels = self.bids if side == "b" else self.asks
        return sorted(levels.items(), reverse=(side == "b"))[:n]

    def crossed(self) -> bool:
        """A best bid at or above the best ask means the copy is broken."""
        b, a = self.best_bid(), self.best_ask()
        return b is not None and a is not None and b >= a
