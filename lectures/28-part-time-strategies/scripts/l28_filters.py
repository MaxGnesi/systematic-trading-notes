"""Lecture 28, §2-§4: the filters as switches, as fixed in results/hypotheses.md. Each filter sets the baseline's target scale to 0 (off) or 1 (on)
from regimes known the day before; the scale moves a tenth of the way each day and every change costs 5 bp of the gross exposure moved.
Luck baseline: 1,000 random filters per filter and dataset with the same share of time off and the same average length of off and on spells
(a two-state Markov chain), attached the same way. Verdict: beats at least 90% of its random filters on the ETFs and on the futures, and the
larger of its two p-values passes Benjamini-Hochberg at 10% within its family. Threshold grid reported for robustness.
Output: results/filters.json, figures/28_filters.png."""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
from numba import njit
from plotly.subplots import make_subplots
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l28 as L
from trading_models.plotting import INK, MUTED, SERIES, apply_theme, save_figure
L26 = L.L26; NRAND = 1000
LEVELS = {"still": ("0.25", "0.33", "0.50"), "busy": ("0.75", "0.67", "0.50")}; FIXED = 1
KIND = {"growth": "still", "inflation": "still", "volatility": "still", "curve": "still", "dollar": "still", "correlation": "busy", "turning": "busy"}
FAMILIES = {"macro": ["growth", "inflation", "fed", "macro composite"],
            "market state": ["volatility", "correlation", "turning", "curve", "dollar", "market composite"],
            "both": ["both agree", "either"]}
NAMES = {"growth": "Growth still", "inflation": "Inflation still", "fed": "Fed on hold", "macro composite": "Macro composite",
         "volatility": "Volatility low", "correlation": "Correlation high", "turning": "Many turning points", "curve": "Yield curve still",
         "dollar": "Dollar still", "market composite": "Market-state composite", "both agree": "Both composites off", "either": "Either composite off"}


def offs(G, level):
    """Off flags (True = off) of every filter at one level of the threshold grid; NaN (no threshold yet) counts as on."""
    f = {k: G[(k, LEVELS[KIND[k]][level])].astype(float).fillna(0).astype(bool) for k in KIND}
    f["fed"] = G[("fed", "hold")].astype(float).fillna(0).astype(bool)
    f["macro composite"] = (f["growth"].astype(int) + f["inflation"].astype(int) + f["fed"].astype(int)) >= 2
    f["market composite"] = sum(f[k].astype(int) for k in ("volatility", "correlation", "turning", "curve", "dollar")) >= 3
    f["both agree"] = f["macro composite"] & f["market composite"]; f["either"] = f["macro composite"] | f["market composite"]
    return pd.DataFrame(f)


@njit(cache=True)
def switched(ret, gross, off, lam, cost):
    n = len(ret); s = 1.0; out = np.empty(n)
    for t in range(n):
        new = s + lam * ((0.0 if off[t] else 1.0) - s)
        out[t] = new * ret[t] - cost * abs(new - s) * gross[t]; s = new
    return out


@njit(cache=True)
def sharpe(x):
    m = x.mean(); sd = x.std()
    return m / sd * np.sqrt(252.0) if sd > 0 else 0.0


@njit(cache=True)
def random_sharpes(ret, gross, p_off_to_on, p_on_to_off, share_off, n, seed, lam, cost):
    np.random.seed(seed); out = np.empty(n); T = len(ret); off = np.empty(T, dtype=np.bool_)
    for i in range(n):
        st = np.random.random() < share_off
        for t in range(T):
            off[t] = st
            if st:
                if np.random.random() < p_off_to_on: st = False
            elif np.random.random() < p_on_to_off: st = True
        out[i] = sharpe(switched(ret, gross, off, lam, cost))
    return out


def spells(b):
    """Mean length of off spells and of on spells."""
    x = b.astype(int).to_numpy(); ch = np.flatnonzero(np.diff(x)) + 1; seg = np.split(x, ch)
    lo = [len(s) for s in seg if s[0] == 1]; ln = [len(s) for s in seg if s[0] == 0]
    return (np.mean(lo) if lo else np.inf), (np.mean(ln) if ln else np.inf)


def measures(r, base, off):
    w = (1 + r).cumprod(); mo = r.index.to_period("M"); worst = base.groupby(mo).sum().nsmallest(12).index
    X = np.column_stack([np.ones(len(r)), base.to_numpy()]); beta, res = np.linalg.lstsq(X, r.to_numpy(), rcond=None)[:2]
    resid = r.to_numpy() - X @ beta; se = np.sqrt(resid.var(ddof=2) / len(r))
    return dict(sharpe=L26.sharpe(r), sharpe_on=L26.sharpe(base[~off]) if (~off).sum() > 20 else np.nan, vol=float(r.std() * np.sqrt(252)),
                drawdown=float((w / w.cummax() - 1).min()), worst12=float(r[mo.isin(worst)].sum()), share_on=float(1 - off.mean()),
                switches_a_year=float(off.astype(int).diff().abs().sum() / (len(off) / 252)), alpha=float(beta[0] * 252), alpha_t=float(beta[0] / se))


def bh(p, q=0.10):
    p = pd.Series(p).sort_values(); m = len(p); ok = p.to_numpy() <= q * np.arange(1, m + 1) / m
    k = np.flatnonzero(ok).max() + 1 if ok.any() else 0; return {i: bool(j < k) for j, i in enumerate(p.index)}


if __name__ == "__main__":
    apply_theme(); B = pd.read_parquet(L.OUT / "l28_base.parquet"); out = {"datasets": {}}; lam, cost = L.LAMBDA, L.COST_BP / 1e4
    for di, (tag, start) in enumerate((("etf", L.ETF_START), ("futures", L.FUT_START))):
        base = B[tag].dropna().loc[start:L.END[tag]]; G = pd.read_parquet(L.OUT / f"l28_regimes_{tag}.parquet").reindex(base.index)
        ret, gross = base.ret.to_numpy(), base.gross.to_numpy(); res = {"baseline": measures(base.ret, base.ret, pd.Series(False, base.index))}
        for lev in range(3):
            F = offs(G, lev)
            for k in F:
                off = F[k]; r = pd.Series(switched(ret, gross, off.to_numpy(), lam, cost), base.index); m = measures(r, base.ret, off)
                if lev == FIXED:
                    lo, ln = spells(off); sh = random_sharpes(ret, gross, 1 / lo if np.isfinite(lo) else 1.0, 1 / ln if np.isfinite(ln) else 0.0,
                                                               float(off.mean()), NRAND, 20261115 + di, lam, cost)
                    m.update(random_median=float(np.median(sh)), random_p95=float(np.quantile(sh, .95)), beaten=float((m["sharpe"] > sh).mean()),
                             spell_off=float(lo), spell_on=float(ln))
                res.setdefault(k, {})[LEVELS[KIND.get(k, "still")][lev] if k in KIND else ("quarter", "third", "half")[lev]] = m
        out["datasets"][tag] = res
        print(tag, "baseline", round(res["baseline"]["sharpe"], 3), flush=True)
        for k in F:
            m = res[k][LEVELS[KIND[k]][FIXED] if k in KIND else "third"]
            print(f"  {NAMES[k]:24s} on {m['share_on']:.0%} SR {m['sharpe']:+.2f} (on-days {m['sharpe_on']:+.2f}) random median {m['random_median']:+.2f} p95 {m['random_p95']:+.2f} beaten {m['beaten']:.0%} "
                  f"alpha {m['alpha']:+.2%} (t {m['alpha_t']:+.1f}) dd {m['drawdown']:.1%} switches {m['switches_a_year']:.1f}/yr | grid SR " +
                  " ".join(f"{v['sharpe']:+.2f}" for v in res[k].values()), flush=True)
    fx = lambda k: LEVELS[KIND[k]][FIXED] if k in KIND else "third"
    out["verdict"] = {}
    for fam, ks in FAMILIES.items():
        p = {k: max(1 - out["datasets"][t][k][fx(k)]["beaten"] for t in ("etf", "futures")) for k in ks}; ok = bh(p)
        out["verdict"][fam] = {k: dict(p=p[k], beats90_both=all(out["datasets"][t][k][fx(k)]["beaten"] >= 0.9 for t in ("etf", "futures")), bh=ok[k],
                                       works=bool(ok[k] and all(out["datasets"][t][k][fx(k)]["beaten"] >= 0.9 for t in ("etf", "futures")))) for k in ks}
    print(json.dumps(out["verdict"], indent=1))
    (L.RESULTS / "filters.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    # chart: l28_charts.py
