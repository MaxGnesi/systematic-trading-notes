"""Trend-following research and backtesting platform.

A general, asset-agnostic layer: data -> signals (baseline + envelope) -> sizing -> engine
(backtest) -> evaluation -> robustness. Built alongside `trading_models.momentum` (the
fixed-income ETF trend study, notebooks 09-10) rather than replacing it; `momentum/` stays as
is, and this package reuses its signal functions through adapters rather than duplicating them.

See `README.md` in this directory for the architecture, the decisions behind it, and what is
implemented versus scaffolded only.
"""
