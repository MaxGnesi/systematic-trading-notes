"""Lecture 22 §3, layers B and D on our data, in sample only (20 September - 9 October). Refill: for real orders of 1 BTC or more, the size standing at the prices the order took,
and over as many levels from the new best on the same side, as a share of what the order met, at each probe time (l22_book.py). Triggered trading: other takers' size on the order's
side in the 1 s after it, less the same at control moments in its cell, taken from l22_s3_response.py. Output: results/s3_refill.json and figures/22_s3_refill.png. --run recomputes."""
import json, sys
from pathlib import Path
import numpy as np, polars as pl
from plotly.subplots import make_subplots
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l22 as L, l22_s3_response as S3
from trading_models.plotting import INK, MUTED, SERIES, apply_theme, save_figure
apply_theme(); OUT = L.RESULTS / "s3_refill.json"; BIG = [(1, 5, "1-5"), (5, 20, "5-20"), (20, 1e9, "20+")]


def compute():
    days = S3.in_sample_days(); R = dict(days=days, refill={}, flow={})
    F = pl.concat([pl.read_parquet(L.OUT / "refill" / f"{d}.parquet").with_columns(pl.lit(d).alias("day")) for d in days]).filter(pl.col("met") > 0)
    O = pl.concat([pl.read_parquet(L.OUT / "orders" / f"{d}.parquet", columns=["ts", "side", "S"]).filter(pl.col("S") >= 1).with_columns(pl.lit(d).alias("day")) for d in days])
    F = F.join(O, on=["day", "ts", "side"], how="inner").with_columns(pl.col("S").cut([5, 20], labels=[b[2] for b in BIG]).alias("cls"))
    for cls in [b[2] for b in BIG] + ["all"]:
        G = F if cls == "all" else F.filter(pl.col("cls") == cls)
        A = G.group_by("probe").agg(pl.len().alias("n"), ((pl.col("fixed") >= 0.9 * pl.col("met")).mean()).alias("fixed90"), ((pl.col("near") >= 0.9 * pl.col("met")).mean()).alias("near90"),
                                    (pl.col("fixed") / pl.col("met")).median().alias("fixed_med"), (pl.col("near") / pl.col("met")).median().alias("near_med")).sort("probe")
        R["refill"][cls] = {c: A[c].to_list() for c in A.columns}
    Q = json.loads(S3.OUT.read_text(encoding="utf-8"))["curves"]                         # triggered trading, net of the cell-matched controls of l22_s3_response.py
    R["flow"] = {c[2]: dict(extra=Q[f"cls|{c[2]}"]["flow"], lo=Q[f"cls|{c[2]}"]["flow_lo"], hi=Q[f"cls|{c[2]}"]["flow_hi"], S=Q[f"cls|{c[2]}"]["S_mean"]) for c in S3.CLASSES}
    OUT.write_text(json.dumps(R), encoding="utf-8")
    return R


if __name__ == "__main__":
    R = compute() if "--run" in sys.argv or not OUT.exists() else json.loads(OUT.read_text(encoding="utf-8"))
    for k, v in R["refill"].items(): print("refill", k, "n", v["n"][0], "near90", [round(x, 2) for x in v["near90"]], "fixed90", [round(x, 2) for x in v["fixed90"]])
    print("flow 1 s", {k: (round(x["extra"], 2), round(x["extra"] / x["S"], 2)) for k, x in R["flow"].items()})
    pr = [p / 1000 for p in R["refill"]["all"]["probe"]]; px = [f"{p:g}" for p in pr]
    fig = make_subplots(rows=1, cols=3, column_widths=[0.4, 0.3, 0.3], horizontal_spacing=0.08, subplot_titles=("Does the depth an order took come back? Orders of 1 BTC or more",
                                                                                                        "Where does it come back? Median share, all sizes", "Do other takers follow on the same side?"))
    for (cls, c) in zip([b[2] for b in BIG], SERIES[:3]):
        v = R["refill"][cls]
        fig.add_scatter(x=px, y=v["near90"], mode="lines+markers", line=dict(color=c, width=2), marker=dict(color=c, size=7), name=f"{cls} BTC: around the new best", row=1, col=1)
        fig.add_scatter(x=px, y=v["fixed90"], mode="lines+markers", line=dict(color=c, width=2, dash="dot"), marker=dict(color=c, size=7), name=f"{cls} BTC: at the prices taken", row=1, col=1)
    fig.update_yaxes(title_text="share of orders with 90% of the depth back", tickformat=".0%", range=[0, 1], row=1, col=1)
    v = R["refill"]["all"]
    fig.add_scatter(x=px, y=v["near_med"], mode="lines+markers", line=dict(color=SERIES[0], width=2), marker=dict(size=7), name="around the new best (median share)", row=1, col=2)
    fig.add_scatter(x=px, y=v["fixed_med"], mode="lines+markers", line=dict(color=MUTED, width=2, dash="dot"), marker=dict(size=7), name="at the prices taken (median share)", row=1, col=2)
    fig.update_yaxes(title_text="depth standing / depth the order met", tickformat=".0%", rangemode="tozero", row=1, col=2)
    for c in (1, 2): fig.update_xaxes(title_text="seconds after the order", type="category", row=1, col=c)
    cls = [c[2] for c in S3.CLASSES]
    v = R["flow"]; fig.add_scatter(x=cls, y=[v[k]["extra"] for k in cls], error_y=dict(type="data", symmetric=False, array=[v[k]["hi"] - v[k]["extra"] for k in cls], arrayminus=[v[k]["extra"] - v[k]["lo"] for k in cls]),
                                   mode="lines+markers", line=dict(color=SERIES[0], width=2), marker=dict(size=8), name="extra same-side taker size in the next 1 s", row=1, col=3)
    fig.add_scatter(x=cls, y=[v[k]["S"] for k in cls], mode="lines+markers", line=dict(color=MUTED, width=2, dash="dot"), marker=dict(size=7), name="the order's own size (average)", row=1, col=3)
    fig.update_xaxes(title_text="order size, BTC", row=1, col=3); fig.update_yaxes(title_text="BTC", type="log", row=1, col=3)
    fig.update_layout(title=f"Section 3: refill and triggered trading on Bybit, in sample<br><sup>BTCUSDT perpetual, {R['days'][0]} to {R['days'][-1]} ({len(R['days'])} days). Left and middle: real orders of 1 BTC or more, depth on the side "
                      "they took. Right: orders of 0.01 BTC or more, net of control moments in the same day, hour, imbalance decile and last-second move; bars: 95% over resampled days</sup>", height=540, width=1600, margin=dict(t=110, l=70, r=30, b=170), legend=dict(orientation="h", y=-0.27, x=0))
    save_figure(fig, L.PREFIX + "22_s3_refill", L.FIG)
