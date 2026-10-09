"""Public FRED series (no API key) with a local CSV cache in data/raw.

Used to check interpretations against independent, non-ETF data (yields, spreads, VIX).
Notes on the source: ICE BofA index series such as BAMLH0A0HYM2 currently expose only about
three years of history on FRED. Yields are end-of-day constructions, slightly out of sync
with ETF closes, so daily correlations against them are attenuated.
"""

from __future__ import annotations

import io
import urllib.request
from pathlib import Path

import pandas as pd

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={}"


def _parse_fred_csv(text: str, series_id: str) -> pd.Series:
    df = pd.read_csv(io.StringIO(text), index_col=0, parse_dates=True)
    return pd.to_numeric(df.iloc[:, 0], errors="coerce").rename(series_id).dropna()


def load_fred(
    series_ids: list[str], refresh: bool = False, cache_dir: Path = RAW_DIR
) -> pd.DataFrame:
    """Levels of each FRED series as columns, on the union of their dates (NaN where missing)."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    cols = []
    for sid in series_ids:
        path = cache_dir / f"fred_{sid}.csv"
        if refresh or not path.exists():
            with urllib.request.urlopen(_URL.format(sid), timeout=30) as resp:
                path.write_text(resp.read().decode(), encoding="utf-8")
        cols.append(_parse_fred_csv(path.read_text(encoding="utf-8"), sid))
    return pd.concat(cols, axis=1, sort=True)
