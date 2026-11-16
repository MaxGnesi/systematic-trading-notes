"""Risk-based allocators used as comparators: inverse volatility, minimum variance, risk parity.

All are long-only, sum to one, and use only the sample covariance of the returns they are given
(no expected returns).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from trading_models.allocation.base import Allocator


def inverse_vol_weights(cov: np.ndarray) -> np.ndarray:
    """Weight proportional to 1 / volatility, from a covariance matrix."""
    inv = 1.0 / np.sqrt(np.diag(cov))
    return inv / inv.sum()


def min_variance_weights(cov: np.ndarray) -> np.ndarray:
    """Long-only, fully invested minimum-variance weights, from a covariance matrix."""
    cov = cov / np.mean(np.diag(cov))  # scale: raw covariances are tiny and stall the optimiser
    n = len(cov)
    if n == 1:
        return np.ones(1)
    res = minimize(
        lambda w: w @ cov @ w,
        np.ones(n) / n,
        jac=lambda w: 2 * cov @ w,
        method="SLSQP",
        bounds=[(0.0, 1.0)] * n,
        constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1.0}],
        options={"ftol": 1e-14, "maxiter": 1000},
    )
    if not res.success:
        raise RuntimeError(f"minimum-variance optimisation failed: {res.message}")
    w = np.clip(res.x, 0.0, None)
    return w / w.sum()


def erc_weights(cov: np.ndarray, tol: float = 1e-12, max_sweeps: int = 50_000) -> np.ndarray:
    """Equal-risk-contribution weights by cyclical coordinate descent."""
    cov = cov / np.mean(np.diag(cov))
    n = len(cov)
    if n == 1:
        return np.ones(1)
    b = 1.0 / n
    diag = np.diag(cov).copy()
    w = 1.0 / np.sqrt(diag)
    w /= w.sum()
    for _ in range(max_sweeps):
        previous = w.copy()
        for i in range(n):
            c = cov[i] @ w - diag[i] * w[i]
            w[i] = (-c + np.sqrt(c * c + 4.0 * diag[i] * b)) / (2.0 * diag[i])
        if np.max(np.abs(w - previous)) < tol:
            break
    else:
        raise RuntimeError("risk-parity coordinate descent did not converge")
    return w / w.sum()


class InverseVolatility(Allocator):
    """Weight proportional to 1 / volatility."""

    def weights(self, returns: pd.DataFrame) -> pd.Series:
        return pd.Series(inverse_vol_weights(returns.cov().to_numpy()), index=returns.columns)


class MinVariance(Allocator):
    """Long-only global minimum-variance portfolio (fully invested)."""

    def weights(self, returns: pd.DataFrame) -> pd.Series:
        return pd.Series(min_variance_weights(returns.cov().to_numpy()), index=returns.columns)


class EqualRiskContribution(Allocator):
    """Risk parity: every asset contributes the same share of portfolio variance.

    Solves min 0.5 w'Sw - (1/n) sum(log w) by cyclical coordinate descent (Griffin et al. style):
    each coordinate has a closed-form positive root, so no line search or tolerances to tune.
    At the optimum w_i (Sw)_i is the same for every asset, i.e. equal risk contributions.
    """

    def __init__(self, tol: float = 1e-12, max_sweeps: int = 50_000):
        self.tol = tol
        self.max_sweeps = max_sweeps

    def weights(self, returns: pd.DataFrame) -> pd.Series:
        w = erc_weights(returns.cov().to_numpy(), self.tol, self.max_sweeps)
        return pd.Series(w, index=returns.columns)
