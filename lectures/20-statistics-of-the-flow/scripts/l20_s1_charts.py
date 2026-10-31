"""Lecture 20 figures 20_01 and 20_02. 20_01: the chain of Part IV, Lecture 20 outlined. 20_02, the key chart: left, one real minute of Bybit BTCUSDT
(1 October 2025, 12:00 UTC): the mid, the book imbalance at the best (a level) and the order-flow imbalance and trade imbalance added up since the
start of the minute (deltas); right, on the whole of that day, the share of the change of the mid over 1 s, 10 s and 60 s explained by each of the three.
Without the data of that day, 20_02 is drawn from the extract shipped in results/key."""
import json, sys
from datetime import datetime, timezone
from pathlib import Path
import numpy as np, polars as pl
import plotly.graph_objects as go
from plotly.subplots import make_subplots
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l20 as L20
from trading_models.plotting import INK, MUTED, GRID, apply_theme, save_figure

apply_theme()
FIG = L20.FIG; FIG.mkdir(parents=True, exist_ok=True)
TRADES = L20.TRADES
DAY, HM, SEC = "2025-10-01", "12:00", 60
LEVEL_C, OFI_C, TI_C = MUTED, "#2a78d6", "#eb6834"

# 20_01: the chain of Part IV
steps = [("18", "The order book", "what is there"), ("19", "Levels", "the state now"), ("20", "Deltas", "what changed"),
         ("21", "Replay", "our own orders"), ("22", "A market that reacts", "simulated agents"), ("23", "Market making", "one venue"),
         ("24", "Cross-exchange", "quote here, hedge there")]
CUR = 2
fig = go.Figure()
for i, (n, a, b) in enumerate(steps):
    x0 = i * 1.45
    fig.add_shape(type="rect", x0=x0, x1=x0 + 1.2, y0=0, y1=1, line=dict(color=INK if i == CUR else MUTED, width=2.5 if i == CUR else 1),
                  fillcolor="#eef3fb" if i == CUR else ("#f4f4f2" if i < CUR else "white"))
    fig.add_annotation(x=x0 + 0.6, y=0.75, text=f"<b>Lecture {n}</b>" + (" ✓" if i < CUR else ""), showarrow=False, font=dict(size=12, color=INK))
    fig.add_annotation(x=x0 + 0.6, y=0.48, text=a, showarrow=False, font=dict(size=12, color=INK))
    fig.add_annotation(x=x0 + 0.6, y=0.22, text=f"<i>{b}</i>", showarrow=False, font=dict(size=11, color=MUTED))
    if i < len(steps) - 1:
        fig.add_annotation(x=x0 + 1.43, y=0.5, ax=x0 + 1.22, ay=0.5, xref="x", yref="y", axref="x", ayref="y", showarrow=True, arrowhead=2,
                           arrowcolor=MUTED, text="")
for x0, x1, lab in ((0, 1.2, "describe"), (1.45, 4.1, "measure"), (4.35, 7.0, "simulate"), (7.25, 9.9, "trade")):
    fig.add_annotation(x=(x0 + x1) / 2, y=1.27, text=lab, showarrow=False, font=dict(size=11, color=MUTED))
    fig.add_shape(type="line", x0=x0, x1=x1, y0=1.13, y1=1.13, line=dict(color=GRID, width=2))
fig.update_xaxes(visible=False, range=[-0.1, 10]); fig.update_yaxes(visible=False, range=[-0.15, 1.42])
fig.update_layout(title="Part IV in one line: Lecture 20 measures what changes in the book<br><sup>Each lecture builds on the one before; "
                        "the current one is outlined, done ones are ticked</sup>", height=270, width=1250, margin=dict(t=80, l=20, r=20, b=10), showlegend=False)
save_figure(fig, L20.PREFIX + "20_01_part_iv", FIG)


def ofi_terms(X):
    """Contribution of each book update to the order-flow imbalance at the best (Cont, Kukanov and Stoikov, 2014), in BTC."""
    b, a, qb, qa = (X[c].to_numpy() for c in ("bid", "ask", "q_bid", "q_ask"))
    e = np.zeros(len(X))
    e[1:] = (np.where(b[1:] >= b[:-1], qb[1:], 0) - np.where(b[1:] <= b[:-1], qb[:-1], 0)
             - np.where(a[1:] <= a[:-1], qa[1:], 0) + np.where(a[1:] >= a[:-1], qa[:-1], 0))
    return e


# 20_02: the key chart, from Lecture 19's book state and the trades of DAY if there; otherwise from the extract shipped in results/key
if (L20.STATE / f"{DAY}.parquet").exists() and (TRADES / f"{DAY}.parquet").exists():
    S = pl.read_parquet(L20.STATE / f"{DAY}.parquet").sort("ts")
    S = S.with_columns(pl.Series("e", ofi_terms(S)), ((pl.col("bid") + pl.col("ask")) / 2).alias("mid"),
                       ((pl.col("q_bid") - pl.col("q_ask")) / (pl.col("q_bid") + pl.col("q_ask"))).alias("I"))
    T = pl.read_parquet(TRADES / f"{DAY}.parquet").sort("ts").with_columns((pl.col("side") * pl.col("size")).alias("st"))
    t0 = int(datetime.fromisoformat(f"{DAY}T{HM}").replace(tzinfo=timezone.utc).timestamp() * 1000); t1 = t0 + SEC * 1000
    W = S.filter(pl.col("ts").is_between(t0, t1 - 1))
    W = W.with_columns((pl.col("e").cum_sum() - pl.col("e").first()).alias("ofi"), ((pl.col("ts") - t0) / 1000).alias("t"))   # 0 at the first update
    WT = T.filter(pl.col("ts").is_between(t0, t1 - 1)).with_columns(pl.col("st").cum_sum().alias("ti"), ((pl.col("ts") - t0) / 1000).alias("t"))

    # over the day: the change of the mid over interval k (last mid of k minus last mid of k-1) against the flow in k and the level just before k
    R2 = {}
    for D in (1, 10, 60):
        A = S.with_columns((pl.col("ts") // (D * 1000)).alias("k")).group_by("k").agg(
            pl.col("e").sum().alias("ofi"), pl.col("I").last().alias("I_end"), pl.col("mid").last().alias("m_end")).sort("k")
        A = A.with_columns((pl.col("m_end") - pl.col("m_end").shift(1)).alias("dm"), pl.col("I_end").shift(1).alias("I0")).drop_nulls("dm")
        TT = T.with_columns((pl.col("ts") // (D * 1000)).alias("k")).group_by("k").agg(pl.col("st").sum().alias("ti"))
        A = A.join(TT, on="k", how="left").fill_null(0)
        R2[D] = {n: float(np.corrcoef(A[c], A["dm"])[0, 1] ** 2) for n, c in (("level", "I0"), ("trades", "ti"), ("book", "ofi"))}
    W.select("t", "mid", "I", "ofi").write_parquet(L20.KEY / "minute_book.parquet"); WT.select("t", "ti").write_parquet(L20.KEY / "minute_trades.parquet")
    (L20.KEY / "r2.json").write_text(json.dumps(R2))
W = pl.read_parquet(L20.result_path(L20.KEY, "minute_book.parquet")); WT = pl.read_parquet(L20.result_path(L20.KEY, "minute_trades.parquet"))
R2 = {int(D): v for D, v in json.loads(L20.result_path(L20.KEY, "r2.json").read_text()).items()}
flips = int((np.diff(np.sign(W["I"].to_numpy())) != 0).sum())
print("window: updates", W.height, "trades", WT.height, "mid", W["mid"][0] / 10, "->", W["mid"][-1] / 10, "OFI", round(W["ofi"][-1], 1),
      "TI", round(WT["ti"][-1], 1), "sign flips of I", flips)
print("R2", {D: {k: round(v, 3) for k, v in r.items()} for D, r in R2.items()})

fig = make_subplots(rows=3, cols=2, column_widths=[0.66, 0.34], horizontal_spacing=0.1, vertical_spacing=0.08,
                    row_heights=[0.36, 0.26, 0.38], specs=[[{}, {"rowspan": 3}], [{}, None], [{}, None]],
                    subplot_titles=("One minute: the mid price", "One day: share of the mid's change explained",
                                    "A level: book imbalance at the best, at each update", "Deltas: flow at the best, added up since 12:00"))
fig.add_scatter(x=W["t"], y=W["mid"] / 10, mode="lines", line=dict(color=INK, width=2, shape="hv"), showlegend=False, row=1, col=1)
fig.add_scatter(x=W["t"], y=W["I"], mode="lines", line=dict(color=LEVEL_C, width=1, shape="hv"), name="book imbalance (a level)", row=2, col=1)
fig.add_hline(y=0, line=dict(color=GRID, width=1), row=2, col=1)
fig.add_scatter(x=W["t"], y=W["ofi"], mode="lines", name="order-flow imbalance: book and trades", line=dict(color=OFI_C, width=2, shape="hv"), row=3, col=1)
fig.add_scatter(x=WT["t"], y=WT["ti"], mode="lines", name="trade imbalance: trades only", line=dict(color=TI_C, width=2, shape="hv"), row=3, col=1)
fig.add_hline(y=0, line=dict(color=GRID, width=1), row=3, col=1)
for k in (1, 2, 3):
    fig.update_xaxes(range=[0, SEC], showticklabels=(k == 3), matches="x", row=k, col=1)
fig.update_xaxes(title_text="seconds after 12:00 UTC", row=3, col=1)
fig.update_yaxes(title_text="$", tickformat=",.0f", row=1, col=1); fig.update_yaxes(title_text="−1 asks · +1 bids", range=[-1.08, 1.08], row=2, col=1)
fig.update_yaxes(title_text="BTC", row=3, col=1)
labs = ["1 s", "10 s", "60 s"]
for n, c, lab in (("level", LEVEL_C, "book imbalance at the start"), ("trades", TI_C, "trade imbalance"), ("book", OFI_C, "order-flow imbalance")):
    v = [R2[D][n] for D in (1, 10, 60)]
    fig.add_bar(x=labs, y=v, marker_color=c, name=lab, showlegend=False, text=[f"{x:.0%}" for x in v], textposition="outside",
                textfont=dict(size=10, color=INK), row=1, col=2)
fig.update_yaxes(title_text="R², share of variance", tickformat=".0%", range=[0, 0.72], row=1, col=2)
fig.update_xaxes(title_text="length of the interval", row=1, col=2)
fig.update_layout(barmode="group", bargap=0.25, bargroupgap=0.08,
                  title="A level forgets, a delta adds up: over one minute the added-up flow at the best followed the mid, the book's imbalance did not<br>"
                        f"<sup>Bybit BTCUSDT. Left: 1 October 2025, 12:00–12:01 UTC, {W.height} book updates and {WT.height:,} trades. "
                        "Right: all of 1 October; bars in the same order as the lines</sup>",
                  height=680, width=1250, margin=dict(t=110, l=70, r=30, b=60), legend=dict(orientation="h", y=-0.12, x=0))
save_figure(fig, L20.PREFIX + "20_02_level_vs_delta", FIG)
