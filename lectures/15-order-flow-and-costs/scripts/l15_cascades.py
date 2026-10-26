"""Lecture 15 §4: early warnings of a cascade, fuel and spark. Hourly panel, every warning read from data known at the start of the hour.
Cascade: an hour whose move, over its typical size (the square root of the 28-day median daily variance / 24), is in the top 1% (cut-off from 2021-2024).
Control: the last hour's realised variance against its 28-day median, in fifths. Fuel: F1 open interest vs its 28-day median (top fifth), F2 funding's
distance from 0.01% (top fifth), F3 accounts' long/short ratio, distance from its 28-day median (top fifth), F4a last 24 h's variance vs the 28-day median
(bottom fifth), F4b 28-day variance vs the trailing year (bottom fifth), F5 hours spent in a band of one typical daily move (top fifth).
Spark, the last 15 minutes: S1 open interest change (bottom fifth: largest fall), S2 net flow's absolute share (top fifth), S3 price change per dollar
traded vs its 28-day median (top fifth), S4 at least one sweep of 10 bp or more. Cut-offs from 2021-2024; tested in-sample and on 2025-2026.
Test: cascade (0/1) on the warning plus control-fifth dummies, ordinary least squares, days as clusters; BH over the in-sample tests."""
import json, math, sys
from datetime import datetime, timedelta
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
from l15_cascade_fn import hours_in_band, same_sign_run

D = tape.ROOT / "interim" / "tape" / "BTCUSDT"
m1 = pl.scan_parquet(sorted(D.glob("*/m1.parquet"))).select("time", "high", "low", "close", "usd", "signed_usd").collect().sort("time")
t0 = m1["time"][0].replace(minute=0, second=0, microsecond=0); n = int((m1["time"][-1] - t0).total_seconds() // 60) + 1
g = (pl.DataFrame({"time": pl.datetime_range(t0, t0 + timedelta(minutes=n - 1), "1m", eager=True)}).join(m1, on="time", how="left").sort("time")
     .with_columns(pl.col("close").forward_fill(), pl.col("usd").fill_null(0.0), pl.col("signed_usd").fill_null(0.0)))
g = g.with_columns(pl.col("high").fill_null(pl.col("close")), pl.col("low").fill_null(pl.col("close")))
del m1
lp = np.log(g["close"].to_numpy()); r1 = np.r_[0.0, np.diff(lp)]; usd = g["usd"].to_numpy(); sus = g["signed_usd"].to_numpy()
cs = lambda x: np.r_[0.0, np.cumsum(x)]                                         # window sums from cumulative sums: S[a, b) = c[b] - c[a]
c_r2, c_usd, c_sus, c_abs = cs(r1 ** 2), cs(usd), cs(sus), cs(np.abs(r1))
dvar = pl.Series(r1 ** 2).rolling_sum(1440).rolling_median(28 * 1440, min_samples=7 * 1440).shift(1).to_numpy()   # typical daily variance, known before

H = np.arange(28 * 1440 + 60, n - 60, 60)                                       # hour starts (index of the hour's first minute)
time = g["time"].to_numpy()[H]; day = H // 1440
sig_h = np.sqrt(dvar[H] / 24); move = (lp[H + 59] - lp[H - 1]) / sig_h          # the hour's move over its typical size
rv_last = c_r2[H] - c_r2[H - 60]
rv60 = c_r2[60:] - c_r2[:-60]; rv60 = np.r_[np.full(60, np.nan), rv60][:n]     # rv over the 60 minutes up to and including minute i
med60 = pl.Series(rv60).rolling_median(28 * 1440, min_samples=7 * 1440).shift(1).to_numpy()
ctrl = rv_last / med60[H - 1]

# fuel from the tape
f4a = (c_r2[H] - c_r2[H - 1440]) / dvar[H]
dd = pl.DataFrame({"r2": r1 ** 2, "d": np.arange(n) // 1440}).group_by("d").agg(pl.col("r2").sum()).sort("d")
v28 = dd["r2"].rolling_mean(28).to_numpy()
rank = np.full(len(v28), np.nan)
for k in range(365 + 28, len(v28)):
    w = v28[k - 365:k]; rank[k] = np.mean(w < v28[k - 1])                       # yesterday's 28-day variance against the year before: known at day k
f4b = rank[np.searchsorted(dd["d"].to_numpy(), day)]
hb = g.with_columns((pl.int_range(pl.len()) // 60).alias("h")).group_by("h").agg(pl.col("high").max(), pl.col("low").min()).sort("h")
lh, ll = np.log(hb["high"].to_numpy()), np.log(hb["low"].to_numpy())
width = np.full(len(lh), np.nan); width[H // 60] = np.sqrt(dvar[H])
f5 = hours_in_band(lh, ll, width, 2000)[H // 60]
hi24 = np.array([lh[h - 24:h].max() for h in H // 60]); hi20d = np.array([lh[max(h - 480, 0):h].max() for h in H // 60])
lo24 = np.array([ll[h - 24:h].min() for h in H // 60]); lo20d = np.array([ll[max(h - 480, 0):h].min() for h in H // 60])
def gap(k):                                                                     # how far apart the 1-day and k-hour highs and lows are, in typical daily moves
    hk = np.array([lh[max(h - k, 0):h].max() for h in H // 60]); lk = np.array([ll[max(h - k, 0):h].min() for h in H // 60])
    return ((hk - hi24) + (lo24 - lk)) / 2 / np.sqrt(dvar[H])
gap_levels = gap(480); gap3, gap7 = gap(72), gap(168)

# spark from the tape: the last 15 minutes
s2 = same_sign_run(sus)[H - 1]                                                # minutes in a row with net flow on the same side, up to the hour start
ill15 = (c_abs[15:] - c_abs[:-15]) / np.where(c_usd[15:] - c_usd[:-15] > 0, c_usd[15:] - c_usd[:-15], np.nan); ill15 = np.r_[np.full(15, np.nan), ill15][:n]
illmed = pl.Series(ill15).rolling_median(28 * 1440, min_samples=7 * 1440).shift(1).to_numpy()
s3 = ill15[H] / illmed[H]                                                       # |price change| per dollar over the last 15 min, vs its 28-day median
SW = pl.read_parquet(tape.ROOT / "interim" / "l15_sweeps.parquet", columns=["time_ms", "move_bp"]).filter(pl.col("move_bp") >= 10)
t0ms = int(np.datetime64(t0, "ms").astype(np.int64)); swm = np.sort((SW["time_ms"].to_numpy() - t0ms) // 60_000)
s4 = (np.searchsorted(swm, H) - np.searchsorted(swm, H - 15)) > 0

P = pl.DataFrame({"time": time, "day": day, "move": move, "ctrl": ctrl, "F4a quiet": f4a, "F4b complacency": f4b, "F5 time in band": f5, "gap_levels": gap_levels, "gap3": gap3, "gap7": gap7,
                  "S2 one-sided flow": s2, "S3 impact per dollar": s3, "S4 sweep": s4.astype(float)})

# open interest, crowding, funding (if downloaded)
mf = tape.ROOT / "interim" / "l15_metrics.parquet"
if mf.exists():
    M = pl.read_parquet(mf).select("time", pl.col("sum_open_interest").alias("oi"), pl.col("count_long_short_ratio").log().alias("lls")).sort("time")
    M = M.with_columns((pl.col("oi") / pl.col("oi").rolling_median(28 * 288, min_samples=7 * 288).shift(1)).alias("oi_rel"),
                       (pl.col("lls") - pl.col("lls").rolling_median(28 * 288, min_samples=7 * 288).shift(1)).abs().alias("crowd"),
                       (pl.col("oi") / pl.col("oi").shift(3)).log().alias("doi15"))
    # a metrics row stamped T describes the 5 minutes up to T; to be safe, use the last stamp at least 5 minutes before the hour start
    P = P.with_columns((pl.col("time") - pl.duration(minutes=5)).alias("tk")).sort("tk").join_asof(
        M.select(pl.col("time").alias("tk"), "oi_rel", "crowd", "doi15").sort("tk"), on="tk", strategy="backward", tolerance="15m").drop("tk")
    P = P.rename({"oi_rel": "F1 open interest", "crowd": "F3 crowding", "doi15": "S1 open interest change"})
fr = pl.read_parquet(tape.ROOT / "raw" / "binance" / "um" / "fundingRate" / "BTCUSDT-fundingRate.parquet").select(
    pl.col("fundingTime").cast(pl.Int64).cast(pl.Datetime("ms")).cast(pl.Datetime("us")).alias("ft"), (pl.col("fundingRate") - 0.0001).abs().alias("F2 funding")).sort("ft")
P = P.sort("time").join_asof(fr, left_on="time", right_on="ft", strategy="backward").drop("ft")

IS = P["time"] < datetime(2025, 1, 1)
cut = float(np.nanquantile(np.abs(P.filter(IS)["move"].to_numpy()), 0.99))
P = P.sort("time").with_columns((pl.col("move").abs() >= cut).cast(pl.Float64).alias("cascade"))
P = P.with_columns(pl.col("cascade").reverse().rolling_max(24, min_samples=24).reverse().alias("cascade24"), (pl.col("day") // 7).alias("week"))   # a cascade within the next 24 hours
cq = np.nanquantile(P.filter(IS)["ctrl"].to_numpy(), [0.2, 0.4, 0.6, 0.8])
P = P.with_columns(pl.col("ctrl").cut(list(cq), labels=[str(k) for k in range(5)]).cast(pl.Utf8).alias("cfifth"))
SIDE = {"F1 open interest": "top", "F2 funding": "top", "F3 crowding": "top", "F4a quiet": "bottom", "F4b complacency": "bottom", "F5 time in band": "top",
        "S1 open interest change": "bottom", "S2 one-sided flow": "top", "S3 impact per dollar": "top", "S4 sweep": "flag"}


def lpm(df, flag, target="cascade", cl="day"):
    """Cascade on the warning and control-fifth dummies; returns the warning's coefficient and its day-clustered standard error."""
    X = np.column_stack([flag] + [(df["cfifth"] == str(k)).to_numpy().astype(float) for k in range(5)]); y = df[target].to_numpy()
    XtX = np.linalg.inv(X.T @ X); b = XtX @ X.T @ y; e = y - X @ b
    _, inv = np.unique(df[cl].to_numpy(), return_inverse=True); sc = np.zeros((inv.max() + 1, X.shape[1])); np.add.at(sc, inv, X * e[:, None])
    V = XtX @ (sc.T @ sc) @ XtX; G = sc.shape[0]; V *= G / (G - 1); return b[0], math.sqrt(V[0, 0])


def bh(p):
    p = np.asarray(p); o = np.argsort(p); q = p[o] * len(p) / np.arange(1, len(p) + 1); q = np.minimum.accumulate(q[::-1])[::-1]; out = np.empty_like(q); out[o] = np.minimum(q, 1); return out


rows = []
for w, side in SIDE.items():
    if w not in P.columns: continue
    x_is = P.filter(IS)[w].to_numpy()
    thr = None if side == "flag" else float(np.nanquantile(x_is, 0.8 if side == "top" else 0.2))
    for target, cl in (("cascade", "day"), ("cascade24", "week")):
        if target == "cascade24" and not w.startswith("F"): continue                 # the 24-hour horizon is for fuel only
        for lab, part in (("2021-2024", P.filter(IS)), ("2025-2026", P.filter(~IS))):
            part = part.drop_nulls([w, "cfifth", target]).filter(pl.col(w).is_not_nan())
            x = part[w].to_numpy(); f = (x > 0.5) if side == "flag" else ((x >= thr) if side == "top" else (x <= thr)); f = f.astype(float)
            y = part[target].to_numpy(); yrs = (part["time"].max() - part["time"].min()).total_seconds() / (365.25 * 86400)
            b, se = lpm(part, f, target, cl)
            rows.append(dict(warning=w, horizon="1 h" if target == "cascade" else "24 h", sample=lab, hours=len(y), flagged=round(f.mean(), 3),
                             rate_flag=round(y[f == 1].mean() * 100, 2), rate_no=round(y[f == 0].mean() * 100, 2), lift=round(y[f == 1].mean() / y[f == 0].mean(), 2),
                             caught=round(y[f == 1].sum() / y.sum(), 2), false_alarms_per_year=round(((f == 1) & (y == 0)).sum() / yrs), added_pp=round(b * 100, 2),
                             t=round(b / se, 1), p=math.erfc(abs(b / se) / math.sqrt(2))))
ins = [r for r in rows if r["sample"] == "2021-2024"]
for r, q in zip(ins, bh([r["p"] for r in ins])): r["q_bh"] = round(float(q), 4)
# the control alone: how much does the last hour's volatility say?
ctl = {lab: {k: round(float(part.filter(pl.col("cfifth") == str(k))["cascade"].mean() * 100), 2) for k in range(5)} for lab, part in (("2021-2024", P.filter(IS)), ("2025-2026", P.filter(~IS)))}
# mechanism check for F5: do the 1-day and 20-day levels converge after a long time in the band?
P5 = P.filter(IS).drop_nulls(["F5 time in band"]).with_columns(pl.col("F5 time in band").qcut(5, labels=[str(k) for k in range(5)], allow_duplicates=True).alias("q5"))
mech = P5.group_by("q5").agg(pl.col("F5 time in band").median().alias("hours"), pl.col("gap3").median(), pl.col("gap7").median(), pl.col("gap_levels").median().alias("gap20"), pl.len()).sort("q5").to_dicts()
# the footprint at the break: hours in which the band of the previous L hours is broken (the next hour's band count does not grow), by L
Q = P.sort("time").with_columns(pl.col("F5 time in band").shift(-1).alias("f5_next"), pl.col("move").abs().alias("am"), pl.col("move").abs().shift(-1).alias("am_next"), pl.col("cascade").shift(-1).alias("casc_next"))
Q = Q.filter((pl.col("F5 time in band") >= 2) & (pl.col("f5_next") <= pl.col("F5 time in band")))
brk = {}
for lab, part in (("2021-2024", Q.filter(pl.col("time") < datetime(2025, 1, 1))), ("2025-2026", Q.filter(pl.col("time") >= datetime(2025, 1, 1)))):
    part = part.with_columns(pl.col("F5 time in band").qcut(5, labels=[str(k) for k in range(5)], allow_duplicates=True).alias("q5"))
    brk[lab] = part.group_by("q5").agg(pl.len(), pl.col("F5 time in band").median().alias("band_hours"), pl.col("am").median().alias("break_move"), pl.col("am_next").median().alias("next_move"),
                                       (pl.col("cascade").mean() * 100).alias("casc_pct"), (pl.col("casc_next").mean() * 100).alias("casc_next_pct")).sort("q5").to_dicts()
R = dict(cascade_cut=round(cut, 2), cascade_rate_is=round(float(P.filter(IS)["cascade"].mean() * 100), 2), control=ctl, warnings=rows, f5_mechanism=mech, f5_break=brk)
(L15_RESULTS / "l15_cascades.json").write_text(json.dumps(R, indent=1, default=str))
P.write_parquet(tape.ROOT / "interim" / "l15_cascade_panel.parquet")
print("cascade: |move| >=", round(cut, 2), "typical hourly moves; rate", R["cascade_rate_is"], "%"); print("cascade rate % by control fifth:", ctl)
for r in rows:
    print(f"{r['warning']:26}{r['horizon']:5}{r['sample']:10} flagged {r['flagged']:.2f}  rate {r['rate_flag']:5.2f}% vs {r['rate_no']:5.2f}%  lift {r['lift']:5.2f}  caught {r['caught']:.2f}  "
          f"false/yr {r['false_alarms_per_year']:5}  added {r['added_pp']:+5.2f} pp (t {r['t']:+5.1f})" + (f"  q {r['q_bh']:.4f}" if "q_bh" in r else ""))
print("F5 mechanism:"); [print(m) for m in mech]
print("F5 break:"); [print(k, m) for k, v in brk.items() for m in v]
