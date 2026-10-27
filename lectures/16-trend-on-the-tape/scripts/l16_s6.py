"""Lecture 16 §6: the premium in the perpetual. At each funding snapshot T (00:00, 08:00, 16:00 UTC): the premium of the perpetual over the spot index
during the interval that ends at T (mean of the hourly premium-index closes, Binance archive) and the funding settled at T. Split by the premium known
at T (thirds, cut on 2021-2024): bitcoin's return over the next 8 and 24 hours, and the rule's long and short legs over the next 8 hours (the rule of §2
with plain sizing and the patient entry; gross price return of the position held). Means in bp, t-statistics with days as clusters. Figure 16_09."""
import io, json, math, sys, zipfile
from pathlib import Path
import numpy as np, polars as pl
from plotly.subplots import make_subplots
import os, sys
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # tables print on any console; Jupyter handles its own
HERE = Path(__file__).resolve().parent                                     # lectures/16-.../scripts
sys.path[:0] = [str(HERE), str(HERE.parents[1] / "13-bars-not-cut-by-time" / "scripts"), str(HERE.parents[1] / "12-tick-data-the-tape"), str(HERE.parents[2])]
import tape
L16_RESULTS = tape.ROOT / "interim" / "l16"; L16_RESULTS.mkdir(parents=True, exist_ok=True)          # results: in the data folder, never committed
FIG = Path(os.environ.get("L16_FIG", HERE.parent / "figures")); FIG.mkdir(parents=True, exist_ok=True)
PREFIX = os.environ.get("L16_PREFIX", "nb_")                               # "nb_": the lecture's own figures are never overwritten
import tape
from trading_models.plotting import INK, MUTED, SERIES, apply_theme, save_figure

J = L16_RESULTS / "l16_s6.json"


def load(folder):
    out = []
    for f in sorted(folder.glob("*.zip")):
        z = zipfile.ZipFile(f); t = z.read(z.namelist()[0]).decode()
        d = pl.read_csv(io.StringIO(t), has_header=t.startswith("open_time"), infer_schema_length=0)
        out.append(d.rename(dict(zip(d.columns[:5], ["open_time", "open", "high", "low", "close"]))).select(pl.col("open_time").cast(pl.Int64), pl.col("close").cast(pl.Float64)))
    d = pl.concat(out).with_columns(pl.when(pl.col("open_time") > 10 ** 14).then(pl.col("open_time") // 1000).otherwise(pl.col("open_time")).alias("ms"))
    return d.with_columns(pl.from_epoch("ms", time_unit="ms").cast(pl.Datetime("us")).alias("t")).sort("t")


if not J.exists():
    import l16_buildup as B
    prem = (load(tape.ROOT / "raw" / "binance" / "um" / "premiumIndexKlines" / "BTCUSDT").with_columns((pl.col("t").dt.truncate("8h") + pl.duration(hours=8)).alias("T"))
            .group_by("T").agg(pl.col("close").mean().alias("premium"), pl.len().alias("k")).filter(pl.col("k") >= 6).sort("T"))
    fr = pl.read_parquet(tape.ROOT / "raw" / "binance" / "um" / "fundingRate" / "BTCUSDT-fundingRate.parquet").select(
        pl.col("fundingTime").cast(pl.Int64).cast(pl.Datetime("ms")).cast(pl.Datetime("us")).dt.truncate("1h").alias("T"), "fundingRate")
    S = prem.join(fr, on="T", how="inner")
    net, parts = B.simulate(B.sig_plain, B.TAKER + B.HALF - B.REPOST_SAVING, False, fc=B.forecast(B.dp_sd, [1, 2, 3]))
    held = np.r_[0.0, parts["pos"][:-1]]; g = held * B.r
    tc = B.H["t_close"].to_numpy(); lp = np.log(B.p)
    c_long = np.r_[0.0, np.cumsum(np.where(held > 0, g, 0.0))]; c_short = np.r_[0.0, np.cumsum(np.where(held < 0, g, 0.0))]
    T = S["T"].to_numpy(); i0 = np.searchsorted(tc, T, side="right") - 1                         # hour that closes at T
    ok = (i0 >= 0) & (i0 + 24 < len(tc)) & B.live[np.clip(i0, 0, len(tc) - 1)]
    S = S.filter(pl.Series(ok)); i0 = i0[ok]
    S = S.with_columns(pl.Series("btc_8h", (lp[i0 + 8] - lp[i0]) * 1e4), pl.Series("btc_24h", (lp[i0 + 24] - lp[i0]) * 1e4),
                       pl.Series("long_8h", (c_long[i0 + 9] - c_long[i0 + 1]) * 1e4), pl.Series("short_8h", (c_short[i0 + 9] - c_short[i0 + 1]) * 1e4),
                       pl.Series("pos", parts["pos"][i0]), (pl.col("T").dt.date()).alias("day"))
    IS = S["T"] < pl.datetime(2025, 1, 1) if False else (S["T"].to_numpy() < np.datetime64("2025-01-01"))
    q1, q2 = np.quantile(S.filter(pl.Series(IS))["premium"].to_numpy(), [1 / 3, 2 / 3])
    S = S.with_columns(pl.when(pl.col("premium") < q1).then(pl.lit("low")).when(pl.col("premium") < q2).then(pl.lit("middle")).otherwise(pl.lit("high")).alias("third"))

    def clustered(df, col):
        d = df.group_by("day").agg(pl.col(col).sum().alias("s"), pl.len().alias("k")); m = d["s"].sum() / d["k"].sum(); e = d["s"].to_numpy() - m * d["k"].to_numpy()
        G = d.height; se = math.sqrt(G / (G - 1) * (e ** 2).sum()) / d["k"].sum(); return round(float(m), 2), round(float(m / se), 1)

    R = {"cut_bp": [round(q1 * 1e4, 2), round(q2 * 1e4, 2)], "by_third": {}, "funding_vs_premium_corr": round(float(np.corrcoef(S["premium"], S["fundingRate"])[0, 1]), 3)}
    for smp, mk in (("2021-2024", IS), ("2025-2026", ~IS)):
        R["by_third"][smp] = {}
        for th in ("low", "middle", "high"):
            d = S.filter(pl.Series(mk) & (pl.col("third") == th))
            R["by_third"][smp][th] = dict(n=d.height, premium_bp=round(float(d["premium"].mean() * 1e4), 2), funding_bp=round(float(d["fundingRate"].mean() * 1e4), 2),
                                          share_long=round(float((d["pos"] > 0).mean()), 2),
                                          **{c: clustered(d, c) for c in ("btc_8h", "btc_24h", "long_8h", "short_8h")})
    daily = S.group_by("day").agg(pl.col("premium").mean(), pl.col("fundingRate").sum()).sort("day")
    R["daily"] = {"day": [str(x) for x in daily["day"]], "premium_bp": [round(x * 1e4, 3) for x in daily["premium"]], "funding_bp_day": [round(x * 1e4, 3) for x in daily["fundingRate"]]}
    J.write_text(json.dumps(R, indent=1))
R = json.loads(J.read_text())

apply_theme()
d = pl.DataFrame({"day": pl.Series(R["daily"]["day"]).str.to_date(), "p": R["daily"]["premium_bp"], "f": R["daily"]["funding_bp_day"]}).with_columns(
    pl.col("p").rolling_mean(7).alias("p7"), pl.col("f").rolling_mean(7).alias("f7"))
fig = make_subplots(rows=1, cols=2, column_widths=[0.6, 0.4], horizontal_spacing=0.09,
                    subplot_titles=("The premium of the perpetual over spot, and the funding it sets", "Bitcoin's next day, by the premium at the snapshot"))
fig.add_scatter(x=d["day"].to_list(), y=d["p7"].to_list(), mode="lines", line=dict(color=SERIES[0], width=1.6), name="premium, bp (7-day average)", row=1, col=1)
fig.add_scatter(x=d["day"].to_list(), y=d["f7"].to_list(), mode="lines", line=dict(color=SERIES[3], width=1.6), name="funding paid by a long, bp a day (7-day average)", row=1, col=1)
fig.add_hline(y=0, line=dict(color=INK, dash="dot", width=1), row=1, col=1)
fig.add_hline(y=3, line=dict(color=MUTED, dash="dot", width=1), row=1, col=1)
fig.add_annotation(x=d["day"][30], y=3, xref="x", yref="y", text="0.01% every 8 hours", showarrow=False, yshift=9, xanchor="left", font=dict(size=10, color=MUTED))
for k, (smp, col) in enumerate((("2021-2024", SERIES[0]), ("2025-2026", SERIES[1]))):
    b = R["by_third"][smp]
    fig.add_bar(x=["low premium", "middle", "high premium"], y=[b[t]["btc_24h"][0] for t in ("low", "middle", "high")], name=f"bitcoin's next 24 hours, {smp}",
                marker=dict(color=col, line=dict(width=0)), text=[f"t {b[t]['btc_24h'][1]:+.1f}" for t in ("low", "middle", "high")], textposition="outside", row=1, col=2)
fig.add_hline(y=0, line=dict(color=INK, dash="dot", width=1), row=1, col=2)
fig.update_yaxes(title_text="bp", row=1, col=1); fig.update_yaxes(title_text="mean return, bp", range=[-16, 34], row=1, col=2)
fig.update_layout(barmode="group", title="The perpetual's premium: what the crowd pays to be long, and what follows<br><sup>BTCUSDT on Binance, October 2021 to September 2026; "
                        "premium: the perpetual over the spot index, averaged over each 8-hour funding interval; thirds cut on 2021-2024</sup>",
                  height=480, width=1200, margin=dict(t=110, l=70), legend=dict(orientation="h", y=-0.2, x=0))
save_figure(fig, PREFIX + "16_09_premium", FIG)
print("cut (bp):", R["cut_bp"], " corr(premium, funding):", R["funding_vs_premium_corr"])
for smp, b in R["by_third"].items():
    for th, v in b.items():
        print(smp, f"{th:7}", f"n {v['n']:5} premium {v['premium_bp']:+6.2f} funding {v['funding_bp']:+5.2f} long share {v['share_long']:.2f} | btc 8h {v['btc_8h']} 24h {v['btc_24h']} | long leg 8h {v['long_8h']} short leg 8h {v['short_8h']}")
