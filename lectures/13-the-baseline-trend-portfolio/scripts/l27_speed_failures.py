"""Lecture 13 §2.3: which speeds fail most often? EWMA crossover streams, net of costs, every market with data over 2013-2026:
the median Sharpe ratio by speed and the share of markets in which each speed lost money. Output: results/speed_failures.json.
Usage: python l27_speed_failures.py"""
import json, sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path[:0] = [str(REPO), str(REPO / "lectures" / "12-trend-speeds-by-asset-class" / "scripts"), str(REPO / "lectures" / "11-choosing-the-markets" / "scripts")]
import l26 as L  # noqa: E402

SPEEDS = [11, 17, 23, 31, 43, 61, 89, 127, 179, 251, 359]

if __name__ == "__main__":
    rows = []
    for f in sorted((L.OUT / "streams").glob("*.parquet")):
        X = L.net(pd.read_parquet(f)).loc["2013":"2026"]
        if len(X) < 2000: continue
        r = {}
        for s in SPEEDS:
            x = X.get(f"ewma_{s}")
            if x is not None and x.dropna().std() > 0:
                x = x.dropna(); r[s] = float(x.mean() / x.std() * np.sqrt(252))
        rows.append(r)
    D = pd.DataFrame(rows)
    out = {"markets": len(D), "by_speed": {str(s): dict(median_sharpe=float(D[s].median()), share_negative=float((D[s] < 0).mean()),
                                                       p10=float(D[s].quantile(0.1))) for s in SPEEDS}}
    (HERE.parent / "results" / "speed_failures.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))
