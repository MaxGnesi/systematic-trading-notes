"""Price download (Yahoo Finance via yfinance)."""

from __future__ import annotations

import pandas as pd


def load_prices(tickers: list[str], start: str, end: str | None = None) -> pd.DataFrame:
    """Adjusted close prices, one column per ticker.

    Yahoo data is convenient but not survivorship-bias free; do not base
    decisions on results from it without checking the universe.
    """
    import yfinance as yf

    raw = yf.download(tickers, start=start, end=end, auto_adjust=True, progress=False)
    prices = raw["Close"]
    if isinstance(prices, pd.Series):
        prices = prices.to_frame(tickers[0])
    return prices.dropna(how="all").sort_index()


def to_returns(prices: pd.DataFrame, log: bool = False) -> pd.DataFrame:
    """Simple (default) or log returns; the first row is dropped."""
    if log:
        import numpy as np

        return np.log(prices).diff().dropna(how="all")
    return prices.pct_change().dropna(how="all")
