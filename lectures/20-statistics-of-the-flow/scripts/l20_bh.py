"""Lecture 20: Benjamini-Hochberg at 5% over H1-H9 (parts counted separately). A bootstrap p of 0 is set to 1/2001 (no resample at or
below the null). Inputs: L20_OUT/s3/stats.json, L20_OUT/s4/stats.json. Output: L20_OUT/s4/bh.json."""
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l20 as L20
A = json.loads((L20.S3 / "stats.json").read_text()); B = json.loads((L20.S4 / "stats.json").read_text())
p = {k[:-2]: max(A[k], 1 / 2001) for k in A if k.endswith("_p")}
p.update({k[:-2]: B[k] for k in ("H8a_p", "H8b_p", "H9a_p", "H9b_p", "H9c_p")})
m, q = len(p), 0.05
order = sorted(p, key=p.get); k_max = max([i + 1 for i, h in enumerate(order) if p[h] <= (i + 1) / m * q], default=0)
out = {h: dict(p=p[h], rank=i + 1, threshold=(i + 1) / m * q, holds=i < k_max) for i, h in enumerate(order)}
(L20.S4 / "bh.json").write_text(json.dumps(out))
for h, v in out.items(): print(f"{h:4s} p {v['p']:.4f}  rank {v['rank']:2d}  threshold {v['threshold']:.4f}  {'HOLDS' if v['holds'] else 'fails'}")
