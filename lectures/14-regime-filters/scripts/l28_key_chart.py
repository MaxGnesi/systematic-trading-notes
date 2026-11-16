"""Lecture 14, §1 key chart: the running example of §2 as money over time. Always-in baseline trend portfolio, the same portfolio switched off
by the growth filter (as run), and the switched portfolio scaled after the fact to the always-in volatility; off periods shaded.
Capstone futures 2006 to 18 November 2022. Output: figures/28_key.png."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l28 as L
from l28_filters import offs, switched
import plotly.graph_objects as go
from trading_models.plotting import INK, MUTED, SERIES, apply_theme, save_figure
L26 = L.L26

if __name__ == "__main__":
    apply_theme(); B = pd.read_parquet(L.OUT / "l28_base.parquet"); base = B["futures"].dropna().loc[L.FUT_START:L.END["futures"]]
    G = pd.read_parquet(L.OUT / "l28_regimes_futures.parquet").reindex(base.index); off = offs(G, 1)["growth"]
    part = pd.Series(switched(base.ret.to_numpy(), base.gross.to_numpy(), off.to_numpy(), L.LAMBDA, L.COST_BP / 1e4), base.index)
    k = base.ret.std() / part.std(); lines = (("Always in", "Always in", base.ret, INK, "solid"), ("Filtered trend: growth filter, as run", "Filtered, as run", part, SERIES[0], "solid"),
                                               (f"Filtered trend, scaled after the fact to the same risk (× {k:.2f})", "Filtered, same risk", part * k, SERIES[0], "dash"))
    fig = go.Figure()
    g = (off != off.shift()).cumsum()
    for _, s in off.groupby(g):
        if s.iloc[0]: fig.add_vrect(x0=s.index[0], x1=s.index[-1], fillcolor=MUTED, opacity=0.18, line_width=0, layer="below")
    for name, short, r, col, dash in lines:
        w = 100 * (1 + r).cumprod(); sr, ret = L26.sharpe(r), r.mean() * 252
        fig.add_scatter(x=w.index, y=w, name=name, line=dict(color=col, width=2.5, dash=dash))
        fig.add_annotation(x=w.index[-1], y=w.iloc[-1], text=f"<b>{short}</b><br>Sharpe {sr:.2f} · {ret:.1%} a year",
                           showarrow=False, xanchor="left", xshift=8, align="left", font=dict(size=12, color=col))
    fig.add_scatter(x=[None], y=[None], mode="markers", marker=dict(symbol="square", size=14, color=MUTED, opacity=0.4), name="filter off: trend switched off (growth still)")
    fig.update_xaxes(range=[base.index[0], base.index[-1] + pd.Timedelta(days=30)])
    fig.update_yaxes(title_text="value of 100 invested (excess return over cash)")
    fig.update_layout(title="A higher Sharpe ratio, a lower return<br><sup>the baseline trend portfolio on the capstone futures, always in or switched off while US growth stands still "
                            "(known the day before); after costs; 2006 to November 2022</sup>",
                      height=560, width=1250, margin=dict(t=90, l=70, r=200, b=110), legend=dict(orientation="h", y=-0.12, x=0))
    save_figure(fig, L.PREFIX + "28_key", L.FIG)
