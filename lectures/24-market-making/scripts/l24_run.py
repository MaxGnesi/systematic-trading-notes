"""Lecture 24: every design of results/hypotheses.md through whole days, all designs in one pass over each book window. Output per day: L24_OUT/fills/DAY.parquet
(the fills of every design, with a column design) and L24_RESULTS/days/DAY.json (each design's measures, l24_engine.score). A day already done is skipped.
Usage: python l24_run.py [DAY ...] (default: every day with a book state, in-sample days first)."""
import json, sys, time
from pathlib import Path
import polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l24 as L
import l24_engine as E, l24_designs as G
FILLS = L.OUT / "fills"; DAYS = L.RESULTS / "days"
for p in (FILLS, DAYS): p.mkdir(parents=True, exist_ok=True)


def designs():
    return ([G.Quoter()] + [G.Quoter(theta=t) for t in (1, 2, 3, 5)] + [G.Quoter(k=k) for k in (1, 2, 5, 110)] + G.grid_as() + G.grid_pingpong())


if __name__ == "__main__":
    days = [a for a in sys.argv[1:] if not a.startswith("--")] or sorted(p.stem for p in L.L21.STATE.glob("*.parquet"))
    days = sorted(days, key=lambda d: (not (L.IN_SAMPLE[0] <= d <= L.IN_SAMPLE[1]), d))
    for d in days:
        if (DAYS / f"{d}.json").exists(): continue
        t0 = time.time(); D = designs(); R, A = E.run_days(d, D)
        pl.concat([f.with_columns(pl.lit(k).alias("design")) for k, f in R.items()]).write_parquet(FILLS / f"{d}.parquet")
        (DAYS / f"{d}.json").write_text(json.dumps({k: E.score(f, A) for k, f in R.items()}), encoding="utf-8")
        print(d, f"{time.time() - t0:.0f} s", len(D), "designs", flush=True)
