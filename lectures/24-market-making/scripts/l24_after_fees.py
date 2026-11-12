"""Lecture 24, every design after fees: the 85 variants on the sampled hours (four hours a day, 6 in-sample and 6 out-of-sample days), maker fills at
2 bp and taker fills at 5.5 bp, the taker value read from the fills. Ping-pong from the runs after the ledger fix only. Output: results/after_fees.json."""
import json, sys
from pathlib import Path
import polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l24 as L
from l24_tests import MAKER, TAKER
FIRST_OOS = "2025-10-11"


def rows():
    out = []
    for src, fdir in (("sample_days", "sample_fills"), ("sample_days_ledger", "sample_fills_ledger")):
        for f in sorted((L.RESULTS / src).glob("*.json")):
            d = f.stem; S = json.loads(f.read_text(encoding="utf-8"))
            F = pl.read_parquet(L.OUT / fdir / f"{d}.parquet").with_columns((pl.col("p") * 0.1 * L.SIZE).alias("v"))     # ticks -> USDT, 0.001 BTC
            tv = dict(F.filter(pl.col("taker")).group_by("design").agg(pl.col("v").sum()).iter_rows())
            for k, s in S.items():
                if not s.get("fills") or (k.startswith("pp_") and src != "sample_days_ledger"): continue    # ping-pong before the ledger fix: void
                out.append(dict(day=d, oos=d >= FIRST_OOS, design=k, res=s["result_usdt"], val=s["value_usdt"], tval=tv.get(k, 0.0), fills=s["fills"]))
    return pl.DataFrame(out)


if __name__ == "__main__":
    T = rows(); res = {}
    for (k, oos), g in T.group_by("design", "oos"):
        r, v, tv = g["res"].sum(), g["val"].sum(), g["tval"].sum(); fee = (MAKER * (v - tv) + TAKER * tv) / 1e4; hours = 4 * g.height
        res.setdefault(k, {})["oos" if oos else "in"] = dict(before_bp=1e4 * r / v, fee_bp=1e4 * fee / v, after_bp=1e4 * (r - fee) / v,
                                                             after_usdt_hour=(r - fee) / hours, fills_hour=g["fills"].sum() / hours, taker_value_share=tv / v)
    (L.RESULTS / "after_fees.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    for k, v in sorted(res.items(), key=lambda kv: -kv[1]["oos"]["after_usdt_hour"]):
        o, i = v["oos"], v["in"]
        print(f"{k:18s} oos: before {o['before_bp']:+.2f} fee {o['fee_bp']:.2f} after {o['after_bp']:+.2f} bp {o['after_usdt_hour']:+8.1f} USDT/h {o['fills_hour']:6.0f} fills/h taker {o['taker_value_share']:.0%} | in: after {i['after_usdt_hour']:+8.1f} USDT/h")
