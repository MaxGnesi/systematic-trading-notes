"""Minute history for the live bot: the saved monthly files, topped up from Deribit's REST API (Lecture 24 §8).

The live bot must compute its signal exactly as the backtest did, so it builds the same hourly closes from
the same one-minute candles: the close of the minute that ends at `decision_minute` past each hour. On start
it reads what was downloaded and fetches the rest (at most 5,000 minutes per request); at each decision it
fetches only the last few minutes. Only finished minutes are used: the minute still running is dropped.
"""
import time
from pathlib import Path

import pandas as pd

from capstone.connectors import deribit_rest

HIST = Path(__file__).resolve().parents[1] / "data" / "history"
MINUTE = 60_000


def _fetch(env: str, instrument: str, start_ms: int, end_ms: int) -> pd.DataFrame:
    rows, t = [], start_ms
    while t < end_ms:
        e = min(t + 5000 * MINUTE, end_ms)
        for b in deribit_rest.candles(env, instrument, t, e):
            rows.append((b["start_ms"], float(b["close"])))
        t = e
        time.sleep(0.1)
    return pd.DataFrame(rows, columns=["ts", "close"]).drop_duplicates("ts")


class MinuteCloses:
    """The one-minute closes of one instrument, kept up to date."""

    def __init__(self, instrument: str, env: str = "mainnet", days: int = 400):
        self.instrument, self.env = instrument, env
        now = int(time.time() * 1000)
        start = now - days * 86_400_000
        parts = [pd.read_parquet(f, columns=["ts", "close"]) for f in sorted(HIST.glob("candles_1m_*.parquet"))]
        have = pd.concat(parts) if parts else pd.DataFrame(columns=["ts", "close"])
        have = have[have.ts >= start]
        last = int(have.ts.max()) + MINUTE if len(have) else start
        new = _fetch(env, instrument, last, now)
        self.df = pd.concat([have, new]).drop_duplicates("ts").sort_values("ts").reset_index(drop=True)
        self._trim_running()

    def _trim_running(self):
        now_minute = int(time.time() * 1000) // MINUTE * MINUTE
        self.df = self.df[self.df.ts < now_minute]          # the minute still running is not a close yet

    def update(self):
        last = int(self.df.ts.max())
        new = _fetch(self.env, self.instrument, last - 5 * MINUTE, int(time.time() * 1000))
        self.df = pd.concat([self.df[self.df.ts < last - 5 * MINUTE], new]).drop_duplicates("ts").sort_values("ts").reset_index(drop=True)
        self._trim_running()

    def hourly(self, decision_minute: int) -> pd.Series:
        """The close of the minute ending at `decision_minute` past each hour, indexed by that decision time."""
        s = pd.Series(self.df.close.to_numpy(), index=pd.to_datetime(self.df.ts, unit="ms", utc=True))
        s = s[s.index.minute == (decision_minute - 1) % 60]
        s.index = s.index + pd.Timedelta(minutes=1)
        return s
