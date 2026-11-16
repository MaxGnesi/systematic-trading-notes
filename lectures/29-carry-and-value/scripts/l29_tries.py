"""Lecture 29 §6 (plan entry of 2026-11-16): the number of tries. Every carry configuration tried in this lecture, rebuilt on the futures period
(monthly, 2006 to October 2022): the robustness grid, the hedges, the value tilts, the best-row combinations and the mixes. From their monthly
returns: each Sharpe ratio, their average pairwise correlation, the effective number of independent tries N_eff = rho + (1 - rho) M
(Lopez de Prado), and the deflated Sharpe ratio of the rule (Bailey and Lopez de Prado 2014):
    SR0 = sqrt(V[SR]) * ((1 - g) Phi^-1(1 - 1/N) + g Phi^-1(1 - 1/(N e))),  g = 0.5772 (Euler-Mascheroni),
    DSR = Phi((SR - SR0) sqrt(T - 1) / sqrt(1 - skew SR + (kurt - 1) / 4 SR^2)),  SR per month.
Output: results/tries.json."""
import json, os, sys
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import norm
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); import l29_combined as M, l29_grids as Gr, l29_bonds_g10 as G
RESD = Path(os.environ.get("L29_RESULTS", HERE.parent / "results")); RESD.mkdir(parents=True, exist_ok=True)
A, B = "2006-01", "2022-10"


def dsr(r, trials):
    """Deflated Sharpe ratio of monthly returns r, given the monthly Sharpe ratios of all trials and N (effective)."""
    sr_all, n = trials
    r = r.dropna(); T = len(r); sr = r.mean() / r.std(); sk = r.skew(); ku = r.kurt() + 3
    g = 0.5772156649; v = np.var(sr_all, ddof=1)
    sr0 = np.sqrt(v) * ((1 - g) * norm.ppf(1 - 1 / n) + g * norm.ppf(1 - 1 / (n * np.e)))
    z = (sr - sr0) * np.sqrt(T - 1) / np.sqrt(1 - sk * sr + (ku - 1) / 4 * sr ** 2)
    return dict(sr_month=float(sr), sr0_month=float(sr0), sr0_annual=float(sr0 * np.sqrt(12)), dsr=float(norm.cdf(z)), T=T, skew=float(sk), kurt=float(ku))


if __name__ == "__main__":
    Gs = M.groups(); V5 = M.value5(Gs)
    def tot(W, vm=36): return M.scale_total(pd.DataFrame({g: G.stream(W[g], Gs[g]["R"], vm) for g in Gs}).mean(axis=1, skipna=True))
    def sig(level=True, change=3): return {g: Gr.sig(Gs[g]["C"], Gs[g]["R"], level, change) for g in Gs}
    def hedged(W, a): return {g: (Gr.hedge(W[g], Gs[g]["R"], a) if g in ("fx", "commod") else W[g]) for g in Gs}
    rule = sig(); rank = {g: (G.rank_centred(Gs[g]["C"]) + G.rank_centred(Gs[g]["C"] - Gs[g]["C"].shift(3))) / 2 for g in Gs}
    own = {g: np.sign(Gs[g]["C"]) for g in Gs}
    T = {"rule": tot(rule), "sizing 12m": tot(rule, 12), "sizing 60m": tot(rule, 60), "level only": tot(sig(True, 0)), "change only": tot(sig(False, 3)),
         "level + 1m change": tot(sig(True, 1)), "level + 6m change": tot(sig(True, 6)), "rank": tot(rank), "own sign": tot(own),
         "hedge 0": tot(hedged(rule, 0)), "hedge 1/2": tot(hedged(rule, 0.5)), "hedge 1": tot(hedged(rule, 1))}
    for w in (0.25, 0.5, 1): T[f"value tilt {w}"] = tot(M.tilted(Gs, w, V5))
    s6 = sig(True, 6)
    T["6m + hedge 1/2"] = tot(hedged(s6, 0.5)); T["6m + hedge 0"] = tot(hedged(s6, 0)); T["6m + 12m vol"] = tot(s6, 12); T["6m + hedge 1/2 + 12m vol"] = tot(hedged(s6, 0.5), 12)
    D = pd.DataFrame(T).loc[A:B]
    D["mix of 5"] = M.scale_total(D[["rule", "sizing 12m", "level + 6m change", "rank", "hedge 1/2"]].mean(axis=1)).reindex(D.index)
    D["average of 11"] = M.scale_total(D[["rule", "sizing 12m", "sizing 60m", "level only", "change only", "level + 1m change", "level + 6m change", "rank",
                                          "hedge 0", "hedge 1/2", "hedge 1"]].mean(axis=1)).reindex(D.index)
    D = D.dropna(); Mn = D.shape[1]
    C = D.corr().to_numpy(); rho = float(C[np.triu_indices(Mn, 1)].mean()); n_eff = rho + (1 - rho) * Mn
    srm = (D.mean() / D.std()).to_numpy()
    out = dict(tries=Mn, avg_corr=rho, n_eff=n_eff, sharpe={k: float(v * np.sqrt(12)) for k, v in zip(D.columns, srm)},
               rule=dsr(D["rule"], (srm, n_eff)), rule_if_all_independent=dsr(D["rule"], (srm, Mn)),
               best=str(D.columns[np.argmax(srm)]), best_sharpe=float(srm.max() * np.sqrt(12)))
    print(json.dumps({k: v for k, v in out.items() if k != "sharpe"}, indent=1))
    print("Sharpe ratios:", {k: round(v, 2) for k, v in sorted(out["sharpe"].items(), key=lambda x: -x[1])})
    (RESD / "tries.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
