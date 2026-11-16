"""Spectral risk parity: spread risk evenly across the principal components of the covariance.

Portfolio variance splits exactly over the eigenvectors of the covariance:
    w' S w = sum_k lambda_k * (v_k' w)^2
so component k carries the share p_k = lambda_k (v_k' w)^2 / (w' S w). The effective number of
bets (Meucci, 2009) is exp(-sum p_k ln p_k): 1 when one component holds all the risk, N when
risk is spread evenly over all N components.

Two allocators are provided:
  * unconstrained: p_k equal for all k. Equal risk needs exposure y_k = c / sqrt(lambda_k) to every
    component, i.e. w = sum_k s_k v_k / sqrt(lambda_k) with arbitrary signs s_k, so the solution
    is a family of 2^N portfolios, not one. We take s_k = sign(v_k' 1), which aligns each
    exposure with the equal-weight direction. The result is generally long-short and gives the
    lowest-variance components as much risk as the largest, so it leverages the noisiest part
    of the covariance.
  * long-only: maximise the effective number of bets subject to w >= 0, sum(w) = 1 (a smooth,
    non-convex problem solved from several starting points).

`n_components` limits the entropy to the top-k components (the "signal" part of the spectrum),
which stops the optimiser chasing the near-null directions. Further options:
`eigenvalue_floor` (fraction of the largest eigenvalue) lifts the smallest eigenvalues, a ridge-like
regularisation; `pc1_budget` fixes PC1's target risk share and spreads the rest evenly (KL
divergence to that budget); `ignore_pc1` drops PC1 from the objective (its share is then
unconstrained); `cov_fn` replaces the sample covariance (for example with a denoised one).
`switch_tol` (long-only only) adds hysteresis against local-optimum flips: the optimiser is
warm-started from the previous call's weights and only moves to a different optimum if that
improves the objective by more than `switch_tol`. It makes the allocator stateful.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from trading_models.allocation.base import Allocator


def _eig_desc(cov: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    lam, v = np.linalg.eigh(cov)
    return lam[::-1], v[:, ::-1]


def pc_risk_shares(w: np.ndarray, cov: np.ndarray) -> np.ndarray:
    """Share of portfolio variance carried by each principal component (descending eigenvalue)."""
    lam, v = _eig_desc(np.asarray(cov, dtype=float))
    contrib = lam * (v.T @ np.asarray(w, dtype=float)) ** 2
    return contrib / contrib.sum()


def effective_number_of_bets(
    w: np.ndarray, cov: np.ndarray, n_components: int | None = None
) -> float:
    """exp(entropy) of the component risk shares, over the top `n_components` if given."""
    p = pc_risk_shares(w, cov)
    if n_components is not None:
        p = p[:n_components] / p[:n_components].sum()
    p = p[p > 1e-15]
    return float(np.exp(-(p * np.log(p)).sum()))


class SpectralRiskParity(Allocator):
    """Risk parity across the principal components of the sample covariance."""

    def __init__(
        self,
        n_components: int | None = None,
        long_only: bool = True,
        eigenvalue_floor: float = 0.0,
        pc1_budget: float | None = None,
        ignore_pc1: bool = False,
        cov_fn=None,
        switch_tol: float | None = None,
    ):
        self.n_components = n_components
        self.long_only = long_only
        self.eigenvalue_floor = eigenvalue_floor
        self.pc1_budget = pc1_budget
        self.ignore_pc1 = ignore_pc1
        self.cov_fn = cov_fn
        self.switch_tol = switch_tol
        self._last: np.ndarray | None = None

    def weights(self, returns: pd.DataFrame) -> pd.Series:
        cov = (returns.cov() if self.cov_fn is None else self.cov_fn(returns)).to_numpy()
        cov = cov / np.mean(np.diag(cov))  # scale-free: shares do not depend on the scale
        n = len(cov)
        if not self.long_only:
            lam, v = _eig_desc(cov)
            signs = np.sign(v.T @ np.ones(n))
            signs[signs == 0] = 1.0
            w = v @ (signs / np.sqrt(lam))
            return pd.Series(w / w.sum(), index=returns.columns)

        k = self.n_components or n
        lam, v = _eig_desc(cov)
        lam = np.maximum(lam, self.eigenvalue_floor * lam[0])
        idx = np.arange(1 if self.ignore_pc1 else 0, k)
        budget = None
        if self.pc1_budget is not None and not self.ignore_pc1:
            budget = np.full(len(idx), (1.0 - self.pc1_budget) / (len(idx) - 1))
            budget[0] = self.pc1_budget

        def loss(w: np.ndarray) -> float:
            contrib = (lam * (v.T @ w) ** 2)[idx]
            p = np.clip(contrib / contrib.sum(), 1e-15, None)
            if budget is None:
                return float((p * np.log(p)).sum())  # negative entropy
            return float((budget * np.log(budget / p)).sum())  # KL divergence to the budget

        inv_vol = 1.0 / np.sqrt(np.diag(cov))

        def solve(x0: np.ndarray):
            return minimize(
                loss,
                x0,
                method="SLSQP",
                bounds=[(0.0, 1.0)] * n,
                constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1.0}],
                options={"ftol": 1e-12, "maxiter": 500},
            )

        fresh = [solve(x0) for x0 in (np.ones(n) / n, inv_vol / inv_vol.sum())]
        best = min(fresh, key=lambda res: res.fun)
        if self.switch_tol is not None and self._last is not None:
            kept = solve(self._last)
            if best.fun >= kept.fun - self.switch_tol:
                best = kept
        w = np.clip(best.x, 0.0, None)
        w = w / w.sum()
        self._last = w
        return pd.Series(w, index=returns.columns)
