"""Lecture 19 §3.7 figure 19_16: the book's clock. Pulls and depth by second of the minute, in minutes :00 and :30 and in other minutes; the share
of seconds with a spread wider than one tick, by slot; H23, whether the depth added and the taker flow at :00/:30 follow the last half hour.
From l19_s37_stats.json and l19_s37_second.parquet (L19_OUT, or results/ as shipped)."""
import json, sys
from pathlib import Path
import polars as pl
from plotly.subplots import make_subplots
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l19 as L19
from trading_models.plotting import INK, MUTED, GRID, SERIES, apply_theme, save_figure
apply_theme(); sys.stdout.reconfigure(encoding="utf-8")
R = json.loads(L19.result_path("l19_s37_stats.json").read_text()); Q = pl.read_parquet(L19.result_path("l19_s37_second.parquet"))
ROUND, OTHER, FUND = SERIES[0], MUTED, SERIES[1]

fig = make_subplots(rows=2, cols=2, vertical_spacing=0.2, horizontal_spacing=0.12,
                    subplot_titles=("Pulls (× the day's rate)", "Depth in the best 5 levels (× the hour's average)",
                                    "Seconds with a spread wider than one tick (%)", "H23: rank correlation with the last half hour's return"))
for grp, col, lab in (("other minutes", OTHER, "other minutes"), ("minute :00 or :30", ROUND, "minutes :00 and :30 of the hour")):
    g = Q.filter(pl.col("grp") == grp).sort("sec")
    fig.add_scatter(x=g["sec"], y=g["pulls"], mode="lines", line=dict(color=col, width=2), name=lab, legendgroup=grp, row=1, col=1)
    fig.add_scatter(x=g["sec"], y=g["depth"], mode="lines", line=dict(color=col, width=2), name=lab, legendgroup=grp, showlegend=False, row=1, col=2)
for c in (1, 2):
    fig.add_hline(y=1, line=dict(color=GRID, width=1), row=1, col=c); fig.update_xaxes(title_text="second of the minute", range=[0, 59], row=1, col=c)
W = R["wide_share"]
names = [("control", "control: :07 :17 :37 :47"), ("m59", ":59"), ("m15_45", ":15 and :45"), ("m30", ":30"), ("other_00", ":00 without funding"), ("funding_00", ":00 with funding")]
v = [100 * W[k]["seconds"] / W[k]["of"] for k, _ in names]
fig.add_bar(x=v, y=[n for _, n in names], orientation="h", marker_color=[OTHER, ROUND, ROUND, ROUND, ROUND, FUND], showlegend=False,
            text=[f"{x:.2f}%  ({W[k]['seconds']} s)" for x, (k, _) in zip(v, names)], textposition="outside", textfont=dict(size=10, color=INK), row=2, col=1)
fig.update_xaxes(title_text="% of the seconds in those minutes, 44 days", range=[0, max(v) * 1.45], row=2, col=1)
H = R["H23"]
for k, col, lab in (("corr_control", OTHER, "control minutes"), ("corr_round", ROUND, "minutes :00 and :30")):
    y = [H["H23a"][k], H["H23b"][k]]
    fig.add_bar(x=["depth added, bid minus ask<br>(−5 s to +10 s)", "net taker flow<br>(first 10 s)"], y=y, marker_color=col, name=lab,
                text=[f"{x:+.3f}" for x in y], textposition="outside", textfont=dict(size=10, color=INK), row=2, col=2)
fig.add_hline(y=0, line=dict(color=GRID, width=1), row=2, col=2)
fig.update_yaxes(range=[-0.06, 0.15], row=2, col=2)
fig.update_layout(barmode="group", title="The book's clock: quotes are replaced every minute and, far more, at :00 and :30, with more size on both sides; "
                  "taker orders then follow the last half hour<br><sup>Bybit BTCUSDT, 44 days (20 September – 3 November 2025 without 10 October). "
                  "Pulls: 5 or more of the best 20 levels on one side cancelled in one update (Lecture 18)</sup>",
                  height=760, width=1300, margin=dict(t=110, l=160, r=30, b=60), legend=dict(orientation="h", y=-0.1, x=0))
save_figure(fig, L19.PREFIX + "19_16_book_clock", L19.FIG)
print("done")
