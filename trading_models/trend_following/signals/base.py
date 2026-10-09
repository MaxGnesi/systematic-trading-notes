"""The two protocols every signal in this package satisfies.

A `Baseline` is a raw trend estimate: sign and magnitude both carry information, but scale is
*not* assumed to be in [-1, 1] -- a 20-day return and a Hurst exponent live on different scales,
and squashing them is the Envelope's job, not the Baseline's. Must use data up to and including
each row only (every Baseline in this package is tested for that; see `tests/trend_following`).

An `Envelope` maps one or more Baseline outputs to a target position in [-1, 1] per instrument
(time-series envelopes: sign, clip, tanh), or a joint cross-section of positions summing to a
chosen gross/net exposure (cross-sectional envelopes: rank top/bottom). Envelopes do not size
positions into portfolio weights -- that is `sizing`'s job (vol targeting), kept separate so the
same envelope output works whether sizing targets 5% or 20% annualised instrument volatility.
"""

from __future__ import annotations

from typing import Protocol

import pandas as pd

from trading_models.trend_following.data.schema import InstrumentPanel


class Baseline(Protocol):
    """`(panel, **params) -> DataFrame`, same index and columns as `panel.close`."""

    def __call__(self, panel: InstrumentPanel, **params: object) -> pd.DataFrame: ...


class Envelope(Protocol):
    """`(score, **params) -> DataFrame` of target positions in [-1, 1]."""

    def __call__(self, score: pd.DataFrame, **params: object) -> pd.DataFrame: ...
