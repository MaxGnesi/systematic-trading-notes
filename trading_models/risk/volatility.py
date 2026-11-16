"""Volatility estimators and return standardisation.

Convention: every estimator returns the one-step-ahead volatility forecast
sigma_t built from returns up to and including t-1. Dividing r_t by sigma_t
therefore never lets r_t influence its own scale. Inputs are daily returns
with no missing values; outputs have the same index and columns.

Why standardise before estimating correlation: volatility clusters, and
sample correlation is inflated in high-volatility windows because the shared
variance swamps the idiosyncratic part. Nobody "discovered" this alone:
  - Mandelbrot (1963) and Fama (1965) documented volatility clustering.
  - Engle (1982, ARCH) and Bollerslev (1986, GARCH) modelled it.
  - King & Wadhwani (1990) and Boyer, Gibson & Loretan (1999) noted that
    volatility shifts distort measured correlations; Forbes & Rigobon (2002),
    "No Contagion, Only Interdependence", made the heteroskedasticity bias
    the central point.
  - Engle (2002, DCC-GARCH) gave the recipe used here: divide each asset by its
    own conditional volatility, then estimate correlation on the standardised
    returns. J.P. Morgan's RiskMetrics (1996) popularised the EWMA version.
(References are from memory; verify before citing.)

Look-ahead is confined to the choices flagged in each docstring: seeding
`ewma_vol` with a full-sample variance, and `garch_vol(fit="full")`.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.signal import lfilter

_PCT = 100.0  # optimise GARCH on percent returns; daily decimals are badly scaled


def _check(returns: pd.DataFrame) -> None:
    if returns.isna().any().any():
        raise ValueError("returns must not contain NaN; align the panel first")


def rolling_vol(returns: pd.DataFrame, window: int = 30) -> pd.DataFrame:
    """Trailing `window`-day sample standard deviation, lagged one day.

    The first `window` rows are NaN.
    """
    _check(returns)
    return returns.rolling(window).std().shift(1)


def _seed_variance(returns: pd.DataFrame, seed: str | int) -> np.ndarray:
    if seed == "sample":
        return returns.var().to_numpy()
    if isinstance(seed, int):
        return returns.iloc[:seed].var().to_numpy()
    raise ValueError("seed must be 'sample' or an int number of initial observations")


def ewma_vol(
    returns: pd.DataFrame,
    lam: float = 0.94,
    seed: str | int = "sample",
) -> pd.DataFrame:
    """RiskMetrics EWMA: var_t = lam * var_{t-1} + (1 - lam) * r_{t-1}^2.

    `seed` sets var_0, the unconditional variance the recursion starts from:
    "sample" uses the full-sample variance (a small look-ahead that decays as
    lam**t, so ~0.2% weight after 100 days at lam=0.94); an int uses the
    variance of that many initial observations instead.
    """
    _check(returns)
    r2 = returns.to_numpy() ** 2
    x = np.empty_like(r2)
    x[0] = _seed_variance(returns, seed)
    x[1:] = (1.0 - lam) * r2[:-1]
    var = lfilter([1.0], [1.0, -lam], x, axis=0)
    return pd.DataFrame(np.sqrt(var), index=returns.index, columns=returns.columns)


@dataclass(frozen=True)
class GarchParams:
    """GARCH(1,1): h_t = omega + alpha * r_{t-1}^2 + beta * h_{t-1} (daily decimal units)."""

    omega: float
    alpha: float
    beta: float

    @property
    def persistence(self) -> float:
        return self.alpha + self.beta

    @property
    def uncond_var(self) -> float:
        return self.omega / (1.0 - self.persistence)


def _garch_filter(r2: np.ndarray, p: GarchParams, h0: float) -> np.ndarray:
    x = np.empty_like(r2)
    x[0] = h0
    x[1:] = p.omega + p.alpha * r2[:-1]
    return lfilter([1.0], [1.0, -p.beta], x)


def fit_garch11(r: np.ndarray | pd.Series) -> GarchParams:
    """Gaussian quasi-MLE with variance targeting (omega = var * (1 - alpha - beta)).

    Only alpha and beta are estimated; h_0 is the sample variance of `r`, which
    is also the target. Zero conditional mean is assumed.
    """
    x = np.asarray(r, dtype=float) * _PCT
    x2 = x**2
    v = x.var()

    def nll(theta: np.ndarray) -> float:
        alpha, beta = theta
        p = GarchParams(v * (1 - alpha - beta), alpha, beta)
        h = _garch_filter(x2, p, v)
        if not np.all(h > 0):
            return 1e10
        return 0.5 * float(np.sum(np.log(h) + x2 / h))

    best = None
    for start in ([0.05, 0.90], [0.10, 0.80], [0.02, 0.95]):
        res = minimize(
            nll,
            start,
            method="SLSQP",
            bounds=[(1e-6, 0.5), (1e-6, 0.9999)],
            constraints=[{"type": "ineq", "fun": lambda t: 0.9999 - t[0] - t[1]}],
        )
        if best is None or res.fun < best.fun:
            best = res
    alpha, beta = best.x
    return GarchParams(v * (1 - alpha - beta) / _PCT**2, float(alpha), float(beta))


def garch_vol(
    returns: pd.DataFrame,
    fit: str = "full",
    refit_every: int = 63,
    min_obs: int = 756,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Per-asset GARCH(1,1) volatility forecasts and the parameters behind them.

    fit="full":      one fit on the whole sample. Parameters and the variance
                     target use future data, so early forecasts are look-ahead.
    fit="expanding": refit every `refit_every` days on data through the prior
                     day only, and hold the parameters until the next refit.
                     No forecast before `min_obs` (those rows are NaN).

    Returns (vol, params). `params` has columns (param, asset) with param in
    {alpha, beta, persistence, uncond_vol}, indexed by the date each fit took
    effect (a single row for fit="full").
    """
    _check(returns)
    n = len(returns)
    r = returns.to_numpy()
    r2 = r**2
    vol = np.full_like(r, np.nan)

    if fit == "full":
        fit_ends = [n]
        effective = [returns.index[-1]]
        blocks = [(0, n)]
    elif fit == "expanding":
        fit_ends = list(range(min_obs, n, refit_every))
        effective = [returns.index[t] for t in fit_ends]
        blocks = [(t, min(t + refit_every, n)) for t in fit_ends]
    else:
        raise ValueError("fit must be 'full' or 'expanding'")

    rows = []
    for end, (lo, hi) in zip(fit_ends, blocks, strict=True):
        row = {}
        for j, asset in enumerate(returns.columns):
            p = fit_garch11(r[:end, j])
            h = _garch_filter(r2[:, j], p, r[:end, j].var())
            vol[lo:hi, j] = np.sqrt(h[lo:hi])
            row[("alpha", asset)] = p.alpha
            row[("beta", asset)] = p.beta
            row[("persistence", asset)] = p.persistence
            row[("uncond_vol", asset)] = np.sqrt(p.uncond_var)
        rows.append(row)

    params = pd.DataFrame(rows, index=pd.Index(effective, name="effective"))
    params.columns = pd.MultiIndex.from_tuples(params.columns, names=["param", "asset"])
    return pd.DataFrame(vol, index=returns.index, columns=returns.columns), params


def standardize(returns: pd.DataFrame, vol: pd.DataFrame) -> pd.DataFrame:
    """r_t / sigma_t, dropping rows where the volatility forecast is unavailable."""
    return (returns / vol).dropna(how="any")


def cov_from_corr(corr: pd.DataFrame, vol: pd.Series) -> pd.DataFrame:
    """Rebuild a covariance from a correlation matrix and a volatility vector."""
    v = vol.reindex(corr.index).to_numpy()
    return pd.DataFrame(corr.to_numpy() * np.outer(v, v), index=corr.index, columns=corr.columns)
