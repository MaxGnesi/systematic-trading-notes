"""The contract every allocation method follows.

To add a method (HRP, risk parity, spectral risk parity, NCO), subclass
`Allocator` in its own module here, and make `weights` return a long-only
Series that sums to 1. The backtester only depends on this interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd


class Allocator(ABC):
    @abstractmethod
    def weights(self, returns: pd.DataFrame) -> pd.Series:
        """Target weights from a trailing window of returns (no look-ahead)."""


class EqualWeight(Allocator):
    """1/N benchmark."""

    def weights(self, returns: pd.DataFrame) -> pd.Series:
        n = returns.shape[1]
        return pd.Series(1.0 / n, index=returns.columns)
