"""Lecture 15 §4 checks on the fuel warnings, from the hourly panel of l15_cascades.py.
(1) Direction: funding above 0.01% and more long than short accounts mean the longs are crowded; does that raise the chance of a cascade DOWN (and the
reverse for crowded shorts)? Target: a cascade against the crowded side, in the next hour and within 24 hours. (2) Extremes: the top (bottom) 5% instead of
the top (bottom) fifth. Same regression as l15_cascades.py: control-fifth dummies, days (24 h: weeks) as clusters; BH over the in-sample tests."""
import json, math, sys
from datetime import datetime
from pathlib import Path
import numpy as np, polars as pl
import os, sys
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # tables print on any console; Jupyter handles its own
HERE = Path(__file__).resolve().parent                                     # lectures/15-.../scripts
sys.path[:0] = [str(HERE), str(HERE.parents[1] / "13-bars-not-cut-by-time" / "scripts"), str(HERE.parents[1] / "12-tick-data-the-tape"), str(HERE.parents[2])]
import tape
L15_RESULTS = tape.ROOT / "interim" / "l15"; L15_RESULTS.mkdir(parents=True, exist_ok=True)          # results: in the data folder, never committed
FIG = Path(os.environ.get("L15_FIG", HERE.parent / "figures")); FIG.mkdir(parents=True, exist_ok=True)
PREFIX = os.environ.get("L15_PREFIX", "nb_")                               # "nb_": the lecture's own figures are never overwritten
import tape

CUT = json.loads((L15_RESULTS / "l15_cascades.json").read_text())["cascade_cut"]
P = pl.read_parquet(tape.ROOT / "interim" / "l15_cascade_panel.parquet").sort("time")
M = pl.read_parquet(tape.ROOT / "interim" / "l15_metrics.parquet").select("time", pl.col("count_long_short_ratio").log().alias("lls")).sort("time")
M = M.with_columns((pl.col("lls") - pl.col("lls").rolling_median(28 * 288, min_samples=7 * 288).shift(1)).alias("crowd_signed"))
P = P.with_columns((pl.col("time") - pl.duration(minutes=5)).alias("tk")).sort("tk").join_asof(M.select(pl.col("time").alias("tk"), "crowd_signed"), on="tk",
                                                                                            strategy="backward", tolerance="15m").drop("tk").sort("time")
fr = pl.read_parquet(tape.ROOT / "raw" / "binance" / "um" / "fundingRate" / "BTCUSDT-fundingRate.parquet").select(
    pl.col("fundingTime").cast(pl.Int64).cast(pl.Datetime("ms")).cast(pl.Datetime("us")).alias("ft"), (pl.col("fundingRate") - 0.0001).alias("funding_signed")).sort("ft")
P = P.join_asof(fr, left_on="time", right_on="ft", strategy="backward").drop("ft")
# directional targets: a cascade down (up) in the next hour, and within the next 24 hours
P = P.with_columns((pl.col("move") <= -CUT).cast(pl.Float64).alias("down"), (pl.col("move") >= CUT).cast(pl.Float64).alias("up"))
P = P.with_columns(pl.col("down").reverse().rolling_max(24, min_samples=24).reverse().alias("down24"), pl.col("up").reverse().rolling_max(24, min_samples=24).reverse().alias("up24"))
IS = P["time"] < datetime(2025, 1, 1)


def lpm(df, flag, target, cl):
    X = np.column_stack([flag] + [(df["cfifth"] == str(k)).to_numpy().astype(float) for k in range(5)]); y = df[target].to_numpy()
    XtX = np.linalg.inv(X.T @ X); b = XtX @ X.T @ y; e = y - X @ b
    _, inv = np.unique(df[cl].to_numpy(), return_inverse=True); sc = np.zeros((inv.max() + 1, X.shape[1])); np.add.at(sc, inv, X * e[:, None])
    V = XtX @ (sc.T @ sc) @ XtX; G = sc.shape[0]; V *= G / (G - 1); return b[0], math.sqrt(V[0, 0])


def bh(p):
    p = np.asarray(p); o = np.argsort(p); q = p[o] * len(p) / np.arange(1, len(p) + 1); q = np.minimum.accumulate(q[::-1])[::-1]; out = np.empty_like(q); out[o] = np.minimum(q, 1); return out


rows = []


def test(name, flag_fn, target_fn, horizons=(("1 h", "day"), ("24 h", "week"))):
    for hz, cl in horizons:
        for lab, part in (("2021-2024", P.filter(IS)), ("2025-2026", P.filter(~IS))):
            part = part.drop_nulls(["cfifth"]).with_columns(target_fn(hz).alias("y")).drop_nulls("y")
            f = flag_fn(part); ok = np.isfinite(f); part = part.filter(pl.Series(ok)); f = f[ok]; y = part["y"].to_numpy()
            if f.sum() < 20:                                                       # too few flagged hours to test (funding never above 0.01% in 2025-2026)
                rows.append(dict(check=name, horizon=hz, sample=lab, flagged=round(f.mean(), 3), note="not testable")); continue
            b, se = lpm(part, f, "y", cl)
            rows.append(dict(check=name, horizon=hz, sample=lab, flagged=round(f.mean(), 3), rate_flag=round(y[f == 1].mean() * 100, 2), rate_no=round(y[f == 0].mean() * 100, 2),
                             lift=round(y[f == 1].mean() / y[f == 0].mean(), 2), added_pp=round(b * 100, 2), t=round(b / se, 1), p=math.erfc(abs(b / se) / math.sqrt(2))))


# (1) direction: crowded long (top fifth of the signed measure) -> cascade down; crowded short (bottom fifth) -> cascade up
for col, lab in (("funding_signed", "funding"), ("crowd_signed", "long/short accounts")):
    hi, lo = np.nanquantile(P.filter(IS)[col].to_numpy(), [0.8, 0.2])
    flag = lambda d, c=col, h=hi: np.where(d[c].is_null().to_numpy(), np.nan, (d[c].fill_null(0).to_numpy() > max(h, 0)).astype(float))
    test(f"longs crowded ({lab}) -> cascade down", flag, lambda hz: pl.col("down" if hz == "1 h" else "down24"))
    flag = lambda d, c=col, l=lo: np.where(d[c].is_null().to_numpy(), np.nan, (d[c].fill_null(0).to_numpy() < min(l, 0)).astype(float))
    test(f"shorts crowded ({lab}) -> cascade up", flag, lambda hz: pl.col("up" if hz == "1 h" else "up24"))
# (2) extremes: the top (bottom) 5%
for col, side in (("F1 open interest", "top"), ("F2 funding", "top"), ("F3 crowding", "top"), ("F4b complacency", "bottom"), ("F5 time in band", "top")):
    q = np.nanquantile(P.filter(IS)[col].to_numpy(), 0.95 if side == "top" else 0.05)
    flag = lambda d, c=col, q=q, s=side: np.where(d[c].is_null().to_numpy() | d[c].is_nan().fill_null(True).to_numpy(), np.nan,
                                                  ((d[c].fill_null(0).to_numpy() >= q) if s == "top" else (d[c].fill_null(0).to_numpy() <= q)).astype(float))
    test(f"{col}, extreme 5%", flag, lambda hz: pl.col("cascade" if hz == "1 h" else "cascade24"))
ins = [r for r in rows if r["sample"] == "2021-2024" and "p" in r]
for r, q in zip(ins, bh([r["p"] for r in ins])): r["q_bh"] = round(float(q), 4)
(L15_RESULTS / "l15_cascades_checks.json").write_text(json.dumps(rows, indent=1))
for r in rows:
    if "note" in r: print(f"{r['check']:46}{r['horizon']:5}{r['sample']:10} not testable, flagged {r['flagged']}"); continue
    print(f"{r['check']:46}{r['horizon']:5}{r['sample']:10} flagged {r['flagged']:.2f}  rate {r['rate_flag']:6.2f}% vs {r['rate_no']:6.2f}%  lift {r['lift']:5.2f}  "
          f"added {r['added_pp']:+6.2f} pp (t {r['t']:+5.1f})" + (f"  q {r['q_bh']:.3f}" if "q_bh" in r else ""))
