"""The data layer: a typed instrument panel, plus adapters onto real data sources.

`schema.InstrumentPanel` is the one container every other layer reads: OHLCV, optionally funding
and open interest. Validated once at construction (aligned index/columns, no duplicate or
unordered timestamps), so a misalignment surfaces at the data boundary, not three layers downstream
in a silently-wrong backtest.
"""

from trading_models.trend_following.data.schema import InstrumentPanel

__all__ = ["InstrumentPanel"]
