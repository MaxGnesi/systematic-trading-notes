"""Lecture 24, does a faster maker lose less? (described, not tested): the baseline and Avellaneda-Stoikov (kappa 5, c 2) on the sampled hours with the
order-entry latency L at 5, 10, 25 and 50 ms. Decisions still see the recorded book, published every 100 ms, and the trades, to the millisecond, so this
measures the speed of our orders, not of our view. Output: results/latency.json."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l24 as L
import l24_engine as E, l24_designs as G
from l24_after_fees import FIRST_OOS
from l24_lean_check import DAYS
LATS = (5, 10, 25, 50)

if __name__ == "__main__":
    out = json.loads((L.RESULTS / "latency.json").read_text(encoding="utf-8")) if (L.RESULTS / "latency.json").exists() else {}
    for d in DAYS:
        if d in out: continue
        A = E.Arrays(d); B = E.blocks(d, (4, 5, 16, 17, 28, 29, 40, 41)); out[d] = {}
        for lat in LATS:
            R, _ = E.run_days(d, [G.Quoter(), G.AS(5, 2)], lat=lat, A=A, windows=(4, 5, 16, 17, 28, 29, 40, 41))
            out[d][str(lat)] = {k: E.score(f, A, B=B) for k, f in R.items()}
            print(d, lat, {k: round(v["result_bp"], 3) for k, v in out[d][str(lat)].items()}, flush=True)
        del A; (L.RESULTS / "latency.json").write_text(json.dumps(out), encoding="utf-8")
