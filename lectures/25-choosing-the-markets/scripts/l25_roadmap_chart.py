"""Lecture 25, the roadmap chart from results/roadmap.json: left, the capacity of each stage 1-2 market (or stage 3 group), log scale, coloured by
class, stage 2 additions marked; right, what each stage adds: markets, share of the variance of all 116 ETFs explained, mean |correlation|, capacity.
Output: figures/25_roadmap.png."""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
from plotly.subplots import make_subplots
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l25 as L
sys.path.insert(0, str(L.REPO)); from trading_models.plotting import INK, MUTED, SERIES, apply_theme, save_figure
COL = dict(zip(L.CLASSES, SERIES))

if __name__ == "__main__":
    apply_theme(); R = json.loads((L.RESULTS / "roadmap.json").read_text(encoding="utf-8")); S = R["stages"]
    cap2 = pd.Series(S["2 more bets"]["per_unit"]).sort_values(); cap3 = pd.Series(S["3 capacity"]["per_unit"])
    added = {x for v in R["stage2"].values() for x in v}; liq = R["liquidity"]
    fig = make_subplots(rows=1, cols=2, column_widths=[0.62, 0.38], horizontal_spacing=0.12, specs=[[{"type": "xy"}, {"type": "table"}]],
                        subplot_titles=("Capacity on each ETF's own trading volume, stages 1 and 2", "What each stage adds"))
    y = list(cap2.index)
    fig.add_bar(y=y, x=cap2.values / 1e6, orientation="h", marker=dict(color=[COL[L.CLASS[x]] for x in y], pattern_shape=["/" if x in added else "" for x in y]),
                showlegend=False, row=1, col=1, customdata=[liq[x] / 1e6 for x in y],
                hovertemplate="%{y}: capacity USD %{x:,.0f} m; trades USD %{customdata:,.1f} m a day<extra></extra>")
    g3 = [x for x in y if x in cap3.index and cap3[x] > cap2[x] * 1.05]
    fig.add_scatter(y=g3, x=cap3[g3].values / 1e6, mode="markers", marker=dict(symbol="diamond", size=9, color=INK), name="with its stage 3 twins sharing the trading",
                    row=1, col=1)
    for k in L.CLASSES: fig.add_bar(y=[None], x=[None], marker_color=COL[k], name=k, row=1, col=1)
    fig.add_bar(y=[None], x=[None], marker=dict(color="white", pattern_shape="/", line=dict(color=INK, width=1)), name="added in stage 2", row=1, col=1)
    fig.update_xaxes(type="log", range=[0, 6], title_text="capital the ETF can carry on its screen volume, USD million (log scale)", row=1, col=1)
    fig.add_annotation(x=np.log10(300), y=1, text="FX and government bonds (yellow, orange): limits of the ETF wrapper only;<br>the currency and Treasury markets behind them are far deeper", showarrow=False,
                       xanchor="left", align="left", font=dict(size=11, color=INK), bgcolor="rgba(252,252,251,0.9)", row=1, col=1)
    fig.update_yaxes(tickfont=dict(size=10), row=1, col=1)
    st = ["1 core", "2 more bets", "3 capacity"]; lab = ["1. Core", "2. More bets", "3. Capacity"]
    rows = [("markets", [S[s]["n"] for s in st], "{:.0f}"), ("variance of all 116 explained", [S[s]["explained_all"] for s in st], "{:.0%}"),
            ("mean |correlation| among them", [S[s]["mean_abs"] for s in st], "{:.2f}"), ("capacity, USD million", [S[s]["capacity_usd"] / 1e6 for s in st], "{:,.1f}"),
            ("bound by", [S[s]["binding"] for s in st], "{}")]
    fig.add_table(header=dict(values=["", *lab], fill_color="#efeee8", align="left", font=dict(size=12)),
                  cells=dict(values=[[r[0] for r in rows]] + [[r[2].format(r[1][i]) for r in rows] for i in range(3)], align="left", height=30, font=dict(size=12),
                             fill_color="#fcfcfb"), row=1, col=2)
    fig.update_layout(title="A roadmap for growing capital: what an account trading ETFs on screen can carry<br><sup>End-2025 review; placeholder weights: equal risk per class, inverse "
                            "volatility within, 10% portfolio volatility; capacity: a reversal day trades 20% of a position (Lecture 9) and at most 1% of the market's daily "
                            "dollar volume</sup>", height=760, width=1250, barmode="overlay", margin=dict(t=110, l=70, r=20, b=60),
                      legend=dict(orientation="h", y=-0.1, x=0))
    fig.layout.annotations[1].update(x=0.81)
    save_figure(fig, L.PREFIX + "25_roadmap", L.FIG)
