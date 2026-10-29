"""Lecture 18 figures 18_07 and 18_08, from l18_s55_summary.json and l18_s55_clock.json. 18_07: large market orders (>= 1 BTC) against the last
recorded book: the share that did worse and better than walking that book predicted, by the mid's move in the second before and by the order's size;
the mean fade on top of each pair. 18_08: pulls: (a) the pull rate by the mid's move in the previous second, median day and range over the 45 days;
(b) through the minute, the pull rate (all updates and quiet ones) and the mid's move, relative to the day's average; (c) the pull rate day by day."""
import datetime as dt, json, sys
from pathlib import Path
import polars as pl
from plotly.subplots import make_subplots
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l18 as L18
from trading_models.plotting import INK, MUTED, SERIES, GRID, apply_theme, save_figure

apply_theme()
FIG = L18.FIG
J = json.loads(L18.result_path("l18_s55_summary.json").read_text()); C = pl.DataFrame(json.loads(L18.result_path("l18_s55_clock.json").read_text())).sort("sec")
WORSE, BETTER = SERIES[1], SERIES[0]

fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.08, shared_yaxes=True,
                    subplot_titles=("By how far the mid moved in the second before the order", "By the order's size"))
for c, (key, names) in enumerate((("by_move", ["< 0.5 bp", "0.5 – 2 bp", "2 – 5 bp", "> 5 bp"]), ("by_size", ["1 – 2 BTC", "2 – 5 BTC", "5 – 10 BTC", "> 10 BTC"])), 1):
    D = [r for r in J[key] if r[key[3:] + "_bin" if key == "by_move" else "size_bin"] is not None]
    fig.add_bar(x=names, y=[r["worse"] for r in D], marker=dict(color=WORSE), name="did worse than the book promised", showlegend=c == 1, row=1, col=c)
    fig.add_bar(x=names, y=[r["better"] for r in D], marker=dict(color=BETTER), name="did better", showlegend=c == 1, row=1, col=c)
    for n, r in zip(names, D):
        fig.add_annotation(x=n, y=max(r["worse"], r["better"]), text=f"mean {r['fade_mean']:+.2f} bp", showarrow=False, yshift=12, font=dict(size=10, color=INK), row=1, col=c)
fig.update_yaxes(tickformat=".0%", range=[0, 0.5], row=1, col=1); fig.update_yaxes(title_text="share of orders", row=1, col=1)
fig.update_layout(title="Large market orders against the last recorded book: in fast seconds, four in ten did worse than the book promised<br>"
                        f"<sup>Bybit BTCUSDT, {J['overall']['orders']:,} market orders of 1 BTC or more, 45 days without 10 October</sup>",
                  barmode="group", bargap=0.25, height=520, width=1200, margin=dict(t=110, l=70, b=90), legend=dict(orientation="h", y=-0.14, x=0))
save_figure(fig, L18.PREFIX + "18_07_quote_fading", FIG)

P = pl.DataFrame([{k: v for k, v in r.items() if k != "by_sec"} for r in J["pulls"]]).sort("day")
bins = ["<0.5 bp", "0.5-2", "2-5", ">5 bp"]; labels = ["< 0.5 bp", "0.5 – 2 bp", "2 – 5 bp", "> 5 bp"]
fig = make_subplots(rows=2, cols=2, vertical_spacing=0.2, horizontal_spacing=0.08, specs=[[{}, {}], [{"colspan": 2}, None]],
                    subplot_titles=("Pulls, by the mid's move in the previous second",
                                    "Through the minute, relative to the day's average", "Pulls, day by day"))
med = [P[f"move {b}"].median() for b in bins]; lo = [P[f"move {b}"].min() for b in bins]; hi = [P[f"move {b}"].max() for b in bins]
fig.add_bar(x=labels, y=med, marker=dict(color=INK), showlegend=False, error_y=dict(type="data", symmetric=False, array=[h - m for h, m in zip(hi, med)],
            arrayminus=[m - l for m, l in zip(med, lo)], color=MUTED, thickness=1.2), row=1, col=1)
fig.update_yaxes(tickformat=".0%", range=[0, 1], row=1, col=1)
fig.add_scatter(x=C["sec"], y=C["all"], mode="lines", line=dict(color=INK, width=2), name="pulls, all updates", row=1, col=2)
fig.add_scatter(x=C["sec"], y=C["quiet"], mode="lines", line=dict(color=INK, width=1.5, dash="dot"), name="pulls, after a quiet second (mid moved < 0.5 bp)", row=1, col=2)
fig.add_scatter(x=C["sec"], y=C["move"], mode="lines", line=dict(color=SERIES[1], width=2), name="the mid's move in the previous second", row=1, col=2)
fig.add_hline(y=1, line=dict(color=MUTED, width=1, dash="dot"), row=1, col=2)
fig.update_xaxes(title_text="second of the minute", tickvals=list(range(0, 60, 10)), row=1, col=2)
wd = [dt.date.fromisoformat(d).weekday() >= 5 for d in P["day"]]
fig.add_bar(x=P["day"], y=P["rate"], marker=dict(color=[GRID if w else INK for w in wd]), showlegend=False, row=2, col=1)
fig.add_vline(x="2025-10-10", line=dict(color=SERIES[4], width=1.5, dash="dash"), row=2, col=1)
fig.add_annotation(x="2025-10-10", y=1.0, yref="y domain", text="10 October", showarrow=False, xanchor="left", xshift=6, font=dict(size=11, color=INK), row=2, col=1)
fig.add_annotation(x="2025-09-27", y=P.filter(pl.col("day") == "2025-09-27")["rate"][0], text="weekends (light)", showarrow=True, ax=0, ay=-40, font=dict(size=10, color=MUTED), row=2, col=1)
fig.update_yaxes(tickformat=".0%", title_text="share of updates", row=2, col=1); fig.update_yaxes(title_text="share of updates", row=1, col=1)
fig.update_layout(title="When the book is pulled: when the price moves, at the turn of every minute, and more after the cascade<br>"
                        "<sup>Bybit BTCUSDT, 45 days. A pull: five or more of the best 20 levels of one side shrink in one update by more than was traded there</sup>",
                  height=820, width=1200, margin=dict(t=110, l=70, b=70), legend=dict(orientation="v", y=0.97, x=0.99, xanchor="right", yanchor="top", bgcolor="rgba(252,252,251,0.8)", font=dict(size=10)), bargap=0.15)
save_figure(fig, L18.PREFIX + "18_08_pulls", FIG)
print("ok")
