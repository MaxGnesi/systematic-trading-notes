"""Lecture 13, correlation assumptions and a stress test of the baseline (results/hypotheses.md, 2026-11-16, plan fixed before any result).

(1) Split a class into two groups only where the data show two stable groups. (2) The correlations the portfolio assumes, within and across
classes, in three scenarios (calm 2017; average 2008-09 to 2025; crisis: the highest of 2008-09, 2020, 2022). (3) The baseline's weights
under each scenario, scaled to 10% on 2023-2025, and the bound with every correlation at 1.
Output: results/corr_stress.json, figures/27_corr_stress.png. Usage: python l27_corr_stress.py"""
import json, os, sys, warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform
from sklearn.metrics import adjusted_rand_score

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path[:0] = [str(REPO), str(REPO / "lectures" / "12-trend-speeds-by-asset-class" / "scripts"), str(REPO / "lectures" / "11-choosing-the-markets" / "scripts")]
import l26 as L26  # noqa: E402

RES, FIG = Path(os.environ.get("L27_RESULTS", HERE.parent / "results")), HERE.parent / "figures"
UNI = json.loads((REPO / "lectures" / "11-choosing-the-markets" / "results" / "fill.json").read_text(encoding="utf-8"))["reviews"]
CORE = [f"{r}_{s}" for r in ("ewma", "breakout", "return") for s in (61, 89, 127, 179)] + ["ewma_251"]
CALM, AVG = ("2017-01-01", "2017-12-31"), ("2008-09-01", "2025-12-31")
CRISES = {"2008-2009": ("2008-09-01", "2009-03-31"), "2020": ("2020-02-15", "2020-06-30"), "2022": ("2022-01-01", "2022-12-31")}
RECENT = ("2023-01-01", "2025-12-31")
CLASSES = ["Equity", "Rates", "Credit", "Commodities", "FX"]


def market_stream(t):
    N = L26.net(pd.read_parquet(L26.OUT / "streams" / f"{t}.parquet"))
    X = N[[c for c in CORE if c in N.columns]].dropna(how="all")
    X = X / X.rolling(252, min_periods=126).std().shift(1)                   # each stream at unit risk, known at the time
    return X.mean(axis=1)


def members(year):
    return UNI[str(year)]["sc"]


def corr(S, w):
    return S.loc[w[0]:w[1]].dropna(how="all").corr(min_periods=40)


def block_avgs(C, cls):
    """Average correlation within each class and between each pair of classes."""
    out = {}
    for a in CLASSES:
        for b in CLASSES:
            ia, ib = cls[a], cls[b]
            vals = [C.loc[x, y] for x in ia for y in ib if x != y and x in C and y in C and not np.isnan(C.loc[x, y])]
            out[(a, b)] = float(np.mean(vals)) if vals else np.nan
    return out


def weights(cls):
    """Risk weights: markets at equal risk within their class, classes at equal risk (unit-risk streams)."""
    w = {}
    for c, ms in cls.items():
        for m in ms: w[m] = 1 / len(CLASSES) / len(ms)
    return pd.Series(w)


def vol(w, C):
    M = C.reindex(index=w.index, columns=w.index).fillna(0.0).to_numpy(copy=True)
    np.fill_diagonal(M, 1.0)
    return float(np.sqrt(w.values @ M @ w.values))


def bets(C, w):
    M = C.reindex(index=w.index, columns=w.index).fillna(0.0).to_numpy(copy=True); np.fill_diagonal(M, 1.0)
    return float(w.sum() ** 2 / (w.values @ M @ w.values))


if __name__ == "__main__":
    allm = sorted({m for y in range(2009, 2026) for ms in members(y).values() for m in ms})
    S = pd.DataFrame({t: market_stream(t) for t in allm})
    out = {}

    # idea 1: split a class into two stable groups?
    parts, agree = {}, {c: [] for c in CLASSES}
    for y in range(2012, 2026):
        for c, ms in members(y).items():
            if len(ms) < 3: continue
            C = corr(S[ms], (f"{y - 2}-01-01", f"{y}-12-31")).fillna(0)
            D = squareform(np.clip(1 - C.values, 0, 2), checks=False)
            lab = fcluster(linkage(D, "average"), 2, "maxclust")
            parts[(y, c)] = dict(zip(ms, lab))
            if (y - 1, c) in parts:
                prev = parts[(y - 1, c)]; common = [m for m in ms if m in prev]
                if len(common) >= 3: agree[c].append(adjusted_rand_score([prev[m] for m in common], [parts[(y, c)][m] for m in common]))
    end = members(2025)
    out["split"] = {}
    for c in CLASSES:
        if not agree[c]: out["split"][c] = dict(median_agreement=None, accepted=False); continue
        med = float(np.median(agree[c])); acc = med >= 0.5
        rec = {"median_agreement": med, "accepted": acc}
        if (2025, c) in parts:
            g = parts[(2025, c)]; groups = {k: [m for m in g if g[m] == k] for k in sorted(set(g.values()))}
            ms = end[c]; C = corr(S[ms], RECENT)
            flat = pd.Series(1 / len(ms), index=ms)
            split = pd.Series({m: 1 / len(groups) / len(gm) for gm in groups.values() for m in gm})
            rec.update(groups_2025=list(groups.values()), bets_flat=bets(C, flat), bets_split=bets(C, split))
        out["split"][c] = rec
    print("idea 1: two stable groups per class?")
    for c, r in out["split"].items(): print(f"  {c:12s} {r}")

    # idea 2: the correlation assumptions
    cls = {c: end[c] for c in CLASSES}
    scen = {"Calm (2017)": corr(S, CALM), "Average (2008-2025)": corr(S, AVG)}
    crisis_mats = {k: corr(S, w) for k, w in CRISES.items()}
    stack = np.stack([m.reindex(index=allm, columns=allm).values for m in crisis_mats.values()])
    scen["Crisis (highest of 2008-09, 2020, 2022)"] = pd.DataFrame(np.nanmax(stack, axis=0), index=allm, columns=allm)
    table = {}
    for k, C in scen.items():
        b = block_avgs(C, cls)
        table[k] = {"within": {c: b[(c, c)] for c in CLASSES}, "across": float(np.nanmean([b[(a, bb)] for i, a in enumerate(CLASSES) for bb in CLASSES[i + 1:]])),
                    "pairs": {f"{a} / {bb}": b[(a, bb)] for i, a in enumerate(CLASSES) for bb in CLASSES[i + 1:]}}
    out["assumptions"] = table
    print("\nidea 2: average correlation of trend streams, within each class and across classes")
    for k, v in table.items():
        print(f"  {k:42s} within " + " ".join(f"{c[:5]} {v['within'][c]:+.2f}" for c in CLASSES) + f" | across {v['across']:+.2f}")

    # idea 3: the stress test
    w = weights(cls)
    base = vol(w, corr(S, RECENT)); k = 0.10 / base
    stress = {"Measured, 2023-2025 (the target)": 10.0}
    for name, C in {**scen, **{f"Crisis window {kk}": m for kk, m in crisis_mats.items()}}.items():
        stress[name] = 100 * k * vol(w, C)
    stress["Every correlation at 1 (bound)"] = 100 * k * float(w.sum())
    out["stress_total_pct"] = stress
    print("\nidea 3: the baseline's 10% total under each scenario (% a year)")
    for n, v in stress.items(): print(f"  {n:42s} {v:5.1f}%")
    (RES / "corr_stress.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
