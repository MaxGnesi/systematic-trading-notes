"""Lecture 25, three charts from saved results:
  25_concordance  every pair since 2007: correlation of weekly returns (sign ignored) against the share of weeks in the same 26-week trend phase,
                  with the duplicate rule and named pairs (results/pairs.parquet)
  25_downside     every pair: correlation over all weeks against correlation in weeks when both fall by more than one standard deviation, with what a
                  normal distribution gives under the same selection (results/screen.json)
  25_tradeoff     the ways to fill the class slots, out of sample 2010-2026: variance of each class explained next year against the overlap next year;
                  medians and interquartile ranges over the 17 years, and random selections in the same slots (results/fill.json)"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
from plotly.subplots import make_subplots
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l25 as L
sys.path.insert(0, str(L.REPO)); from trading_models.plotting import INK, MUTED, GRID, SERIES, apply_theme, save_figure

if __name__ == "__main__":
    apply_theme()

    # correlation against concordance
    P = pd.read_parquet(L.RESULTS / "pairs.parquet"); P["arho"] = P.rho.abs(); same = P.ca == P.cb
    fig = make_subplots(rows=1, cols=1)
    fig.add_shape(type="rect", x0=L.DUP_R, x1=1, y0=L.DUP_C, y1=1, fillcolor=GRID, opacity=0.7, line_width=0, layer="below")
    for m, name, c in ((~same, "pair from two different classes", MUTED), (same, "pair within one class", SERIES[0])):
        fig.add_scatter(x=P.arho[m], y=P.conc[m], mode="markers", marker=dict(size=4, color=c, opacity=0.35), name=name,
                        text=P.a[m] + " / " + P.b[m], hovertemplate="%{text}: |correlation| %{x:.2f}, same phase %{y:.0%}<extra></extra>")
    NAMED = {("QQQ", "AIQ"): (25, -45), ("FXE", "UUP"): (40, 40), ("TLT", "IEF"): (-100, -30), ("IWM", "UFO"): (60, 45), ("EWC", "RWX"): (70, 15),
             ("GDX", "GLD"): (-80, -45), ("XLE", "OIH"): (60, 60), ("EEM", "SPY"): (-80, -25), ("FXI", "KWEB"): (-70, -75)}
    for (a, b), (ax, ay) in NAMED.items():
        r = P[((P.a == a) & (P.b == b)) | ((P.a == b) & (P.b == a))]
        if len(r): fig.add_annotation(x=r.arho.iloc[0], y=r.conc.iloc[0], text=f"{a} / {b}", showarrow=True, arrowwidth=1, ax=ax, ay=ay, font=dict(size=11),
                                      bgcolor="rgba(252,252,251,0.85)")
    fig.add_annotation(x=0.895, y=0.995, xanchor="right", yanchor="top", text="shaded: duplicates, |correlation| at least 0.9<br>and the same phase at least 85% of weeks",
                       showarrow=False, align="right", font=dict(size=11))
    fig.update_xaxes(title_text="correlation of weekly returns, sign ignored", range=[0, 1])
    fig.update_yaxes(title_text="share of weeks in the same 26-week trend phase (sign ignored)", tickformat=".0%", range=[0.4, 1])
    fig.update_layout(title=f"Correlation and trend phases: the same bet, or not?<br><sup>{len(P):,} pairs of ETFs, weekly log returns 2007-2026 (pairs with at least "
                            "three years in common); a trend phase is the sign of the past 26 weeks' return; mirror images (negative correlation) count as the same bet</sup>",
                      height=700, width=1250, margin=dict(t=110, l=80, r=30, b=60), legend=dict(orientation="h", y=-0.1, x=0))
    save_figure(fig, "25_concordance", L.FIG)

    # downside correlation
    S = json.loads((L.RESULTS / "screen.json").read_text(encoding="utf-8")); D = pd.DataFrame(S["downside_pairs"])
    eq = lambda c: c == "Equity"; D["g"] = np.where(eq(D.ca) & eq(D.cb), "both equity", np.where(eq(D.ca) | eq(D.cb), "equity and another class", "neither equity"))
    fig = make_subplots(rows=1, cols=1)
    for (g, c) in (("both equity", SERIES[0]), ("equity and another class", SERIES[1]), ("neither equity", SERIES[2])):
        m = D.g == g
        fig.add_scatter(x=D["all"][m], y=D.down[m], mode="markers", marker=dict(size=4, color=c, opacity=0.3), name=f"{g} ({int(m.sum()):,} pairs)",
                        text=D.a[m] + " / " + D.b[m], hovertemplate="%{text}: all weeks %{x:.2f}, both falling %{y:.2f}<extra></extra>")
    g = D[D["all"] <= 0.95].sort_values("all"); fig.add_scatter(x=g["all"], y=g.normal, mode="lines", line=dict(color=INK, width=2.2), name="what a normal distribution gives in the same weeks")
    fig.add_scatter(x=[-1, 1], y=[-1, 1], mode="lines", line=dict(color=MUTED, width=1, dash="dot"), name="same correlation in falls as in all weeks")
    med = D.groupby("g")[["all", "down", "normal"]].median()
    for gname, c in (("both equity", SERIES[0]), ("equity and another class", SERIES[1])):
        r = med.loc[gname]
        fig.add_annotation(x=r["all"], y=r.down, text=f"median, {gname}: {r.down:.2f} in falls<br>against {r.normal:.2f} for a normal", showarrow=True, ax=170 if gname == "both equity" else -200,
                           ay=230 if gname == "both equity" else -40, font=dict(size=11, color=c), bgcolor="rgba(252,252,251,0.85)")
    fig.update_xaxes(title_text="correlation over all weeks", range=[-0.6, 1]); fig.update_yaxes(title_text="correlation in weeks when both fall by more than one standard deviation", range=[-0.6, 1])
    fig.update_layout(title="In joint falls, markets move together far more than a normal distribution allows<br><sup>Pairs of ETFs, weekly log returns 2007-2026, pairs with at least "
                            "20 weeks of joint falls; the black line: the same selection applied to a normal distribution with the pair's correlation (selecting tail weeks lowers "
                            "correlation by itself)</sup>", height=720, width=1250, margin=dict(t=110, l=80, r=30, b=60), legend=dict(orientation="h", y=-0.1, x=0))
    save_figure(fig, "25_downside", L.FIG)

    # trade-off between the ways to fill the slots
    F = pd.DataFrame(json.loads((L.RESULTS / "fill.json").read_text(encoding="utf-8"))["oos"])
    NAMES = {"dr": "greedy diversification", "pc": "one market per factor", "ev": "explained variance, step by step", "hy": "key market + diversify",
             "sc_div": "score (chosen)"}
    fig = make_subplots(rows=1, cols=1)
    rx = pd.concat([F[f"{m}_abs_rand"] for m in NAMES]); ry = pd.concat([F[f"{m}_ev_rand"] for m in NAMES])
    fig.add_scatter(x=[rx.median()], y=[ry.median()], mode="markers+text", marker=dict(size=14, color=MUTED, symbol="square"), text=["random markets, same slots"],
                    textposition="bottom center", name="random markets in the same slots (median of the medians)",
                    error_x=dict(type="data", symmetric=False, array=[rx.quantile(.75) - rx.median()], arrayminus=[rx.median() - rx.quantile(.25)], color=MUTED),
                    error_y=dict(type="data", symmetric=False, array=[ry.quantile(.75) - ry.median()], arrayminus=[ry.median() - ry.quantile(.25)], color=MUTED))
    pos = {"dr": "middle left", "pc": "top center", "ev": "top center", "hy": "middle right", "sc_div": "bottom center"}
    for i, (m, name) in enumerate(NAMES.items()):
        x, y = F[f"{m}_abs"], F[f"{m}_ev"]; c = INK if m == "sc_div" else SERIES[i]
        fig.add_scatter(x=[x.median()], y=[y.median()], mode="markers+text", marker=dict(size=14 if m == "sc_div" else 11, color=c, symbol="diamond" if m == "sc_div" else "circle"),
                        text=[name], textposition=pos[m], textfont=dict(color=c, size=12), name=name,
                        error_x=dict(type="data", symmetric=False, array=[x.quantile(.75) - x.median()], arrayminus=[x.median() - x.quantile(.25)], color=c, thickness=1),
                        error_y=dict(type="data", symmetric=False, array=[y.quantile(.75) - y.median()], arrayminus=[y.median() - y.quantile(.25)], color=c, thickness=1))
    fig.add_annotation(x=0, y=1, xref="paper", yref="paper", xanchor="left", yanchor="top", showarrow=False, align="left", font=dict(size=11, color=MUTED),
                       text="better: up (represents its class) and left (little overlap)")
    fig.update_xaxes(title_text="average correlation between the chosen markets next year, sign ignored (lower: less overlap)", autorange="reversed")
    fig.update_yaxes(title_text="share of each class's variance the chosen markets explain next year", tickformat=".0%")
    fig.update_layout(title="Filling the slots: representing a class against overlapping less<br><sup>Out of sample 2010-2026 (17 yearly reviews, each judged on the following year); "
                            "markers: medians over the years, bars: interquartile range; the slots per class are the same for every method</sup>",
                      height=680, width=1250, margin=dict(t=110, l=80, r=30, b=60), showlegend=False)
    save_figure(fig, "25_tradeoff", L.FIG)
    print(med.round(2).to_string()); print({m: (round(F[f'{m}_abs'].median(), 3), round(F[f'{m}_ev'].median(), 3)) for m in NAMES}, round(rx.median(), 3), round(ry.median(), 3))
