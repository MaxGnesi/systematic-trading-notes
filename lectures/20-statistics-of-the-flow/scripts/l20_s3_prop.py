"""Lecture 20, H3: impact over time. Per day, Bybit taker orders in time order: signs e_i, sign autocorrelation C(l), response
R(l) = mean e_i (m_i+l - m_i) in ticks (m_i: mid just before order i), and the propagator G(l) solved by least squares from
R(l) = sum_n G(n) C(|n - l|) - sum_n G(n) C(n), lags 1..1000 (Bouchaud, Gefen, Potters and Wyart, 2004). Also the power-law exponent of C
on lags 10..1000. Output: L20_OUT/s3/prop.json (one entry per day). Usage: python l20_s3_prop.py [DAY ...]"""
import json, sys
from pathlib import Path
import numpy as np, polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l20 as L20

OUT = L20.S3
L = 1000
res = {}
for day in L20.day_list():
    O = pl.read_parquet(L20.ORD / f"bybit_{day}.parquet").drop_nulls("mid2").sort("ts")
    e = O["side"].to_numpy().astype(float); m = O["mid2"].to_numpy() / 2.0
    e0 = e - e.mean()
    C = np.array([1.0] + [np.mean(e0[:-l] * e0[l:]) / e0.var() for l in range(1, 2 * L + 1)])      # C[0..2L]
    R = np.array([np.mean(e[:-l] * (m[l:] - m[:-l])) for l in range(1, L + 1)])
    ell = np.arange(1, L + 1); n = np.arange(1, L + 1)
    A = C[np.abs(n[None, :] - ell[:, None])] - C[n][None, :]
    G = np.linalg.lstsq(A, R, rcond=None)[0]
    k = np.arange(10, L + 1); ok = C[k] > 0
    gam = float(-np.polyfit(np.log(k[ok]), np.log(C[k][ok]), 1)[0]) if ok.sum() > 10 else None
    res[day] = dict(n=len(e), C=C[:L + 1].round(5).tolist(), R=R.round(4).tolist(), G=G.round(4).tolist(), gamma=gam, c_pos=int((C[1:L + 1] > 0).sum()))
    print(day, len(e), "C1", round(C[1], 3), "C100", round(C[100], 3), "gamma", None if gam is None else round(gam, 2), "R1", round(R[0], 2),
          "R1000", round(R[-1], 2), "G1", round(G[0], 2), "G500", round(G[499], 3), flush=True)
(OUT / f"{L20.tag()}prop.json").write_text(json.dumps(res))
