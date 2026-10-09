"""The catalogue of single-fund trend models used in the trend-following study.

Every family is instantiated on one grid of time frames T (in trading days) so that models can be
compared; each family's other parameters are simple functions of T. NOTE: the label T does not
guarantee equal behaviour across families (see the effective-horizon diagnostic in notebook 09);
compare models by realised trades per year, not by label.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from trading_models.momentum.portfolio import long_flat, long_short_ts
from trading_models.momentum.signals import (
    breakout_position,
    ewma_crossover,
    multi_horizon_sign,
    past_return,
    risk_adjusted_return,
    sma_signal,
    trend_tstat,
)
from trading_models.momentum.signals_ohlc import (
    chandelier_state,
    darvas_state,
    donchian_state,
    kama_signal,
    pivot_state,
    sma_crossover,
    supertrend,
)

LOOKBACKS = {"1m": 21, "2m": 42, "3m": 63, "4m": 84, "6m": 126, "9m": 189, "12m": 252}

G_RET, G_MA, G_BRK, G_STOP = "Return momentum", "Moving averages", "Breakouts", "Volatility stops"


def _clip2(x: pd.DataFrame) -> pd.DataFrame:
    return (x / 2).clip(-1, 1)


def build_catalog(
    close: pd.DataFrame,
    high: pd.DataFrame,
    low: pd.DataFrame,
    lookbacks: dict[str, int] | None = None,
) -> list[dict]:
    """All single-fund signal variants: dicts with group, family, lookback, params, signal, kind.

    kind is 'sign' (+1/-1), 'continuous' (in [-1, 1]) or 'state' (+1/0/-1).
    """
    lookbacks = lookbacks or LOOKBACKS
    catalog: list[dict] = []

    def add(group, family, t, params, signal, kind):
        catalog.append(
            {
                "group": group,
                "family": family,
                "lookback": t,
                "params": params,
                "signal": signal,
                "kind": kind,
            }
        )

    for label, t in lookbacks.items():
        fast, ewma_f, ewma_s = max(5, t // 4), max(3, t / 8), t / 2
        er, slow = max(5, round(t / 5)), max(10, round(t / 2))
        exit_, k = max(5, t // 3), max(3, round(t / 10))
        confirm, atr_p = max(3, round(t / 20)), max(7, round(t / 5))
        add(G_RET, "Pure momentum (sign)", t, label, np.sign(past_return(close, t)), "sign")
        add(
            G_RET,
            "Risk-adjusted momentum (continuous)",
            t,
            label,
            _clip2(risk_adjusted_return(close, t)),
            "continuous",
        )
        add(
            G_RET,
            "Trend t-stat (continuous)",
            t,
            label,
            _clip2(trend_tstat(close, t)),
            "continuous",
        )
        add(G_MA, "Price vs SMA", t, label, sma_signal(close, t), "sign")
        add(
            G_MA,
            "Dual SMA crossover",
            t,
            f"{label} ({fast}/{t}d)",
            sma_crossover(close, fast, t),
            "sign",
        )
        add(
            G_MA,
            "EWMA crossover",
            t,
            f"{label} (half-lives {ewma_f:.0f}/{ewma_s:.0f}d)",
            ewma_crossover(close, ewma_f, ewma_s),
            "sign",
        )
        add(
            G_MA,
            "KAMA (price cross)",
            t,
            f"{label} (ER {er}, slow {slow})",
            kama_signal(close, er, 2, slow, None),
            "sign",
        )
        add(
            G_MA,
            "KAMA (Kaufman filter)",
            t,
            f"{label} (ER {er}, slow {slow})",
            kama_signal(close, er, 2, slow, 0.5),
            "sign",
        )
        add(
            G_BRK,
            "Donchian channel (turtle)",
            t,
            f"{label} (exit {exit_}d)",
            donchian_state(high, low, close, t, exit_),
            "state",
        )
        add(
            G_BRK,
            "Range position (continuous)",
            t,
            label,
            breakout_position(close, t),
            "continuous",
        )
        add(
            G_BRK,
            "Pivot breakout",
            t,
            f"{label} (k={k})",
            pivot_state(high, low, close, k),
            "state",
        )
        add(
            G_BRK,
            "Darvas box",
            t,
            f"{label} (confirm {confirm})",
            darvas_state(high, low, close, confirm, t),
            "state",
        )
        add(
            G_STOP,
            "SuperTrend",
            t,
            f"{label} (ATR {atr_p} x 3)",
            supertrend(high, low, close, atr_p, 3.0),
            "sign",
        )
        add(
            G_STOP,
            "ATR trailing stop (chandelier)",
            t,
            f"{label} (ATR 20 x 3)",
            chandelier_state(high, low, close, t, 20, 3.0),
            "state",
        )

    add(
        G_RET,
        "Pure momentum (sign)",
        252,
        "12m skip 1m",
        np.sign(past_return(close, 252, 21)),
        "sign",
    )
    add(
        G_RET,
        "Risk-adjusted momentum (continuous)",
        252,
        "12m skip 1m",
        _clip2(risk_adjusted_return(close, 252, 21)),
        "continuous",
    )
    add(
        G_RET,
        "Multi-horizon (1,3,6,12m)",
        np.nan,
        "21,63,126,252",
        multi_horizon_sign(close),
        "continuous",
    )
    add(
        G_RET,
        "Multi-horizon (all 7 time frames)",
        np.nan,
        "21 to 252",
        multi_horizon_sign(close, tuple(lookbacks.values())),
        "continuous",
    )
    return catalog


def weights_for(entry: dict, mapping: str, base: pd.DataFrame) -> pd.DataFrame:
    """Target weights of an entry: 'long-flat' switches base weights on, 'long-short' flips them."""
    if mapping == "long-flat":
        return long_flat(entry["signal"], base, continuous=(entry["kind"] == "continuous"))
    if mapping == "long-short":
        return long_short_ts(entry["signal"], base)
    raise ValueError("mapping must be 'long-flat' or 'long-short'")


def find_entry(catalog: list[dict], family: str, params: str) -> dict:
    """The catalogue entry for a family and parameter label."""
    for e in catalog:
        if e["family"] == family and e["params"] == params:
            return e
    raise KeyError(f"no catalogue entry for {family!r} with params {params!r}")
