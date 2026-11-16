"""Nested Clustered Optimisation (NCO), Lopez de Prado (2019).

1. Cluster the assets on the correlation distance sqrt((1 - rho) / 2).
2. Inside each cluster, compute weights with an "inner" optimiser.
3. Collapse every cluster into one portfolio (its inner weights) and compute the covariance of
   those cluster portfolios.
4. Across clusters, compute weights with an "outer" optimiser on that reduced covariance.
5. Final weight of an asset = its inner weight x its cluster's outer weight.

Because every optimisation is done on a small block (a cluster, or the handful of cluster
portfolios), estimation error and ill-conditioning stay contained. Weights are long-only and sum
to one whenever the inner and outer optimisers are.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import fcluster, linkage
from sklearn.metrics import silhouette_score

from trading_models.allocation.base import Allocator
from trading_models.allocation.hrp import correlation_distance
from trading_models.allocation.risk_based import (
    erc_weights,
    inverse_vol_weights,
    min_variance_weights,
)
from trading_models.risk.covariance import sample_cov

OPTIMISERS = {
    "inverse_vol": inverse_vol_weights,
    "erc": erc_weights,
    "min_var": min_variance_weights,
    "equal": lambda cov: np.ones(len(cov)) / len(cov),
}


def cluster_labels(
    corr: pd.DataFrame, n_clusters: int | str = 3, method: str = "ward", max_k: int = 8
) -> np.ndarray:
    """Cluster labels from hierarchical clustering; `n_clusters="auto"` maximises the silhouette."""
    dist = correlation_distance(corr)
    tree = linkage(dist, method)
    if n_clusters != "auto":
        return fcluster(tree, int(n_clusters), "maxclust")
    from scipy.spatial.distance import squareform

    full = squareform(dist)
    best_k, best_score = 2, -np.inf
    for k in range(2, min(max_k, len(corr) - 1) + 1):
        labels = fcluster(tree, k, "maxclust")
        if len(set(labels)) < 2:
            continue
        score = silhouette_score(full, labels, metric="precomputed")
        if score > best_score:
            best_k, best_score = k, score
    return fcluster(tree, best_k, "maxclust")


class NCO(Allocator):
    """Nested clustered optimisation with pluggable inner/outer optimisers.

    `inner` and `outer` are keys of `OPTIMISERS` ('inverse_vol', 'erc', 'min_var', 'equal').
    `cov_fn` replaces the sample covariance (for example with a shrunk or denoised one).
    After `weights()` the fitted structure is available as `clusters_` (label per asset) and
    `cluster_weights_` (outer weights).
    """

    def __init__(
        self,
        n_clusters: int | str = 3,
        inner: str = "erc",
        outer: str = "erc",
        method: str = "ward",
        cov_fn=sample_cov,
    ):
        for name in (inner, outer):
            if name not in OPTIMISERS:
                raise ValueError(f"unknown optimiser {name!r}; choose from {sorted(OPTIMISERS)}")
        self.n_clusters = n_clusters
        self.inner = inner
        self.outer = outer
        self.method = method
        self.cov_fn = cov_fn
        self.clusters_: pd.Series | None = None
        self.cluster_weights_: pd.Series | None = None

    def weights(self, returns: pd.DataFrame) -> pd.Series:
        cov = self.cov_fn(returns)
        c = cov.to_numpy()
        sd = np.sqrt(np.diag(c))
        corr = pd.DataFrame(c / np.outer(sd, sd), index=cov.index, columns=cov.columns)
        labels = cluster_labels(corr, self.n_clusters, self.method)
        groups = sorted(set(labels))

        n = len(c)
        inner_w = np.zeros((n, len(groups)))
        for j, g in enumerate(groups):
            idx = np.where(labels == g)[0]
            inner_w[idx, j] = OPTIMISERS[self.inner](c[np.ix_(idx, idx)])

        cluster_cov = inner_w.T @ c @ inner_w
        outer_w = OPTIMISERS[self.outer](cluster_cov)
        w = inner_w @ outer_w

        self.clusters_ = pd.Series(labels, index=cov.index)
        self.cluster_weights_ = pd.Series(outer_w, index=[f"cluster {g}" for g in groups])
        return pd.Series(w / w.sum(), index=cov.index)
