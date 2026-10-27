"""Lecture 16: the trend rule built up step by step, on hourly candles, fast spans 1, 2 and 3 days blended with equal weights (slow = 4 x fast).
Step 0, plain: sized by the past 36 days' volatility of hourly returns; market orders at the close (5 bp taker + 0.04 bp half-spread); funding at every
settlement. Step 1, + sizing by forecast risk: the next 24 hours' variance forecast by a HAR on one-minute realised variance (last hour, day, week),
fitted on 2021-2024. Step 2, + the re-posted entry of Lecture 15 §6: 1.96 bp cheaper per unit traded than a market order. Step 3, + longs in spot:
long positions held in spot (no funding; 10 bp spot fee on the long side; the cash tied up forgoes the 3-month T-bill rate); shorts stay in the
perpetual. Buffer 10%. Measures: Sharpe, return and volatility, costs, funding, turnover, maximum drawdown, and how steady risk is: the spread of the
monthly realised volatility around its average (coefficient of variation)."""
import json, sys
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
TAKER, HALF, REPOST_SAVING, SPOT_FEE, TARGET, BUFFER = 5.0, 0.04, 1.96, 10.0, 0.10, 0.10
FAST_D = [1, 2, 3]; PY = 24 * 365
m1 = pl.scan_parquet(sorted(D.glob("*/m1.parquet"))).select("time", "close").collect().sort("time")
Hh = (m1.with_columns(pl.col("close").log().diff().alias("lr")).group_by_dynamic("time", every="1h")
      .agg(pl.col("close").last(), (pl.col("lr") ** 2).sum().alias("rv")).sort("time"))
H = (pl.DataFrame({"time": pl.datetime_range(Hh["time"][0], Hh["time"][-1], "1h", eager=True)}).join(Hh, on="time", how="left")
     .with_columns(pl.col("close").forward_fill(), pl.col("rv").fill_null(0.0)).drop_nulls("close").with_columns((pl.col("time") + pl.duration(hours=1)).alias("t_close")))
p = H["close"].to_numpy(); n = len(p); r = np.r_[0.0, p[1:] / p[:-1] - 1]; rv = H["rv"].to_numpy()
fr = pl.read_parquet(tape.ROOT / "raw" / "binance" / "um" / "fundingRate" / "BTCUSDT-fundingRate.parquet").select(
    pl.col("fundingTime").cast(pl.Int64).cast(pl.Datetime("ms")).cast(pl.Datetime("us")).dt.truncate("1h").alias("ft"), "fundingRate")
# a settlement at time T is paid by the position open at T: the one held through the hour that ends at T
fund = H.select("t_close").join(fr.group_by("ft").agg(pl.col("fundingRate").sum()), left_on="t_close", right_on="ft", how="left")["fundingRate"].fill_null(0.0).to_numpy()
tb = pl.read_csv(tape.ROOT / "raw" / "fred_DTB3.csv", infer_schema_length=0)
tb = tb.select(pl.col(tb.columns[0]).str.to_date().cast(pl.Datetime("us")).alias("d"), pl.col(tb.columns[1]).cast(pl.Float64, strict=False).alias("bill")).drop_nulls().sort("d")
bill = H.select(pl.col("time").alias("d")).join_asof(tb, on="d", strategy="backward")["bill"].fill_null(0.0).to_numpy() / 100 / PY   # per hour
tc = H["t_close"].to_numpy(); IS = tc < np.datetime64("2025-01-01"); live = np.arange(n) >= 90 * 24
month = H["t_close"].dt.strftime("%Y-%m").to_numpy()

# risk forecasts, annualised volatility known at each close
sig_plain = np.sqrt(pl.Series(r ** 2).ewm_mean(span=36 * 24, min_samples=7 * 24).to_numpy() * PY)
c = np.r_[0.0, np.cumsum(rv)]
def back(k): out = np.full(n, np.nan); out[k - 1:] = (c[k:] - c[:-k]) / k; return out                 # mean hourly rv over the last k hours, incl. this one
fwd24 = np.full(n, np.nan); fwd24[:-24] = (c[25:] - c[1:-24]) / 24                                     # mean hourly rv over the next 24 hours
X = np.column_stack([np.ones(n), np.log(np.maximum(rv, 1e-12)), np.log(back(24)), np.log(back(168))]); y = np.log(fwd24)
ok = np.all(np.isfinite(X), axis=1) & np.isfinite(y) & live
b = np.linalg.lstsq(X[ok & IS], y[ok & IS], rcond=None)[0]; corr = np.mean(np.exp(y[ok & IS] - X[ok & IS] @ b))
sig_har = np.sqrt(np.exp(X @ b) * corr * PY)


def forecast(sig_dp, fast_days=FAST_D):
    fcs = []
    for fd in fast_days:
        f = fd * 24
        raw = (pl.Series(p).ewm_mean(span=f, adjust=False).to_numpy() - pl.Series(p).ewm_mean(span=4 * f, adjust=False).to_numpy()) / sig_dp
        okr = np.isfinite(raw); fcs.append(raw / (np.cumsum(np.where(okr, np.abs(raw), 0.0)) / np.maximum(np.cumsum(okr), 1)))
    fc = sum(fcs) / len(fcs); okf = np.isfinite(fc)
    return fc / (np.cumsum(np.where(okf, np.abs(fc), 0.0)) / np.maximum(np.cumsum(okf), 1))      # the blend rescaled to an average size of 1


dp_sd = pl.Series(np.r_[0.0, np.diff(p)] ** 2).ewm_mean(span=36 * 24, min_samples=7 * 24).sqrt().to_numpy()
FC = forecast(dp_sd)


def simulate(sig, cost_bp, spot_longs=False, fc=None):
    target = np.nan_to_num((FC if fc is None else fc) * TARGET / sig); target[: 90 * 24] = 0.0
    avg = np.cumsum(np.abs(target)) / np.arange(1, n + 1); pos = np.empty(n); cur = 0.0
    for i in range(n):
        if abs(target[i] - cur) > BUFFER * max(avg[i], 1e-9): cur = target[i]
        pos[i] = cur
    held = np.r_[0.0, pos[:-1]]; prev = np.r_[0.0, pos[:-1]]
    gross = held * r
    if not spot_longs:
        cost = np.abs(pos - prev) * cost_bp / 1e4; funding = held * fund; carry = np.zeros(n)
    else:                                                                                           # longs in spot, shorts in the perpetual
        lp, ls = np.maximum(pos, 0), np.minimum(pos, 0); lpp, lsp = np.maximum(prev, 0), np.minimum(prev, 0)
        cost = np.abs(lp - lpp) * (SPOT_FEE - REPOST_SAVING * 0) / 1e4 + np.abs(ls - lsp) * cost_bp / 1e4
        funding = np.minimum(held, 0) * fund; carry = np.maximum(held, 0) * bill                     # cash tied up in spot forgoes the bill rate
    net = gross - cost - funding - carry
    return net, dict(gross=gross, cost=cost, funding=funding, carry=carry, pos=pos)


def stats(net, parts, m):
    yrs = m.sum() / PY; x = net[m]; w = np.cumsum(x)
    mv = pl.DataFrame({"m": month[m], "x": x}).group_by("m").agg((pl.col("x").std() * np.sqrt(PY)).alias("v"), pl.len().alias("k")).filter(pl.col("k") >= 24 * 25)["v"].to_numpy()
    return dict(sharpe=round(float(x.mean() / x.std() * np.sqrt(PY)), 2), ret=round(float(x.mean() * PY), 4), vol=round(float(x.std() * np.sqrt(PY)), 4),
                maxdd=round(float((w - np.maximum.accumulate(w)).min()), 4), cost=round(float(parts["cost"][m].sum() / yrs), 4),
                funding=round(float(parts["funding"][m].sum() / yrs), 4), carry=round(float(parts["carry"][m].sum() / yrs), 4),
                turnover=round(float(np.abs(np.diff(np.r_[0.0, parts["pos"]]))[m].sum() / yrs), 1), vol_cv=round(float(mv.std() / mv.mean()), 2),
                worst_day=round(float(pl.Series(x).rolling_sum(24).min() / (x.std() * np.sqrt(24))), 1))


sig_smooth = np.sqrt(pl.Series(sig_har ** 2).fill_nan(None).ewm_mean(span=24, min_samples=1, ignore_nulls=True).to_numpy().astype(float))   # correction after the first run: the risk forecast smoothed over a day
STEPS = [("0 plain", sig_plain, TAKER + HALF, False), ("1 + sizing by forecast risk", sig_har, TAKER + HALF, False), ("1b sizing, forecast smoothed", sig_smooth, TAKER + HALF, False),
         ("2 + re-posted entry", sig_smooth, TAKER + HALF - REPOST_SAVING, False), ("3 + longs in spot", sig_smooth, TAKER + HALF - REPOST_SAVING, True)]

if __name__ == "__main__":                                                         # the build-up's own runs; other scripts import only the data and functions above
    R = {}; series = {}
    for lab, sig, cb, spot in STEPS:
        net, parts = simulate(sig, cb, spot); series[lab] = net
        R[lab] = {"2021-2024": stats(net, parts, IS & live), "2025-2026": stats(net, parts, ~IS)}
    (L16_RESULTS / "l16_buildup.json").write_text(json.dumps(R, indent=1))
    pl.DataFrame({"t": H["t_close"], **{k: v for k, v in series.items()}}).write_parquet(tape.ROOT / "interim" / "l16_buildup.parquet")
    print("HAR coefficients (const, last hour, last day, last week):", np.round(b, 3))
    for k, v in R.items():
        a, z = v["2021-2024"], v["2025-2026"]
        print(f"{k:30} IS Sharpe {a['sharpe']:+5.2f} ret {a['ret']:+6.1%} vol {a['vol']:5.1%} cost {a['cost']:5.1%} fund {a['funding']:+5.1%} carry {a['carry']:4.1%} "
              f"vol-cv {a['vol_cv']:.2f} worst day {a['worst_day']:+.1f}sd | OOS Sharpe {z['sharpe']:+5.2f} ret {z['ret']:+6.1%} vol {z['vol']:5.1%} maxdd {z['maxdd']:+6.1%} vol-cv {z['vol_cv']:.2f}")

    # the same steps for single speeds, from 12 hours to three weeks, each about 1.6 times the last
    CURVE = {}
    for fd in (0.5, 1, 2, 3, 5, 8, 13, 21):
        fcs = forecast(dp_sd, [fd]); CURVE[f"{fd} d"] = {}
        for lab, sig, cb, spot in STEPS:
            net, parts = simulate(sig, cb, spot, fc=fcs)
            CURVE[f"{fd} d"][lab] = {"2021-2024": stats(net, parts, IS & live), "2025-2026": stats(net, parts, ~IS)}
    R["curve"] = CURVE
    (L16_RESULTS / "l16_buildup.json").write_text(json.dumps(R, indent=1))
    print("Sharpe after costs by speed, 2021-2024 / 2025-2026")
    print(f"{'fast span':>9} | " + " | ".join(f"{lab[:24]:>24}" for lab, *_ in STEPS))
    for k, v in CURVE.items():
        print(f"{k:>9} | " + " | ".join(f"{v[lab]['2021-2024']['sharpe']:+5.2f} / {v[lab]['2025-2026']['sharpe']:+5.2f} c{v[lab]['2021-2024']['cost']:4.1%}".rjust(24) for lab, *_ in STEPS))
