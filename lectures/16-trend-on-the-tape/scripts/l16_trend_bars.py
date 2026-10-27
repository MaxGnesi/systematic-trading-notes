"""Lecture 16: the plain trend rule (l16_trend.py) on candles of 5 and 15 minutes, 1 and 4 hours and 1 day, with fast spans from 3 hours to 8 days
(slow = 4 x fast). Spans are in hours of history, the same on every candle size; a span shorter than two candles is skipped. Sizing, buffer, costs and
funding as in l16_trend.py. Judged on 2021-2024, shown on 2025-2026."""
import json, sys
from datetime import timedelta
from pathlib import Path
import numpy as np, polars as pl
import os, sys
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # tables print on any console; Jupyter handles its own
HERE = Path(__file__).resolve().parent                                     # lectures/16-.../scripts
sys.path[:0] = [str(HERE), str(HERE.parents[1] / "13-bars-not-cut-by-time" / "scripts"), str(HERE.parents[1] / "12-tick-data-the-tape"), str(HERE.parents[2])]
import tape
L16_RESULTS = tape.ROOT / "interim" / "l16"; L16_RESULTS.mkdir(parents=True, exist_ok=True)          # results: in the data folder, never committed
FIG = Path(os.environ.get("L16_FIG", HERE.parent / "figures")); FIG.mkdir(parents=True, exist_ok=True)
PREFIX = os.environ.get("L16_PREFIX", "nb_")                               # "nb_": the lecture's own figures are never overwritten
import tape

D = tape.ROOT / "interim" / "tape" / "BTCUSDT"
TAKER, HALF, TARGET, BUFFER = 5.0, 0.04, 0.10, 0.10
FAST_H = [3, 6, 12, 24, 48, 96, 192]; BARS = {"5 min": 5, "15 min": 15, "1 hour": 60, "4 hours": 240, "1 day": 1440}
m1 = pl.scan_parquet(sorted(D.glob("*/m1.parquet"))).select("time", "close").collect().sort("time")
fr = pl.read_parquet(tape.ROOT / "raw" / "binance" / "um" / "fundingRate" / "BTCUSDT-fundingRate.parquet").select(
    pl.col("fundingTime").cast(pl.Int64).cast(pl.Datetime("ms")).cast(pl.Datetime("us")).alias("ft"), "fundingRate")


def run(minutes):
    every = f"{minutes}m"; per_day = 1440 // minutes; per_year = per_day * 365
    B = m1.group_by_dynamic("time", every=every).agg(pl.col("close").last()).sort("time")
    B = (pl.DataFrame({"time": pl.datetime_range(B["time"][0], B["time"][-1], every, eager=True)}).join(B, on="time", how="left")
         .with_columns(pl.col("close").forward_fill()).drop_nulls("close").with_columns((pl.col("time") + pl.duration(minutes=minutes)).alias("t_close")))
    f = fr.with_columns((pl.col("ft") - pl.duration(milliseconds=1)).dt.truncate(every).alias("bar")).group_by("bar").agg(pl.col("fundingRate").sum())   # paid by the position open at the settlement: the bar that ends at it
    fund = B.select("time").join(f, left_on="time", right_on="bar", how="left")["fundingRate"].fill_null(0.0).to_numpy()
    p = B["close"].to_numpy(); n = len(p); r = np.r_[0.0, p[1:] / p[:-1] - 1]
    span_vol = 36 * per_day
    sig_ann = np.sqrt(pl.Series(r ** 2).ewm_mean(span=span_vol, min_samples=7 * per_day).to_numpy() * per_year)
    dp_sd = pl.Series(np.r_[0.0, np.diff(p)] ** 2).ewm_mean(span=span_vol, min_samples=7 * per_day).sqrt().to_numpy()
    IS = B["t_close"].to_numpy() < np.datetime64("2025-01-01"); live = np.arange(n) >= 90 * per_day
    out = {}
    for fh in FAST_H:
        fast = fh * per_day / 24
        if fast < 2: continue
        raw = (pl.Series(p).ewm_mean(span=fast, adjust=False).to_numpy() - pl.Series(p).ewm_mean(span=4 * fast, adjust=False).to_numpy()) / dp_sd
        ok = np.isfinite(raw); fc = raw / (np.cumsum(np.where(ok, np.abs(raw), 0.0)) / np.maximum(np.cumsum(ok), 1))
        target = np.nan_to_num(fc * TARGET / sig_ann); target[: 60 * per_day] = 0.0
        avg = np.cumsum(np.abs(target)) / np.arange(1, n + 1)
        pos = np.empty(n); cur = 0.0
        for i in range(n):
            if abs(target[i] - cur) > BUFFER * max(avg[i], 1e-9): cur = target[i]
            pos[i] = cur
        held = np.r_[0.0, pos[:-1]]; trade = np.abs(np.diff(np.r_[0.0, pos]))
        gross = held * r; cost = trade * (TAKER + HALF) / 1e4; funding = held * fund; net = gross - cost - funding
        row = {}
        for lab, m in (("2021-2024", IS & live), ("2025-2026", ~IS)):
            yrs = m.sum() / per_year
            row[lab] = dict(sharpe=round(float(net[m].mean() / net[m].std() * np.sqrt(per_year)), 2), gross_sharpe=round(float(gross[m].mean() / gross[m].std() * np.sqrt(per_year)), 2),
                            ret=round(float(net[m].mean() * per_year), 4), vol=round(float(net[m].std() * np.sqrt(per_year)), 4), cost=round(float(cost[m].sum() / yrs), 4),
                            funding=round(float(funding[m].sum() / yrs), 4), turnover=round(float(trade[m].sum() / yrs), 1))
        out[f"{fh} h"] = row
    return out


R = {}
for lab, mins in BARS.items():
    R[lab] = run(mins); print(lab, "done", flush=True)
(L16_RESULTS / "l16_trend_bars.json").write_text(json.dumps(R, indent=1))
print("\nSharpe after costs, 2021-2024 / 2025-2026 (gross 2021-2024)")
print(f"{'fast span':>10} | " + " | ".join(f"{b:>18}" for b in BARS))
for fh in FAST_H:
    cells = []
    for b in BARS:
        x = R[b].get(f"{fh} h")
        cells.append(f"{x['2021-2024']['sharpe']:+5.2f} / {x['2025-2026']['sharpe']:+5.2f} ({x['2021-2024']['gross_sharpe']:+4.2f})" if x else f"{'—':>18}")
    print(f"{fh:>8} h | " + " | ".join(f"{c:>18}" for c in cells))
print("\ncosts a year, 2021-2024")
for fh in FAST_H:
    print(f"{fh:>8} h | " + " | ".join(f"{R[b][f'{fh} h']['2021-2024']['cost']:>18.1%}" if f"{fh} h" in R[b] else f"{'—':>18}" for b in BARS))
