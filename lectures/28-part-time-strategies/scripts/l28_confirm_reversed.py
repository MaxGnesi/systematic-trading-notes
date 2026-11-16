"""Lecture 28 (2026-11-16, fixed in results/hypotheses.md before running): the Fed and dollar filters reversed, tested on 1990-2005.
Fed moving: off while the Fed changed its target in the past six months. Dollar moving: off while |12-month log change| of the trade-weighted
dollar against major currencies (FRED DTWEXM) is in the top third of its own history to date (at least five years). Both known the day before.
Machinery as l28_confirm_corr. Output: results/confirm_reversed.json."""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l28 as L, l28_confirm as C
from l28_filters import switched, random_sharpes, spells, bh
L26 = L.L26

if __name__ == "__main__":
    R = C.returns(); base = C.portfolio(R).loc[C.START:C.END]; days = pd.bdate_range("1980-01-01", C.END)
    fed_moving = (~L.fed_on_hold(days).astype(bool)).shift(1).reindex(base.index)
    usd = np.log(L.fred("DTWEXM")).reindex(days).ffill(); size = (usd - usd.shift(252)).abs()
    dollar_moving = L.expanding_flags(size, "busy")["0.67"].reindex(base.index)
    gross = float(pd.read_parquet(L.OUT / "l28_base.parquet")[("futures", "gross")].dropna().median())
    ret = base.to_numpy(); g = np.full(len(ret), gross); out = {"always_in": L26.sharpe(base)}
    for k, flag in (("fed moving", fed_moving), ("dollar moving", dollar_moving)):
        off = flag.astype(float).fillna(0).astype(bool)
        r = pd.Series(switched(ret, g, off.to_numpy(), L.LAMBDA, L.COST_BP / 1e4), base.index)
        lo, ln = spells(off); sh = random_sharpes(ret, g, 1 / lo, 1 / ln, float(off.mean()), 1000, 20261116, L.LAMBDA, L.COST_BP / 1e4)
        out[k] = dict(filter=L26.sharpe(r), share_off=float(off.mean()), sharpe_on=L26.sharpe(base[~off]), sharpe_off=L26.sharpe(base[off]),
                      random_median=float(np.median(sh)), random_p95=float(np.quantile(sh, .95)), beaten=float((L26.sharpe(r) > sh).mean()),
                      p=float(1 - (L26.sharpe(r) > sh).mean()), flag_from=str(flag.first_valid_index().date()))
    passed = bh({k: out[k]["p"] for k in ("fed moving", "dollar moving")})
    for k in ("fed moving", "dollar moving"):
        b = out[k]["beaten"]; out[k]["bh"] = bool(passed.get(k, False)) if isinstance(passed, dict) else None
        out[k]["verdict"] = "confirmed" if b >= 0.9 else ("consistent" if b >= 0.7 else "not repeated")
    print(json.dumps(out, indent=1)); (L.RESULTS / "confirm_reversed.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
