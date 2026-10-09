"""Trend-following and momentum strategies: signals, position construction, backtest."""

from trading_models.momentum.attribution import ASSET_CLASS, attribute, by_asset_class
from trading_models.momentum.backtest import backtest, summarise
from trading_models.momentum.catalog import LOOKBACKS, build_catalog, find_entry, weights_for
from trading_models.momentum.portfolio import (
    cross_sectional_top_bottom,
    dual_momentum,
    inverse_vol_base,
    long_flat,
    long_short_ts,
    rebalance_every,
    score_weighted,
)
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
    average_true_range,
    chandelier_state,
    darvas_state,
    donchian_state,
    kama,
    kama_signal,
    pivot_state,
    sma_crossover,
    supertrend,
)

__all__ = [
    "ASSET_CLASS",
    "LOOKBACKS",
    "attribute",
    "build_catalog",
    "by_asset_class",
    "find_entry",
    "weights_for",
    "average_true_range",
    "chandelier_state",
    "darvas_state",
    "donchian_state",
    "kama",
    "kama_signal",
    "pivot_state",
    "sma_crossover",
    "supertrend",
    "backtest",
    "breakout_position",
    "cross_sectional_top_bottom",
    "dual_momentum",
    "ewma_crossover",
    "inverse_vol_base",
    "long_flat",
    "long_short_ts",
    "multi_horizon_sign",
    "past_return",
    "rebalance_every",
    "risk_adjusted_return",
    "score_weighted",
    "sma_signal",
    "summarise",
    "trend_tstat",
]
