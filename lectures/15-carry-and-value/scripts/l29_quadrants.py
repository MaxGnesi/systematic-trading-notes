"""Lecture 15 §6.4: carry against trend in Lecture 14's quadrants (volatility, correlation, growth x inflation), futures period, monthly; each
month classified by its quadrant at the end of the month before. Output: results/quadrants.json."""
import json, os, sys
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parent; REPO = HERE.parents[1]
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(REPO / "lectures" / "14-part-time-strategies" / "scripts"))
import l29_combined as M, l29_grids as Gr, l29_bonds_g10 as G, l29 as L
import l28 as L28
from l28_regime_charts import series
RESD = Path(os.environ.get("L29_RESULTS", HERE.parent / "results")); RESD.mkdir(parents=True, exist_ok=True)

if __name__ == "__main__":
    Gs = M.groups(); W = {g: Gr.sig(Gs[g]["C"], Gs[g]["R"]) for g in Gs}
    carry = M.scale_total(pd.DataFrame({g: G.stream(W[g], Gs[g]["R"]) for g in Gs}).mean(axis=1, skipna=True)).loc["2006-01":"2022-10"]
    trend = M.compound(pd.read_parquet(L.RAW / "l29_trend_futures_fixed.parquet")["ret"]).loc["2006-01":"2022-10"]
    base = pd.read_parquet(L28.OUT / "l28_base.parquet")["futures"].dropna().loc[L28.FUT_START:L28.END["futures"]]
    Q = {k: series("futures", k, base)[3] for k in ("volatility", "correlation")}
    R = pd.read_parquet(L28.OUT / "l28_regimes_futures.parquet"); g = R[("growth", "sign")].reindex(base.index); i = R[("inflation", "sign")].reindex(base.index)
    Q["growth x inflation"] = pd.Series(np.where(g > 0, "growth up", "growth down") + np.char.array(", ") + np.where(i > 0, "inflation up", "inflation down"),
                                        base.index).where(g.notna() & i.notna())
    out = {}
    for k, q in Q.items():
        qm = q.resample("ME").last().shift(1); qm.index = qm.index.to_period("M")
        x = pd.concat([carry, trend, qm.reindex(carry.index)], axis=1, keys=["carry", "trend", "q"]).dropna()
        out[k] = {s: dict(carry=float(G.sharpe_m(d["carry"])), trend=float(G.sharpe_m(d["trend"])), months=int(len(d))) for s, d in x.groupby("q")}
        print(k, {s: (round(v["carry"], 2), round(v["trend"], 2), v["months"]) for s, v in out[k].items()})
    (RESD / "quadrants.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
