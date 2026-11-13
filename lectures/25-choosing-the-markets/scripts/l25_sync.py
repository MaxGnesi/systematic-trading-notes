"""Lecture 25, are the closes synchronous? For US-listed ETFs of foreign markets, the correlation with SPY of daily and of weekly log returns, and of
daily returns one day apart (a stale price would show as a higher weekly than daily correlation and a positive next-day correlation; Burns, Engle
and Mezrich, 1998). QQQ (a US market), TLT and GLD as controls. 2007-2026. Output: results/sync.json."""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l25 as L
ETFS = ["EWJ", "EWA", "EWH", "EWT", "EWY", "FXI", "INDA", "EWG", "EWU", "EWQ", "EWZ", "EWW", "EWC", "QQQ", "TLT", "GLD"]

if __name__ == "__main__":
    close, dv, R, PH, POS = L.load(); c = close["2007":]; d = np.log(c).diff(); w = R["2007":]; out = {}
    for t in ETFS:
        x = d[[t, "SPY"]].dropna(); xw = w[[t, "SPY"]].dropna()
        out[t] = dict(daily=x[t].corr(x.SPY), weekly=xw[t].corr(xw.SPY), etf_after_spy=x[t].corr(x.SPY.shift(1)), etf_before_spy=x[t].corr(x.SPY.shift(-1)), days=len(x))
    (L.RESULTS / "sync.json").write_text(json.dumps(out, indent=1), encoding="utf-8"); print(pd.DataFrame(out).T.round(3).to_string())
