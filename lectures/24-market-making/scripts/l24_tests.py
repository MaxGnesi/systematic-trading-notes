"""Lecture 24's tests (results/hypotheses.md): each design against the baseline, result before the fee in bp of the value traded, all fills of the 24
out-of-sample days pooled; bootstrap over days (2,000), one-sided; Benjamini-Hochberg at 5% over H1 to H4. Writes results/tests.json.
Value traded by taker exits is read from the fills (L24_OUT/fills), so that the result after fees can charge maker and taker fills their own fee."""
import json, sys
from pathlib import Path
import numpy as np, polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l24 as L
TESTS = {"H1": "guard_2", "H2": "as_5_1", "H3": "behind_1", "H4": "pp_e0_c110_n2"}
MAKER, TAKER = 2.0, 5.5                                                                            # bp, Bybit's standard tier (checked at source before quoting)


def load():
    rows = []
    for f in sorted((L.RESULTS / "days").glob("*.json")):
        d = f.stem; S = json.loads(f.read_text(encoding="utf-8"))
        F = pl.read_parquet(L.OUT / "fills" / f"{d}.parquet").with_columns((pl.col("p") * 0.1 * L.SIZE).alias("v"))   # ticks -> USDT, 0.001 BTC
        tv = dict(F.filter(pl.col("taker")).group_by("design").agg(pl.col("v").sum()).iter_rows())
        for k, s in S.items():
            rows.append({"day": d, "design": k, "res": s["result_usdt"], "val": s["value_usdt"], "taker_val": tv.get(k, 0.0), "fills": s["fills"],
                         "taker": s["taker"], "mk10": s["mk10"], "max_pos": s["max_pos"]})
    return pl.DataFrame(rows)


def pooled(res, val, idx):
    return 1e4 * res[:, idx].sum(1) / val[:, idx].sum(1)


if __name__ == "__main__":
    T = load(); days = sorted(T["day"].unique()); n = len(days); rng = np.random.default_rng(24); B = rng.integers(0, n, (2000, n))
    def arr(k, c): return T.filter(pl.col("design") == k).sort("day")[c].to_numpy()
    out = {"days": n, "designs": {}, "tests": {}}
    for k in T["design"].unique().sort():
        r, v, tv = arr(k, "res"), arr(k, "val"), arr(k, "taker_val")
        fee = MAKER * (v - tv) / 1e4 + TAKER * tv / 1e4
        out["designs"][k] = {"result_bp": 1e4 * r.sum() / v.sum(), "after_fee_usdt_day": float((r - fee).sum() / n), "fills_hour": float(arr(k, "fills").sum() / n / 24),
                             "taker_share": float(arr(k, "taker").sum() / arr(k, "fills").sum()), "taker_value_share": float(tv.sum() / v.sum()),
                             "value_usdt_day": float(v.sum() / n), "days_above_baseline": None,
                             "per_day_bp": dict(zip(days, (1e4 * r / v).tolist()))}
    rb, vb = arr("baseline", "res"), arr("baseline", "val")
    for h, k in TESTS.items():
        r, v = arr(k, "res"), arr(k, "val")
        diff = 1e4 * r.sum() / v.sum() - 1e4 * rb.sum() / vb.sum()
        boot = (1e4 * r[B].sum(1) / v[B].sum(1)) - (1e4 * rb[B].sum(1) / vb[B].sum(1))
        p = float((np.sum(boot - diff >= diff) + 1) / (len(boot) + 1))                             # one-sided, the bootstrap centred on the null
        out["tests"][h] = {"design": k, "diff_bp": float(diff), "ci90": np.percentile(boot, [5, 95]).tolist(), "p": p,
                           "days_above": int((1e4 * r / v > 1e4 * rb / vb).sum())}
        out["designs"][k]["days_above_baseline"] = out["tests"][h]["days_above"]
    ps = sorted((t["p"], h) for h, t in out["tests"].items()); m = len(ps); ok = 0
    for i, (p, h) in enumerate(ps, 1):
        if p <= 0.05 * i / m: ok = i
    for i, (p, h) in enumerate(ps, 1): out["tests"][h]["bh_holds"] = i <= ok
    (L.RESULTS / "tests.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    for k, s in out["designs"].items():
        print(f"{k:16s} {s['result_bp']:+.3f} bp  {s['after_fee_usdt_day']:+9.0f} USDT/day  {s['fills_hour']:6.0f} fills/h  taker {s['taker_share']:.0%}")
    for h, t in out["tests"].items():
        print(h, t["design"], f"{t['diff_bp']:+.3f}", [round(x, 3) for x in t["ci90"]], f"p={t['p']:.4f}", t["days_above"], "/", n, "BH" if t["bh_holds"] else "-")
