"""Lecture 14 (2026-11-16, fixed in results/hypotheses.md before running): the correlation-high filter, the one filter beating at least 70% of its
random filters on both datasets, tested unchanged on the 1990-2005 trend portfolio of l28_confirm (untouched by any filter test).
Off while the six-month average absolute pairwise correlation of the portfolio's markets is in the top third of its own history to date (at
least five years), known the day before; positions a tenth of the way each day; 5 bp per change on the futures baseline's median gross exposure.
Against 1,000 random filters with the same time in the market and spell lengths. Output: results/confirm_corr.json."""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l28 as L, l28_confirm as C
from l28_filters import switched, random_sharpes, spells
L26 = L.L26

if __name__ == "__main__":
    R = C.returns(); base = C.portfolio(R).loc[C.START:C.END]
    X = R.loc["1985-01-01":C.END]; vals = X.to_numpy(); cr = pd.Series(np.nan, X.index)
    for i in range(125, len(X)):
        w = vals[i - 125: i + 1]; ok = np.isnan(w).mean(axis=0) <= 0.1
        if ok.sum() >= 5: c = pd.DataFrame(w[:, ok]).corr(min_periods=100).to_numpy(); cr.iloc[i] = np.nanmean(np.abs(c[np.triu_indices(ok.sum(), 1)]))
    flag = L.expanding_flags(cr, "busy")["0.67"].reindex(base.index)
    off = flag.astype(float).fillna(0).astype(bool)
    gross = float(pd.read_parquet(L.OUT / "l28_base.parquet")[("futures", "gross")].dropna().median())
    ret = base.to_numpy(); g = np.full(len(ret), gross)
    r = pd.Series(switched(ret, g, off.to_numpy(), L.LAMBDA, L.COST_BP / 1e4), base.index)
    lo, ln = spells(off); sh = random_sharpes(ret, g, 1 / lo, 1 / ln, float(off.mean()), 1000, 20261116, L.LAMBDA, L.COST_BP / 1e4)
    out = dict(always_in=L26.sharpe(base), filter=L26.sharpe(r), share_off=float(off.mean()), sharpe_on=L26.sharpe(base[~off]), sharpe_off=L26.sharpe(base[off]),
               random_median=float(np.median(sh)), random_p95=float(np.quantile(sh, .95)), beaten=float((L26.sharpe(r) > sh).mean()), gross=gross,
               flag_from=str(flag.first_valid_index().date()))
    out["verdict"] = "confirmed" if out["beaten"] >= 0.9 else ("consistent" if out["beaten"] >= 0.7 else "not repeated")
    print(json.dumps(out, indent=1))
    (L.RESULTS / "confirm_corr.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
