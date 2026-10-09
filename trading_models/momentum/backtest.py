"""Daily backtest of a weight panel with cash, transaction costs and short borrow cost."""

from __future__ import annotations

import numpy as np
import pandas as pd


def backtest(
    returns: pd.DataFrame,
    weights: pd.DataFrame,
    cash_rate: pd.Series,
    cost_bps: float = 0.0,
    borrow_bps: float = 0.0,
    lag: int = 1,
    trade_threshold: float = 0.005,
) -> pd.DataFrame:
    """Daily gross and net returns of `weights`, traded `lag` days after they are set.

    cash_rate: daily return on cash. Uninvested capital and short proceeds earn it; leverage
    above 1 pays it. cost_bps: one-way cost per unit of traded notional. borrow_bps: annual fee
    on short notional. Weights that are NaN (signal warm-up) are treated as flat. A *trade* is a
    change in one asset's weight of at least `trade_threshold` of NAV (default 0.5%) on a day.
    """
    w = weights.shift(lag).reindex(returns.index).fillna(0.0)
    rf = cash_rate.reindex(returns.index).ffill().fillna(0.0)
    gross = (w * returns).sum(axis=1) + (1.0 - w.sum(axis=1)) * rf
    change = w.diff().abs()
    turnover = 0.5 * change.sum(axis=1)
    turnover.iloc[0] = 0.0
    trades = (change >= trade_threshold).sum(axis=1)
    trades.iloc[0] = 0
    cost = turnover * cost_bps / 1e4
    borrow = w.clip(upper=0.0).abs().sum(axis=1) * borrow_bps / 1e4 / 252.0
    return pd.DataFrame(
        {
            "gross": gross,
            "net": gross - cost - borrow,
            "turnover": turnover,
            "trades": trades,
            "gross exposure": w.abs().sum(axis=1),
            "net exposure": w.sum(axis=1),
            "cash": rf,
        }
    )


def summarise(bt: pd.DataFrame, start: pd.Timestamp | None = None) -> dict[str, float]:
    """Sharpe (on excess return over cash), volatility, drawdown and trading intensity."""
    d = bt.loc[start:] if start is not None else bt
    out: dict[str, float] = {}
    for kind in ("gross", "net"):
        excess = d[kind] - d["cash"]
        out[f"{kind} Sharpe"] = float(excess.mean() / excess.std() * np.sqrt(252))
    equity = (1.0 + d["net"]).cumprod()
    out["net return p.a."] = float(equity.iloc[-1] ** (252 / len(d)) - 1.0)
    out["volatility"] = float(d["net"].std() * np.sqrt(252))
    out["max drawdown"] = float((equity / equity.cummax() - 1.0).min())
    out["turnover p.a."] = float(d["turnover"].mean() * 252)
    if "trades" in d:
        out["trades p.a."] = float(d["trades"].mean() * 252)
    out["avg gross exposure"] = float(d["gross exposure"].mean())
    out["avg net exposure"] = float(d["net exposure"].mean())
    return out
