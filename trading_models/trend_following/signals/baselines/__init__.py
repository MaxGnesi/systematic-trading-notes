"""The signal zoo, grouped as in the project brief: price-based trend/breakout/stop rules
(`price_trend`), trend-strength filters (`trend_strength`), statistical/model-based baselines
(`statistical`). `regime`, `ml` and `carry` are interface-only stubs (see their module
docstrings for why each is deferred).
"""

from trading_models.trend_following.signals.baselines.price_trend import (
    bollinger_state,
    chandelier_baseline,
    donchian_baseline,
    ewma_crossover_baseline,
    hull_ma,
    hull_ma_signal,
    kama_baseline,
    keltner_state,
    macd,
    macd_signal,
    multi_horizon_baseline,
    parabolic_sar,
    past_return_baseline,
    risk_adjusted_return_baseline,
    sma_crossover_baseline,
    sma_signal_baseline,
    supertrend_baseline,
)
from trading_models.trend_following.signals.baselines.statistical import kalman_local_linear_trend
from trading_models.trend_following.signals.baselines.trend_strength import (
    adx,
    efficiency_ratio,
    hurst_exponent,
    regression_slope_tstat,
    rolling_r_squared,
)

__all__ = [
    "adx",
    "bollinger_state",
    "chandelier_baseline",
    "donchian_baseline",
    "efficiency_ratio",
    "ewma_crossover_baseline",
    "hull_ma",
    "hull_ma_signal",
    "hurst_exponent",
    "kalman_local_linear_trend",
    "kama_baseline",
    "keltner_state",
    "macd",
    "macd_signal",
    "multi_horizon_baseline",
    "parabolic_sar",
    "past_return_baseline",
    "regression_slope_tstat",
    "risk_adjusted_return_baseline",
    "rolling_r_squared",
    "sma_crossover_baseline",
    "sma_signal_baseline",
    "supertrend_baseline",
]
