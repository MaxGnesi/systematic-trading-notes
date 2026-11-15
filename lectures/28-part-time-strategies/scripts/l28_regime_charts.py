"""Lecture 28, §6 graphics (prototypes): the regime clock and the regime timeline for the four volatility and correlation quadrants.
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
    apply_theme(); B = pd.read_parquet(L.OUT / "l28_base.parquet"); tag = "futures"; base = B[tag].dropna().loc[L.FUT_START:"2022-11-18"]   # last week with all 14 markets; the data run out in December 2022
    LABEL = {"volatility": ("VIX", "VIX level against its average to date (log ratio)", "3-month change of the VIX (log)"),
             "correlation": ("correlation", "correlation against its average to date (log ratio)", "3-month change of the correlation")}
    # ---- regime clock
    fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.09, subplot_titles=("Volatility (VIX)", "Correlation across markets"))
    for c, k in enumerate(("volatility", "correlation")):
        l, avg, ch, q = series(tag, k, base); x = np.log(l / avg); S = {s: L26.sharpe(base.ret[q == s]) for s in QCOL}; sh = {s: float((q == s).mean()) for s in QCOL}
        mx, my = float(np.nanmax(np.abs(x))) * 1.08, float(np.nanmax(np.abs(ch))) * 1.08
        for s in QCOL:
            x0, x1 = (0, mx) if s.startswith("above") else (-mx, 0); y0, y1 = (0, my) if s.endswith("rising") else (-my, 0)
            col = SERIES[0] if S[s] > 0 else SERIES[1]; op = min(abs(S[s]) / 1.5, 1) * 0.35
            fig.add_shape(type="rect", x0=x0, x1=x1, y0=y0, y1=y1, fillcolor=col, opacity=op, line_width=0, layer="below", row=1, col=c + 1)
            fig.add_annotation(x=(x0 + x1) / 2, y=y1 * 0.88 if y1 > 0 else y0 * 0.88, text=f"<b>{s.replace(' ', ', ')}</b><br>Sharpe {S[s]:.2f} · {sh[s]:.0%} of days",
                               showarrow=False, font=dict(size=12, color=INK), bgcolor="rgba(255,255,255,0.7)", row=1, col=c + 1)
        m = pd.DataFrame({"x": x, "y": ch}).resample("ME").last().dropna()
        fig.add_scatter(x=m.x, y=m.y, mode="markers", marker=dict(size=5, color=MUTED, opacity=0.45), text=m.index.strftime("%b %Y"),
                        hovertemplate="%{text}<extra></extra>", name="every month end 2006-2022", legendgroup="m", showlegend=(c == 0), row=1, col=c + 1)
        for (a, b, n), dash in zip(PATHS, ("solid", "dash")):
            e = pd.DataFrame({"x": x, "y": ch}).loc[a:b].resample("ME").last().dropna()
            fig.add_scatter(x=e.x, y=e.y, mode="lines+markers", line=dict(color=INK, width=2, dash=dash), marker=dict(size=7, color=INK, symbol="arrow", angleref="previous"),
                            name=n, legendgroup=n, showlegend=(c == 0), text=e.index.strftime("%b %Y"), hovertemplate="%{text}<extra></extra>", row=1, col=c + 1)
            for d in (e.index[0], e.index[-1]):
                fig.add_annotation(x=e.x[d], y=e.y[d], text=d.strftime("%b %Y"), showarrow=False, yshift=12, font=dict(size=11, color=INK), row=1, col=c + 1)
        fig.add_hline(y=0, line=dict(color=INK, width=1), row=1, col=c + 1); fig.add_vline(x=0, line=dict(color=INK, width=1), row=1, col=c + 1)
        fig.update_xaxes(title_text=LABEL[k][1], range=[-mx, mx], zeroline=False, row=1, col=c + 1)
        fig.update_yaxes(title_text=LABEL[k][2], range=[-my, my], zeroline=False, row=1, col=c + 1)
    fig.update_layout(title="The regime clock: where the market was, and what trend earned there<br><sup>capstone futures 2006-2022; grey dots: every month end; black: two crises month by month (arrows point forward in time); "
                            "quadrant tint: the trend portfolio's Sharpe ratio after costs on the quadrant's days (blue positive, orange negative, stronger = larger)</sup>",
                      height=700, width=1300, margin=dict(t=100, l=70, r=40, b=120), legend=dict(orientation="h", y=-0.15, x=0))
    save_figure(fig, L.PREFIX + "28_clock", L.FIG)
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
