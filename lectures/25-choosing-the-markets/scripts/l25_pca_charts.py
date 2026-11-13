"""Lecture 25, correlation, factors and co-movement (weekly log returns, 2007-2026):
  24_key        left: the correlation matrix of the 116 ETFs, ordered by class and, within a class, by a clustering tree; right: the factors' sizes
                (eigenvalues) against the Marchenko-Pastur band of pure noise
  25_factors    the first four factors: each market's correlation with the factor (its loading), coloured by class
  25_comovement rolling 52 weeks, the ETFs with data since March 2007: share of the variance on factor 1; average correlation within equity and between
                equity and the other classes
Output: figures/25_*.png and results/pca.json."""
import json, sys, warnings; warnings.filterwarnings("ignore")
from pathlib import Path
import numpy as np, pandas as pd
from plotly.subplots import make_subplots
from scipy.cluster.hierarchy import linkage, leaves_list
from scipy.spatial.distance import squareform
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l25 as L
sys.path.insert(0, str(L.REPO)); from trading_models.plotting import INK, MUTED, GRID, SERIES, apply_theme, save_figure

COL = dict(zip(L.CLASSES, SERIES))
READ = {1: "risk on or off: equity, credit, commodities, currencies against the dollar",
        2: "interest rates: Treasuries, mortgages, TIPS against the dollar, energy, financials",
        3: "growth technology against commodities, gold and currencies",
        4: "income (utilities, real estate, staples, credit) against speculative themes and gold"}


def ordered(C):
    """Class order, and within a class the leaf order of an average-linkage tree, so related markets sit together."""
    out = []
    for k in L.CLASSES:
        m = [x for x in C.index if L.CLASS[x] == k]
        if len(m) > 2:
            D = np.sqrt(np.maximum(2 * (1 - C.loc[m, m].values), 0)); np.fill_diagonal(D, 0); m = [m[i] for i in leaves_list(linkage(squareform(D, checks=False), "average"))]
        out += m
    return out


if __name__ == "__main__":
    apply_theme(); close, dv, R, PH, POS = L.load(); F = R["2007":]; F = F.loc[:, F.notna().sum() >= L.WIN]
    C = L.corr(F, L.MINW); v, E = np.linalg.eigh(C.values); o = np.argsort(v)[::-1]; v, E = v[o], E[:, o]; N, T = len(v), len(F)
    edge = L.mp_edge(N, T, v[0]); lo = (1 - v[0] / N) * (1 - np.sqrt(N / T)) ** 2; nsig = int((v > edge).sum())
    load = pd.DataFrame(E[:, :6] * np.sqrt(v[:6]), C.index, range(1, 7))
    for j in load: load[j] *= np.sign(load[j].loc["SPY"]) if abs(load[j].loc["SPY"]) > 0.05 else np.sign(load[j].loc["IEF"])   # equity (else bonds) positive
    out = dict(n=N, weeks=T, eig=v.tolist(), share=(v / N).tolist(), mp_low=float(lo), mp_edge=float(edge), above=nsig,
               loadings={str(j): load[j].round(4).to_dict() for j in load})

    # key chart
    order = ordered(C); M = C.loc[order, order]; bounds = np.cumsum([sum(L.CLASS[x] == k for x in order) for k in L.CLASSES])
    fig = make_subplots(rows=1, cols=2, column_widths=[0.6, 0.4], horizontal_spacing=0.09,
                        subplot_titles=("Correlation of weekly returns, 116 ETFs", f"Size of each factor (eigenvalue), first 40 of {N}"))
    fig.add_heatmap(z=M.values, x=order, y=order, zmin=-1, zmax=1, zmid=0, colorscale="RdBu_r", colorbar=dict(title=dict(text="correlation", side="bottom"), orientation="h", thickness=10, x=0.3, xanchor="center", y=-0.13, len=0.45),
                    hovertemplate="%{y} and %{x}: %{z:.2f}<extra></extra>", row=1, col=1)
    start = 0
    for k, b in zip(L.CLASSES, bounds):
        for ln in (dict(x0=start - .5, x1=b - .5, y0=start - .5, y1=b - .5),):
            fig.add_shape(type="rect", **ln, line=dict(color=INK, width=1.2), row=1, col=1)
        fig.add_annotation(x=-2, y=(start + b - 1) / 2, text=f"{k} ({b - start})", showarrow=False, xanchor="right", font=dict(size=11, color=COL[k]), row=1, col=1)
        start = b
    fig.update_xaxes(showticklabels=False, showgrid=False, ticks="", row=1, col=1); fig.update_yaxes(showticklabels=False, showgrid=False, ticks="", autorange="reversed", row=1, col=1)
    k = 40; x = np.arange(1, k + 1)
    fig.add_bar(x=x, y=v[:k], marker_color=[SERIES[0] if e > edge else MUTED for e in v[:k]], name="factor above the noise band", showlegend=False, row=1, col=2,
                hovertemplate="factor %{x}: eigenvalue %{y:.2f}<extra></extra>")
    fig.add_hrect(y0=lo, y1=edge, fillcolor=GRID, opacity=0.8, line_width=0, layer="below", row=1, col=2)
    fig.add_hline(y=edge, line=dict(color=INK, width=1, dash="dot"), row=1, col=2)
    fig.add_annotation(x=k, y=np.log10(1.0), text=f"grey band: what pure noise gives<br>(Marchenko-Pastur), {lo:.2f} to {edge:.2f}", showarrow=False, xanchor="right", yanchor="bottom", align="right",
                       font=dict(size=11, color=INK), row=1, col=2)
    fig.add_annotation(x=1, y=np.log10(v[0]), text=f"factor 1: {v[0] / N:.0%} of the variance", showarrow=False, xanchor="left", xshift=12, font=dict(size=11), row=1, col=2)
    fig.add_annotation(x=nsig, y=np.log10(v[nsig - 1]), text=f"{nsig} factors above noise", showarrow=True, ax=70, ay=-120, font=dict(size=11), row=1, col=2)
    fig.update_yaxes(type="log", tickvals=[0.2, 0.5, 1, 2, 5, 10, 20, 50], range=[np.log10(0.15), np.log10(80)], title_text="eigenvalue (log scale); 1 = one market's worth of variance", row=1, col=2)
    fig.update_xaxes(title_text="factor, largest first", row=1, col=2)
    fig.update_layout(title="116 ETFs, a few bets<br><sup>Weekly log returns, January 2007 - October 2026 (shorter for younger ETFs; pairwise correlations); blue bars: factors "
                            "larger than pure noise would give</sup>", height=760, width=1250, margin=dict(t=110, l=150, r=30, b=130))
    save_figure(fig, "25_key", L.FIG)

    # factor loadings
    order = [x for k in L.CLASSES for x in load.sort_values(1, ascending=False).index if L.CLASS[x] == k]
    fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.05,
                        subplot_titles=[f"Factor {j}, {v[j - 1] / N:.0%} of the variance: {READ[j]}" for j in range(1, 5)])
    for j in range(1, 5):
        fig.add_bar(x=order, y=load.loc[order, j], marker_color=[COL[L.CLASS[x]] for x in order], showlegend=False, row=j, col=1,
                    hovertemplate="%{x}: %{y:.2f}<extra>factor " + str(j) + "</extra>")
    for k in L.CLASSES: fig.add_bar(x=[None], y=[None], marker_color=COL[k], name=k, row=1, col=1)
    fig.update_yaxes(range=[-1, 1], zeroline=True, zerolinecolor=MUTED, title_text="correlation with the factor")
    fig.update_xaxes(tickangle=90, tickfont=dict(size=8), row=4, col=1)
    fig.update_annotations(font_size=12, xanchor="left", x=0)
    fig.update_layout(title="What the first four factors are<br><sup>Each bar: one ETF's correlation with the factor (its loading), weekly log returns 2007-2026; ETFs grouped by class, "
                            "sorted by their loading on factor 1; the sign of a factor is arbitrary (set so that SPY, or else IEF, is positive)</sup>",
                      height=1150, width=1250, barmode="overlay", margin=dict(t=130, l=70, r=20, b=80), legend=dict(orientation="h", y=1.06, x=0))
    save_figure(fig, "25_factors", L.FIG)

    # co-movement over time: the ETFs with data since March 2007, rolling 52 weeks
    G = F["2007-03-09":]; G = G.loc[:, G.notna().all()]   # from 9 March 2007, the first weekly return of UUP (the dollar)
    eq = [x for x in G if L.CLASS[x] == "Equity"]; grp = {k: [x for x in G if L.CLASS[x] == k] for k in L.CLASSES[1:]}
    rows = []
    for i in range(52, len(G) + 1):
        W = G.iloc[i - 52:i]; Cw = W.corr().values; ev = np.linalg.eigvalsh(Cw); Cd = pd.DataFrame(Cw, G.columns, G.columns)
        r = dict(t=G.index[i - 1], share1=ev.max() / len(ev))
        e = Cd.loc[eq, eq].values; r["Equity"] = (e.sum() - len(eq)) / (len(eq) * (len(eq) - 1))
        for k, m in grp.items(): r[k] = Cd.loc[eq, m].values.mean()
        r["dollar"] = Cd.loc[eq, "UUP"].mean() if "UUP" in Cd else np.nan
        rows.append(r)
    Q = pd.DataFrame(rows).set_index("t"); Q.to_csv(L.RESULTS / "comovement.csv"); out["comovement_n"] = dict(all=G.shape[1], equity=len(eq), **{k: len(m) for k, m in grp.items()})
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.09, row_heights=[0.4, 0.6],
                        subplot_titles=(f"Share of the variance of {G.shape[1]} ETFs on factor 1", "Average correlation of the equity ETFs: with each other, and with each class"))
    fig.add_scatter(x=Q.index, y=Q.share1, mode="lines", line=dict(color=INK, width=1.6), name="factor 1 share", showlegend=False, row=1, col=1)
    lines = [("Equity", "equity with equity", SERIES[0]), ("Credit", "equity with credit (LQD, the only credit ETF with data since 2007)", SERIES[2]), ("Commodities", "equity with commodities", SERIES[3]),
             ("Rates", "equity with government bonds", SERIES[1]), ("dollar", "equity with the dollar (UUP)", SERIES[4])]
    for c, name, colr in lines:
        fig.add_scatter(x=Q.index, y=Q[c], mode="lines", line=dict(color=colr, width=1.6), name=name, row=2, col=1)
    fig.add_hline(y=0, line=dict(color=MUTED, width=1), row=2, col=1)
    for d, txt in (("2008-10-10", "2008 crisis"), ("2011-08-12", "2011 euro crisis"), ("2020-03-20", "Covid crash"), ("2022-06-17", "2022 inflation")):
        fig.add_vline(x=pd.Timestamp(d), line=dict(color=MUTED, width=1, dash="dot"))
        fig.add_annotation(x=pd.Timestamp(d), y=1, yref="y domain", text=txt, showarrow=False, xanchor="left", xshift=3, yanchor="top", font=dict(size=10, color=MUTED), row=1, col=1)
    fig.update_yaxes(title_text="share of variance", tickformat=".0%", row=1, col=1); fig.update_yaxes(title_text="average correlation", range=[-1, 1], row=2, col=1)
    fig.update_layout(title=f"Co-movement is not constant<br><sup>Rolling 52-week windows of weekly log returns, the {G.shape[1]} ETFs with data since March 2007; a point is dated at the "
                            "end of its window</sup>", height=780, width=1250, margin=dict(t=110, l=70, r=20, b=60), legend=dict(orientation="h", y=-0.08, x=0))
    save_figure(fig, "25_comovement", L.FIG)
    (L.RESULTS / "pca.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    print("eig top", np.round(v[:6], 2), "edge", round(edge, 2), "above", nsig)
    print(Q.describe().round(2).to_string()); print(Q.resample("YE").last().round(2).to_string())
