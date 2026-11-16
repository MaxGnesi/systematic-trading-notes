"""Hierarchical Risk Parity (Lopez de Prado, 2016).

Three steps: (1) cluster assets on the correlation distance sqrt((1 - rho) / 2);
(2) quasi-diagonalise, i.e. reorder assets so similar ones are adjacent (the dendrogram
leaf order); (3) recursive bisection: split the ordered list in half, give each half a share
of the weight inversely proportional to its risk, and repeat inside each half.

The cluster risk is the variance of the half's inverse-variance portfolio. No matrix
inversion is needed, so HRP works with singular or ill-conditioned covariances.
Weights are long-only and sum to one.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import linkage, to_tree
from scipy.spatial.distance import squareform

from trading_models.allocation.base import Allocator
from trading_models.risk.covariance import sample_cov


def correlation_distance(corr: pd.DataFrame) -> np.ndarray:
    """Condensed distance vector sqrt((1 - rho) / 2), the input scipy's linkage expects."""
    dist = np.sqrt(0.5 * (1 - corr.to_numpy().clip(-1, 1)))
    np.fill_diagonal(dist, 0.0)
    return squareform(dist, checks=False)


def quasi_diagonal_order(link: np.ndarray) -> list[int]:
    """Leaf order of the dendrogram (asset positions), left subtree before right."""
    return to_tree(link).pre_order()


def _cluster_variance(cov: np.ndarray, items: list[int]) -> float:
    sub = cov[np.ix_(items, items)]
    ivp = 1.0 / np.diag(sub)
    ivp /= ivp.sum()
    return float(ivp @ sub @ ivp)


@dataclass(frozen=True)
class HRPResult:
    weights: pd.Series
    order: list[str]  # assets in quasi-diagonal order
    link: np.ndarray  # scipy linkage matrix
    splits: pd.DataFrame  # one row per bisection


def hrp(
    cov: pd.DataFrame,
    method: str = "single",
    corr: pd.DataFrame | None = None,
    cluster_risk: str = "variance",
    max_depth: int | None = None,
) -> HRPResult:
    """HRP weights for `cov`. Clusters on `corr` if given, else on the correlation implied by `cov`.

    `method` is the linkage: 'single' (the original paper), 'average' or 'ward'.
    `cluster_risk` is the risk each half is sized by: 'variance' (the original paper) or
    'volatility', which spreads weight less aggressively when volatilities differ a lot.
    `max_depth` limits the bisection: groups still unsplit at that depth are weighted inside by
    the same rule (inverse variance or inverse volatility). 0 means no bisection at all, None
    (the original algorithm) splits down to single assets.
    """
    if cluster_risk not in ("variance", "volatility"):
        raise ValueError("cluster_risk must be 'variance' or 'volatility'")
    assets = list(cov.columns)
    cov_np = cov.to_numpy()
    if corr is None:
        sd = np.sqrt(np.diag(cov_np))
        corr = pd.DataFrame(cov_np / np.outer(sd, sd), index=assets, columns=assets)
    link = linkage(correlation_distance(corr), method)
    order = quasi_diagonal_order(link)

    w = pd.Series(1.0, index=range(len(assets)))
    records = []
    queue = [order]
    depth = 0
    while queue:
        nxt = []
        for items in queue:
            if len(items) < 2:
                continue
            if max_depth is not None and depth >= max_depth:
                inside = 1.0 / np.diag(cov_np)[items]
                inside = inside if cluster_risk == "variance" else inside**0.5
                w[items] *= inside / inside.sum()
                continue
            half = len(items) // 2
            left, right = items[:half], items[half:]
            v_left, v_right = _cluster_variance(cov_np, left), _cluster_variance(cov_np, right)
            r_left, r_right = (
                (v_left, v_right) if cluster_risk == "variance" else (v_left**0.5, v_right**0.5)
            )
            alpha = 1.0 - r_left / (r_left + r_right)  # share to the left half
            w[left] *= alpha
            w[right] *= 1.0 - alpha
            records.append(
                {
                    "depth": depth,
                    "left": ", ".join(str(assets[i]) for i in left),
                    "right": ", ".join(str(assets[i]) for i in right),
                    "left variance": v_left,
                    "right variance": v_right,
                    "share to left": alpha,
                }
            )
            nxt += [left, right]
        queue = nxt
        depth += 1

    weights = pd.Series(w.to_numpy(), index=assets, name="hrp")
    return HRPResult(weights, [assets[i] for i in order], link, pd.DataFrame(records))


class HRPAllocator(Allocator):
    """HRP from a trailing window of returns (sample covariance unless `cov_fn` is given)."""

    def __init__(
        self,
        method: str = "single",
        cov_fn=sample_cov,
        cluster_risk: str = "variance",
        max_depth: int | None = None,
    ):
        self.method = method
        self.cov_fn = cov_fn
        self.cluster_risk = cluster_risk
        self.max_depth = max_depth

    def weights(self, returns: pd.DataFrame) -> pd.Series:
        return hrp(
            self.cov_fn(returns),
            self.method,
            cluster_risk=self.cluster_risk,
            max_depth=self.max_depth,
        ).weights
