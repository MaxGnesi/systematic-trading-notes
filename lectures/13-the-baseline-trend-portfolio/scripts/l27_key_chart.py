"""Lecture 13's key chart: left, the correlation of two trend streams in the same market against the ratio of their speeds (pooled over markets,
each asset class the same weight, end-2025 review, results/speeds.json), one line per rule, plus pairs of different rules at the same speed;
right, each asset class's share of capital and of risk, averaged over the years 2013-2025 (results/leverage.json). Output: figures/27_key.png."""
import json, sys
from itertools import combinations
from pathlib import Path
import numpy as np, pandas as pd
from plotly.subplots import make_subplots
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l27 as M
from trading_models.plotting import INK, MUTED, SERIES, apply_theme, save_figure

RULES = (("ewma", "EWMA crossover"), ("breakout", "breakout"), ("return", "past return"))
CLASSES = (("Equity", "Equity"), ("Rates", "Govt bonds"), ("Credit", "Credit"), ("Commodities", "Commodities"), ("FX", "Currencies"))


def ratio_curve(C, rule):
    """Correlation of every pair of speeds of one rule, by the ratio of the slower to the faster speed."""
    ks = sorted([k for k in C if k.startswith(rule + "_")], key=lambda k: int(k.split("_")[1]))
    pts = [(int(b.split("_")[1]) / int(a.split("_")[1]), C[a][b]) for a, b in combinations(ks, 2)]
    return pd.DataFrame(pts, columns=["ratio", "corr"]).sort_values("ratio")


if __name__ == "__main__":
    apply_theme(); S = json.loads((M.RESULTS / "speeds.json").read_text(encoding="utf-8")); L = json.loads((M.RESULTS / "leverage.json").read_text(encoding="utf-8"))
    C = S["reviews"]["2025"]["corr"]
    fig = make_subplots(rows=1, cols=2, column_widths=[0.55, 0.45], horizontal_spacing=0.12,
                        subplot_titles=("How much do two speeds overlap? End-2025 review", "Equal risk, not equal capital: 2013-2025"))
    for i, (rule, name) in enumerate(RULES):
        d = ratio_curve(C, rule).groupby("ratio")["corr"].mean().reset_index()
        fig.add_scatter(x=d["ratio"], y=d["corr"], mode="markers", marker=dict(color=SERIES[i], size=8), name=name, legendgroup="r", row=1, col=1)
    same = [C[f"{a}_{h}"][f"{b}_{h}"] for h in (61, 89, 127, 179, 251, 359) for (a, _), (b, _) in combinations(RULES, 2)]
    fig.add_scatter(x=[1.0], y=[float(np.mean(same))], mode="markers", marker=dict(color=INK, size=12, symbol="diamond"),
                    name="two different rules, same speed (mean)", legendgroup="r", row=1, col=1)
    fig.update_xaxes(type="log", title_text="ratio of the slower to the faster speed (log scale)", tickvals=[1, 1.4, 2, 4, 8, 16, 46], row=1, col=1)
    fig.update_yaxes(title_text="correlation of daily returns", range=[0, 1.02], row=1, col=1)
    yrs = sorted(L["class_shares"]); cap = {k: np.mean([L["class_shares"][y][k]["capital"] for y in yrs]) for k, _ in CLASSES}
    risk = {k: np.mean([L["class_shares"][y][k]["risk"] for y in yrs]) for k, _ in CLASSES}
    lab = [n for _, n in CLASSES]
    fig.add_bar(y=lab, x=[cap[k] for k, _ in CLASSES], orientation="h", marker_color=MUTED, name="share of capital (gross exposure)", legendgroup="c", row=1, col=2)
    fig.add_bar(y=lab, x=[risk[k] for k, _ in CLASSES], orientation="h", marker_color=SERIES[0], name="share of risk (realised)", legendgroup="c", row=1, col=2)
    fig.add_vline(x=0.2, line=dict(color=INK, width=1, dash="dot"), row=1, col=2)
    fig.add_annotation(x=0.2, y="Currencies", yshift=-30, text=" equal: 20%", showarrow=False, xanchor="left", yanchor="middle", font=dict(size=11), row=1, col=2)
    fig.update_yaxes(autorange="reversed", row=1, col=2); fig.update_xaxes(title_text="share of the portfolio, mean of the 13 years", tickformat=".0%", row=1, col=2)
    fig.update_layout(title="The baseline trend portfolio<br><sup>left: pairs of the 36 trend streams (three rules, twelve speeds) in the same market, correlation pooled over markets "
                            "(each class the same weight), in-sample data to end-2025<br>right: Lecture 12's out-of-sample portfolio, markets equal risk in a class, "
                            "classes equal risk; excess returns over cash, 5 bp per trade</sup>", barmode="group",
                      height=640, width=1250, margin=dict(t=125, l=70, r=30, b=110), legend=dict(orientation="h", y=-0.2, x=0))
    save_figure(fig, M.PREFIX + "27_key", M.FIG)
    for rule, _ in RULES:
        d = ratio_curve(C, rule); print(rule, d.groupby(pd.cut(d["ratio"], [1, 1.5, 2.5, 5, 10, 60]))["corr"].mean().round(2).to_dict())
    print("same speed, different rules", round(float(np.mean(same)), 2))
    print({k: (round(cap[k], 3), round(risk[k], 3)) for k, _ in CLASSES})
