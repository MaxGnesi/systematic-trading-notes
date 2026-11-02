"""Lecture 21 §3 figures. 21_10 (§3.1): left, the share of the size sold at the best bid that must have been refilled within the same book update, with
the trades shifted against the book, on five days (clock_shift.parquet); right, the same share at no shift, both sides, every day of the 45
(net_days.parquet). From L21_OUT/s31, or results/s31 as shipped."""
import sys
from datetime import date
from pathlib import Path
import polars as pl
from plotly.subplots import make_subplots
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l21 as L21
from trading_models.plotting import INK, MUTED, GRID, SERIES, apply_theme, save_figure

apply_theme()
S31 = L21.OUT / "s31"
C = pl.read_parquet(L21.result_path(S31, "clock_shift.parquet"))
N = (pl.read_parquet(L21.result_path(S31, "net_days.parquet")).group_by("day").agg(pl.col("traded", "hidden").sum())
     .with_columns((pl.col("hidden") / pl.col("traded")).alias("share")).sort("day"))
wk = [date.fromisoformat(d).weekday() >= 5 for d in N["day"]]
fig = make_subplots(rows=1, cols=2, column_widths=[0.42, 0.58], horizontal_spacing=0.09,
                    subplot_titles=("Do the two clocks agree? Five days", "What the book hides, day by day"))
for i, (day, g) in enumerate(C.sort("shift_ms").group_by("day", maintain_order=True)):
    fig.add_scatter(x=g["shift_ms"], y=g["hidden_share"], mode="lines+markers", line=dict(color=SERIES[i % len(SERIES)], width=1.8), marker=dict(size=5),
                    name=day[0], row=1, col=1)
fig.add_vline(x=0, line=dict(color=MUTED, width=1, dash="dot"), row=1, col=1)
fig.update_xaxes(title_text="trades shifted against the book, ms", tickvals=[-100, -50, -20, 0, 20, 50, 100], row=1, col=1)
fig.update_yaxes(title_text="share of traded size refilled unseen", tickformat=".0%", range=[0, 0.9], row=1, col=1)
col = [SERIES[1] if d == "2025-10-10" else (GRID if w else SERIES[0]) for d, w in zip(N["day"], wk)]
fig.add_bar(x=N["day"], y=N["share"], marker=dict(color=col, line=dict(width=0)), showlegend=False, row=1, col=2)
fig.add_hline(y=float(N["share"].median()), line=dict(color=INK, width=1, dash="dot"), row=1, col=2)
fig.add_annotation(x=N["day"][-1], y=float(N["share"].median()), text=f"median {N['share'].median():.0%}", showarrow=False, xanchor="right",
                   yanchor="bottom", font=dict(size=10, color=INK), row=1, col=2)
fig.update_yaxes(tickformat=".0%", range=[0, 0.32], row=1, col=2)
fig.update_xaxes(title_text="day (weekends light, 10 October orange)", row=1, col=2)
fig.update_layout(title="The trades and the book share one clock to the millisecond; even so, a 100 ms book hides about a fifth of the flow at the best"
                        "<br><sup>Bybit BTCUSDT. Share of the size traded at an unchanged best price that must have been refilled within the same update "
                        "(more traded than the queue fell), both sides; left: sells at the best bid with the trades shifted, five days</sup>",
                  height=470, width=1250, margin=dict(t=100, l=80, r=30, b=60), legend=dict(orientation="h", y=-0.2, x=0))
save_figure(fig, L21.PREFIX + "21_10_hidden_flow", L21.FIG)
print("median", round(float(N["share"].median()), 3), "min", round(float(N["share"].min()), 3), "max", round(float(N["share"].max()), 3))
