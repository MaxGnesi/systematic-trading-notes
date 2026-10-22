"""Lecture 13 §7: seasonality of activity, and when each clock makes you trade. From the one-minute bars of Lecture 12 and the bars of bars.py."""
import json, sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import numpy as np, polars as pl
from plotly.subplots import make_subplots
from pandas.tseries.holiday import USFederalHolidayCalendar
import os, sys
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # tables print on any console; Jupyter handles its own
HERE = Path(__file__).resolve().parent                                     # lectures/13-.../scripts
sys.path[:0] = [str(HERE), str(HERE.parents[1] / "12-tick-data-the-tape"), str(HERE.parents[2])]   # this folder, tape.py, trading_models
import tape
L13_RESULTS = tape.ROOT / "interim" / "l13"; L13_RESULTS.mkdir(parents=True, exist_ok=True)          # results: in the data folder, never committed
FIG = Path(os.environ.get("L13_FIG", HERE.parent / "figures")); FIG.mkdir(parents=True, exist_ok=True)
PREFIX = os.environ.get("L13_PREFIX", "nb_")                               # "nb_": the lecture's own figures are never overwritten
import tape, bars, event_dates
from trading_models.plotting import INK, MUTED, SERIES, apply_theme, save_figure

apply_theme()
SYM = "BTCUSDT"; D = tape.ROOT / "interim" / "tape" / SYM
R = {}


def us_dst(d):
    """US daylight saving time: from the second Sunday of March to the first Sunday of November."""
    m = date(d.year, 3, 8); start = m + timedelta(days=(6 - m.weekday()) % 7)
    n = date(d.year, 11, 1); end = n + timedelta(days=(6 - n.weekday()) % 7)
    return start <= d < end


m1 = (pl.concat([pl.read_parquet(f, columns=["time", "usd", "signed_usd", "trades", "close", "high", "low"]) for f in sorted(D.glob("*/m1.parquet"))]).sort("time")
        .with_columns(pl.col("time").dt.date().alias("day"), (pl.col("time").dt.hour().cast(pl.Int32) * 60 + pl.col("time").dt.minute().cast(pl.Int32)).alias("mod"),
                      pl.col("time").dt.weekday().cast(pl.Int32).alias("wd")))
dst_days = {d for d in m1["day"].unique().to_list() if us_dst(d)}
m1 = m1.with_columns(pl.col("day").is_in(sorted(dst_days)).alias("dst"))
m1 = m1.join(m1.group_by("day").agg(pl.col("usd").mean().alias("dm")), on="day").with_columns((pl.col("usd") / pl.col("dm")).alias("rel"))
wk = m1.filter(pl.col("wd") <= 5)

# ---------------------------------------------------------------- 7.1 time of day, and the daylight-saving test
prof = wk.group_by("mod", "dst").agg(pl.col("rel").median()).sort("mod")
hourly = wk.group_by(pl.col("mod") // 60, "dst").agg(pl.col("usd").sum()).sort("mod")
for flag, nm in ((True, "summer"), (False, "winter")):
    h = hourly.filter(pl.col("dst") == flag); sh = h["usd"].to_numpy() / h["usd"].sum()
    p = prof.filter(pl.col("dst") == flag).with_columns(pl.col("rel").rolling_mean(5, center=True).alias("sm"))
    R[f"busiest_hour_{nm}"] = int(h["mod"][int(np.argmax(sh))]); R[f"busiest_hour_share_{nm}"] = round(float(sh.max()), 3)
    R[f"peak_minute_{nm}"] = f"{int(p.sort('rel')['mod'][-1]) // 60:02d}:{int(p.sort('rel')['mod'][-1]) % 60:02d}"
    us = wk.filter((pl.col("dst") == flag) & pl.col("mod").is_between(13 * 60 + 30 if flag else 14 * 60 + 30, 20 * 60 if flag else 21 * 60, closed="left"))
    R[f"open_minute_jump_{nm}"] = round(float(prof.filter((pl.col("dst") == flag) & (pl.col("mod") == (13 * 60 + 30 if flag else 14 * 60 + 30)))["rel"].item()
                                         / prof.filter((pl.col("dst") == flag) & (pl.col("mod") == (13 * 60 + 29 if flag else 14 * 60 + 29)))["rel"].item()), 2)
fig = make_subplots(rows=1, cols=1)
for flag, col, nm in ((True, SERIES[1], "US summer time (second Sunday of March to first Sunday of November)"), (False, SERIES[0], "US winter time")):
    p = prof.filter(pl.col("dst") == flag)
    fig.add_scatter(x=p["mod"] / 60, y=p["rel"], mode="lines", line=dict(color=col, width=1.2), name=nm)
for h, lab in ((13.5, "13:30"), (14.5, "14:30")):
    fig.add_vline(x=h, line=dict(color=MUTED, dash="dot", width=1))
fig.update_xaxes(title_text="time of day, UTC (hours)", dtick=2); fig.update_yaxes(title_text="dollars per minute ÷ day's average")
fig.update_layout(title="The daylight-saving test: when the US changes its clocks, bitcoin's busiest hour moves with it<br><sup>The US stock market opens at 9:30 New York time: "
                        "13:30 UTC in summer, 14:30 UTC in winter. Weekdays, October 2021 to September 2026</sup>",
                  height=470, width=1100, margin=dict(t=90), legend=dict(orientation="h", y=-0.18, x=0))
save_figure(fig, PREFIX + "13_07_time_of_day_dst", FIG)

# ---------------------------------------------------------------- 7.2 the week
how = m1.group_by(((pl.col("wd") - 1) * 24 + pl.col("mod") // 60).alias("h")).agg(pl.col("usd").mean().alias("usd")).sort("h")
wdays = m1.group_by("wd", "day").agg(pl.col("usd").sum()).group_by("wd").agg(pl.col("usd").mean()).sort("wd")
R["dollars_by_weekday_vs_mean"] = {int(w): round(float(u / wdays["usd"].mean()), 2) for w, u in wdays.iter_rows()}
hol = {d.date() for d in USFederalHolidayCalendar().holidays(start="2021-10-01", end="2026-09-30")}
dd = m1.group_by("day", "wd").agg(pl.col("usd").sum()).filter(pl.col("wd") <= 5)
R["us_holiday_vs_weekday"] = round(float(dd.filter(pl.col("day").is_in(sorted(hol)))["usd"].median() / dd.filter(~pl.col("day").is_in(sorted(hol)))["usd"].median()), 2)
R["us_holidays_on_weekdays"] = int(dd.filter(pl.col("day").is_in(sorted(hol))).height)
fig = make_subplots(rows=1, cols=1)
fig.add_scatter(x=how["h"], y=how["usd"] / 1e6, mode="lines", line=dict(color=SERIES[0], width=1.5), showlegend=False)
for i, nm in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]):
    fig.add_vline(x=i * 24, line=dict(color=MUTED, width=1, dash="dot"))
    fig.add_annotation(x=i * 24 + 12, y=1, yref="paper", text=nm, showarrow=False, yanchor="bottom")
fig.update_xaxes(title_text="hour of the week, UTC", tickvals=list(range(0, 169, 12)), ticktext=[f"{h % 24:02d}:00" for h in range(0, 169, 12)])
fig.update_yaxes(title_text="$ millions per minute")
fig.update_layout(title="The week: five busy days, a quiet weekend, and the Monday that starts on Sunday evening", height=440, width=1100, margin=dict(t=80))
pass                                                                    # 13_08_week: no longer in the lecture

# ---------------------------------------------------------------- 7.3 the clock itself: round minutes
m1h = wk.with_columns((pl.col("mod") % 60).alias("moh"), (pl.col("mod") // 60).alias("hh"))
m1h = m1h.join(m1h.group_by("day", "hh").agg(pl.col("usd").mean().alias("hm")), on=["day", "hh"]).with_columns((pl.col("usd") / pl.col("hm")).alias("rel_h"),
            (pl.col("usd") / pl.col("trades")).alias("size"), (pl.col("signed_usd") / pl.col("usd")).abs().alias("oneside"))
moh = m1h.group_by("moh").agg(pl.col("rel_h").median(), pl.col("size").median(), pl.col("oneside").median()).sort("moh")
other = moh.filter(~pl.col("moh").is_in([0, 15, 30, 45]))
R["round_minutes"] = {int(m): dict(activity_vs_hour=round(float(r), 2), trade_size_vs_other=round(float(sz / other["size"].median()), 2), one_sidedness_vs_other=round(float(o / other["oneside"].median()), 2))
                      for m, r, sz, o in moh.filter(pl.col("moh").is_in([0, 1, 15, 30, 45, 59])).iter_rows()}
R["other_minutes_activity_vs_hour"] = round(float(other["rel_h"].median()), 2)
fig = make_subplots(rows=1, cols=1)
fig.add_bar(x=moh["moh"], y=moh["rel_h"], marker=dict(color=[SERIES[3] if m in (0, 15, 30, 45) else SERIES[0] for m in moh["moh"]], line=dict(width=0)), showlegend=False)
fig.add_hline(y=1, line=dict(color=MUTED, dash="dot"))
fig.update_xaxes(title_text="minute of the hour", dtick=5); fig.update_yaxes(title_text="dollars per minute ÷ hour's average")
fig.update_layout(title="The clock itself: trading jumps at the full hour, and at :15, :30 and :45<br><sup>Weekdays, five years. Orders scheduled by the clock: execution algorithms, "
                        "and strategies that decide at the close of time bars</sup>", height=440, width=1100, margin=dict(t=90))
pass                                                                    # 13_09_round_minutes: no longer in the lecture

# ---------------------------------------------------------------- 7.4 scheduled events
m1 = m1.with_columns(pl.col("close").log().diff().abs().alias("absr"))
m1 = m1.join(m1.group_by("day").agg(pl.col("absr").mean().alias("dr")), on="day").with_columns((pl.col("absr") / pl.col("dr")).alias("relr"))
def at(day_list, hh_summer, mm, hh_winter):
    ks = []
    for s in day_list:
        d = date.fromisoformat(s); hh = hh_summer if us_dst(d) else hh_winter
        ks.append(datetime(d.year, d.month, d.day, hh, mm))
    return ks
def friday_last(d): return d.weekday() == 4 and (d + timedelta(days=7)).month != d.month
days_all = sorted(m1["day"].unique().to_list())
events = {"Fed decision (2 p.m. New York)": at(event_dates.FOMC, 18, 0, 19), "US inflation release, CPI (8:30 a.m. New York)": at(event_dates.CPI, 12, 30, 13),
          "Funding payment (00:00, 08:00, 16:00 UTC)": [datetime(d.year, d.month, d.day, h) for d in days_all for h in (0, 8, 16)],
          "Monthly option expiry, Deribit (last Friday, 08:00 UTC)": [datetime(d.year, d.month, d.day, 8) for d in days_all if friday_last(d)],
          "Weekly option expiry, other Fridays (08:00 UTC)": [datetime(d.year, d.month, d.day, 8) for d in days_all if d.weekday() == 4 and not friday_last(d)]}
idx = m1.select("time", "rel", "relr")
ev_rows = []
for nm, ts in events.items():
    e = idx.filter(pl.col("time").is_in(ts))
    ctrl = idx.filter(pl.col("time").is_in([t - timedelta(days=7) for t in ts]))          # the same minute a week earlier
    ev_rows.append(dict(event=nm, occurrences=e.height, activity_vs_day=round(float(e["rel"].median()), 1), activity_week_before=round(float(ctrl["rel"].median()), 1),
                        move_vs_day=round(float(e["relr"].median()), 1), move_week_before=round(float(ctrl["relr"].median()), 1)))
R["events"] = ev_rows
# confirm the Fed's 2 p.m. release time from the tape: the busiest minute around each decision
fed_peaks = []
for s in event_dates.FOMC:
    d = date.fromisoformat(s); w = m1.filter((pl.col("day") == d) & pl.col("mod").is_between(16 * 60, 21 * 60))
    if w.height: fed_peaks.append((s, us_dst(d), int(w.sort("trades")["mod"][-1])))
R["fed_peak_minute"] = {"summer": sorted({f"{m // 60:02d}:{m % 60:02d}" for s, f, m in fed_peaks if f}), "winter": sorted({f"{m // 60:02d}:{m % 60:02d}" for s, f, m in fed_peaks if not f})}

# ---------------------------------------------------------------- 7.5 change over the years: the US share of the trading day
yr = wk.with_columns(pl.when(pl.col("dst")).then(pl.col("mod").is_between(13 * 60 + 30, 20 * 60, closed="left")).otherwise(pl.col("mod").is_between(14 * 60 + 30, 21 * 60, closed="left")).alias("us"),
                     pl.col("mod").is_between(0, 8 * 60, closed="left").alias("asia"))
R["us_hours_share_by_year"] = (yr.group_by(pl.col("time").dt.year().alias("year")).agg((pl.col("usd").filter(pl.col("us")).sum() / pl.col("usd").sum()).round(3).alias("us_stock_hours"),
                                (pl.col("usd").filter(pl.col("asia")).sum() / pl.col("usd").sum()).round(3).alias("00_08_utc")).sort("year").to_dicts())

# ---------------------------------------------------------------- 7.6 when each clock makes you trade
how_avg = how.with_columns(pl.col("usd").rank().alias("rk"))
deep = set(how_avg.filter(pl.col("rk") > 168 * 0.75)["h"].to_list()); thin = set(how_avg.filter(pl.col("rk") <= 168 * 0.25)["h"].to_list())
burst = m1.filter(pl.col("trades") > 20 * pl.col("trades").median().over("day")).select("time")
burst_set = set(burst["time"].to_list())
clocks = []
for k in ("time", "tick", "volume", "dollar", "range", "cusum"):
    b = (pl.concat([pl.read_parquet(f, columns=["end_ms"]) for f in sorted(bars.bars_dir(SYM, k).glob("*.parquet"))])
           .with_columns(pl.from_epoch("end_ms", time_unit="ms").alias("t")).with_columns(((pl.col("t").dt.weekday().cast(pl.Int32) - 1) * 24 + pl.col("t").dt.hour().cast(pl.Int32)).alias("h"),
                                                                                         pl.col("t").dt.minute().alias("mi"), pl.col("t").dt.truncate("1m").alias("m")))
    clocks.append(dict(clock=k, deep_hours=round(float(b["h"].is_in(sorted(deep)).mean()), 3), thin_hours=round(float(b["h"].is_in(sorted(thin)).mean()), 3),
                       round_minute=round(float(b["mi"].is_in([0, 15, 30, 45]).mean()), 3) if k != "time" else 1.0,
                       in_bursts=round(float(b["m"].is_in(sorted(burst_set)).mean()), 4)))
R["when_clocks_trade"] = clocks
R["deep_hours_share_of_time"] = round(len(deep) / 168, 2); R["share_of_dollars_in_deep_hours"] = round(float(how_avg.filter(pl.col("h").is_in(sorted(deep)))["usd"].sum() / how_avg["usd"].sum()), 2)
R["share_of_dollars_in_thin_hours"] = round(float(how_avg.filter(pl.col("h").is_in(sorted(thin)))["usd"].sum() / how_avg["usd"].sum()), 2)
R["burst_minutes_share"] = round(len(burst_set) / m1.height, 4)
(L13_RESULTS / "l13_s7.json").write_text(json.dumps(R, indent=1, default=str)); print(json.dumps(R, indent=1, default=str))
