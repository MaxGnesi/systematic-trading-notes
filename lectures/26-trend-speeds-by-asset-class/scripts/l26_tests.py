"""Lecture 26, out-of-sample tests 2013-2026 (OUT/oos.parquet from l26_select.py): Sharpe ratio after costs and worst drawdown per variant and class;
differences of the rule (per class, size-weighted votes) against each comparison by block bootstrap over months (2,000 resamples of calendar months), one-sided; Benjamini-Hochberg at 5% over
the five classes for the rule against the shared set. Output: results/tests.json."""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l26 as L

if __name__ == "__main__":
    O = pd.read_parquet(L.OUT / "oos.parquet"); rng = np.random.default_rng(20261113); cols = list(L.CLASSES) + ["total"]
    V = {v: g.drop(columns="variant") for v, g in O.groupby("variant")}
    dd = lambda x: float(((1 + x).cumprod() / (1 + x).cumprod().cummax() - 1).min())
    out = {"sharpe": {v: {c: L.sharpe(V[v][c]) for c in cols} for v in V}, "drawdown": {v: {c: dd(V[v][c]) for c in cols} for v in V}, "tests": {}}
    months = V["class"].index.to_period("M"); um = months.unique()
    for v in ("shared", "class_equal_vote", "all36", "intersection", "union"):
        for c in cols:
            a, b = V["class"][c], V[v][c]; d0 = L.sharpe(a) - L.sharpe(b); boots = []
            for _ in range(2000):
                pick = rng.choice(len(um), len(um)); idx = np.concatenate([np.where(months == um[i])[0] for i in pick])
                boots.append(L.sharpe(a.iloc[idx]) - L.sharpe(b.iloc[idx]))
            boots = np.array(boots); out["tests"][f"rule_vs_{v}_{c}"] = dict(diff=d0, p_rule_better=float((boots <= 0).mean()), p_other_better=float((boots >= 0).mean()),
                                                                                   ci90=[float(np.quantile(boots, .05)), float(np.quantile(boots, .95))])
    p = pd.Series({c: out["tests"][f"rule_vs_shared_{c}"]["p_rule_better"] for c in L.CLASSES}).sort_values(); m = len(p)
    out["bh_rule_beats_shared"] = {c: bool(p.iloc[i] <= 0.05 * (i + 1) / m) for i, c in enumerate(p.index)}
    (L.RESULTS / "tests.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("Sharpe 2013-2026"); print(pd.DataFrame(out["sharpe"]).round(2).to_string()); print("worst drawdown"); print(pd.DataFrame(out["drawdown"]).round(3).to_string())
    print(pd.DataFrame(out["tests"]).T.round(3).to_string()); print("per-class rule beats shared after BH:", out["bh_rule_beats_shared"])
