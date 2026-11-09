"""Lecture 23 §3: H10, H11 and H12 on Bybit BTCUSDT, day by day, every day in and out of sample (the tests use only 11 October - 3 November).
H10: orders sent within 100 ms after Binance's last trade price moved 2 bp or more their way (sniper-like) against other orders of the same size class, net R(10 s) as in Lecture 22 §3.
H11: Lecture 22's marks() at whole minutes against fake marks 10 to 50 s after them, per day (the funding minutes 00:00, 08:00, 16:00 left out, and reported apart).
H12: the share of taker size in runs of eight or more equal orders at regular gaps, against the same day with sizes shuffled within 5-minute blocks.
Per day to L23_RESULTS/s3_days/DAY.json, so that a day is never computed twice. Usage: python l23_s3.py [DAY ...] (default: all days); python l23_s3.py --tests aggregates."""
import io, json, sys, zipfile
from pathlib import Path
import numpy as np, polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l23 as L
import l22_styles as St, l22_s3_response as S3
DAYS = L.RESULTS / "s3_days"; DAYS.mkdir(parents=True, exist_ok=True)
JUMP, LOOK = 2.0, 100                                                                # bp, ms: H10's move on Binance and the look-back
FAKES = range(10_000, 50_001, 500); FUNDING = (0, 8, 16)


def binance(day):
    with zipfile.ZipFile(L.L22.BN_RAW / f"{L.L22.SYM}-aggTrades-{day}.zip") as z:
        B = pl.read_csv(io.BytesIO(z.read(z.namelist()[0])), columns=["price", "transact_time"]).sort("transact_time")
    return B["transact_time"].to_numpy(), B["price"].to_numpy()


def sniper_like(t, side, bt, bp):
    a = np.searchsorted(bt, t, "right") - 1; b = np.searchsorted(bt, t - LOOK, "right") - 1; ok = (a >= 0) & (b >= 0)
    mv = np.where(ok, (bp[np.maximum(a, 0)] - bp[np.maximum(b, 0)]) / bp[np.maximum(a, 0)] * 1e4, 0.0)
    return side * mv >= JUMP


def h10(day):
    bt, bp = binance(day); X = S3.net_day(day)
    X = X.with_columns(pl.Series("sn", sniper_like(X["ts"].to_numpy(), X["side"].to_numpy(), bt, bp))); del bt, bp
    G = X.group_by("cls", "sn").agg(pl.len().alias("n"), pl.col("n_m10000").sum().alias("s"), pl.col("n_m1000").sum().alias("s1"), pl.col("n_m60000").sum().alias("s60"), pl.col("S").sum().alias("size"),
                                    pl.col("cost_bp").sum().alias("cost"))
    return [dict(cls=r["cls"], sn=bool(r["sn"]), n=r["n"], s=r["s"], s1=r["s1"], s60=r["s60"], size=r["size"], cost=r["cost"]) for r in G.iter_rows(named=True)]


def ex(O, Q, off):
    """One day's mean excess at marks `off` ms after the whole minute: H11a (a), H11b (x), the size burst (g), the spread after (s), all marks but the funding minutes, and the funding minutes apart."""
    M = St.marks(O, Q, offset=off).with_columns((pl.col("w0") - pl.col("wc")).alias("a"), (pl.col("xb") - pl.col("xc")).alias("x"), (pl.col("g0") - pl.col("gc")).alias("g"), (pl.col("sa") - pl.col("sc")).alias("s"),
                                                (((pl.col("t") - off) % 3_600_000 == 0) & ((pl.col("t") - off) // 3_600_000 % 24).is_in(FUNDING)).alias("fund"))
    out = {}
    for k, F in (("", M.filter(~pl.col("fund"))), ("fund_", M.filter(pl.col("fund")))):
        for c in "axgs": out[k + c] = float(F[c].mean()) if F.height else None
    for per, name in ((300_000, "m5"), (900_000, "m15"), (3_600_000, "h")):                     # reported: by kind of mark
        F = M.filter(~pl.col("fund") & ((pl.col("t") - off) % per == 0))
        for c in "axg": out[f"{name}_{c}"] = float(F[c].mean())
    return out


def h11(day):
    O = pl.read_parquet(L.L22.OUT / "orders" / f"{day}.parquet", columns=["ts", "side", "S"]).rename({"ts": "t", "S": "q"}).sort("t")
    Q = pl.read_parquet(L.L22.STATE / f"{day}.parquet", columns=["ts", "bid", "ask"]).rename({"ts": "t"}).sort("t")
    real = ex(O, Q, 0); F = [ex(O, Q, f) for f in FAKES]
    fake = {k: float(np.mean([f[k] for f in F if f[k] is not None])) for k in F[0]}
    return dict(real=real, fake=fake, taker=float(O["q"].sum()))


def h12(day):
    O = pl.read_parquet(L.L22.OUT / "orders" / f"{day}.parquet", columns=["ts", "side", "S"]).rename({"ts": "t", "S": "q"}).sort("t").with_columns(pl.col("q").round(3))
    tot = float(O["q"].sum()); R, lab = St.runs(O); _, labs = St.runs(St.shuffled(O, seed=0))
    q = O["q"].to_numpy(); runs = [] if R is None else R.select("side", "q", "n", "gap_s", "cv", "start", "size").to_dicts()
    return dict(share=float(q[lab >= 0].sum() / tot), share_shuf=float(q[labs >= 0].sum() / tot), n_runs=len(runs), runs=runs)


def day_list():
    return sorted(p.stem for p in (L.L22.OUT / "orders").glob("*.parquet"))


def tests():
    """The out-of-sample tests, and the same numbers in sample as a description. H10, H12: bootstrap over days (2,000); H11: one-sided t over days, as fixed."""
    from scipy import stats
    rng = np.random.default_rng(0); D = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted(DAYS.glob("*.json"))}
    part = lambda a, b: [d for d in D if a <= d <= b]; R = {}
    for name, days in (("in", part(*L.L22.IN_SAMPLE)), ("out", part(*L.L22.OUT_SAMPLE))):
        o = dict(days=len(days)); k = [rng.integers(0, len(days), len(days)) for _ in range(2000)]
        def h10(idx, key="s"):
            a = {}
            for j in idx:
                for r in D[days[j]]["h10"]:
                    v = a.setdefault((r["cls"], r["sn"]), np.zeros(5)); v += (r["n"], r[key], r["size"], r["cost"], 1)
            cls = sorted({c for c, _ in a}); w = np.array([a[(c, True)][0] if (c, True) in a else 0 for c in cls]); w = w / w.sum()
            diff = np.array([a[(c, True)][1] / a[(c, True)][0] - a[(c, False)][1] / a[(c, False)][0] if (c, True) in a and (c, False) in a else 0 for c in cls])
            return float(w @ diff), dict(zip(cls, diff.tolist())), a
        st, by, a = h10(range(len(days))); bs = np.array([h10(i)[0] for i in k])
        n_sn = sum(v[0] for (c, sn), v in a.items() if sn); n_all = sum(v[0] for v in a.values())
        o["H10"] = dict(stat=st, p=float(np.mean(bs <= 0)), ci=np.percentile(bs, [2.5, 97.5]).tolist(), by_class=by, share_orders=n_sn / n_all,
                        share_size=sum(v[2] for (c, sn), v in a.items() if sn) / sum(v[2] for v in a.values()),
                        r1=h10(range(len(days)), "s1")[0], r60=h10(range(len(days)), "s60")[0],
                        cost={c: [a[(c, True)][3] / a[(c, True)][0], a[(c, False)][3] / a[(c, False)][0]] for c, _ in a if (c, True) in a and (c, False) in a},
                        what="net R(10 s) of sniper-like orders less other orders of the same size class, bp, classes weighted by sniper-like orders")
        for key in ("a", "x", "g", "s", "fund_a", "fund_x", "fund_g", "m5_a", "m5_g", "m15_a", "m15_g", "h_a", "h_g"):
            d = np.array([D[x]["h11"]["real"][key] - D[x]["h11"]["fake"][key] for x in days if D[x]["h11"]["real"][key] is not None])
            t = float(d.mean() / d.std(ddof=1) * np.sqrt(len(d))); o.setdefault("H11", {})[key] = dict(diff=float(d.mean()), t=t, p=float(stats.t.sf(t, len(d) - 1)), n=len(d))
        o["H11"]["taker_per_s"] = float(np.mean([D[x]["h11"]["taker"] for x in days]) / 86_400)
        d = np.array([D[x]["h12"]["share"] - D[x]["h12"]["share_shuf"] for x in days]); bs = np.array([d[i].mean() for i in k])
        runs = [r for x in days for r in D[x]["h12"]["runs"]]
        o["H12"] = dict(stat=float(d.mean()), p=float(np.mean(bs <= 0)), ci=np.percentile(bs, [2.5, 97.5]).tolist(), share=float(np.mean([D[x]["h12"]["share"] for x in days])),
                        share_shuf=float(np.mean([D[x]["h12"]["share_shuf"] for x in days])), daily=[[x, D[x]["h12"]["share"], D[x]["h12"]["share_shuf"]] for x in days], n_runs=len(runs),
                        near30=float(np.mean([abs(r["gap_s"] - 30.22) <= 1 for r in runs])) if runs else None,
                        size_near30=float(sum(r["size"] for r in runs if abs(r["gap_s"] - 30.22) <= 1) / max(sum(r["size"] for r in runs), 1e-9)))
        R[name] = o
    (L.RESULTS / "s3_tests.json").write_text(json.dumps(R, indent=1), encoding="utf-8"); return R


if __name__ == "__main__" and "--tests" in sys.argv:
    R = tests(); o = R["out"]
    print("H10", {k: o["H10"][k] for k in ("stat", "p", "ci", "share_orders", "share_size", "r1", "r60")}); print(" by class", o["H10"]["by_class"])
    print("H11", {k: (round(v["diff"], 4), round(v["t"], 2), round(v["p"], 4)) for k, v in o["H11"].items() if isinstance(v, dict)})
    print("H12", {k: o["H12"][k] for k in ("stat", "p", "ci", "share", "share_shuf", "n_runs", "near30", "size_near30")})
elif __name__ == "__main__":
    import time
    for d in [a for a in sys.argv[1:] if not a.startswith("--")] or day_list():
        f = DAYS / f"{d}.json"
        if f.exists(): continue
        t0 = time.time(); r = dict(day=d, h12=h12(d)); r["h11"] = h11(d); r["h10"] = h10(d)
        f.write_text(json.dumps(r), encoding="utf-8"); print(d, f"{time.time() - t0:.0f} s", "runs share", round(r["h12"]["share"], 4), "shuffled", round(r["h12"]["share_shuf"], 4), flush=True)
