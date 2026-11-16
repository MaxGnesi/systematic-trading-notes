"""Tools for reading the eigenvectors of a correlation matrix.

Everything returns plain pandas/numpy objects so it can be tabulated and plotted.
Conventions: eigenvalues in descending order; each eigenvector's sign is flipped so its
largest absolute weight is positive (the overall sign of an eigenvector is arbitrary).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform


def eigendecompose(corr: pd.DataFrame) -> tuple[np.ndarray, pd.DataFrame]:
    """Eigenvalues (descending) and eigenvectors as a DataFrame (assets x PC1..PCN)."""
    w, v = np.linalg.eigh(corr.to_numpy())
    w, v = w[::-1], v[:, ::-1]
    v = v * np.sign(v[np.abs(v).argmax(axis=0), np.arange(v.shape[1])])
    cols = [f"PC{i + 1}" for i in range(len(w))]
    return w, pd.DataFrame(v, index=corr.index, columns=cols)


def effective_n(v: pd.DataFrame) -> pd.Series:
    """Participation ratio 1 / sum(w^4): about how many assets an eigenvector really uses."""
    return 1.0 / (v**4).sum()


def coverage_n(v: pd.DataFrame, frac: float = 0.8) -> pd.Series:
    """Fewest assets (largest absolute weight first) holding `frac` of the squared weight."""
    out = {}
    for pc in v:
        sq = np.sort(v[pc].to_numpy() ** 2)[::-1]
        out[pc] = int(np.searchsorted(np.cumsum(sq), frac - 1e-12) + 1)
    return pd.Series(out)


def clean_loadings(v: pd.DataFrame, frac: float = 0.8) -> pd.DataFrame:
    """Keep the assets holding `frac` of each eigenvector's squared weight; the rest become NaN."""
    n = coverage_n(v, frac)
    out = v.copy()
    for pc in v:
        keep = v[pc].abs().nlargest(n[pc]).index
        out.loc[~out.index.isin(keep), pc] = np.nan
    return out


def cluster_blocks(corr: pd.DataFrame, k: int = 3) -> list[list[str]]:
    """Ward clustering on the distance sqrt((1 - rho) / 2); returns k groups of asset names."""
    dist = np.sqrt(0.5 * (1 - corr.to_numpy().clip(-1, 1)))
    np.fill_diagonal(dist, 0)
    labels = fcluster(linkage(squareform(dist, checks=False), "ward"), k, "maxclust")
    return [
        [a for a, lab in zip(corr.columns, labels, strict=True) if lab == g]
        for g in sorted(set(labels))
    ]


def block_shares(v: pd.DataFrame, blocks: dict[str, list[str]]) -> pd.DataFrame:
    """Share of each eigenvector's squared weight that falls in each block (rows sum to 1)."""
    return pd.DataFrame({name: (v.loc[members] ** 2).sum() for name, members in blocks.items()})


def relative_gaps(w: np.ndarray) -> np.ndarray:
    """(w_i - w_{i+1}) / w_i for consecutive eigenvalues."""
    return (w[:-1] - w[1:]) / w[:-1]


def eigenvalue_relative_se(
    z: pd.DataFrame, n_boot: int = 200, block: int = 20, seed: int = 0
) -> np.ndarray:
    """Block-bootstrap relative standard error of each eigenvalue of corr(z)."""
    rng = np.random.default_rng(seed)
    n_obs = len(z)
    draws = []
    for _ in range(n_boot):
        starts = rng.integers(0, n_obs - block, n_obs // block)
        take = np.concatenate([np.arange(s, s + block) for s in starts])
        draws.append(np.linalg.eigvalsh(z.iloc[take].corr().to_numpy())[::-1])
    draws = np.array(draws)
    return draws.std(axis=0) / draws.mean(axis=0)


def eigenvalue_groups(w: np.ndarray, threshold: float) -> list[list[int]]:
    """Group consecutive eigenvalues whose relative gap is below `threshold` (0-based indices)."""
    groups, current = [], [0]
    for i, gap in enumerate(relative_gaps(w)):
        if gap < threshold:
            current.append(i + 1)
        else:
            groups.append(current)
            current = [i + 1]
    groups.append(current)
    return groups


def subspace_overlap(a: np.ndarray, b: np.ndarray) -> float:
    """Mean squared cosine of the principal angles between two column spaces (1 = identical)."""
    return float(np.mean(np.linalg.svd(a.T @ b, compute_uv=False) ** 2))


def subspace_stability(z: pd.DataFrame, cuts: range) -> pd.Series:
    """Overlap of the top-K eigenvector subspace between the first and second half of `z`."""
    half = len(z) // 2
    _, va = eigendecompose(z.iloc[:half].corr())
    _, vb = eigendecompose(z.iloc[half:].corr())
    return pd.Series(
        {k: subspace_overlap(va.to_numpy()[:, :k], vb.to_numpy()[:, :k]) for k in cuts}
    )


def varimax(loadings: np.ndarray, iters: int = 500, tol: float = 1e-9) -> np.ndarray:
    """Orthogonal varimax rotation of an (assets x factors) loading matrix."""
    p, k = loadings.shape
    rot, d = np.eye(k), 0.0
    for _ in range(iters):
        lr = loadings @ rot
        u, sv, vt = np.linalg.svd(loadings.T @ (lr**3 - lr @ np.diag((lr**2).sum(axis=0)) / p))
        rot = u @ vt
        if sv.sum() < d * (1 + tol):
            break
        d = sv.sum()
    return loadings @ rot


def rotated_factors(corr: pd.DataFrame, k: int) -> pd.DataFrame:
    """Varimax factors from the top-k eigenvectors (loadings scaled by sqrt(eigenvalue))."""
    w, v = eigendecompose(corr)
    lr = varimax(v.to_numpy()[:, :k] * np.sqrt(w[:k]))
    lr = lr * np.sign(lr[np.abs(lr).argmax(axis=0), np.arange(k)])
    lr = lr[:, np.argsort(-np.abs(lr).max(axis=0))]
    return pd.DataFrame(lr, index=corr.index, columns=[f"F{i + 1}" for i in range(k)])
