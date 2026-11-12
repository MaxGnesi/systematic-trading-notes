"""Lecture 24's key chart: where a market maker's money goes. For the five tested designs on the 24 out-of-sample days, each fill's result split into the
spread earned (the mid just before the fill less the fill price, signed for our side), the move of the mid against us in the first second and from 1 to
10 s, the gain or loss on positions held beyond 10 s (the rest of the day's result), and fees (2 bp maker, 5.5 bp taker). Output: results/key.json."""
import json, sys
from pathlib import Path
import numpy as np, polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l24 as L
import l24_engine as E
from l24_tests import TESTS, MAKER, TAKER
USDT = 0.1 * L.SIZE                                                                                # ticks x lots -> USDT
DESIGNS = ["baseline"] + list(TESTS.values())
SRC = (("days", "fills"), ("days_corr", "fills_corr"), ("days_ledger", "fills_ledger"))


if __name__ == "__main__":
    days = sorted(p.stem for p in (L.RESULTS / "days").glob("*.json")); acc = {d: dict(spread=0.0, move_1s=0.0, move_10s=0.0, positions=0.0, fees=0.0,
                                                                                     result=0.0, value=0.0, fills=0) for d in DESIGNS}
    for day in days:
        S = pl.read_parquet(E.L21.STATE / f"{day}.parquet", columns=["ts", "bid", "ask"]).sort("ts")
        ts = S["ts"].to_numpy(); mid = ((S["bid"] + S["ask"]) / 2).to_numpy(); del S
        at = lambda t, side="right": mid[np.maximum(np.searchsorted(ts, t, side=side) - 1, 0)]
        for res_dir, fill_dir in SRC:
            R = json.loads((L.RESULTS / res_dir / f"{day}.json").read_text(encoding="utf-8")); F = pl.read_parquet(L.OUT / fill_dir / f"{day}.parquet")
            for d in F["design"].unique().to_list():
                if d not in DESIGNS or (d.startswith("pp_") and res_dir != "days_ledger"): continue      # ping-pong before the ledger fix: void
                D = F.filter(pl.col("design") == d); t, s, p, tk = D["t"].to_numpy(), D["s"].to_numpy(), D["p"].to_numpy(), D["taker"].to_numpy()
                m0 = at(t, "left"); m1, m10 = at(t + 1_000), at(t + 10_000)                         # the mid just before the fill, after 1 s and 10 s
                a = acc[d]; sp, v1, v10 = (s * (m0 - p)).sum(), (s * (m1 - m0)).sum(), (s * (m10 - m1)).sum()
                a["spread"] += sp * USDT; a["move_1s"] += v1 * USDT; a["move_10s"] += v10 * USDT
                a["positions"] += R[d]["result_usdt"] - (sp + v1 + v10) * USDT; a["result"] += R[d]["result_usdt"]
                a["fees"] -= (p * np.where(tk, TAKER, MAKER) / 1e4).sum() * USDT; a["value"] += R[d]["value_usdt"]; a["fills"] += len(t)
        del ts, mid; print(day, flush=True)
    out = {d: {**a, **{k + "_bp": 1e4 * a[k] / a["value"] for k in ("spread", "move_1s", "move_10s", "positions", "fees", "result")}} for d, a in acc.items()}
    for a in out.values(): a["after_fee_bp"] = a["result_bp"] + a["fees_bp"]
    (L.RESULTS / "key.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    for d, a in out.items():
        print(f"{d:16s} spread {a['spread_bp']:+.3f} 1s {a['move_1s_bp']:+.3f} 10s {a['move_10s_bp']:+.3f} pos {a['positions_bp']:+.3f} = {a['result_bp']:+.3f}; fees {a['fees_bp']:+.2f}; after {a['after_fee_bp']:+.2f}")
