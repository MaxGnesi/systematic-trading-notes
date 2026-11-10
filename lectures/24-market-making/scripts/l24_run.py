"""Lecture 24: every design of results/hypotheses.md through whole days, all designs in one pass over each book window. Output per day: L24_OUT/fills/DAY.parquet
(the fills of every design, with a column design) and L24_RESULTS/days/DAY.json (each design's measures, l24_engine.score). A day already done is skipped.
Usage: python l24_run.py [DAY ...] (default: every day with a book state, in-sample days first)."""
import json, sys, time
from pathlib import Path
import polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l24 as L
import l24_engine as E, l24_designs as G
FILLS = L.OUT / "fills"; DAYS = L.RESULTS / "days"
SAMPLE_IN = ("2025-09-21", "2025-09-24", "2025-09-27", "2025-09-30", "2025-10-03", "2025-10-06")
SAMPLE_OUT = ("2025-10-13", "2025-10-17", "2025-10-21", "2025-10-25", "2025-10-29", "2025-11-02")
WINDOWS = (4, 5, 16, 17, 28, 29, 40, 41)                                                        # 02:00, 08:00, 14:00, 20:00 UTC, one hour each


def designs():
    return ([G.Quoter()] + [G.Quoter(theta=t) for t in (1, 2, 3, 5)] + [G.Quoter(k=k) for k in (1, 2, 5, 110)] + G.grid_as() + G.grid_pingpong())


if __name__ == "__main__":
    sample = "--sample" in sys.argv; only = next((a.split("=", 1)[1].split(",") for a in sys.argv if a.startswith("--designs=")), None)
    days = [a for a in sys.argv[1:] if not a.startswith("--")] or (list(SAMPLE_IN + SAMPLE_OUT) if sample else sorted(p.stem for p in L.L21.STATE.glob("*.parquet")))
    out, fills = (L.RESULTS / "sample_days", L.OUT / "sample_fills") if sample else (DAYS, FILLS)
    for p in (out, fills): p.mkdir(parents=True, exist_ok=True)
    for d in days:
        if (out / f"{d}.json").exists(): continue
        D = [x for x in designs() if only is None or x.name in only]; t0 = time.time()
        R, A = E.run_days(d, D, windows=WINDOWS if sample else None)
        pl.concat([f.with_columns(pl.lit(k).alias("design")) for k, f in R.items()]).write_parquet(fills / f"{d}.parquet")
        (out / f"{d}.json").write_text(json.dumps({k: E.score(f, A, B=E.blocks(d, WINDOWS if sample else None)) for k, f in R.items()}), encoding="utf-8")
        print(d, f"{time.time() - t0:.0f} s", len(D), "designs", flush=True)
