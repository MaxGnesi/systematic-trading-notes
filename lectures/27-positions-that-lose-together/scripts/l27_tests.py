"""Lecture 27, the measures fixed in results/hypotheses.md, out of sample 2013-2026 (OUT/l27_daily.parquet from l27.py):
1. Sharpe ratio after costs; 2. worst drawdown and the loss over the rule's 12 worst months; 3. risk forecast: realised volatility of each month
over the 10% target (mean and spread). Each rival against the rule by block bootstrap over calendar months (2,000 resamples, 90% bands, two-sided
p); Benjamini-Hochberg at 5% over the two rivals (position-aware, Ward groups) and three measures. Output: results/tests.json."""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l27 as M
sharpe = M.L26.sharpe


def drawdown(x):
    v = (1 + x).cumprod(); return float((v / v.cummax() - 1).min())


def worst12(x, months, worst):
    return float(x[months.isin(worst)].sum())


def risk_spread(x, months):
    m = x.groupby(months).std() * np.sqrt(252) / M.TARGET; return float(m.std())


if __name__ == "__main__":
    D = pd.read_parquet(M.OUT / "l27_daily.parquet"); months = D.index.to_period("M"); um = months.unique(); rng = np.random.default_rng(20261113)
    V = ("rule", "aware", "ward", "groups"); worst = D.rule.groupby(months).sum().nsmallest(12).index
    out = {"measures": {}, "monthly_risk": {}, "tests": {}}
    for v in V:
        m = D[v].groupby(months).std() * np.sqrt(252) / M.TARGET
        out["measures"][v] = dict(sharpe=sharpe(D[v]), vol=float(D[v].std() * np.sqrt(252)), drawdown=drawdown(D[v]), worst12=worst12(D[v], months, worst),
                                  risk_mean=float(m.mean()), risk_spread=float(m.std()))
        out["monthly_risk"][v] = {str(k): float(x) for k, x in m.items()}
    idx_of = {u: np.where(months == u)[0] for u in um}
    fns = {"sharpe": lambda x, mo: sharpe(x), "drawdown": lambda x, mo: drawdown(x), "risk_spread": lambda x, mo: -risk_spread(x, mo)}   # higher is better
    for v in ("aware", "ward", "groups"):
        for k, f in fns.items():
            d0 = f(D[v], months) - f(D.rule, months); boots = []
            for _ in range(2000):
                pick = rng.choice(len(um), len(um)); idx = np.concatenate([idx_of[um[i]] for i in pick]); Db = D.iloc[idx]; mb = np.repeat(np.arange(len(pick)), [len(idx_of[um[i]]) for i in pick])   # resampled month labels
                boots.append(f(Db[v].reset_index(drop=True), mb) - f(Db.rule.reset_index(drop=True), mb))
            b = np.array(boots); p = float(min(1.0, 2 * min((b <= 0).mean(), (b >= 0).mean())))
            out["tests"][f"{v}_{k}"] = dict(diff=float(d0), ci90=[float(np.quantile(b, .05)), float(np.quantile(b, .95))], p_two_sided=p)
        print(v, "done", flush=True)
    fam = [f"{v}_{k}" for v in ("aware", "ward") for k in fns]; p = pd.Series({t: out["tests"][t]["p_two_sided"] for t in fam}).sort_values(); n = len(p)
    ok = [i for i in range(n) if p.iloc[i] <= 0.05 * (i + 1) / n]; k = max(ok) + 1 if ok else 0     # step-up: reject the k smallest p-values
    out["bh"] = {t: i < k for i, t in enumerate(p.index)}
    (M.RESULTS / "tests.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(pd.DataFrame(out["measures"]).round(3).to_string()); print(pd.DataFrame(out["tests"]).T.round(3).to_string()); print("BH:", out["bh"])
