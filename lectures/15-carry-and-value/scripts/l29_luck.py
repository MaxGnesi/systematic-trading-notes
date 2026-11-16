"""Lecture 15: luck baseline (plan, measure 4). For each strategy, N random strategies on the same markets: each market's sign follows a
two-state Markov chain switching with the same average holding period as the real strategy's sign in that market; positions built by the
same machinery (weights = signs / their sum within the group, vol-scaled, a tenth of the way each day, 5 bp, groups yearly at 10%, equal
risk, total yearly at 10%); each added to trend in the same way as the real strategy. Reported: the share of random strategies the real
strategy beats, on its own and in the combination with trend (Sharpe ratio, 2006 to 2022-11-18).
Usage: python l29_luck.py [N]"""
import sys, time
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l29 as L, l29_backtest as B


def holding(S):
    """Average run length (days) of each market's sign, on 2006-2022."""
    s = np.sign(S.loc[B.START:B.END]); out = {}
    for c in s:
        x = s[c].dropna(); x = x[x != 0]
        runs = (x != x.shift()).sum(); out[c] = len(x) / max(runs, 1)
    return pd.Series(out)


def markov(index, cols, hold, mask, rng):
    p = 1 / hold.reindex(cols).clip(lower=1).to_numpy(); n = len(index)
    flips = rng.random((n, len(cols))) < p; start = rng.choice([-1.0, 1.0], len(cols))
    sgn = start * np.where(np.cumsum(flips, axis=0) % 2 == 0, 1.0, -1.0)
    return pd.DataFrame(sgn, index, cols).where(mask)


if __name__ == "__main__":
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    R = B.returns(); carry, value, _ = L.signals()
    real = {"carry_rule": {g: (np.sign(L.smooth(carry[g])) if g == "equity" else L.carry_signal(carry[g])) for g in carry},
            "value_rule": {g: L.rank_centred(value[g]) for g in value}}
    S = pd.read_parquet(L.RAW / "l29_streams.parquet"); trend = S["trend"]
    rng = np.random.default_rng(29); out = {}
    for name, sig in real.items():
        hold = {g: holding(sig[g]) for g in sig}
        print(name, "average holding (days):", {g: int(h.mean()) for g, h in hold.items()}, flush=True)
        comb_real = B.yearly_scale(pd.concat([trend, S[name]], axis=1).mean(axis=1)).loc[B.START:B.END]
        alone, comb, t0 = [], [], time.time()
        for i in range(N):
            groups = {g: B.group_stream(markov(sig[g].index, sig[g].columns, hold[g], sig[g].notna(), rng), R[g][sig[g].columns]) for g in sig}
            tot, _ = B.strategy(groups); tot = tot.reindex(S.index)
            alone.append(B.sharpe(tot)); comb.append(B.sharpe(B.yearly_scale(pd.concat([trend, tot], axis=1).mean(axis=1)).loc[B.START:B.END]))
            if i == 9: print(f"  10 runs in {time.time() - t0:.0f}s", flush=True)
        alone, comb = np.array(alone), np.array(comb)
        ra, rc = B.sharpe(S[name]), B.sharpe(comb_real)
        out[name] = dict(alone=ra, alone_beaten=float((alone < ra).mean()), alone_p95=float(np.percentile(alone, 95)), alone_median=float(np.median(alone)),
                         comb=rc, comb_beaten=float((comb < rc).mean()), comb_p95=float(np.percentile(comb, 95)), comb_median=float(np.median(comb)))
        print(f"  {name}: alone {ra:+.2f} beats {out[name]['alone_beaten']:.0%} of random (median {np.median(alone):+.2f}, 95th {np.percentile(alone, 95):+.2f}); "
              f"with trend {rc:+.2f} beats {out[name]['comb_beaten']:.0%} (median {np.median(comb):+.2f}, 95th {np.percentile(comb, 95):+.2f})", flush=True)
    pd.DataFrame(out).to_csv(L.RAW / f"l29_luck_{N}.csv")
