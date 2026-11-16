"""Covariance estimators. Each takes a returns DataFrame and returns an assets x assets DataFrame.

Planned: Marchenko-Pastur denoising, detoning.
"""

from __future__ import annotations

import pandas as pd
from sklearn.covariance import LedoitWolf


def sample_cov(returns: pd.DataFrame) -> pd.DataFrame:
    return returns.cov()


def ledoit_wolf_cov(returns: pd.DataFrame) -> pd.DataFrame:
    """Ledoit-Wolf shrinkage towards a scaled identity."""
    est = LedoitWolf().fit(returns.to_numpy())
    return pd.DataFrame(est.covariance_, index=returns.columns, columns=returns.columns)
