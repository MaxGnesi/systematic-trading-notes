"""Marchenko-Pastur (MP) denoising of a correlation matrix.

Random-matrix theory: for N assets and T i.i.d. observations, the eigenvalues of a
sample correlation matrix of pure noise fall in [var*(1-sqrt(q))^2, var*(1+sqrt(q))^2]
with q = N/T. Eigenvalues above the upper bound are treated as signal; the rest as noise.
Method follows Lopez de Prado, "Machine Learning for Asset Managers" (2020), ch. 2.

Both shrinkage variants keep the matrix symmetric, positive semi-definite and unit
diagonal, so no Higham repair is needed after them (Higham is still the last step of
the pipeline for anything applied on top).

Caveat: the noise band assumes i.i.d. data. Autocorrelation, fat tails and regime
changes make the effective T smaller than the row count, so the true noise band is wider.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar
from scipy.stats import gaussian_kde


def mp_bounds(q: float, var: float = 1.0) -> tuple[float, float]:
    """(lambda_min, lambda_max) of the MP distribution for ratio q = N/T (q <= 1)."""
    return var * (1 - np.sqrt(q)) ** 2, var * (1 + np.sqrt(q)) ** 2


def mp_pdf(x: np.ndarray, q: float, var: float = 1.0) -> np.ndarray:
    lo, hi = mp_bounds(q, var)
    x = np.asarray(x, dtype=float)
    out = np.zeros_like(x)
    inside = (x > lo) & (x < hi)
    out[inside] = np.sqrt((hi - x[inside]) * (x[inside] - lo)) / (2 * np.pi * var * q * x[inside])
    return out


def fit_mp_variance(eigvals: np.ndarray, q: float) -> float:
    """Noise variance that best matches a kernel density of the eigenvalues to the MP density.

    Lopez de Prado's approach. Unreliable for very small N (the density of a dozen
    eigenvalues is barely defined), so prefer var=1.0 in that case.
    """
    grid = np.linspace(max(eigvals.min() * 0.5, 1e-6), eigvals.max() * 1.05, 500)
    emp = gaussian_kde(eigvals, bw_method="silverman")(grid)

    def sse(var: float) -> float:
        return float(np.sum((mp_pdf(grid, q, var) - emp) ** 2))

    return float(minimize_scalar(sse, bounds=(1e-3, 1.0), method="bounded").x)


def _to_corr(c: np.ndarray) -> np.ndarray:
    d = 1.0 / np.sqrt(np.diag(c))
    out = c * np.outer(d, d)
    return (out + out.T) / 2


def denoise_corr(
    corr: pd.DataFrame,
    q: float,
    alpha: float = 0.0,
    method: str = "eigen",
    var: float | str = 1.0,
) -> tuple[pd.DataFrame, int]:
    """Denoise `corr` (N x N) given q = N/T. Returns (denoised, number_of_signal_eigenvalues).

    Eigenvalues above the MP upper bound are signal and left untouched. Noise handling,
    controlled by alpha in [0, 1] (0 = fully denoise, 1 = no change):

    method="eigen":    noise eigenvalues -> alpha * lambda + (1 - alpha) * mean(noise lambdas),
                       then rescaled to unit diagonal.
    method="targeted": C = C_signal + alpha * C_noise + (1 - alpha) * diag(C_noise), i.e.
                       alpha shrinks only the off-diagonal noise co-movement.

    `var` is the assumed noise variance: 1.0 (default) or "fit" to estimate it.
    """
    if not 0.0 <= alpha <= 1.0:
        raise ValueError("alpha must be in [0, 1]")
    w, v = np.linalg.eigh(corr.to_numpy())
    w, v = w[::-1], v[:, ::-1]  # descending
    noise_var = fit_mp_variance(w, q) if var == "fit" else float(var)
    n_signal = int((w > mp_bounds(q, noise_var)[1]).sum())
    if n_signal == 0 or n_signal == len(w):
        return corr.copy(), n_signal

    if method == "eigen":
        w2 = w.copy()
        w2[n_signal:] = alpha * w[n_signal:] + (1 - alpha) * w[n_signal:].mean()
        out = _to_corr((v * w2) @ v.T)
    elif method == "targeted":
        c_sig = (v[:, :n_signal] * w[:n_signal]) @ v[:, :n_signal].T
        c_noise = (v[:, n_signal:] * w[n_signal:]) @ v[:, n_signal:].T
        out = c_sig + alpha * c_noise + (1 - alpha) * np.diag(np.diag(c_noise))
        out = (out + out.T) / 2
    else:
        raise ValueError("method must be 'eigen' or 'targeted'")
    return pd.DataFrame(out, index=corr.index, columns=corr.columns), n_signal


def detone_corr(corr: pd.DataFrame, n_remove: int = 1) -> pd.DataFrame:
    """Remove the `n_remove` largest eigen-components (the "market" mode); rescale to unit diagonal.

    Lopez de Prado's "detoning". This is NOT noise removal: the components removed are the
    strongest real signal. It exposes the finer structure that a dominant common factor
    hides, which helps clustering (HRP, NCO). The result has rank N - n_remove, so it is
    singular and must not be inverted for optimisation; it also drops real market risk.
    Removing more than one or two components leaves tiny diagonals, and the rescaling then
    amplifies estimation error.
    """
    if not 1 <= n_remove < len(corr):
        raise ValueError("n_remove must be between 1 and N - 1")
    w, v = np.linalg.eigh(corr.to_numpy())
    w, v = w[::-1], v[:, ::-1]
    c = corr.to_numpy() - (v[:, :n_remove] * w[:n_remove]) @ v[:, :n_remove].T
    if np.diag(c).min() <= 1e-10:
        raise ValueError("an asset is fully explained by the removed components; cannot rescale")
    return pd.DataFrame(_to_corr(c), index=corr.index, columns=corr.columns)
