"""Lecture 25, do markets trend at the same time? (results/hypotheses.md, addendum 5, fixed 2026-11-13 before the run). Efficiency ratio of Lecture 3 on
weekly closes over 26 weeks, 2007-2026: pairwise correlation of trend strength against that of returns, within and across classes; share on the
first factor; breadth over time; the chosen end-2025 universe against random selections in the same slots. Prices only.
Output: results/trend_strength.json, results/breadth.csv, figures/25_trend_strength.png."""
import json, sys, warnings; warnings.filterwarnings("ignore")
from pathlib import Path
import numpy as np, pandas as pd
from plotly.subplots import make_subplots
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l25 as L
sys.path.insert(0, str(L.REPO)); from trading_models.plotting import INK, MUTED, SERIES, apply_theme, save_figure
N_ER = 26


def offdiag(C, a, b):
    """Mean of C over pairs (i in a, j in b), i != j."""
    M = C.loc[a, b].values.astype(float)
    if a == b: M = M[~np.eye(len(a), dtype=bool)]
    return float(np.nanmean(M))


if __name__ == "__main__":
    apply_theme(); rng = np.random.default_rng(L.SEED); close, dv, R, PH, POS = L.load()
    W = close.resample("W-FRI").last(); W = W["2006-07":]
    ER = (W - W.shift(N_ER)).abs() / W.diff().abs().rolling(N_ER).sum(); ER = ER["2007":]
    Rt = R["2007":]; keep = [x for x in ER.columns if ER[x].notna().sum() >= L.WIN and Rt[x].notna().sum() >= L.WIN]; ER, Rt = ER[keep], Rt[keep]
    CE = L.corr(ER, L.MINW); CR = L.corr(Rt, L.MINW); m = [x for x in CE.index if x in CR.index]; CE, CR = CE.loc[m, m], CR.loc[m, m]
    iu = np.triu_indices(len(m), 1); er_pairs, ret_pairs = CE.values[iu], np.abs(CR.values[iu])
    same = np.array([[L.CLASS[a] == L.CLASS[b] for b in m] for a in m])[iu]
    v = np.sort(np.linalg.eigvalsh(CE.values))[::-1]; vr = np.sort(np.linalg.eigvalsh(CR.values))[::-1]
    out = dict(n=len(m), weeks=int(len(ER)), er_corr_mean=float(er_pairs.mean()), ret_abscorr_mean=float(ret_pairs.mean()),
               er_corr_within=float(er_pairs[same].mean()), er_corr_across=float(er_pairs[~same].mean()),
               ret_within=float(ret_pairs[same].mean()), ret_across=float(ret_pairs[~same].mean()),
               er_share1=float(v[0] / len(v)), ret_share1=float(vr[0] / len(vr)), corr_of_corrs=float(np.corrcoef(er_pairs, ret_pairs)[0, 1]))
    out["by_class"] = {a: {b: offdiag(CE, [x for x in m if L.CLASS[x] == a], [x for x in m if L.CLASS[x] == b]) for b in L.CLASSES} for a in L.CLASSES}
    breadth = ER.mean(axis=1); breadth_cls = pd.DataFrame({k: ER[[x for x in m if L.CLASS[x] == k]].mean(axis=1) for k in L.CLASSES})
    pd.concat([breadth.rename("all"), breadth_cls], axis=1).to_csv(L.RESULTS / "breadth.csv")
    out["breadth"] = dict(mean=float(breadth.mean()), top=[(str(d.date()), round(float(x), 3)) for d, x in breadth.nlargest(5).items()],
                          by_year=breadth.resample("YE").mean().round(3).rename(lambda d: str(d.year)).to_dict())
    # the chosen universe against random selections in the same slots
    sel = json.loads((L.RESULTS / "fill.json").read_text(encoding="utf-8"))["reviews"]["2025"]["sc_div"]
    flat = [x for v_ in sel.values() for x in v_ if x in m]; liq = L.liquidity(dv, pd.Timestamp("2025-12-31"))
    def mean_er(names): s = CE.loc[names, names].values; n = len(names); return float((s.sum() - n) / (n * (n - 1)))
    rand = []
    for _ in range(300):
        s_ = []
        for k, v_ in sel.items():
            pool = [x for x in m if L.CLASS[x] == k and liq.get(x, 0) >= L.FLOOR] or [x for x in v_ if x in m]
            s_ += list(rng.choice(pool, size=min(sum(x in m for x in v_), len(pool)), replace=False))
        rand.append(mean_er(s_))
    rand = np.array(rand); out["universe"] = dict(n=len(flat), er_corr=mean_er(flat), random_median=float(np.median(rand)), share_random_higher=float((rand > mean_er(flat)).mean()))
    (L.RESULTS / "trend_strength.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps({k: v_ for k, v_ in out.items() if k != "by_class"}, indent=1)); print(pd.DataFrame(out["by_class"]).round(2).to_string())

    # chart: left, trend-strength correlation against return correlation for every pair; right, breadth over time by class
    fig = make_subplots(rows=1, cols=2, column_widths=[0.42, 0.58], horizontal_spacing=0.09,
                        subplot_titles=("Do two markets trend at the same time?", "How many markets trend at once? Average trend strength"))
    for msk, name, c in ((~same, "pair from two classes", MUTED), (same, "pair within one class", SERIES[0])):
        fig.add_scatter(x=ret_pairs[msk], y=er_pairs[msk], mode="markers", marker=dict(size=3, color=c, opacity=0.3), name=name, row=1, col=1)
    fig.add_scatter(x=[0, 1], y=[0, 1], mode="lines", line=dict(color=INK, width=1, dash="dot"), name="equal correlation", row=1, col=1)
    fig.update_xaxes(title_text="correlation of weekly returns, sign ignored", range=[0, 1], row=1, col=1)
    fig.update_yaxes(title_text="correlation of trend strength (26-week efficiency ratio)", range=[-0.6, 1], row=1, col=1)
    for i, k in enumerate(L.CLASSES):
        fig.add_scatter(x=breadth_cls.index, y=breadth_cls[k].rolling(4).mean(), mode="lines", line=dict(color=SERIES[i], width=1.3), name=k, row=1, col=2)
    fig.add_scatter(x=breadth.index, y=breadth.rolling(4).mean(), mode="lines", line=dict(color=INK, width=2.4), name="all markets", row=1, col=2)
    fig.update_yaxes(title_text="average efficiency ratio (0: no trend, 1: straight line)", row=1, col=2)
    fig.update_layout(title="Trend strength across markets<br><sup>Efficiency ratio over 26 weeks on weekly closes, 2007-2026 (Lecture 3, §6.1); left: every pair of ETFs; right: "
                            "the average over the ETFs of each class, smoothed over 4 weeks</sup>", height=640, width=1250, margin=dict(t=110, l=70, r=20, b=60),
                      legend=dict(orientation="h", y=-0.14, x=0))
    save_figure(fig, L.PREFIX + "25_trend_strength", L.FIG)
