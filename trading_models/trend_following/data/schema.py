"""The typed container every layer above the data sources reads: `InstrumentPanel`.

One instrument per column, one row per timestamp, same index and columns across every field
that is provided. `close` is the only mandatory field (every signal and the engine can run on
close alone); `open`/`high`/`low`/`volume` are needed by some signals (Donchian, ATR-based
rules); `funding_rate`/`open_interest` are perp-specific and `None` for equities/ETFs.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

_OPTIONAL_FIELDS = ("open", "high", "low", "volume", "funding_rate", "open_interest")


@dataclass(frozen=True)
class InstrumentPanel:
    close: pd.DataFrame
    open: pd.DataFrame | None = None
    high: pd.DataFrame | None = None
    low: pd.DataFrame | None = None
    volume: pd.DataFrame | None = None
    funding_rate: pd.DataFrame | None = None
    open_interest: pd.DataFrame | None = None

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        """Index is a strictly increasing, unique DatetimeIndex; every provided field shares
        `close`'s index and columns exactly (no silent reindex/misalignment downstream)."""
        idx = self.close.index
        if not isinstance(idx, pd.DatetimeIndex):
            raise TypeError("InstrumentPanel.close must have a DatetimeIndex")
        if not idx.is_monotonic_increasing:
            raise ValueError("InstrumentPanel.close index must be sorted ascending")
        if idx.has_duplicates:
            raise ValueError("InstrumentPanel.close index has duplicate timestamps")
        for name in _OPTIONAL_FIELDS:
            field = getattr(self, name)
            if field is None:
                continue
            if not field.index.equals(idx):
                raise ValueError(f"InstrumentPanel.{name} index does not match close's index")
            if not field.columns.equals(self.close.columns):
                raise ValueError(f"InstrumentPanel.{name} columns do not match close's columns")

    @property
    def instruments(self) -> list[str]:
        return list(self.close.columns)

    def returns(self) -> pd.DataFrame:
        """Simple daily returns of `close`. Recomputed on each call, not cached: cheap, and
        avoids staleness if a caller ever mutates the underlying frame."""
        return self.close.pct_change()

    def has(self, *fields: str) -> bool:
        """True if every named optional field (e.g. 'high', 'funding_rate') is present."""
        return all(getattr(self, f, None) is not None for f in fields)

    def loc(self, index: pd.Index) -> InstrumentPanel:
        """A new panel restricted to `index` (e.g. for a walk-forward train/test split)."""
        return InstrumentPanel(
            close=self.close.loc[index],
            open=self.open.loc[index] if self.open is not None else None,
            high=self.high.loc[index] if self.high is not None else None,
            low=self.low.loc[index] if self.low is not None else None,
            volume=self.volume.loc[index] if self.volume is not None else None,
            funding_rate=self.funding_rate.loc[index] if self.funding_rate is not None else None,
            open_interest=self.open_interest.loc[index] if self.open_interest is not None else None,
        )
