"""Lecture 19 §4, tests H14-H18 (fixed in results/hypotheses.md) around the cascade of 10 October.
T0 from l19_T0.txt (first minute of 10 Oct with a one-minute change of the mid larger than any on the in-sample days). Pre-window [T0 - 2 h, T0);
reference: every 2-hour window of the other days on the same clock phase, none touching 10 October. Binance: BTCUSDT perpetual aggTrades (zip,
data.binance.vision), converted once to L19_OUT/binance/DAY.parquet (ts, price). Output: l19_s4_stats.json, l19_s4_profile.parquet (15-minute steps)."""
import io, json, sys, zipfile
from pathlib import Path
import numpy as np, polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l19 as L19
D = L19.S3; BN_RAW = L19.BN_RAW; BN = L19.BN
DAYS = sorted(p.stem.replace("samples_", "") for p in D.glob("samples_*.parquet")); CASC = "2025-10-10"
T0 = int((L19.result_path("l19_T0.txt")).read_text()); H2, Q15 = 7_200_000, 900_000
rng = np.random.default_rng(1910)
c0 = T0 - (T0 % 86_400_000); c1 = c0 + 86_400_000                                   # 10 October, 00:00 to 24:00 UTC

# Binance: last trade price, one parquet per day
for d in DAYS:
    if (BN / f"{d}.parquet").exists(): continue
    with zipfile.ZipFile(BN_RAW / f"BTCUSDT-aggTrades-{d}.zip") as z:
        raw = z.read(z.namelist()[0])
    head = raw[:200].decode()
    df = pl.read_csv(io.BytesIO(raw), has_header=head[0].isalpha(), new_columns=["id", "price", "qty", "f", "l", "ts", "m"])
    df.select(pl.col("ts").cast(pl.Int64), pl.col("price").cast(pl.Float64)).sort("ts").write_parquet(BN / f"{d}.parquet")

# per-minute series of every measure
rows = []
for d in DAYS:
    m = pl.read_parquet(D / f"b2_min_{d}.parquet").select(pl.col("t"), (pl.col("depth_b10") + pl.col("depth_a10")).alias("depth"))
    ice = pl.read_parquet(D / f"b3_ice_{d}.parquet").with_columns((pl.col("t").cast(pl.Int64) // 60000 * 60000).alias("t")).group_by("t").agg(pl.len().alias("chains"))
    lag = pl.read_parquet(D / f"b3_lag_{d}.parquet").with_columns((pl.col("cts") // 60000 * 60000).alias("t"))
    st = pl.read_parquet(L19.STATE / f"{d}.parquet").select("ts", ((pl.col("bid") + pl.col("ask")) / 20).alias("mid"))   # dollars
    bn = pl.read_parquet(BN / f"{d}.parquet").rename({"price": "bn"})
    g = st.sort("ts").join_asof(bn, on="ts", strategy="backward").drop_nulls().with_columns((pl.col("bn") - pl.col("mid")).alias("gap"), (pl.col("ts") // 60000 * 60000).alias("t"))
    gm = g.group_by("t").agg(pl.col("gap").abs().mean().alias("absgap"), pl.col("gap").mean().alias("gap"))
    lm = lag.group_by("t").agg(pl.col("lag"))
    rows.append(m.join(ice, on="t", how="left").join(gm, on="t", how="left").join(lm, on="t", how="left").with_columns(pl.col("chains").fill_null(0)))
    del st, bn, g
A = pl.concat(rows).sort("t").unique("t", keep="first").sort("t")


def window_stats(w):
    lags = np.concatenate([np.asarray(x) for x in w["lag"].drop_nulls().to_list()]) if w["lag"].drop_nulls().len() else np.array([np.nan])
    return {"chains": float(w["chains"].sum()), "depth": float(w["depth"].mean()), "lag99": float(np.percentile(lags, 99)), "absgap": float(w["absgap"].mean())}


pre = window_stats(A.filter((pl.col("t") >= T0 - H2) & (pl.col("t") < T0)))
ref = []
k = 1
starts = sorted({T0 - H2 + j * H2 for j in range(-400, 400)})
for s in starts:
    if s + H2 <= A["t"].min() or s < A["t"].min() or s + H2 > A["t"].max() + 60000: continue
    if s < c1 and s + H2 > c0: continue
    w = A.filter((pl.col("t") >= s) & (pl.col("t") < s + H2))
    if w.height < 100: continue
    ref.append(window_stats(w))
R = {"T0": T0, "pre": pre, "n_ref": len(ref)}
def pval(key, higher=True):
    v = np.array([r[key] for r in ref]); x = pre[key]
    return float((1 + (v >= x).sum() if higher else 1 + (v <= x).sum()) / (1 + len(v)))
R["H14_p"] = pval("chains"); R["H15_p"] = pval("depth", higher=False); R["H16_p"] = pval("lag99"); R["H18a_p"] = pval("absgap")
R["ref_quantiles"] = {k: np.nanquantile([r[k] for r in ref], [0.05, 0.5, 0.95, 1.0]).tolist() for k in ("chains", "depth", "lag99", "absgap")}

# H17: AUC per 15-minute step from T0 - 2 h to T0 + 2 h; Mann-Whitney normal approximation
from math import erf, sqrt
S = pl.read_parquet(D / f"samples_{CASC}.parquet")
def auc_mw(I, up):
    r = pl.Series(I).rank("average").to_numpy(); n1 = up.sum(); n0 = len(up) - n1
    if n1 == 0 or n0 == 0: return np.nan, 1.0, int(len(up))
    U = r[up].sum() - n1 * (n1 + 1) / 2; a = U / (n1 * n0); z = (U - n1 * n0 / 2) / sqrt(n1 * n0 * (n1 + n0 + 1) / 12)
    return float(a), float(0.5 * (1 - erf(z / sqrt(2)))), int(len(up))
steps = []
for j in range(-24, 12):
    s = T0 + j * Q15; w = S.filter((pl.col("ts") >= s) & (pl.col("ts") < s + Q15))
    a, p, n = auc_mw(w["I1"].to_numpy(), w["up"].to_numpy()) if w.height else (np.nan, 1.0, 0)
    steps.append({"start": s, "auc": a, "p": p, "n": n})
R["H17_steps"] = steps; R["H17_p"] = max(x["p"] for x in steps if -8 * Q15 <= x["start"] - T0 < 8 * Q15)

# H18b: rank correlation of I1 and the gap (Binance - Bybit mid) on 10 Oct, T0 - 2 h to T0 + 2 h; bootstrap over 15-minute blocks
bn = pl.read_parquet(BN / f"{CASC}.parquet").rename({"price": "bn"})
st = pl.read_parquet(L19.STATE / f"{CASC}.parquet").select("ts", ((pl.col("bid") + pl.col("ask")) / 20).alias("mid"))
W = S.filter((pl.col("ts") >= T0 - H2) & (pl.col("ts") < T0 + H2)).sort("ts").join_asof(st.sort("ts"), on="ts").join_asof(bn, on="ts").drop_nulls()
W = W.with_columns((pl.col("bn") - pl.col("mid")).alias("gap"), ((pl.col("ts") - (T0 - H2)) // Q15).alias("blk"))
def spear(x, y): return float(np.corrcoef(pl.Series(x).rank().to_numpy(), pl.Series(y).rank().to_numpy())[0, 1])
R["H18b_rho"] = spear(W["I1"].to_numpy(), W["gap"].to_numpy())
blocks = [W.filter(pl.col("blk") == b) for b in range(16)]; blocks = [b for b in blocks if b.height > 10]
bs = []
for _ in range(2000):
    pick = pl.concat([blocks[i] for i in rng.integers(0, len(blocks), len(blocks))]); bs.append(spear(pick["I1"].to_numpy(), pick["gap"].to_numpy()))
R["H18b_ci"] = np.quantile(bs, [0.025, 0.975]).tolist(); R["H18b_p"] = float(np.mean(np.array(bs) <= 0))
R["H18b_rho_by_block"] = [spear(b["I1"].to_numpy(), b["gap"].to_numpy()) for b in blocks]
# same correlation on the in-sample days, for comparison
cmp_ = []
for d in [x for x in DAYS if x <= "2025-10-09"]:
    s_ = pl.read_parquet(D / f"samples_{d}.parquet").sort("ts"); st_ = pl.read_parquet(L19.STATE / f"{d}.parquet").select("ts", ((pl.col("bid") + pl.col("ask")) / 20).alias("mid"))
    w_ = s_.join_asof(st_.sort("ts"), on="ts").join_asof(pl.read_parquet(BN / f"{d}.parquet").rename({"price": "bn"}), on="ts").drop_nulls()
    cmp_.append(spear(w_["I1"].to_numpy(), (w_["bn"] - w_["mid"]).to_numpy()))
R["H18b_rho_insample_days"] = cmp_

# Benjamini-Hochberg over H14-H18
P = {"H14": R["H14_p"], "H15": R["H15_p"], "H16": R["H16_p"], "H17": R["H17_p"], "H18a": R["H18a_p"], "H18b": R["H18b_p"]}
ks = sorted(P, key=P.get); m = len(ks); kmax = max([i + 1 for i, k_ in enumerate(ks) if P[k_] <= (i + 1) * 0.05 / m] or [0])
R["BH"] = {k_: {"p": P[k_], "reject_null": ks.index(k_) < kmax} for k_ in P}

# 15-minute profile from T0 - 6 h to T0 + 3 h, and the same clock steps on the reference days (median and 5-95%)
prof = []
for j in range(-24, 12):
    s = T0 + j * Q15; w = A.filter((pl.col("t") >= s) & (pl.col("t") < s + Q15)); x = window_stats(w); x["start"] = s; prof.append(x)
pl.DataFrame(prof).write_parquet(L19.result_path("l19_s4_profile.parquet"))
refq = []
for j in range(-24, 12):
    vals = []
    for d in DAYS:
        if d == CASC: continue
        off = int(pl.Series([d]).str.to_date().dt.epoch("d").item()) * 86_400_000 - c0
        s = T0 + j * Q15 + off; w = A.filter((pl.col("t") >= s) & (pl.col("t") < s + Q15))
        if w.height: vals.append(window_stats(w))
    refq.append({k_: np.nanquantile([v[k_] for v in vals], [0.05, 0.5, 0.95]).tolist() for k_ in ("chains", "depth", "lag99", "absgap")} | {"start": T0 + j * Q15})
R["profile_ref"] = refq
(L19.OUT / "l19_s4_stats.json").write_text(json.dumps(R, indent=1, default=float))
for k_ in ("pre", "n_ref", "ref_quantiles", "H14_p", "H15_p", "H16_p", "H17_p", "H18a_p", "H18b_rho", "H18b_ci", "H18b_p", "BH"):
    print(k_, json.dumps(R[k_], default=float))
print("H18b in-sample days", np.round(cmp_, 3).tolist())
print("H17", [(round((x["start"] - T0) / 60000), round(x["auc"], 3), x["n"]) for x in steps])
