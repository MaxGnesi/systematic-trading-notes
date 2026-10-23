"""Lecture 14 §5: volatility built up.
1. Two days, every estimator as a running curve: an ordinary weekday (median realised variance) and the Fed decision of 21 September 2022.
2. The interval: realised variance from 1-second to 1-hour returns (Lecture 12's daily tables) and the variance ratio to a week (l14_path_tests), relative to 1 minute.
3. Five years: each daily estimator against one-minute realised variance; the share of a day's variance in its busiest 1% of minutes; the jump share (1 - bipower/RV)."""
import json, sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import numpy as np, polars as pl
from plotly.subplots import make_subplots
import os, sys
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # tables print on any console; Jupyter handles its own
HERE = Path(__file__).resolve().parent                                     # lectures/14-.../scripts
sys.path[:0] = [str(HERE), str(HERE.parents[1] / "13-bars-not-cut-by-time" / "scripts"), str(HERE.parents[1] / "12-tick-data-the-tape"), str(HERE.parents[2])]
import tape
L14_RESULTS = tape.ROOT / "interim" / "l14"; L14_RESULTS.mkdir(parents=True, exist_ok=True)          # results: in the data folder, never committed
FIG = Path(os.environ.get("L14_FIG", HERE.parent / "figures")); FIG.mkdir(parents=True, exist_ok=True)
PREFIX = os.environ.get("L14_PREFIX", "nb_")                               # "nb_": the lecture's own figures are never overwritten
import tape
from trading_models.plotting import INK, MUTED, SERIES, apply_theme, save_figure

apply_theme()
SYM = "BTCUSDT"; D = tape.ROOT / "interim" / "tape" / SYM
R = {}
m1 = pl.scan_parquet(sorted(D.glob("*/m1.parquet"))).select("time", "open", "high", "low", "close").collect().sort("time").with_columns(pl.col("time").dt.date().alias("day"))
rvd = pl.scan_parquet(sorted(D.glob("*/rv_days.parquet"))).collect().sort("day")
LN2 = np.log(2)

# ---------------------------------------------------------------- daily estimators, five years
d = (m1.with_columns(pl.col("close").log().diff().alias("r"))
       .group_by("day").agg(pl.col("open").first().alias("O"), pl.col("high").max().alias("H"), pl.col("low").min().alias("L"), pl.col("close").last().alias("C"),
                            (pl.col("r") ** 2).sum().alias("rv1m"), (np.pi / 2 * (pl.col("r").abs() * pl.col("r").abs().shift(1))).sum().alias("bv1m"),
                            pl.col("r").pow(2).sort(descending=True).head(14).sum().alias("top1pct"), pl.len().alias("n"))
       .filter(pl.col("n") == 1440).sort("day"))
c5 = (m1.filter(pl.col("time").dt.minute() % 5 == 4).with_columns(pl.col("close").log().diff().alias("r5")).group_by("day").agg((pl.col("r5") ** 2).sum().alias("rv5m")))
d = d.join(c5, on="day").join(rvd.select("day", pl.col("rv_1").alias("rv1s")), on="day").with_columns(
    (pl.col("C") / pl.col("C").shift(1)).log().pow(2).alias("cc"),
    ((pl.col("H") / pl.col("L")).log().pow(2) / (4 * LN2)).alias("park"),
    (0.5 * (pl.col("H") / pl.col("L")).log().pow(2) - (2 * LN2 - 1) * (pl.col("C") / pl.col("O")).log().pow(2)).alias("gk")).drop_nulls()
EST = {"close to close": "cc", "Parkinson (high-low)": "park", "Garman-Klass": "gk", "realised, 5 min": "rv5m", "realised, 1 s": "rv1s", "bipower, 1 min": "bv1m"}
R["vs_rv1m"] = {}
for lab, col in EST.items():
    x = np.log((d[col] / d["rv1m"]).to_numpy()); x = x[np.isfinite(x)]
    R["vs_rv1m"][lab] = dict(median=round(float(np.exp(np.median(x))), 2), p10=round(float(np.exp(np.quantile(x, .1))), 2), p90=round(float(np.exp(np.quantile(x, .9))), 2))
top = (d["top1pct"] / d["rv1m"]).to_numpy(); jump = np.clip(1 - (d["bv1m"] / d["rv1m"]).to_numpy(), 0, None)
R["top1pct_share"] = dict(median=round(float(np.median(top)), 3), p90=round(float(np.quantile(top, .9)), 3))
R["jump_share"] = dict(median=round(float(np.median(jump)), 3), p90=round(float(np.quantile(jump, .9)), 3), mean=round(float(jump.mean()), 3))
print(json.dumps(R, indent=1), flush=True)

fig = make_subplots(rows=1, cols=1)
labs = list(EST)[::-1]
for i, lab in enumerate(labs):
    v = R["vs_rv1m"][lab]
    fig.add_scatter(x=[v["p10"], v["p90"]], y=[lab, lab], mode="lines", line=dict(color=SERIES[0], width=6), showlegend=(i == 0), name="10th to 90th percentile of days")
    fig.add_scatter(x=[v["median"]], y=[lab], mode="markers", marker=dict(color=INK, size=11), showlegend=(i == 0), name="median day")
fig.add_vline(x=1, line=dict(color=MUTED, dash="dot"))
fig.update_xaxes(type="log", tickvals=[0.01, 0.1, 0.3, 1, 3, 10], ticktext=["0.01", "0.1", "0.3", "1", "3", "10"], title_text="the estimate ÷ one-minute realised variance (log scale)")
fig.update_layout(title="Every estimator measures the same day's variance, with very different precision<br><sup>Each day's estimate divided by the day's one-minute realised variance, "
                        "five years of BTCUSDT; a narrow bar is a precise estimator, a bar away from 1 a biased one</sup>", height=420, width=1100, margin=dict(t=100, l=190),
                  legend=dict(orientation="h", y=-0.22, x=0))
save_figure(fig, PREFIX + "14_09_estimators_five_years", FIG)

# ---------------------------------------------------------------- 1. two days, running curves
wk = d.filter(pl.col("day").dt.weekday() <= 5)
wk = wk.with_columns(pl.col("cc").sqrt().alias("move")).filter(pl.col("day").dt.year() >= 2024)
ordinary = wk.with_columns(((pl.col("rv1m").rank() / wk.height - 0.5).abs() + (pl.col("move").rank() / wk.height - 0.5).abs()).alias("dist")).sort("dist")["day"][0]   # median variance and median net move
DAYS = [(ordinary, f"An ordinary day: {ordinary:%d %B %Y}"), (date(2022, 9, 21), "A day with a jump: the Fed decision, 21 September 2022")]
fig = make_subplots(rows=2, cols=2, shared_xaxes=True, row_heights=[0.4, 0.6], vertical_spacing=0.06, horizontal_spacing=0.06, subplot_titles=[t for _, t in DAYS] + ["", ""])
COLS = {"every trade": MUTED, "realised, 1 s": SERIES[1], "realised, 1 min": SERIES[0], "realised, 5 min": SERIES[2], "bipower, 1 min": SERIES[3], "Parkinson, range so far": INK}
R["days"] = {}
for c, (d0, _) in enumerate(DAYS, start=1):
    a = int(datetime(d0.year, d0.month, d0.day, tzinfo=timezone.utc).timestamp() * 1000)
    t = (pl.scan_parquet(tape.source(SYM, d0.strftime("%Y-%m"))).filter(pl.col("transact_time").is_between(a, a + 86_400_000, closed="left"))
           .select("transact_time", "price").collect())
    tt = (t["transact_time"].to_numpy() - a) / 3_600_000; lp = np.log(t["price"].to_numpy())
    q = m1.filter(pl.col("day") == d0); hrs = np.arange(1440) / 60 + 1 / 60; lc = np.log(q["close"].to_numpy())
    fig.add_scatter(x=hrs, y=q["close"], mode="lines", line=dict(color=INK, width=1), showlegend=False, row=1, col=c)
    curves = {}
    curves["every trade"] = (tt[1:], np.cumsum(np.diff(lp) ** 2))
    sec = (t.with_columns((pl.col("transact_time") // 1000).alias("s")).group_by("s", maintain_order=True).agg(pl.col("price").last()))
    ls = np.log(sec["price"].to_numpy()); curves["realised, 1 s"] = ((sec["s"].to_numpy()[1:] * 1000 - a) / 3_600_000 + 1 / 3600, np.cumsum(np.diff(ls) ** 2))
    r1 = np.diff(lc); curves["realised, 1 min"] = (hrs[1:], np.cumsum(r1 ** 2))
    r5 = np.diff(lc[4::5]); curves["realised, 5 min"] = (hrs[4::5][1:], np.cumsum(r5 ** 2))
    curves["bipower, 1 min"] = (hrs[2:], np.cumsum(np.pi / 2 * np.abs(r1[1:]) * np.abs(r1[:-1])))
    hi = np.maximum.accumulate(q["high"].to_numpy()); lo = np.minimum.accumulate(q["low"].to_numpy())
    curves["Parkinson, range so far"] = (hrs, np.log(hi / lo) ** 2 / (4 * LN2))
    R["days"][str(d0)] = {}
    for k, (x, y) in curves.items():
        R["days"].setdefault(str(d0), {})[k] = round(float(np.sqrt(y[-1]) * 100), 2)
        if k == "every trade": continue                                  # off the chart: 9% and 80%, single prints and sweeps; given in the text
        step = max(1, len(x) // 3000)
        fig.add_scatter(x=x[::step], y=np.sqrt(y[::step]) * 100, mode="lines", line=dict(color=COLS[k], width=2 if k != "every trade" else 1.2), name=k, legendgroup=k,
                        showlegend=(c == 1), row=2, col=c)
        R["days"][str(d0)][k] = round(float(np.sqrt(y[-1]) * 100), 2)
    cc = abs(lc[-1] - np.log(q["open"][0])) * 100
    fig.add_scatter(x=[24], y=[cc], mode="markers", marker=dict(color=INK, size=10, symbol="diamond"), name="close to close (one return)", legendgroup="cc", showlegend=(c == 1), row=2, col=c)
    R["days"][str(d0)]["close to close"] = round(float(cc), 2)
fig.update_xaxes(tickvals=[0, 6, 12, 18, 24], ticktext=["00:00", "06:00", "12:00", "18:00", "24:00"], title_text="UTC", row=2)
fig.update_yaxes(title_text="price, USDT", row=1, col=1); fig.update_yaxes(title_text="volatility so far, %", row=2, col=1)
fig.update_layout(title="How a day's volatility number is built<br><sup>Each estimator's volatility accumulated through the day (the square root of the variance so far); "
                        "the diamond is the single close-to-close return</sup>", height=640, width=1100, margin=dict(t=100), legend=dict(orientation="h", y=-0.12, x=0))
save_figure(fig, PREFIX + "14_07_volatility_built_up", FIG)

# ---------------------------------------------------------------- 2. the interval: three measures, from 1 second to a week, relative to realised variance at 1 minute
vr = json.loads((L14_RESULTS / "l14_path_tests.json").read_text())["variance_ratio"]
sg = json.loads((L14_RESULTS / "l14_signatures.json").read_text())
xs = [1, 5, 10, 30, 60, 300, 900, 1800, 3600]; key = {1: "1s", 5: "5s", 10: "10s", 30: "30s", 60: "60s", 300: "5m", 900: "15m", 1800: "30m", 3600: "60m"}
fig = make_subplots(rows=1, cols=1)
for lab, col in (("realised variance", SERIES[0]), ("bipower", SERIES[3]), ("realised range", INK)):
    y = [sg["short"][key[x]][lab] if x <= 60 else sg["long"][key[x]][lab] for x in xs]
    xx, yy = (xs + [4 * 3600, 86400, 7 * 86400], y + [vr["4 hours"]["ratio"], vr["1 day"]["ratio"], vr["1 week"]["ratio"]]) if lab == "realised variance" else (xs, y)
    fig.add_scatter(x=xx, y=yy, mode="lines+markers", line=dict(color=col, width=2.3), marker=dict(size=7), name=lab)
fig.add_hline(y=1, line=dict(color=MUTED, dash="dot"))
fig.update_xaxes(type="log", tickvals=[1, 10, 60, 600, 3600, 86400, 604800], ticktext=["1 s", "10 s", "1 min", "10 min", "1 hour", "1 day", "1 week"], title_text="length of the bars the measure uses")
fig.update_yaxes(title_text="÷ realised variance from one-minute returns", range=[0.5, 1.12])
fig.update_layout(title="Each measure has its own best interval<br><sup>Realised variance and bipower peak around a minute; the realised range (Parkinson per bar) needs bars of five minutes "
                        "or more and then stays level. Below a minute from 59 sample days, above from all days</sup>", height=470, width=1100, margin=dict(t=100),
                  legend=dict(orientation="h", y=-0.2, x=0))
save_figure(fig, PREFIX + "14_08_interval", FIG)
xs = xs
ys = [sg["short"][key[x]]["realised variance"] if x <= 60 else sg["long"][key[x]]["realised variance"] for x in xs]; xl = []; yl = []
R["interval"] = dict(zip([f"{s}s" for s in xs + xl], [round(v, 3) for v in ys + yl])); R["ordinary_day"] = str(ordinary)
(L14_RESULTS / "l14_s5.json").write_text(json.dumps(R, indent=1, default=str)); print(json.dumps({k: R[k] for k in ("days", "interval", "ordinary_day")}, indent=1, default=str))
