"""Per-fund and per-asset-class attribution of a weight panel's net returns."""

from __future__ import annotations

import pandas as pd

# Asset classes for the 13 fixed-income ETFs (finer than the Rates / Credit-EM / FLOT clustering).
ASSET_CLASS = {
    "SHY": "Short Treasuries",
    "IEI": "Short Treasuries",
    "IEF": "Long Treasuries",
    "TLT": "Long Treasuries",
    "TIP": "TIPS",
    "STIP": "TIPS",
    "MBB": "Mortgage-backed",
    "FLOT": "Floating rate & loans",
    "BKLN": "Floating rate & loans",
    "HYG": "High yield & convertibles",
    "CWB": "High yield & convertibles",
    "EMB": "Emerging markets",
    "EMLC": "Emerging markets",
}


def attribute(
    returns: pd.DataFrame,
    weights: pd.DataFrame,
    cash_rate: pd.Series,
    cost_bps: float = 0.0,
    borrow_bps: float = 0.0,
    lag: int = 1,
) -> pd.DataFrame:
    """Daily net return contributed by each fund, plus 'cash' (same accounting as `backtest`).

    Each fund's column is w * r minus its own share of transaction cost (0.5 * |change in w| * bps)
    and short borrow cost. 'cash' is the return on uninvested capital and short proceeds. The
    columns sum exactly to the net return of `backtest` with the same arguments.
    """
    w = weights.shift(lag).reindex(returns.index).fillna(0.0)
    rf = cash_rate.reindex(returns.index).ffill().fillna(0.0)
    change = w.diff().abs()
    change.iloc[0] = 0.0
    cost = 0.5 * change * cost_bps / 1e4
    borrow = w.clip(upper=0.0).abs() * borrow_bps / 1e4 / 252.0
    out = w * returns.fillna(0.0) - cost - borrow
    out["cash"] = (1.0 - w.sum(axis=1)) * rf
    return out


def by_asset_class(contrib: pd.DataFrame, mapping: dict[str, str] | None = None) -> pd.DataFrame:
    """Sum fund contributions into asset classes (the 'cash' column stays as its own class)."""
    mapping = mapping or ASSET_CLASS
    cols = {c: mapping.get(c, c) for c in contrib.columns}
    return contrib.T.groupby(cols).sum().T
