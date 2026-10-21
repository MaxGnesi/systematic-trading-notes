"""Lecture 12: the code behind the lecture's figures, one function per script, for any symbol and period.

run_<name>(SYM, MONTHS, FIG, PREFIX) reads the derived layer of tape.py for the months in MONTHS, draws the lecture's figures into the
folder FIG under names starting with PREFIX, and returns the numbers quoted in the lecture as a dictionary. On October 2021 to
September 2026 with PREFIX="" it reproduces the lecture's figures; on another period it draws the same figures for that period.
Generated from the scripts that made the figures; the bodies are those scripts' code."""
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
import polars as pl
from plotly.subplots import make_subplots
from scipy.stats import norm

import tape
import l12_stats
from trading_models.plotting import MUTED, SERIES, apply_theme, save_figure

apply_theme()


def run_activity(SYM, MONTHS, FIG, PREFIX="nb_"):
    """Lecture 12, §5.5, figure 12_01."""
    FIG = Path(FIG); FIG.mkdir(parents=True, exist_ok=True)
    D = tape.ROOT / "interim" / "tape" / SYM
    months = [D / ym for ym in MONTHS]
    days = pl.concat([pl.read_parquet(f) for f in [m / "days.parquet" for m in months]]).sort("day")
    flags = pl.concat([pl.read_parquet(f) for f in [m / "flag_counts.parquet" for m in months]])
    patches = pl.read_parquet(D / "patches.parquet")
    patched = sorted({datetime.fromtimestamp(ms / 1000, timezone.utc).date() for ms, st in zip(patches["to_ms"], patches["status"]) if st == "filled"})
    patched_days = set()
    for h in patches.filter(pl.col("status") == "filled").iter_rows(named=True):
        patched_days.update(tape.hole_days(h["from_ms"], h["to_ms"]))
    silence = flags.filter(pl.col("rule") == "silence over 60 seconds")["day"].to_list()
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.06, subplot_titles=("Trades per day, millions", "Dollars traded per day, billions"))
    fig.add_scatter(x=days["day"], y=days["trades"] / 1e6, mode="lines", line=dict(color=SERIES[0], width=1), name="trades", showlegend=False, row=1, col=1)
    fig.add_scatter(x=days["day"], y=days["usd"] / 1e9, mode="lines", line=dict(color=SERIES[2], width=1), name="dollars", showlegend=False, row=2, col=1)
    pd_ = days.filter(pl.col("day").is_in(sorted(patched_days)))
    fig.add_scatter(x=pd_["day"], y=pd_["trades"] / 1e6, mode="markers", marker=dict(color=SERIES[1], size=8, symbol="diamond"), name="day filled from the daily files", row=1, col=1)
    sd_ = days.filter(pl.col("day").cast(pl.Utf8).is_in(silence))
    fig.add_scatter(x=sd_["day"], y=sd_["trades"] / 1e6, mode="markers", marker=dict(color=SERIES[3], size=9, symbol="x"), name="outage: no trade for over a minute", row=1, col=1)
    fig.update_layout(title=f"{SYM} perpetual, {MONTHS[0]} to {MONTHS[-1]}: activity, with the repaired days and the outages", height=560, width=1100, margin=dict(t=80),
                      legend=dict(orientation="h", y=-0.1, x=0, itemsizing="constant"))
    save_figure(fig, PREFIX + "12_01_activity", FIG)
    y = days.with_columns(pl.col("day").dt.year().alias("y")).group_by("y").agg((pl.col("trades").mean() / 1e6).alias("trades_m"), (pl.col("usd").mean() / 1e9).alias("usd_bn")).sort("y")
    return {}


def run_events(SYM, MONTHS, FIG, PREFIX="nb_"):
    """Lecture 12, §5.4, figures 12_02-12_05."""
    FIG = Path(FIG); FIG.mkdir(parents=True, exist_ok=True)
    D = tape.ROOT / "interim" / "tape" / SYM
    months = [D / ym for ym in MONTHS]
    ex = pl.concat([pl.read_parquet(f) for f in [m / "flag_examples.parquet" for m in months] if pl.read_parquet(f).height])
    days = pl.concat([pl.read_parquet(f) for f in [m / "days.parquet" for m in months]]).sort("day")
    m1 = pl.concat([pl.read_parquet(f, columns=["time", "trades", "usd"]) for f in [m / "m1.parquet" for m in months]])

    picks = {}
    r = ex.filter(pl.col("rule") == "jump that persists").sort("value", descending=True).row(0, named=True); picks["largest jump that persists"] = (r["ms"], r["id"])
    r = ex.filter(pl.col("rule") == "spike and revert").sort("value", descending=True).row(0, named=True); picks["largest spike and revert"] = (r["ms"], r["id"])
    big_day = days.sort("max_usd", descending=True).row(0, named=True)["day"]
    a = int(datetime(big_day.year, big_day.month, big_day.day, tzinfo=timezone.utc).timestamp() * 1000)
    lf = pl.scan_parquet(tape.source(SYM, f"{big_day.year}-{big_day.month:02d}"))
    big = lf.filter(pl.col("transact_time").is_between(a, a + 86_400_000, closed="left")).with_columns((pl.col("price") * pl.col("quantity")).alias("usd")).sort("usd", descending=True).head(1).collect().row(0, named=True)
    picks["largest single trade"] = (big["transact_time"], big["agg_trade_id"])
    busiest = m1.sort("trades", descending=True).row(0, named=True); picks["busiest minute"] = (int(busiest["time"].replace(tzinfo=timezone.utc).timestamp() * 1000) + 30_000, None)


    BIG = 250_000                                                                             # trades at least this large get a bubble


    def bubble(usd):                                                                          # diameter grows with the log of the dollar value: $250k 6 px, x10 adds 7 px
        return np.clip(6 + 7 * np.log10(np.maximum(usd, BIG) / BIG), 6, 30)


    def window(ms, before, after):
        ym = datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%Y-%m")
        w = pl.scan_parquet(tape.source(SYM, ym)).filter(pl.col("transact_time").is_between(ms - before, ms + after)).collect()
        return w.with_columns(pl.from_epoch("transact_time", time_unit="ms").alias("time"), (pl.col("price") * pl.col("quantity")).alias("usd"),
                              pl.when(pl.col("is_buyer_maker")).then(-1).otherwise(1).alias("sign"))


    results = {}
    for k, (name, (ms, tid)) in enumerate(picks.items()):
        w = window(ms, 120_000, 120_000)
        ids_ = w["agg_trade_id"].to_numpy()
        i = int(np.where(ids_ == tid)[0][0]) if tid is not None else int(np.argmin(np.abs(w["transact_time"].to_numpy() - ms)))
        px = w["price"].to_numpy(); ts = w["transact_time"].to_numpy()
        pre = float(np.median(px[max(i - 50, 0):i])) if i > 0 else px[0]
        jump = px[i] - pre
        after10 = float(np.median(px[i + 1:i + 11])) if i + 1 < len(px) else px[i]
        j60 = np.searchsorted(ts, ts[i] + 60_000); after60 = float(px[min(j60, len(px) - 1)])
        keep = lambda x: float((x - pre) / jump) if jump else float("nan")                  # share of the jump still there
        tick = tape.tick(SYM, datetime.fromtimestamp(ms / 1000, timezone.utc))
        lo, hi = sorted([pre, px[i]])
        levels = np.round(np.arange(lo, hi + tick / 2, tick), 2); traded = np.unique(np.round(px[max(i - 50, 0):i + 1], 2))
        path_share = float(np.isin(levels, traded).mean()) if len(levels) > 1 else 1.0
        max_step_bp = float(np.max(np.abs(np.diff(px[max(i - 50, 0):i + 1])) / px[i]) * 1e4) if i > 0 else 0.0
        near = (np.abs(ts - ts[i]) <= 10_000)
        day0 = int(ts[i] // 86_400_000 * 86_400_000)
        day_row = days.filter(pl.col("day") == datetime.fromtimestamp(day0 / 1000, timezone.utc).date()).row(0, named=True)
        typical_20s_trades = day_row["trades"] / (86_400 / 20); typical_20s_usd = day_row["usd"] / (86_400 / 20)
        sgn = np.sign(jump) if jump else 1.0
        flow = w.filter(pl.col("transact_time").is_between(ts[i] - 10_000, ts[i]))
        flow_share = float(flow.filter(pl.col("sign") == sgn)["usd"].sum() / flow["usd"].sum()) if flow.height else float("nan")
        res = dict(when=datetime.fromtimestamp(ts[i] / 1000, timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] + " UTC", price=float(px[i]), size_usd=float(w["usd"][i]),
                   jump_bp=float(jump / pre * 1e4), kept_after_10_trades=keep(after10), kept_after_60s=keep(after60),
                   levels_between=len(levels), share_levels_traded=path_share, largest_step_bp=max_step_bp,
                   trades_in_20s=int(near.sum()), trades_vs_typical=float(near.sum() / typical_20s_trades), usd_in_20s=float(w.filter(pl.Series(near))["usd"].sum()),
                   usd_vs_typical=float(w.filter(pl.Series(near))["usd"].sum() / typical_20s_usd), flow_share_with_move=flow_share)
        results[name] = res
        # chart: every trade in the window, coloured by aggressor; the event marked
        z = w.filter(pl.col("transact_time").is_between(ms - (20_000 if "spike" in name else 120_000), ms + (20_000 if "spike" in name else 120_000)))
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.72, 0.28], vertical_spacing=0.05)
        for s_, col, nm in ((1, SERIES[0], "buyer-initiated"), (-1, SERIES[3], "seller-initiated")):
            q = z.filter(pl.col("sign") == s_)                                                 # every trade: a small dot
            fig.add_scattergl(x=q["time"], y=q["price"], mode="markers", name=f"{nm} trade", marker=dict(size=3, color=col, opacity=0.45, line=dict(width=0)), row=1, col=1)
            b = q.filter(pl.col("usd") >= BIG)                                                 # large trades: a bubble that grows with the dollar value
            fig.add_scattergl(x=b["time"], y=b["price"], mode="markers", showlegend=False, marker=dict(size=bubble(b["usd"].to_numpy()), color=col, opacity=0.7,
                              line=dict(width=1, color="white")), row=1, col=1)
        for v, lab in ((BIG, "$250k"), (2.5e6, "$2.5m"), (2.5e7, "$25m")):                     # size key: points outside the plot, only for the legend
            fig.add_scattergl(x=[None], y=[None], mode="markers", name=f"trade of {lab}", marker=dict(size=bubble(np.array([v]))[0], color=MUTED, opacity=0.7), row=1, col=1)
        fig.add_scattergl(x=[w["time"][i]], y=[px[i]], mode="markers", name="the event (ringed)", marker=dict(size=34, color="black", symbol="circle-open", line=dict(width=2.5)), row=1, col=1)
        cum = z.select("time", ((pl.col("usd") * pl.col("sign")).cum_sum() / 1e6).alias("cum"))
        fig.add_scattergl(x=cum["time"], y=cum["cum"], mode="lines", line=dict(color=SERIES[2], width=2), showlegend=False, row=2, col=1)
        fig.update_yaxes(title_text="price, USDT", row=1, col=1); fig.update_yaxes(title_text="net buying, $m", row=2, col=1)
        fig.update_layout(title=f"{name.capitalize()}: {res['when']}<br><sup>Each dot is one trade, coloured by the aggressor's side; trades of $250k or more are bubbles that grow with their dollar value (see the key). Below: cumulative net aggressive buying</sup>", height=560, width=1100, margin=dict(t=70), legend=dict(orientation="h", y=-0.12, x=0, itemsizing="constant"))
        save_figure(fig, PREFIX + f"12_0{k + 2}_event_{name.replace(' ', '_')}", FIG)
    return results


def run_activity_stats(SYM, MONTHS, FIG, PREFIX="nb_"):
    """Lecture 12, §6.1-§6.5 and §7.2, figures 12_06-12_10."""
    FIG = Path(FIG); FIG.mkdir(parents=True, exist_ok=True)
    D = tape.ROOT / "interim" / "tape" / SYM
    months = [D / ym for ym in MONTHS]
    R = {}

    # ---------------------------------------------------------------- 6.1 trade sizes
    sz = pl.concat([pl.read_parquet(m / "sizes.parquet") for m in months]).group_by("size_bin").agg(pl.col("n").sum(), pl.col("usd").sum()).sort("size_bin")
    lo = 10 ** (sz["size_bin"].to_numpy() * 0.05); n = sz["n"].to_numpy().astype(float); usd = sz["usd"].to_numpy()
    mid = lo * 10 ** 0.025
    surv = 1 - np.concatenate([[0], np.cumsum(n)[:-1]]) / n.sum()             # share of trades at or above each bin's lower edge
    tail = (lo >= 1e5) & (surv > 1e-7)
    alpha = -np.polyfit(np.log10(lo[tail]), np.log10(surv[tail]), 1)[0]
    def top_share(p):                                                         # share of dollars in the largest p of trades, interpolated inside the bin
        k, need, got = len(n) - 1, p * n.sum(), 0.0
        while need > 0:
            take = min(n[k], need); got += usd[k] * take / n[k]; need -= take; k -= 1
        return got / usd.sum()
    R["sizes"] = dict(trades=int(n.sum()), tail_exponent=float(alpha), top1=top_share(0.01), top10=top_share(0.10),
                      share_trades_under_1000=float(n[lo < 1000].sum() / n.sum()), share_usd_over_1m=float(usd[lo >= 1e6].sum() / usd.sum()))
    fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.1, subplot_titles=("Share of trades and of dollars, by trade size", "Share of trades at least this large (log-log)"))
    fig.add_scatter(x=mid, y=n / n.sum() * 100, mode="lines", line=dict(color=SERIES[0], width=2), name="share of trades", row=1, col=1)
    fig.add_scatter(x=mid, y=usd / usd.sum() * 100, mode="lines", line=dict(color=SERIES[1], width=2), name="share of dollars", row=1, col=1)
    fig.add_scatter(x=lo, y=surv, mode="lines", line=dict(color=SERIES[0], width=2), name="share of trades at least this large", showlegend=False, row=1, col=2)
    xf = lo[tail]; fig.add_scatter(x=xf, y=10 ** np.polyval(np.polyfit(np.log10(xf), np.log10(surv[tail]), 1), np.log10(xf)), mode="lines",
                                   line=dict(color=SERIES[3], width=2, dash="dash"), name=f"straight line above $100k: slope -{alpha:.2f}", row=1, col=2)
    fig.update_xaxes(type="log", title_text="trade size, dollars"); fig.update_yaxes(title_text="percent", row=1, col=1); fig.update_yaxes(type="log", exponentformat="power", row=1, col=2)
    fig.update_layout(title=f"{SYM} perpetual, {n.sum() / 1e9:.2f} billion trades: most trades are small, most dollars are in large trades", height=470, width=1100,
                      legend=dict(orientation="h", y=-0.2, x=0, itemsizing="constant"))
    save_figure(fig, PREFIX + "12_06_trade_sizes", FIG)

    # ---------------------------------------------------------------- 6.2 who is aggressive
    days = pl.concat([pl.read_parquet(m / "days.parquet") for m in months]).sort("day").with_columns((pl.col("buy_usd") / pl.col("usd")).alias("buy_share"))
    m1 = pl.concat([pl.read_parquet(m / "m1.parquet", columns=["time", "close", "usd", "signed_usd", "trades"]) for m in months]).sort("time")
    dclose = m1.group_by(pl.col("time").dt.date().alias("day")).agg(pl.col("close").last()).sort("day")
    days = days.join(dclose, on="day").with_columns(pl.col("close").log().diff().alias("ret"))
    dd = days.drop_nulls("ret")
    m1 = m1.with_columns(pl.col("close").log().diff().alias("ret"), (pl.col("signed_usd") / pl.col("usd")).alias("imb"))
    mm = m1.drop_nulls("ret").filter(pl.col("usd") > 0)
    c_day = float(np.corrcoef(dd["buy_share"], dd["ret"])[0, 1]); c_min = float(np.corrcoef(mm["imb"], mm["ret"])[0, 1])
    R["aggressor"] = dict(buy_share_mean=float(days["buy_share"].mean()), buy_share_p05=float(days["buy_share"].quantile(0.05)),
                          buy_share_p95=float(days["buy_share"].quantile(0.95)), corr_day=c_day, r2_day=c_day ** 2, corr_min=c_min, r2_min=c_min ** 2,
                          same_sign_min=float((np.sign(mm["imb"]) == np.sign(mm["ret"])).filter(mm["ret"] != 0).mean()))
    fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.1, subplot_titles=("Share of dollars bought aggressively, per day", "Day's return against the day's aggressive buying"))
    fig.add_histogram(x=days["buy_share"] * 100, nbinsx=60, marker_color=SERIES[0], showlegend=False, row=1, col=1)
    fig.add_scattergl(x=dd["buy_share"] * 100, y=dd["ret"] * 100, mode="markers", marker=dict(size=4, color=SERIES[0], opacity=0.5), showlegend=False, row=1, col=2)
    fig.update_xaxes(title_text="aggressive buying, percent of the day's dollars", row=1, col=1); fig.update_xaxes(title_text="aggressive buying, percent of the day's dollars", row=1, col=2)
    fig.update_yaxes(title_text="days", row=1, col=1); fig.update_yaxes(title_text="day's return, percent", row=1, col=2)
    fig.update_layout(title=f"Aggressive buying is close to half, and its tilt moves with the price (correlation {c_day:.2f} per day)", height=450, width=1100)
    save_figure(fig, PREFIX + "12_07_aggressor", FIG)

    # ---------------------------------------------------------------- 6.3 time of day, and the funding times
    m1 = m1.with_columns((pl.col("time").dt.hour().cast(pl.Int32) * 60 + pl.col("time").dt.minute().cast(pl.Int32)).alias("mod"), pl.col("time").dt.date().alias("day"),
                         (pl.col("time").dt.weekday() >= 6).alias("weekend"))
    m1 = m1.join(m1.group_by("day").agg(pl.col("usd").mean().alias("day_mean")), on="day").with_columns((pl.col("usd") / pl.col("day_mean")).alias("rel"))
    prof = m1.group_by("mod", "weekend").agg(pl.col("rel").median().alias("rel")).sort("mod")
    hrs = m1.group_by(pl.col("mod") // 60, "weekend").agg(pl.col("usd").sum()).sort("mod")
    wd = hrs.filter(~pl.col("weekend")); share = wd["usd"].to_numpy() / wd["usd"].sum()
    R["time_of_day"] = dict(busiest_hour_utc=int(wd["mod"][int(np.argmax(share))]), busiest_hour_share=float(share.max()), quietest_hour_utc=int(wd["mod"][int(np.argmin(share))]),
                            quietest_hour_share=float(share.min()), weekend_vs_weekday=float(days.filter(pl.col("day").dt.weekday() >= 6)["usd"].mean() / days.filter(pl.col("day").dt.weekday() < 6)["usd"].mean()))
    top = prof.filter(~pl.col("weekend")).sort("rel", descending=True).head(8)
    R["time_of_day"]["top_minutes_weekday"] = [(f"{m // 60:02d}:{m % 60:02d}", round(float(r), 2)) for m, r in zip(top["mod"], top["rel"])]
    fig = go.Figure()
    for wk, col, nm in ((False, SERIES[0], "Monday to Friday"), (True, SERIES[1], "Saturday and Sunday")):
        q = prof.filter(pl.col("weekend") == wk)
        fig.add_scatter(x=q["mod"] / 60, y=q["rel"], mode="lines", line=dict(color=col, width=1.2), name=nm)
    for h in (0, 8, 16):
        fig.add_vline(x=h, line=dict(color=MUTED, dash="dot", width=1))
    fig.add_annotation(x=8, y=1, yref="paper", text="funding times: 00, 08, 16 UTC", showarrow=False, xanchor="left", yanchor="bottom", font=dict(color=MUTED))
    fig.update_xaxes(title_text="time of day, UTC (hours)", dtick=2); fig.update_yaxes(title_text="dollars per minute ÷ day's average")
    fig.update_layout(title=f"When {SYM} trades: the rhythm of a day, minute by minute", height=460, width=1100, legend=dict(orientation="h", y=-0.18, x=0))
    save_figure(fig, PREFIX + "12_08_time_of_day", FIG)

    # funding: activity and order flow in the ten minutes before and after each payment
    fr = l12_stats.funding(SYM, MONTHS).select(pl.col("ft").cast(pl.Datetime("ms")), pl.col("rate").alias("fundingRate"))
    w = m1.select("time", "usd", "signed_usd", "rel").sort("time")
    rows = []
    for ft, rate in fr.iter_rows():
        a = w.filter(pl.col("time").is_between(ft - pl.duration(minutes=10), ft, closed="left")); b = w.filter(pl.col("time").is_between(ft, ft + pl.duration(minutes=10), closed="left"))
        if a.height == 10 and b.height == 10:
            rows.append(dict(rate=rate, rel_before=a["rel"].mean(), rel_after=b["rel"].mean(), imb_before=a["signed_usd"].sum() / a["usd"].sum(), imb_after=b["signed_usd"].sum() / b["usd"].sum()))
    F = pl.DataFrame(rows).with_columns(pl.when(pl.col("rate") > 0.0001).then(pl.lit("above 0.01%")).when(pl.col("rate") >= 0.0001).then(pl.lit("exactly 0.01%"))
                                         .when(pl.col("rate") > 0).then(pl.lit("positive, below 0.01%")).otherwise(pl.lit("zero or negative")).alias("group"))
    # control: the same windows around the hours halfway between funding times (04:00, 12:00, 20:00 UTC)
    w2 = w.with_columns((pl.col("time").dt.hour().cast(pl.Int32) * 60 + pl.col("time").dt.minute().cast(pl.Int32)).alias("mod"))
    def around(centres):
        a = w2.filter(pl.col("mod").is_in([(c * 60 - k) % 1440 for c in centres for k in range(1, 11)]))
        b = w2.filter(pl.col("mod").is_in([(c * 60 + k) % 1440 for c in centres for k in range(0, 10)]))
        return float(a["rel"].mean()), float(b["rel"].mean())
    fb, fa = around((0, 8, 16)); cb, ca = around((4, 12, 20))
    grp = F.group_by("group").agg(pl.len().alias("n"), pl.col("imb_before").mean(), pl.col("imb_after").mean(), (pl.col("imb_before").std() / pl.len().sqrt()).alias("se_before"), (pl.col("imb_after").std() / pl.len().sqrt()).alias("se_after"), pl.col("rel_before").mean(), pl.col("rel_after").mean()).sort("group")
    R["funding"] = dict(windows=F.height, activity_before=fb, activity_after=fa, control_before=cb, control_after=ca,
                        by_rate=[{k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()} for r in grp.iter_rows(named=True)],
                        imb_before_all=float(F["imb_before"].mean()), imb_after_all=float(F["imb_after"].mean()))

    # ---------------------------------------------------------------- 6.4 time between trades
    seq = [json.loads((m / "sequence.json").read_text()) for m in months]
    dh = sum(np.load(m / "dur_hist.npy") for m in months)
    trades_m = np.array([pl.read_parquet(m / "days.parquet")["trades"].sum() for m in months], float); wgt = trades_m / trades_m.sum()
    mean_ms = float(sum(s["dur_mean_ms"] * w_ for s, w_ in zip(seq, wgt)))
    R["durations"] = dict(mean_ms=mean_ms, cv_median=float(np.median([s["dur_cv"] for s in seq])), ac1_median=float(np.median([s["dur_ac1"] for s in seq])),
                          share_zero=float(sum(s["dur_share_zero_ms"] * w_ for s, w_ in zip(seq, wgt))))
    edges = 10 ** tape.DUR_BINS; emp = dh / dh.sum()
    expo = np.exp(-np.r_[0, edges[1:-1]] / mean_ms) - np.exp(-edges[1:] / mean_ms)          # a steady random (Poisson) flow with the same mean
    x = 10 ** (tape.DUR_BINS[:-1] + 0.05); keep = tape.DUR_BINS[:-1] >= 0.1                   # the first bin (0 or 1 ms) is reported in the title
    fig = go.Figure()
    fig.add_scatter(x=x[keep], y=np.where(emp[keep] > 0, emp[keep] * 100, np.nan), mode="lines+markers", line=dict(color=SERIES[0], width=2), marker=dict(size=4), name="the tape")
    fig.add_scatter(x=x[keep], y=expo[keep] / expo.sum() * 100, mode="lines", line=dict(color=SERIES[1], width=2, dash="dash"), name=f"trades arriving at random, same average wait ({mean_ms:.0f} ms)")
    fig.update_xaxes(type="log", range=[0.25, 5], title_text="time to the next trade, milliseconds"); fig.update_yaxes(type="log", range=[-5, 1.3], title_text="percent of waits, per bin", exponentformat="power")
    fig.update_layout(title=f"Trades come in bursts: {emp[0]:.0%} of waits are 0 or 1 ms (not shown), and long silences are far more common than random arrival gives",
                      height=450, width=1100, legend=dict(orientation="h", y=-0.2, x=0))
    save_figure(fig, PREFIX + "12_09_durations", FIG)

    # ---------------------------------------------------------------- 6.5 bid-ask bounce and the signature plot
    rv = pl.concat([pl.read_parquet(m / "rv_days.parquet") for m in months])
    # the sequence stage includes the return across midnight in each day's sum (yesterday's last price is carried over)
    sig = {s: float(np.sqrt(rv[f"rv_{s}"].mean() * 365)) for s in tape.SIG_DT}
    sigm = {s: float(np.sqrt(rv[f"rvm_{s}"].mean() * 365)) for s in tape.SIG_DT}   # from the mid estimated with the aggressor flag
    R["bounce"] = dict(ac1_trade_median=float(np.median([s["ac1_trade_returns"] for s in seq])), ac1_1s_median=float(np.median([s["ac1_1s_returns"] for s in seq])),
                       vol_by_interval={str(k): round(v, 4) for k, v in sig.items()}, vol_by_interval_mid={str(k): round(v, 4) for k, v in sigm.items()},
                       spread_p50_bp=float(rv["spread_p50_bp"].median()), spread_p99_bp_median_day=float(rv["spread_p99_bp"].median()), spread_p99_bp_max_day=float(rv["spread_p99_bp"].max()),
                       spread_one_tick=float(rv["spread_one_tick"].mean()), vol_daily_close=float(dd["ret"].std() * np.sqrt(365)))
    fig = go.Figure()
    fig.add_scatter(x=list(sig), y=[v * 100 for v in sig.values()], mode="lines+markers", line=dict(color=SERIES[0], width=2), name="from trade prices")
    fig.add_scatter(x=list(sigm), y=[v * 100 for v in sigm.values()], mode="lines+markers", line=dict(color=SERIES[2], width=2, dash="dot"), name="from the mid, estimated from the last buy and the last sell of each second")
    fig.add_hline(y=R["bounce"]["vol_daily_close"] * 100, line=dict(color=SERIES[1], dash="dash"), annotation_text="from daily closes", annotation_position="top left")
    fig.update_xaxes(type="log", title_text="sampling interval", tickvals=tape.SIG_DT, ticktext=["1s", "2s", "5s", "10s", "30s", "1m", "2m", "5m", "10m", "15m", "30m", "1h"])
    fig.update_yaxes(title_text="annualised volatility, percent")
    fig.update_layout(title="The signature plot: measured volatility depends on how often the price is sampled", height=450, width=1100, legend=dict(orientation="h", y=-0.2, x=0))
    save_figure(fig, PREFIX + "12_10_signature", FIG)
    return R


def run_funding(SYM, MONTHS, FIG, PREFIX="nb_"):
    """Lecture 12, §6.2, figure 12_17."""
    FIG = Path(FIG); FIG.mkdir(parents=True, exist_ok=True)
    D = tape.ROOT / "interim" / "tape" / SYM
    months = [D / ym for ym in MONTHS]
    m1 = (pl.concat([pl.read_parquet(m / "m1.parquet", columns=["time", "close", "usd", "signed_usd"]) for m in months])
            .sort("time").with_columns(pl.col("time").cast(pl.Datetime("ms")), pl.col("close").log().diff().alias("r"), pl.col("time").dt.date().alias("day")))
    m1 = m1.join(m1.group_by("day").agg(pl.col("usd").mean().alias("d_usd"), pl.col("r").abs().mean().alias("d_absr")), on="day")
    m1 = m1.with_columns((pl.col("usd") / pl.col("d_usd")).alias("act"), (pl.col("r").abs() / pl.col("d_absr")).alias("vol")).select("time", "r", "act", "vol", "signed_usd", "usd")
    fr = l12_stats.funding(SYM, MONTHS).select(pl.col("ft").cast(pl.Datetime("ms")), pl.col("rate").alias("fundingRate"))
    grp = (pl.when(pl.col("fundingRate") > 0.0001).then(pl.lit("above 0.01%")).when(pl.col("fundingRate") >= 0.0001).then(pl.lit("exactly 0.01%"))
             .when(pl.col("fundingRate") > 0).then(pl.lit("positive, below 0.01%")).otherwise(pl.lit("zero or negative")))
    ev = pl.concat([fr.with_columns(grp.alias("group")).select("ft", "group"),
                    fr.select((pl.col("ft") + pl.duration(hours=4)).alias("ft")).with_columns(pl.lit("control: 4 hours later").alias("group"))])
    K = pl.DataFrame({"k": np.arange(-60, 60, dtype=np.int32)})
    E = ev.with_row_index("ev").join(K, how="cross").with_columns((pl.col("ft") + pl.duration(minutes=pl.col("k"))).alias("time")).join(m1, on="time", how="inner")
    prof = E.group_by("group", "k").agg(pl.col("act").mean(), pl.col("vol").mean(), pl.col("r").mean().alias("r_mean")).sort("group", "k")
    # cumulative return over windows, per event: mean and standard error across events
    def window(a, b, name):
        w = E.filter(pl.col("k").is_between(a, b - 1)).group_by("group", "ev").agg(pl.col("r").sum().alias("cr"), pl.len().alias("n")).filter(pl.col("n") == b - a)
        return w.group_by("group").agg((pl.col("cr").mean() * 1e4).alias(f"{name}_bp"), (pl.col("cr").std() / pl.len().sqrt() * 1e4).alias(f"{name}_se"), pl.len().alias("events"))
    T = window(-30, 0, "before30").join(window(0, 30, "after30").drop("events"), on="group").join(window(-5, 0, "before5").drop("events"), on="group").join(window(0, 5, "after5").drop("events"), on="group")
    A = E.group_by("group").agg(pl.col("act").filter(pl.col("k").is_between(-10, -1)).mean().alias("act_before10"), pl.col("act").filter(pl.col("k").is_between(0, 9)).mean().alias("act_after10"),
                                pl.col("vol").filter(pl.col("k").is_between(-10, -1)).mean().alias("vol_before10"), pl.col("vol").filter(pl.col("k").is_between(0, 9)).mean().alias("vol_after10"),
                                pl.col("vol").filter(pl.col("k") == 0).mean().alias("vol_minute0"), pl.col("act").filter(pl.col("k") == 0).mean().alias("act_minute0"))
    R = {r["group"]: {k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items() if k != "group"} for r in T.join(A, on="group").sort("group").iter_rows(named=True)}

    fig = make_subplots(rows=1, cols=3, horizontal_spacing=0.07, subplot_titles=("Dollars traded per minute ÷ day's average", "Size of the move per minute ÷ day's average", "Average cumulative return, basis points"))
    show = [("above 0.01%", SERIES[3]), ("zero or negative", SERIES[0]), ("exactly 0.01%", SERIES[2]), ("control: 4 hours later", MUTED)]
    for g, col in show:
        q = prof.filter(pl.col("group") == g)
        if not q.height: continue
        for c_, y in ((1, q["act"]), (2, q["vol"])):
            fig.add_scatter(x=q["k"], y=y, mode="lines", line=dict(color=col, width=1.6), name=g, legendgroup=g, showlegend=c_ == 1, row=1, col=c_)
        cr = np.cumsum(q["r_mean"].to_numpy()) * 1e4; cr = cr - cr[q["k"].to_numpy() == -1][0]          # zero just before the funding time
        fig.add_scatter(x=q["k"], y=cr, mode="lines", line=dict(color=col, width=1.6), name=g, legendgroup=g, showlegend=False, row=1, col=3)
    for c_ in (1, 2, 3):
        fig.add_vline(x=0, line=dict(color=MUTED, dash="dot"), row=1, col=c_); fig.update_xaxes(title_text="minutes from the funding time", row=1, col=c_)
    fig.update_layout(title="Around the funding times: activity and volatility jump at the hour; the price moves by a few basis points at most", height=470, width=1100,
                      legend=dict(orientation="h", y=-0.22, x=0, title_text="funding rate at the payment:"))
    save_figure(fig, PREFIX + "12_17_funding_event", FIG)
    return R


def run_persistence(SYM, MONTHS, FIG, PREFIX="nb_"):
    """Lecture 12, §7.1, figure 12_11."""
    FIG = Path(FIG); FIG.mkdir(parents=True, exist_ok=True)
    D = tape.ROOT / "interim" / "tape" / SYM
    months = [D / ym for ym in MONTHS]
    rows = []
    for m in months:
        j = json.loads((m / "sequence.json").read_text()); d = pl.read_parquet(m / "days.parquet"); rv = pl.read_parquet(m / "rv_days.parquet")
        rows.append(dict(month=m.name, trades=float(d["trades"].sum()), usd_day=float(d["usd"].mean()), vol=float(np.sqrt(rv["rv_300"].mean() * 365)),
                         **{f"tr_{k}": v for k, v in j["sign_acf_trade"].items()}, **{f"or_{k}": v for k, v in j["sign_acf_order"].items()},
                         **{f"fl_{k}": v for k, v in j["flow_acf_1s"].items()}, ret1s=j["ac1_1s_returns"]))
    M = pl.DataFrame(rows).with_columns(pl.col("month").str.to_date("%Y-%m"))
    w = (M["trades"] / M["trades"].sum()).to_numpy()
    L = tape.SIGN_LAGS
    acf_tr = np.array([float((M[f"tr_{l}"] * w).sum()) for l in L]); acf_or = np.array([float((M[f"or_{l}"] * w).sum()) for l in L])
    fit = np.array(L) >= 20                                          # the aggregation distorts short lags; fit the decay from 20 trades on
    gam_tr = -np.polyfit(np.log(np.array(L)[fit]), np.log(acf_tr[fit]), 1)[0]; gam_or = -np.polyfit(np.log(np.array(L)[fit]), np.log(acf_or[fit]), 1)[0]
    FL = [1, 2, 5, 10, 30, 60]; acf_fl = np.array([float((M[f"fl_{l}"] * w).sum()) for l in FL])
    # month by month: does persistence move with volatility and activity?
    def c(a, b): return float(np.corrcoef(M[a], M[b])[0, 1])
    yr = M.group_by(pl.col("month").dt.year().alias("year")).agg(pl.col("tr_100").mean(), pl.col("fl_1").mean(), pl.col("vol").mean(), pl.col("usd_day").mean()).sort("year")
    R = dict(sign_acf_trade=dict(zip(map(str, L), acf_tr.round(4))), sign_acf_order=dict(zip(map(str, L), acf_or.round(4))), decay_exponent_trade=float(gam_tr),
             decay_exponent_order=float(gam_or), flow_acf_1s=dict(zip(map(str, FL), acf_fl.round(4))), ret_acf_1s=float((M["ret1s"] * w).sum()),
             corr_months=dict(tr100_vol=c("tr_100", "vol"), fl1_vol=c("fl_1", "vol"), tr100_usd=c("tr_100", "usd_day"), fl1_usd=c("fl_1", "usd_day"), vol_usd=c("vol", "usd_day")),
             by_year=[{k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()} for r in yr.iter_rows(named=True)],
             tr100_first12=float(M["tr_100"][:12].mean()), tr100_last12=float(M["tr_100"][-12:].mean()), fl1_first12=float(M["fl_1"][:12].mean()), fl1_last12=float(M["fl_1"][-12:].mean()))

    fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.09, specs=[[{}, {"secondary_y": True}]],
                        subplot_titles=("Correlation of trade signs with the sign k trades later (log-log)", "Month by month: persistence and volatility"))
    show = np.array(L) >= 5                                         # lags below 5 are distorted by the aggregation (alternation built into the rows)
    fig.add_scatter(x=np.array(L)[show], y=acf_tr[show], mode="lines+markers", line=dict(color=SERIES[0], width=2), name="per trade", row=1, col=1)
    fig.add_scatter(x=np.array(L)[show], y=acf_or[show], mode="lines+markers", line=dict(color=SERIES[2], width=2), name=f"per order (same millisecond and side merged), slope -{gam_or:.2f}", row=1, col=1)
    xf = np.array(L)[fit]; fig.add_scatter(x=xf, y=np.exp(np.polyval(np.polyfit(np.log(xf), np.log(acf_tr[fit]), 1), np.log(xf))), mode="lines",
                                           line=dict(color=SERIES[3], dash="dash"), name=f"power law, slope -{gam_tr:.2f}", row=1, col=1)
    fig.add_scatter(x=M["month"], y=M["tr_100"], mode="lines", line=dict(color=SERIES[0], width=2), name="sign correlation at 100 trades (left axis)", row=1, col=2)
    fig.add_scatter(x=M["month"], y=M["fl_1"], mode="lines", line=dict(color=SERIES[1], width=2), name="net dollar flow, correlation with the next second (left axis)", row=1, col=2)
    fig.add_scatter(x=M["month"], y=M["vol"] * 100, mode="lines", line=dict(color=MUTED, width=1.5), name="realised volatility, percent a year (right axis)", row=1, col=2, secondary_y=True)
    fig.update_xaxes(type="log", title_text="lag k, trades", row=1, col=1); fig.update_yaxes(type="log", title_text="correlation", row=1, col=1)
    fig.update_yaxes(title_text="correlation", row=1, col=2); fig.update_yaxes(title_text="volatility, %", row=1, col=2, secondary_y=True, showgrid=False)
    fig.update_layout(title="Order flow is persistent: buys follow buys, over hundreds of trades", height=500, width=1100, legend=dict(orientation="h", y=-0.22, x=0))
    save_figure(fig, PREFIX + "12_11_flow_persistence", FIG)
    return R


def run_large_moves(SYM, MONTHS, FIG, PREFIX="nb_"):
    """Lecture 12, §7.3, figure 12_12."""
    FIG = Path(FIG); FIG.mkdir(parents=True, exist_ok=True)
    D = tape.ROOT / "interim" / "tape" / SYM
    months = [D / ym for ym in MONTHS]
    m1 = (pl.concat([pl.read_parquet(m / "m1.parquet", columns=["time", "close", "usd", "trades"]) for m in months]).sort("time")
          .with_columns(pl.col("close").log().diff().alias("r"), pl.col("time").dt.date().alias("day"))
          .drop_nulls("r"))
    m1 = m1.join(m1.group_by("day").agg(pl.col("trades").median().alias("day_med_trades"), pl.col("usd").median().alias("day_med_usd")), on="day")
    m1 = m1.with_columns((pl.col("r") ** 2).alias("r2"), (pl.col("trades") / pl.col("day_med_trades")).alias("rel_trades"), (pl.col("usd") / pl.col("day_med_usd")).alias("rel_usd"))
    R = {}

    # ---------------------------------------------------------------- 1. activity or size? hourly variance on trade count, average size, dollar volume
    h = (m1.group_by(pl.col("time").dt.truncate("1h").alias("hour")).agg(pl.col("r2").sum().alias("rv"), pl.col("trades").sum(), pl.col("usd").sum(), pl.len().alias("minutes"))
           .filter((pl.col("minutes") >= 50) & (pl.col("rv") > 0)).with_columns((pl.col("usd") / pl.col("trades")).alias("size")))
    y = np.log(h["rv"].to_numpy())
    X = {"trades": np.log(h["trades"].to_numpy()), "size": np.log(h["size"].to_numpy()), "usd": np.log(h["usd"].to_numpy())}
    def ols(cols):
        A = np.column_stack([np.ones(len(y))] + [X[c] for c in cols]); b, *_ = np.linalg.lstsq(A, y, rcond=None); e = y - A @ b
        return dict(coef={c: float(v) for c, v in zip(cols, b[1:])}, r2=float(1 - e.var() / y.var()))
    R["hourly"] = dict(hours=h.height, trades=ols(["trades"]), size=ols(["size"]), usd=ols(["usd"]), trades_and_size=ols(["trades", "size"]))

    # ---------------------------------------------------------------- 2. the trading behind the largest one-minute moves
    m1 = m1.with_columns(pl.col("r").abs().alias("absr"))
    cut1, cut01 = m1["absr"].quantile(0.99), m1["absr"].quantile(0.999)
    def profile(q):
        return dict(minutes=q.height, median_rel_trades=float(q["rel_trades"].median()), median_rel_usd=float(q["rel_usd"].median()),
                    share_below_day_median_trades=float((q["rel_trades"] < 1).mean()), share_below_3x=float((q["rel_trades"] < 3).mean()))
    R["large_moves"] = dict(cut_top1_bp=float(cut1 * 1e4), cut_top01_bp=float(cut01 * 1e4), all=profile(m1), top1=profile(m1.filter(pl.col("absr") >= cut1)),
                            top01=profile(m1.filter(pl.col("absr") >= cut01)))

    # ---------------------------------------------------------------- 3. how much of the variance sits in a few minutes
    tot = m1["r2"].sum(); srt = np.sort(m1["r2"].to_numpy())[::-1]; n = len(srt)
    burst = m1.filter(pl.col("rel_trades") > 20)
    R["concentration"] = dict(minutes=n, share_var_top1pct_moves=float(srt[: n // 100].sum() / tot), share_var_top01pct_moves=float(srt[: n // 1000].sum() / tot),
                              burst_minutes=burst.height, share_var_bursts=float(burst["r2"].sum() / tot),
                              share_var_busiest1pct=float(m1.sort("rel_trades", descending=True).head(n // 100)["r2"].sum() / tot))

    # chart: one-minute moves against activity in that minute
    smp = m1.sample(n=min(200_000, m1.height), seed=1)
    top = m1.filter(pl.col("absr") >= cut01)
    fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.1, subplot_titles=("Volatility of each hour against its number of trades (log-log)", "Size of each one-minute move against trading in that minute"))
    hs = h.sample(n=min(20_000, h.height), seed=1)
    fig.add_scattergl(x=hs["trades"], y=np.sqrt(hs["rv"].to_numpy()) * 1e4, mode="markers", marker=dict(size=3, color=SERIES[0], opacity=0.3), name="one hour", row=1, col=1)
    fig.add_scattergl(x=smp["rel_trades"], y=smp["absr"] * 1e4, mode="markers", marker=dict(size=2, color=MUTED, opacity=0.25), name="one minute (a sample)", row=1, col=2)
    fig.add_scattergl(x=top["rel_trades"], y=top["absr"] * 1e4, mode="markers", marker=dict(size=5, color=SERIES[3], opacity=0.8), name="the largest 0.1% of moves", row=1, col=2)
    fig.add_vline(x=1, line=dict(color=MUTED, dash="dot"), row=1, col=2)
    fig.update_xaxes(type="log", title_text="trades in the hour", row=1, col=1); fig.update_yaxes(type="log", title_text="volatility of the hour, basis points", row=1, col=1)
    fig.update_xaxes(type="log", title_text="trades in the minute ÷ the day's median minute", row=1, col=2); fig.update_yaxes(type="log", title_text="|one-minute return|, basis points", row=1, col=2)
    fig.update_layout(title="Large moves come with heavy trading: variance follows the number of trades", height=480, width=1100, legend=dict(orientation="h", y=-0.2, x=0, itemsizing="constant"))
    save_figure(fig, PREFIX + "12_12_large_moves", FIG)
    return R


def run_candles(SYM, MONTHS, FIG, PREFIX="nb_", PROFILE_DAY="2022-09-21"):
    """Lecture 12, §8.2-§8.6, figures 12_13-12_16."""
    FIG = Path(FIG); FIG.mkdir(parents=True, exist_ok=True)
    D = tape.ROOT / "interim" / "tape" / SYM
    months = [D / ym for ym in MONTHS]
    m1 = pl.concat([pl.read_parquet(m / "m1.parquet") for m in months]).sort("time")
    R = {}


    def bars(every):
        b = (m1.group_by_dynamic("time", every=every).agg(pl.col("open").first(), pl.col("high").max(), pl.col("low").min(), pl.col("close").last(),
                                                           pl.col("qty").sum(), pl.col("usd").sum(), pl.col("signed_usd").sum(), pl.col("trades").sum()))
        return b.with_columns(pl.col("close").log().diff().alias("r"))


    # ---------------------------------------------------------------- 8.3 order flow from candles (Lecture 3) against the truth
    flow = {}
    for every, win in (("1m", 1440), ("1h", 24 * 28), ("1d", 28)):
        b = bars(every).drop_nulls("r")
        sd = b["r"].shift(1).rolling_std(win).to_numpy()                       # past volatility only
        r, usd, true = b["r"].to_numpy(), b["usd"].to_numpy(), b["signed_usd"].to_numpy()
        ok = np.isfinite(sd) & (sd > 0)
        tick = np.sign(r) * usd                                                # on-balance volume: all of the bar's volume to the side of the close-to-close move
        bvc = (2 * norm.cdf(r / np.where(ok, sd, 1)) - 1) * usd                # bulk volume classification: split by the size of the move
        true_buy = (usd + true) / 2 / usd
        flow[every] = dict(bars=int(ok.sum()),
                           corr_tick=float(np.corrcoef(tick[ok], true[ok])[0, 1]), corr_bvc=float(np.corrcoef(bvc[ok], true[ok])[0, 1]),
                           sign_right_tick=float((np.sign(tick[ok]) == np.sign(true[ok])).mean()), sign_right_bvc=float((np.sign(bvc[ok]) == np.sign(true[ok])).mean()),
                           buy_share_err_tick=float(np.median(np.abs((usd + tick)[ok] / 2 / usd[ok] - true_buy[ok]))),
                           buy_share_err_bvc=float(np.median(np.abs((usd + bvc)[ok] / 2 / usd[ok] - true_buy[ok]))),
                           true_imbalance_abs_median=float(np.median(np.abs(true[ok] / usd[ok]))), bvc_imbalance_abs_median=float(np.median(np.abs(bvc[ok] / usd[ok]))))
    R["flow"] = flow
    d = bars("1d").drop_nulls("r"); sdd = d["r"].shift(1).rolling_std(28).to_numpy(); okd = np.isfinite(sdd)
    fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.1, subplot_titles=("Daily net buying: estimated from the candle against the tape", "Share of the day's dollars bought aggressively"))
    true_d = d["signed_usd"].to_numpy() / 1e9; bvc_d = (2 * norm.cdf(d["r"].to_numpy() / np.where(okd, sdd, 1)) - 1) * d["usd"].to_numpy() / 1e9
    fig.add_scattergl(x=true_d[okd], y=bvc_d[okd], mode="markers", marker=dict(size=4, color=SERIES[0], opacity=0.5), name="bulk volume classification", row=1, col=1)
    fig.add_scattergl(x=true_d[okd], y=(np.sign(d["r"].to_numpy()) * d["usd"].to_numpy() / 1e9)[okd], mode="markers", marker=dict(size=4, color=SERIES[1], opacity=0.35), name="tick rule", row=1, col=1)
    tb = ((d["usd"] + d["signed_usd"]) / 2 / d["usd"]).to_numpy() * 100; bb = ((d["usd"].to_numpy() + bvc_d * 1e9) / 2 / d["usd"].to_numpy()) * 100
    fig.add_histogram(x=tb[okd], nbinsx=60, marker_color=SERIES[2], opacity=0.8, name="the tape", row=1, col=2)
    fig.add_histogram(x=bb[okd], nbinsx=60, marker_color=SERIES[0], opacity=0.5, name="bulk volume classification", showlegend=False, row=1, col=2)
    fig.update_xaxes(title_text="true net aggressive buying, $bn", row=1, col=1); fig.update_yaxes(title_text="estimated, $bn", row=1, col=1)
    fig.update_xaxes(title_text="percent of the day's dollars (tick rule: always 0 or 100)", row=1, col=2); fig.update_yaxes(title_text="days", row=1, col=2)
    fig.update_layout(title="Candles get the direction of the flow roughly right, and its size badly wrong", barmode="overlay", height=470, width=1100,
                      legend=dict(orientation="h", y=-0.22, x=0, itemsizing="constant"))
    save_figure(fig, PREFIX + "12_13_flow_from_candles", FIG)

    # ---------------------------------------------------------------- 8.4 range-based volatility (Lecture 3, §4.4) against realised variance
    rv = pl.concat([pl.read_parquet(m / "rv_days.parquet", columns=["day", "rv_300"]) for m in months])
    d = d.with_columns(pl.col("time").dt.date().alias("day")).join(rv, on="day")
    o, h, l, c = (np.log(d[x].to_numpy()) for x in ("open", "high", "low", "close")); cp = np.log(d["close"].shift(1).to_numpy())
    est = {"close to close": (c - cp) ** 2, "Parkinson": (h - l) ** 2 / (4 * np.log(2)),
           "Garman-Klass": 0.5 * (h - l) ** 2 - (2 * np.log(2) - 1) * (c - o) ** 2, "Rogers-Satchell": (h - c) * (h - o) + (l - c) * (l - o)}
    rvd = d["rv_300"].to_numpy(); ok = np.isfinite(cp)
    W = 28; k = 0.34 / (1.34 + (W + 1) / (W - 1))
    def roll(x): return pl.Series(x).rolling_mean(W).to_numpy()
    ov = o - cp; oc = c - o
    yz = pl.Series(ov).rolling_var(W).to_numpy() + k * pl.Series(oc).rolling_var(W).to_numpy() + (1 - k) * roll(est["Rogers-Satchell"])
    rvw = roll(rvd); res = {}
    def daily_corr(x):                                                         # day by day: log estimate against log realised variance
        if x is None: return None
        m = ok & (x > 0) & (rvd > 0)
        return float(np.corrcoef(np.log(x[m]), np.log(rvd[m]))[0, 1])
    for name, x in list(est.items()) + [("Yang-Zhang", None)]:
        v = yz if x is None else roll(np.where(ok, x, np.nan))
        m = np.isfinite(v) & np.isfinite(rvw) & (v > 0)
        lr = np.log(np.sqrt(v[m] / rvw[m]))
        res[name] = dict(bias_vol=float(np.sqrt(np.mean(v[m]) / np.mean(rvw[m]))), median_ratio=float(np.exp(np.median(lr))), spread_ratio=float(np.std(lr)),
                         corr_daily=daily_corr(x))
    R["range_estimators_28d"] = res
    day0 = d.with_columns(pl.col("day").cast(pl.Utf8)).filter(pl.col("day") == "2022-09-06")
    day0 = day0.row(0, named=True) if day0.height else None
    R["outlier_day_2022_09_06"] = None if day0 is None else dict(parkinson_vol_annual=float(np.sqrt((np.log(day0["high"] / day0["low"]) ** 2 / (4 * np.log(2))) * 365)), rv_vol_annual=float(np.sqrt(day0["rv_300"] * 365)),
                                       high=day0["high"], low=day0["low"])
    fig = go.Figure()
    t = d["time"].to_numpy()
    fig.add_scatter(x=t, y=np.sqrt(rvw * 365) * 100, mode="lines", line=dict(color="black", width=2), name="realised (5-minute returns): the benchmark")
    for name, col in (("close to close", SERIES[1]), ("Parkinson", SERIES[0]), ("Yang-Zhang", SERIES[2])):
        v = yz if name == "Yang-Zhang" else roll(np.where(ok, est[name], np.nan))
        fig.add_scatter(x=t, y=np.sqrt(v * 365) * 100, mode="lines", line=dict(color=col, width=1.3), name=name)
    if "2022-09" in MONTHS: fig.add_annotation(x=datetime(2022, 9, 20), y=135, text="one flagged print (§5.4) sets the high<br>of 6 September 2022, for 28 days", showarrow=True, ax=120, ay=-10, font=dict(size=11))
    fig.update_yaxes(title_text="volatility, % a year (28 days)"); fig.update_layout(title="Volatility from daily candles against realised volatility from the tape",
                                                                                                           height=450, width=1100, legend=dict(orientation="h", y=-0.15, x=0))
    save_figure(fig, PREFIX + "12_14_range_estimators", FIG)

    # ---------------------------------------------------------------- 8.5 close against VWAP
    dv = d.with_columns((pl.col("usd") / pl.col("qty")).alias("vwap"))
    dist = np.abs(dv["close"].to_numpy() / dv["vwap"].to_numpy() - 1) * 1e4
    mv = m1.with_columns((pl.col("close") / pl.col("vwap") - 1).abs().alias("dist"))
    rc, rvw_ = np.diff(np.log(dv["close"].to_numpy())), np.diff(np.log(dv["vwap"].to_numpy()))
    R["close_vs_vwap"] = dict(day_median_bp=float(np.median(dist)), day_p90_bp=float(np.quantile(dist, 0.9)), minute_median_bp=float(mv["dist"].median() * 1e4),
                              minute_p99_bp=float(mv["dist"].quantile(0.99) * 1e4), corr_close_vwap_returns=float(np.corrcoef(rc, rvw_)[0, 1]),
                              vol_close=float(rc.std() * np.sqrt(365)), vol_vwap=float(rvw_.std() * np.sqrt(365)))

    # ---------------------------------------------------------------- 8.2 the same candle, different flow: two hours with near-identical candles
    hh = bars("1h").drop_nulls("r").with_columns(((pl.col("high") / pl.col("low")).log() * 1e4).alias("range_bp"), (pl.col("r") * 1e4).alias("ret_bp"),
                                                 pl.col("usd").log().alias("lusd"), (pl.col("signed_usd") / pl.col("usd")).alias("imb"))
    X = hh.select("ret_bp", "range_bp", "lusd").to_numpy(); sc = X.std(axis=0); imb = hh["imb"].to_numpy()
    cand = np.where((np.abs(X[:, 0]) > 40) & (X[:, 1] > 80))[0]                 # hours with a real move, so the comparison matters
    best = (np.inf, None, None)
    for i in cand:
        dd = np.sqrt((((X[cand] - X[i]) / sc) ** 2).sum(1)); dd[cand == i] = np.inf
        score = dd - 3 * np.abs(imb[cand] - imb[i])                            # close candles, very different flow
        j = int(np.argmin(score))
        if score[j] < best[0]: best = (score[j], i, cand[j])
    i, j = best[1], best[2]
    pair = [hh.row(int(i), named=True), hh.row(int(j), named=True)]
    R["same_candle"] = [{k: (str(v) if k == "time" else round(float(v), 4)) for k, v in p.items() if k in ("time", "ret_bp", "range_bp", "usd", "imb", "trades")} for p in pair]
    fig = make_subplots(rows=2, cols=2, shared_xaxes=False, row_heights=[0.62, 0.38], vertical_spacing=0.1, horizontal_spacing=0.08,
                        subplot_titles=[f"{p['time']:%d %b %Y, %H:00} UTC: {p['ret_bp']:+.0f} bp, range {p['range_bp']:.0f} bp, ${p['usd'] / 1e9:.1f}bn" for p in pair])
    for col, p in enumerate(pair, start=1):
        w = m1.filter(pl.col("time").is_between(p["time"], p["time"] + pl.duration(minutes=59)))
        fig.add_candlestick(x=w["time"], open=w["open"], high=w["high"], low=w["low"], close=w["close"], showlegend=False, increasing_line_color=SERIES[0], decreasing_line_color=SERIES[3], row=1, col=col)
        fig.add_scatter(x=w["time"], y=(w["signed_usd"].cum_sum() / 1e6), mode="lines", line=dict(color=SERIES[2], width=2), showlegend=False, row=2, col=col)
        fig.update_xaxes(rangeslider_visible=False, row=1, col=col); fig.update_yaxes(title_text="net aggressive buying, $m" if col == 1 else None, row=2, col=col)
    fig.update_yaxes(title_text="price, minute candles", row=1, col=1)
    fig.update_layout(title="Two hours with almost the same hourly candle, and opposite order flow inside it", height=560, width=1100)
    save_figure(fig, PREFIX + "12_15_same_candle", FIG)

    # ---------------------------------------------------------------- 8.6 volume by price on one day: the FOMC decision of 21 September 2022
    tape.wait_for_memory(1.5)
    a = int(datetime.fromisoformat(PROFILE_DAY).replace(tzinfo=timezone.utc).timestamp() * 1000)
    day = (pl.scan_parquet(tape.source(SYM, PROFILE_DAY[:7])).filter(pl.col("transact_time").is_between(a, a + 86_400_000, closed="left"))
             .select("price", "quantity", "is_buyer_maker", "transact_time").collect())
    day = day.with_columns((pl.col("price") * pl.col("quantity")).alias("usd"), (pl.col("price") / 10).floor().mul(10).alias("bin"),
                           pl.from_epoch("transact_time", time_unit="ms").alias("time"))
    prof = day.group_by("bin").agg(pl.col("usd").filter(~pl.col("is_buyer_maker")).sum().alias("buy"), pl.col("usd").filter(pl.col("is_buyer_maker")).sum().alias("sell")).sort("bin")
    hb = day.group_by_dynamic("time", every="15m").agg(pl.col("price").first().alias("o"), pl.col("price").max().alias("h"), pl.col("price").min().alias("l"), pl.col("price").last().alias("c"))
    vwap_day = float(day["usd"].sum() / day["quantity"].sum()); poc = float(prof.with_columns((pl.col("buy") + pl.col("sell")).alias("t")).sort("t", descending=True)["bin"][0])
    R["volume_profile_2022_09_21"] = dict(trades=day.height, open=float(day["price"][0]), close=float(day["price"][-1]), high=float(day["price"].max()), low=float(day["price"].min()),
                                          vwap=vwap_day, most_traded_10usd_bin=poc)
    fig = make_subplots(rows=1, cols=2, shared_yaxes=True, column_widths=[0.68, 0.32], horizontal_spacing=0.02,
                        subplot_titles=(f"15-minute candles, {PROFILE_DAY} (UTC)", "Dollars traded at each price"))
    fig.add_candlestick(x=hb["time"], open=hb["o"], high=hb["h"], low=hb["l"], close=hb["c"], showlegend=False, increasing_line_color=SERIES[0], decreasing_line_color=SERIES[3], row=1, col=1)
    fig.add_bar(y=prof["bin"], x=prof["buy"] / 1e6, orientation="h", marker_color=SERIES[0], name="bought aggressively", row=1, col=2)
    fig.add_bar(y=prof["bin"], x=prof["sell"] / 1e6, orientation="h", marker_color=SERIES[3], name="sold aggressively", row=1, col=2)
    for yv, lab in ((vwap_day, "the day's VWAP"), (float(day["price"][-1]), "the close")):
        fig.add_hline(y=yv, line=dict(color=MUTED, dash="dot"), annotation_text=lab, annotation_position="top left", row=1, col=1)
    fig.update_xaxes(rangeslider_visible=False, row=1, col=1); fig.update_xaxes(title_text="$m per $10 of price", row=1, col=2); fig.update_yaxes(title_text="price, USDT", row=1, col=1)
    fig.update_layout(title="Volume by price: where the day's trading actually happened", barmode="stack", height=560, width=1100, legend=dict(orientation="h", y=-0.12, x=0.6))
    save_figure(fig, PREFIX + "12_16_volume_profile", FIG)

    # the same day as net aggressive buying at each price (figure 12_18)
    day = day.with_columns(pl.when(pl.col("is_buyer_maker")).then(-1).otherwise(1).alias("sign"))
    hb = day.sort("time").group_by_dynamic("time", every="15m").agg(pl.col("price").first().alias("o"), pl.col("price").max().alias("h"), pl.col("price").min().alias("l"), pl.col("price").last().alias("c"))
    delta = (day.with_columns((pl.col("price") / 10).floor().mul(10).alias("bin")).group_by("bin")
                .agg((pl.col("usd") * pl.col("sign")).sum().alias("delta"), pl.col("usd").sum().alias("total")).sort("bin"))
    lv = (day.with_columns((pl.col("price") / 50).floor().mul(50).alias("level")).group_by("level")
             .agg((pl.col("usd") * pl.col("sign")).sum().alias("delta"), pl.col("usd").sum().alias("total")).sort("level")
             .with_columns((pl.col("delta") / pl.col("total")).alias("share")).filter(pl.col("total") > 3e8))
    R["levels_50usd"] = [{k: (round(float(v), 4) if k != "level" else float(v)) for k, v in r.items()} for r in lv.iter_rows(named=True)]
    R["day_net_usd"] = float(day["usd"].dot(day["sign"])); R["day_usd"] = float(day["usd"].sum())
    fig = make_subplots(rows=1, cols=2, shared_yaxes=True, column_widths=[0.68, 0.32], horizontal_spacing=0.02,
                        subplot_titles=(f"15-minute candles, {PROFILE_DAY} (UTC)", "Net aggressive buying at each price"))
    fig.add_candlestick(x=hb["time"], open=hb["o"], high=hb["h"], low=hb["l"], close=hb["c"], showlegend=False, increasing_line_color=SERIES[0], decreasing_line_color=SERIES[3], row=1, col=1)
    pos = delta.filter(pl.col("delta") > 0); neg = delta.filter(pl.col("delta") <= 0)
    fig.add_bar(y=pos["bin"], x=pos["delta"] / 1e6, orientation="h", marker=dict(color=SERIES[0], line=dict(width=0)), name="more bought aggressively", row=1, col=2)
    fig.add_bar(y=neg["bin"], x=neg["delta"] / 1e6, orientation="h", marker=dict(color=SERIES[3], line=dict(width=0)), name="more sold aggressively", row=1, col=2)
    fig.add_vline(x=0, line=dict(color=MUTED, width=1), row=1, col=2)
    fig.update_xaxes(rangeslider_visible=False, row=1, col=1); fig.update_xaxes(title_text="net $m per $10 of price", row=1, col=2); fig.update_yaxes(title_text="price, USDT", row=1, col=1)
    fig.update_layout(title="The same day as net buying at each price: where pressure met resistance<br><sup>Bars to the right: more bought than sold aggressively at that price; "
                            "to the left: more sold. Read with the price's response: heavy selling where the price held is absorption</sup>",
                      barmode="relative", height=580, width=1100, margin=dict(t=90), legend=dict(orientation="h", y=-0.12, x=0.6))
    save_figure(fig, PREFIX + "12_18_volume_delta", FIG)
    return R
