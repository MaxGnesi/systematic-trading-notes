"""Lecture 14, §1: the regime scan (descriptive, nothing switched). For each regime variable, the baseline's Sharpe ratio on the days the filter
would be off (still, or crowded and turning) and on the days it would be on, at the fixed threshold, on the ETFs (2013-2026) and the capstone
futures (2006-2022); the difference with a 90% band (block bootstrap over calendar months). The growth x inflation quadrants, on data as first
published and on today's revised data. Output: results/scan.json, figures/28_scan.png."""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
from plotly.subplots import make_subplots
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l28 as L
from trading_models.plotting import INK, MUTED, SERIES, apply_theme, save_figure
L26 = L.L26
MACRO = (("growth", "Growth (industrial production)"), ("inflation", "Inflation (CPI)"), ("fed", "Fed on hold"))
MARKET = (("volatility", "Volatility (VIX)"), ("correlation", "Correlation across markets"), ("turning", "Turning points"),
          ("curve", "Yield curve (10y-2y)"), ("dollar", "Dollar"))
FIXED = {"correlation": "0.67", "turning": "0.67"}


def off_flag(G, k):
    return G[("fed", "hold")] if k == "fed" else G[(k, FIXED.get(k, "0.33"))]


def band(r, mask, n=2000, seed=20261115):
    """Sharpe ratio on days on minus on days off, block bootstrap over calendar months."""
    mo = r.index.to_period("M"); um = mo.unique(); idx = {u: np.where(mo == u)[0] for u in um}; rng = np.random.default_rng(seed); b = []
    for _ in range(n):
        ii = np.concatenate([idx[um[i]] for i in rng.choice(len(um), len(um))]); rr, mm = r.iloc[ii], mask.iloc[ii]
        b.append(L26.sharpe(rr[~mm]) - L26.sharpe(rr[mm]))
    return [float(np.quantile(b, .05)), float(np.quantile(b, .95))]


if __name__ == "__main__":
    apply_theme(); B = pd.read_parquet(L.OUT / "l28_base.parquet"); out = {}
    for tag, start in (("etf", L.ETF_START), ("futures", L.FUT_START)):
        base = B[tag].dropna().loc[start:L.END[tag]]; G = pd.read_parquet(L.OUT / f"l28_regimes_{tag}.parquet").reindex(base.index); r = base.ret; out[tag] = {}
        for k, _ in MACRO + MARKET:
            f = off_flag(G, k); ok = f.notna(); m = f[ok].astype(bool); rr = r[ok]
            out[tag][k] = dict(share_off=float(m.mean()), sharpe_off=L26.sharpe(rr[m]), sharpe_on=L26.sharpe(rr[~m]),
                               diff=L26.sharpe(rr[~m]) - L26.sharpe(rr[m]), ci90=band(rr, m), days=int(ok.sum()))
        for src in ("", "_revised"):
            g, i = G[(f"growth{src}", "sign")], G[(f"inflation{src}", "sign")]; ok = g.notna() & i.notna()
            q = (np.where(g > 0, "growth up", "growth down") + np.char.array(", ") + np.where(i > 0, "inflation up", "inflation down"))
            q = pd.Series(q, G.index)[ok]
            out[tag]["quadrant" + (src or "_first_published")] = {s: dict(share=float((q == s).mean()), sharpe=L26.sharpe(r[ok][q == s])) for s in sorted(q.unique())}
        a, b = G[("growth", "sign")], G[("growth_revised", "sign")]; c, d = G[("inflation", "sign")], G[("inflation_revised", "sign")]; ok = a.notna() & b.notna() & c.notna() & d.notna()
        out[tag]["quadrant_disagreement"] = float(((a != b) | (c != d))[ok].mean())
        print(tag, json.dumps({k: {kk: (round(vv, 3) if isinstance(vv, float) else vv) for kk, vv in v.items() if kk != "ci90"} for k, v in out[tag].items() if k in dict(MACRO + MARKET)}, indent=0)[:3000])
        print(tag, "quadrants first published:", {s: (round(v["share"], 2), round(v["sharpe"], 2)) for s, v in out[tag]["quadrant_first_published"].items()})
        print(tag, "quadrants revised:", {s: (round(v["share"], 2), round(v["sharpe"], 2)) for s, v in out[tag]["quadrant_revised"].items()}, "| days in a different quadrant:", round(out[tag]["quadrant_disagreement"], 2))
    (L.RESULTS / "scan.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    # chart: l28_charts.py
