"""Signal layer: Baseline (raw trend estimate) + Envelope (maps it to a position in [-1, 1]).

This split is the key architectural difference from `trading_models.momentum`, where each
signal function already returns a mapped position. Splitting them lets one baseline be tried
under several envelopes and vice versa without duplicating logic -- the "baseline x envelope x
parameter" grid this platform exists to sweep (see `registry` for the catalog that does so).
"""

from trading_models.trend_following.signals.base import Baseline, Envelope
from trading_models.trend_following.signals.ensemble import average_positions, majority_vote
from trading_models.trend_following.signals.envelopes import (
    clip_envelope,
    dual_gate_envelope,
    rank_top_bottom_envelope,
    sign_envelope,
    tanh_envelope,
)

__all__ = [
    "Baseline",
    "Envelope",
    "average_positions",
    "clip_envelope",
    "dual_gate_envelope",
    "majority_vote",
    "rank_top_bottom_envelope",
    "sign_envelope",
    "tanh_envelope",
]
