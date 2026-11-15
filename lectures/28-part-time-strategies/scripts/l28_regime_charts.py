"""Lecture 28, §6.3: the regime timeline (the clock is in l28_charts.py) for the four volatility and correlation quadrants.
Clock: x = level against its own average to date (log ratio), y = 3-month change; monthly path of the market through the quadrants, each
quadrant tinted by the trend portfolio's Sharpe ratio on its days. Timeline: the level with its average to date and the quadrant as a ribbon,
and the trend portfolio's cumulative return on the same shading. Same quadrant definition as l28_quadrants.py (both known the day before).
Output: figures/28_clock.png, figures/28_timeline.png."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
from plotly.subplots import make_subplots
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l28 as L
from trading_models.plotting import INK, MUTED, SERIES, apply_theme, save_figure
L26 = L.L26
QCOL = {"below rising": SERIES[4], "above rising": SERIES[1], "above falling": SERIES[0], "below falling": SERIES[2]}
PATHS = (("2008-06-01", "2009-12-31", "one turn of the clock: Jun 2008 to Dec 2009"), ("2020-01-01", "2020-12-31", "Jan to Dec 2020"))


def series(tag, k, base):
    if k == "volatility":
        v = L.fred("VIXCLS").reindex(pd.bdate_range("1990-01-01", base.index[-1])).ffill(); lvl = v.rolling(21).mean(); chg = np.log(v) - np.log(v.shift(63))
    else:
        G = pd.read_parquet(L.OUT / f"l28_regimes_{tag}.parquet"); lvl = G[("correlation", "measure")]; chg = lvl.diff(63)
    l = lvl.shift(1); avg = l.expanding(1260).mean(); c = chg.shift(1)
    q = (np.where(l > avg, "above", "below") + np.char.array(" ") + np.where(c > 0, "rising", "falling"))
    q = pd.Series(q, l.index).where(avg.notna() & c.notna())
    return l.reindex(base.index), avg.reindex(base.index), c.reindex(base.index), q.reindex(base.index)


def spans(q):
    """Runs of equal quadrant: (start, end, quadrant)."""
    g = (q != q.shift()).cumsum(); return [(s.index[0], s.index[-1], s.iloc[0]) for _, s in q.groupby(g) if isinstance(s.iloc[0], str)]


if __name__ == "__main__":
    apply_theme(); B = pd.read_parquet(L.OUT / "l28_base.parquet"); tag = "futures"; base = B[tag].dropna().loc[L.FUT_START:L.END[tag]]
    LABEL = {"volatility": ("VIX", "VIX level against its average to date (log ratio)", "3-month change of the VIX (log)"),
             "correlation": ("correlation", "correlation against its average to date (log ratio)", "3-month change of the correlation")}
    # ---- regime timeline
    fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.22, 0.28, 0.22, 0.28],
                        subplot_titles=("Volatility: VIX (21-day average), coloured by quadrant; dotted: its average to date",
                                        "Where trend earned: cumulative return of the trend portfolio on each volatility quadrant's days",
                                        "Correlation across markets, coloured by quadrant; dotted: its average to date",
                                        "Where trend earned: cumulative return on each correlation quadrant's days"))
    for r, k in enumerate(("volatility", "correlation")):
        l, avg, ch, q = series(tag, k, base)
        for s_, col in QCOL.items():
            y = l.where(q == s_)
            fig.add_bar(x=l.index, y=y, marker=dict(color=col, line_width=0), opacity=0.75, width=86400000 * 1.6,
                        name=s_.replace(" ", ", "), legendgroup=s_, showlegend=(r == 0), hoverinfo="skip", row=2 * r + 1, col=1)
            cr = base.ret.where(q == s_, 0.0).cumsum()
            fig.add_scatter(x=cr.index, y=cr, mode="lines", line=dict(color=col, width=2.5), legendgroup=s_, showlegend=False,
                            hovertemplate=s_ + ": %{y:.0%}<extra></extra>", row=2 * r + 2, col=1)
            fig.add_annotation(x=cr.index[-1], y=cr.iloc[-1], text=f"{s_.replace(' ', ', ')}: {cr.iloc[-1]:+.0%}", showarrow=False, xanchor="left", xshift=6,
                               font=dict(size=11, color=INK), row=2 * r + 2, col=1)
        fig.add_scatter(x=l.index, y=l, mode="lines", line=dict(color=INK, width=1), showlegend=False, hoverinfo="skip", row=2 * r + 1, col=1)
        fig.add_scatter(x=avg.index, y=avg, mode="lines", line=dict(color=INK, width=1, dash="dot"), showlegend=False, hoverinfo="skip", row=2 * r + 1, col=1)
        fig.update_yaxes(tickformat=".0%", title_text="sum of daily returns", row=2 * r + 2, col=1)
    fig.update_layout(title="The regime timeline: four quadrants over time, and where trend earned<br><sup>capstone futures 2006-2022; quadrant: the level against its average to date "
                            "and its 3-month direction, known the day before; returns after costs</sup>", height=1100, width=1300, margin=dict(t=100, l=80, r=170, b=80),
                      legend=dict(orientation="h", y=-0.04, x=0, title_text="quadrant: "), barmode="overlay", bargap=0)
    fig.update_xaxes(range=[base.index[0], base.index[-1] + pd.Timedelta(days=20)])
    save_figure(fig, L.PREFIX + "28_timeline", L.FIG)
