"""Lecture 28, simple result charts read from the saved results (run l28_scan.py, l28_filters.py first):
  28_scan.png    §4: per variable, Sharpe ratio while the regime moves minus while it stands still; ETFs and futures; star = 90% band excludes zero.
  28_filters.png §5: per filter, the share of its 1,000 random switches (same time in the market) it beats; lines at 50% and 90%.
  28_clock.png   §6.3: the volatility quadrants as a clock, with the 2008-2009 crisis month by month."""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
import plotly.graph_objects as go
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l28 as L
from l28_filters import FAMILIES, KIND, LEVELS, FIXED, NAMES
from l28_regime_charts import series
from trading_models.plotting import INK, MUTED, SERIES, apply_theme, save_figure
L26 = L.L26
DS = (("etf", "ETFs 2013-2026", SERIES[0]), ("futures", "Capstone futures 2006-2022", SERIES[1]))


def scan():
    S = json.loads((L.RESULTS / "scan.json").read_text(encoding="utf-8"))
    rows = (("growth", "Growth (macro)"), ("inflation", "Inflation (macro)"), ("fed", "Fed (macro)"), ("volatility", "Volatility"),
            ("correlation", "Correlation across markets"), ("turning", "Turning points"), ("curve", "Yield curve"), ("dollar", "Dollar"))
    fig = go.Figure()
    for tag, name, col in DS:
        d = [S[tag][k]["diff"] for k, _ in rows]
        star = ["*" if (S[tag][k]["ci90"][0] > 0 or S[tag][k]["ci90"][1] < 0) else "" for k, _ in rows]
        fig.add_bar(y=[n for _, n in rows], x=d, orientation="h", name=name, marker_color=col, text=[f"{v:+.2f}{s}" for v, s in zip(d, star)],
                    textposition="outside", textfont=dict(color=INK, size=12))
    fig.add_vline(x=0, line=dict(color=INK, width=1))
    fig.add_annotation(x=0.75, y=1.04, yref="paper", text="trend did better while the regime moved (as the rule expects) →", showarrow=False, font=dict(color=MUTED, size=12))
    fig.add_annotation(x=-0.75, y=1.04, yref="paper", text="← trend did better while the regime stood still", showarrow=False, font=dict(color=MUTED, size=12))
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(title_text="Sharpe ratio on the days the filter keeps trend on, minus on the days it would switch trend off", range=[-1.5, 1.5])
    fig.update_layout(title="Does trend earn less when the regime stands still?<br><sup>the baseline trend portfolio, days split by each variable's state, known the day before; "
                            "* the 90% band of the difference excludes zero; nothing is switched here</sup>",
                      barmode="group", height=650, width=1100, margin=dict(t=120, l=200, r=40, b=110), legend=dict(orientation="h", y=-0.15, x=0))
    save_figure(fig, L.PREFIX + "28_scan", L.FIG)


def filters():
    F = json.loads((L.RESULTS / "filters.json").read_text(encoding="utf-8")); fx = lambda k: LEVELS[KIND[k]][FIXED] if k in KIND else "third"
    ks = [k for v in FAMILIES.values() for k in v]; lab = [NAMES[k] for k in ks]
    fig = go.Figure()
    for tag, name, col in DS:
        b = [F["datasets"][tag][k][fx(k)]["beaten"] for k in ks]
        fig.add_bar(y=lab, x=b, orientation="h", name=name, marker_color=col, text=[f"{v:.0%}" for v in b], textposition="outside", textfont=dict(color=INK, size=12))
    fig.add_vline(x=0.5, line=dict(color=MUTED, width=1.5, dash="dot")); fig.add_vline(x=0.9, line=dict(color=INK, width=1.5, dash="dash"))
    fig.add_annotation(x=0.5, y=1.03, yref="paper", text="a coin: 50%", showarrow=False, font=dict(color=MUTED, size=12))
    fig.add_annotation(x=0.9, y=1.03, yref="paper", text="the bar to clear: 90%", showarrow=False, font=dict(color=INK, size=12))
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(title_text="share of 1,000 random switches (same time in the market) that the filter beats", tickformat=".0%", range=[0, 1.08])
    fig.update_layout(title="Regime filters against luck<br><sup>a filter works if it clears 90% on both datasets and passes the multiple-testing correction; none does</sup>",
                      barmode="group", height=780, width=1100, margin=dict(t=120, l=200, r=40, b=110), legend=dict(orientation="h", y=-0.1, x=0))
    save_figure(fig, L.PREFIX + "28_filters", L.FIG)


def clock():
    B = pd.read_parquet(L.OUT / "l28_base.parquet"); base = B["futures"].dropna().loc[L.FUT_START:L.END["futures"]]
    l, avg, ch, q = series("futures", "volatility", base); x = np.log(l / avg)
    WORDS = {"below rising": "Calm, nerves building", "above rising": "Stress building", "above falling": "Stress fading", "below falling": "Calm, getting calmer"}
    e = pd.DataFrame({"x": x, "y": ch}).loc["2008-06-01":"2009-12-31"].resample("ME").last()
    mx, my = 1.35, 1.2; fig = go.Figure()
    for s, w in WORDS.items():
        sr, sh = L26.sharpe(base.ret[q == s]), float((q == s).mean())
        x0, x1 = (0, mx) if s.startswith("above") else (-mx, 0); y0, y1 = (0, my) if s.endswith("rising") else (-my, 0)
        fig.add_shape(type="rect", x0=x0, x1=x1, y0=y0, y1=y1, fillcolor=SERIES[0], opacity=max(min(sr / 1.6, 1), 0.05) * 0.4, line_width=0, layer="below")
        fig.add_annotation(x=(x0 + x1) / 2, y=(y1 * 0.84 if y1 > 0 else y0 * 0.84), text=f"<b>{w}</b><br>trend's Sharpe ratio {sr:.2f} · {sh:.0%} of days",
                           showarrow=False, font=dict(size=13, color=INK))
    fig.add_scatter(x=e.x, y=e.y, mode="lines+markers", line=dict(color=INK, width=2.5), marker=dict(size=10, color=INK, symbol="arrow", angleref="previous"),
                    name="the VIX month by month, June 2008 to December 2009", text=e.index.strftime("%b %Y"), hovertemplate="%{text}<extra></extra>")
    for d in ("2008-06-30", "2008-10-31", "2009-03-31", "2009-12-31"):
        fig.add_annotation(x=e.x[d], y=e.y[d], text=pd.Timestamp(d).strftime("%b %Y"), showarrow=False, yshift=15, font=dict(size=12, color=INK),
                           bgcolor="rgba(255,255,255,0.7)")
    fig.add_hline(y=0, line=dict(color=INK, width=1)); fig.add_vline(x=0, line=dict(color=INK, width=1))
    fig.update_xaxes(title_text="← VIX below its average to date  ·  above its average →", range=[-mx, mx], showticklabels=False, zeroline=False, showgrid=False)
    fig.update_yaxes(title_text="← VIX falling over 3 months  ·  rising →", range=[-my, my], showticklabels=False, zeroline=False, showgrid=False)
    fig.update_layout(title="The volatility clock: a crisis runs clockwise<br><sup>capstone futures 2006-2022; tint: trend's Sharpe ratio in each quadrant (darker = higher); "
                            "both known the day before</sup>", height=720, width=900, margin=dict(t=90, l=70, r=30, b=100), legend=dict(orientation="h", y=-0.08, x=0))
    save_figure(fig, L.PREFIX + "28_clock", L.FIG)


if __name__ == "__main__":
    apply_theme(); scan(); filters(); clock()
