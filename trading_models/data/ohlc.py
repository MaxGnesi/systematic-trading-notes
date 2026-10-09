"""Daily adjusted OHLC for ETFs from Yahoo Finance, cached as a CSV in data/raw.

`auto_adjust=True` scales open, high, low and close by the same distribution/split factor, so
range-based rules see no artificial gaps on ex-dividend days. Yahoo is convenient but not a
licensed institutional source.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
FIELDS = ("Open", "High", "Low", "Close")


def load_ohlc(
    tickers: list[str],
    start: str | None = None,
    cache: Path | None = None,
    refresh: bool = False,
) -> dict[str, pd.DataFrame]:
    """Adjusted open/high/low/close, each a date x ticker DataFrame keyed by lower-case field.

    `cache` defaults to one shared file, so a call for a ticker set the cache doesn't yet have
    fetches only the missing tickers and merges them in -- a narrower or stale cache from an
    earlier call never silently reindexes to NaN columns for tickers it doesn't happen to hold.
    """
    import yfinance as yf

    cache = cache or RAW_DIR / "etf_ohlc_adjusted.csv"
    existing = None
    missing = list(tickers)
    if cache.exists() and not refresh:
        existing = pd.read_csv(cache, header=[0, 1], index_col=0, parse_dates=True)
        cached_tickers = set(existing.columns.get_level_values(1))
        missing = [t for t in tickers if t not in cached_tickers]

    if refresh or missing:
        fetch_tickers = list(tickers) if refresh else missing
        raw = yf.download(
            fetch_tickers,
            start=start,
            auto_adjust=True,
            actions=False,
            progress=False,
            group_by="column",
        )[list(FIELDS)]
        combined = raw if existing is None else pd.concat([existing, raw], axis=1)
        cache.parent.mkdir(parents=True, exist_ok=True)
        combined.to_csv(cache)

    df = pd.read_csv(cache, header=[0, 1], index_col=0, parse_dates=True)
    return {f.lower(): df[f].reindex(columns=tickers) for f in FIELDS}
