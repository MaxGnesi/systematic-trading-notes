"""Turn the stream of public trades into one-minute bars (open, high, low, close, volume).

A bar is finished when the first trade of the next minute arrives; only finished bars are handed on, so
the strategy never acts on a bar that is still moving (Lecture 18: a bar is known only once it closes).
The first bar after starting is dropped: we joined in the middle of its minute, so it is incomplete.

Checked live (17 November 2026) against Bybit's own one-minute candle for the same minute: high, low, close
and volume identical; the open differs, because Bybit opens each candle at the previous candle's close,
while this builder opens at the minute's first trade. Neither is wrong; a backtest must use one convention.
"""
from decimal import Decimal


class BarBuilder:
    def __init__(self, on_bar, minutes: int = 1):
        self.on_bar, self.ms = on_bar, minutes * 60_000
        self.cur = None
        self.first = True

    def add_trade(self, t: dict) -> None:
        start = t["ts_ms"] // self.ms * self.ms
        if self.cur is not None and start > self.cur["start_ms"]:
            if not self.first:
                self.on_bar(self.cur)                  # the previous bar is complete
            self.first = False
            self.cur = None
        if self.cur is None:
            self.cur = dict(start_ms=start, open=t["price"], high=t["price"], low=t["price"], close=t["price"],
                            volume=Decimal(0), trades=0)
        c = self.cur
        c["high"] = max(c["high"], t["price"]); c["low"] = min(c["low"], t["price"]); c["close"] = t["price"]
        c["volume"] += t["qty"]; c["trades"] += 1
