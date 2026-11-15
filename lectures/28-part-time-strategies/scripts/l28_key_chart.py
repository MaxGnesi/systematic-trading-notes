"""Lecture 28, §1 key chart: every filter's Sharpe ratio over all days against its time in the market, next to what time in the market alone
gives (always-in Sharpe ratio x square root of the share of days on, Lecture 7 §4.3) and the filter's own random filters. Reads results/filters.json
(run l28_filters.py first). Output: figures/28_key.png."""
import json, sys
from pathlib import Path
import numpy as np
from plotly.subplots import make_subplots
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l28 as L
from l28_filters import FAMILIES, KIND, LEVELS, FIXED, NAMES
from trading_models.plotting import INK, MUTED, SERIES, apply_theme, save_figure

if __name__ == "__main__":
    apply_theme(); F = json.loads((L.RESULTS / "filters.json").read_text(encoding="utf-8"))
    fx = lambda k: LEVELS[KIND[k]][FIXED] if k in KIND else "third"
    ks = [k for v in FAMILIES.values() for k in v]; colour = {k: SERIES[0] if k in FAMILIES["macro"] else SERIES[1] if k in FAMILIES["market state"] else SERIES[2] for k in ks}
    LABEL = {"etf": ("correlation", "growth", "fed"), "futures": ("growth", "volatility", "dollar")}
    fig = make_subplots(rows=1, cols=2, shared_yaxes=True, horizontal_spacing=0.05, subplot_titles=("ETFs, out of sample 2013-2026", "Capstone futures 2006-2022"))
    for c, tag in enumerate(("etf", "futures")):
        D = F["datasets"][tag]; b = D["baseline"]["sharpe"]; p = np.linspace(0.4, 1.0, 61)
        fig.add_scatter(x=p, y=b * np.sqrt(p), mode="lines", line=dict(color=INK, width=2, dash="dash"), name="time in the market alone: always-in Sharpe ratio × √(share of days on)",
                        legendgroup="sqrt", showlegend=c == 0, row=1, col=c + 1)
        fig.add_hline(y=b, line=dict(color=INK, width=1, dash="dot"), row=1, col=c + 1)
        fig.add_annotation(x=0.41, y=b, text=f"always in: {b:.2f}", showarrow=False, yshift=10, xanchor="left", font=dict(color=INK, size=12), row=1, col=c + 1)
        for k in ks:
            m = D[k][fx(k)]
            fig.add_shape(type="line", x0=m["share_on"], x1=m["share_on"], y0=m["random_median"], y1=m["random_p95"], line=dict(color=MUTED, width=5), opacity=0.6, row=1, col=c + 1)
        for fam, col, nm in (("macro", SERIES[0], "macro filter"), ("market state", SERIES[1], "market-state filter"), ("both", SERIES[2], "both families combined")):
            kk = FAMILIES[fam]
            fig.add_scatter(x=[D[k][fx(k)]["share_on"] for k in kk], y=[D[k][fx(k)]["sharpe"] for k in kk], mode="markers", marker=dict(color=col, size=11, line=dict(color="white", width=2)),
                            name=nm, legendgroup=fam, showlegend=c == 0, text=[NAMES[k] for k in kk], hovertemplate="%{text}: on %{x:.0%}, Sharpe %{y:.2f}<extra></extra>", row=1, col=c + 1)
        for k in LABEL[tag]:
            m = D[k][fx(k)]
            fig.add_annotation(x=m["share_on"], y=m["sharpe"], text=NAMES[k], showarrow=True, arrowhead=0, ax=40, ay=-28 if m["sharpe"] > m["random_median"] else 28,
                               font=dict(size=12, color=INK), row=1, col=c + 1)
        fig.update_xaxes(title_text="share of days the filter keeps trend on", tickformat=".0%", range=[0.4, 1.02], row=1, col=c + 1)
    fig.add_scatter(x=[None], y=[None], mode="lines", line=dict(color=MUTED, width=5), name="1,000 random switches with the same time in the market: median to 95th percentile", row=1, col=1)
    fig.update_yaxes(title_text="Sharpe ratio after costs, all days", row=1, col=1)
    fig.update_layout(title="A part-time strategy against always-in<br><sup>each dot: the baseline trend portfolio with one regime filter switching it off (known the day before, "
                            "a tenth of the way each day, 5 bp per change), fixed thresholds; idle days earn the cash rate</sup>",
                      height=620, width=1250, margin=dict(t=100, l=70, r=30, b=150), legend=dict(orientation="h", y=-0.2, x=0))
    save_figure(fig, L.PREFIX + "28_key", L.FIG)
