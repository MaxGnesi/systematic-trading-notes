"""Builds lectures/13-the-baseline-trend-portfolio/13_baseline_portfolio.ipynb. Usage: python make_nb27.py <output path>.
Rebuilt 2026-11-18 to the lecture's current outline (§1 equal risk at every level; §2 how weighting methods choose; §3 speeds;
§4 markets and classes; §5 the total; §6 crises). Often-flat streams, timing and crisis speeds moved to Lecture 12's notebook,
the take-profit results to Lecture 8's."""
import sys
from pathlib import Path
import nbformat as nbf

OUT = Path(sys.argv[1])
M, C = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
cells = [
M(r"""# Lecture 13 notebook: the baseline trend portfolio

This notebook replays Lecture 13. Every figure and number of the lecture comes from a script in `scripts/`, next to this notebook; each runs in a fresh process. The data are free and the same as Lecture 12's: the daily prices of Lecture 11's ETFs from Yahoo Finance, the 3-month Treasury bill rate from FRED, and Lecture 12's 36 daily trend streams per market (built by Lecture 12's notebook or here if missing). The regime study of §4.3 also uses long monthly series from FRED and the Kenneth French data library; the futures checks use the capstone futures of Lecture 10 (local, not committed).

By default the notebook builds the baseline's daily returns if they are not there yet, redraws every figure of the lecture as `figures/nb_*.png` from the shipped results, and checks the lecture's mechanics by hand: the baseline rebuilt for one year, minimum variance and equal risk contributions on three speeds, the number of independent bets, and the take-profit rule used in §6. `RUN_ALL` also reruns every analysis (about an hour, one script at a time) and compares the key numbers with the shipped ones. Recomputed results never overwrite the shipped ones.

| § | Content | Lecture |
|---|---|---|
| 0 | Settings and data | |
| 1 | Equal risk at every level: the build, the key chart, the baseline rebuilt for one year | §1 |
| 2 | How weighting methods choose: three speeds in one market by hand, ten methods, 43 markets, resampled weights | §2 |
| 3 | Speeds inside a market: overlap by ratio, equal risk contributions by hand, the blends, the examples and random grids | §3 |
| 4 | Markets and classes: equal risk and equal capital, groups, regimes, the stress test, unstable correlations, losing together | §4 |
| 5 | The total: volatility target and constant leverage | §5 |
| 6 | Today's portfolio in past crises, with the take-profit rule by hand | §6 |
| 7 | Shipped against recomputed; a test of your own | |"""),
M("## 0. Settings and data"),
C(r"""import json, os, shutil, subprocess, sys, time
from itertools import combinations
from pathlib import Path
import numpy as np, pandas as pd
from IPython.display import Image, display

HERE = Path.cwd(); SCRIPTS, FIG = HERE / "scripts", HERE / "figures"
sys.path[:0] = [str(SCRIPTS), str(SCRIPTS.parents[1] / "12-trend-speeds-by-asset-class" / "scripts"), str(SCRIPTS.parents[1] / "08-filters-and-overlays" / "scripts")]
import l27 as M
L26, L25 = M.L26, M.L25
RUN_ALL = False                                                            # True: also rerun every analysis (about an hour)

SHIPPED = HERE / "results"; WORK = L25.DATA / "l27_results"               # recomputed results go to WORK, never over the shipped ones
if not WORK.exists(): shutil.copytree(SHIPPED, WORK)
for f in SHIPPED.glob("*.json"):                                           # results added to the lecture since WORK was made
    if not (WORK / f.name).exists(): shutil.copy(f, WORK / f.name)
pd.set_option("display.width", 200); pd.set_option("display.max_columns", 20)
print("data:", L25.DATA, "| streams:", L26.OUT / "streams", "| daily results:", M.OUT, "| shipped results:", SHIPPED, "| recomputed results:", WORK)


def run(script, *args, show=False):
    "Run a script of this lecture (or of Lectures 8, 11 and 12) in a fresh process; figures as nb_*, results to WORK."
    t0 = time.time(); path = next(p for p in (SCRIPTS / script, M.REPO / "lectures" / "12-trend-speeds-by-asset-class" / "scripts" / script,
                                              M.REPO / "lectures" / "11-choosing-the-markets" / "scripts" / script,
                                              M.REPO / "lectures" / "08-filters-and-overlays" / "scripts" / script) if p.exists())
    env = {**os.environ, "PORTFOLIO_DATA": str(L25.DATA), "L27_RESULTS": str(WORK), "L27_PREFIX": "nb_", "PYTHONIOENCODING": "utf-8"}
    p = subprocess.run([sys.executable, str(path), *args], capture_output=True, text=True, encoding="utf-8", env=env)
    if p.returncode:
        print(p.stdout[-2000:], p.stderr[-4000:]); raise RuntimeError(f"{script} failed")
    print(f"{script} {' '.join(args)}: {time.time() - t0:.0f} s")
    if show: print(p.stdout)


def pictures(*names):
    for nm in names:
        f = FIG / f"nb_{nm}.png"
        display(Image(filename=str(f))) if f.exists() else print("not drawn yet:", f.name)


def result(name, where=None):
    return json.loads(((where or WORK) / name).read_text(encoding="utf-8"))"""),
M(r"""**The data.** Lecture 11's prices, the bill rate and Lecture 12's streams are fetched or built if missing. The baseline's daily out-of-sample returns, with its rivals, are built once by `l27.py` (about ten minutes)."""),
C(r"""if not L25.RAW.exists(): run("l25_fetch.py", show=True)
if not L26.RATE.exists(): run("l26_fetch_rate.py", show=True)
if len(list((L26.OUT / "streams").glob("*.parquet"))) < 100: run("l26_streams.py", show=True)
if not (M.OUT / "l27_daily.parquet").exists(): run("l27.py")
close, high, low, dv, rf = L26.load_daily(); D = pd.read_parquet(M.OUT / "l27_daily.parquet")
print(f"{close.shape[1]} ETFs to {close.index.max().date()}; baseline daily returns {D.index.min().date()} to {D.index.max().date()}, Sharpe ratio {L26.sharpe(D['rule']):.3f}")"""),
M(r"""**Running everything.** With `RUN_ALL` the cell below reruns every analysis of the lecture, one at a time: the baseline and its rivals, the tests, the optimisers, the examples and random grids, the speed blends, scaling the total, the correlation regimes, the stress test, the unstable correlations, losing together, and the crisis replay. The regime study downloads long monthly series once; the futures scripts need the capstone futures of Lecture 10 (`data/interim/l11_series99.pkl`) and are skipped without them."""),
C(r"""if RUN_ALL:
    for s in ("l27.py", "l27_tests.py", "l27_optimisers.py", "l27_optimisers_many.py", "l27_edge_cases.py", "l27_speeds.py", "l27_leverage.py",
              "l27_regimes.py", "l27_corr_stress.py", "l27_unstable_corr.py", "l27_lose_together.py"): run(s)
    if (M.REPO / "data" / "interim" / "l11_series99.pkl").exists():
        for s in ("l27_futures_test.py", "l27_stress.py"): run(s)
    else: print("capstone futures not found: futures checks skipped")
    D = pd.read_parquet(M.OUT / "l27_daily.parquet")"""),

M(r"""## 1. Equal risk at every level

The build in one picture (one rule, equal risk, at every level), then the key chart: the correlation of two streams in the same market against the ratio of their speeds, and each class's share of capital and of risk."""),
C(r"""run("l27_build_diagram.py"); run("l27_key_chart.py", show=True)
pictures("27_build", "27_key")"""),
M(r"""### 1.1 The baseline rebuilt for one year

The baseline in one sentence: speeds at equal weight in each market, markets at equal risk in each class, classes at equal risk, the total scaled to 10% on the past three years. Rebuilt here for 2026, chosen at the end-2025 review, from Lecture 12's net stream returns, against the stored daily returns."""),
C(r"""NET = {}
def net(t):
    if t not in NET: NET[t] = L26.net(pd.read_parquet(L26.OUT / "streams" / f"{t}.parquet")[L26.START:])
    return NET[t]
y = 2025; held = [k for k, v in M.SEL[str(y)]["weights"]["one_set"].items() if v >= 0.2]; uni = M.UNI[str(y)]["sc_div"]
hist, nxt = slice(f"{y - 2}-01-01", f"{y}-12-31"), slice(f"{y + 1}-01-01", f"{y + 1}-12-31"); day = M.TARGET / np.sqrt(252)
R = pd.DataFrame({t: net(t)[held].mean(axis=1) for k in uni for t in uni[k]})          # step 1: speeds at equal weight
a = 1 / R.loc[hist].std()                                                              # step 2: markets at equal risk
cls = {k: R[m].mul(a[m]).mean(axis=1) for k, m in uni.items()}
cls = {k: v * day / v.loc[hist].std() for k, v in cls.items()}                        # step 3: classes at equal risk
U = pd.DataFrame(cls).mean(axis=1); base = (U * day / U.loc[hist].std()).loc[nxt]       # step 4: total at 10%
print(f"{len(held)} streams, {sum(map(len, uni.values()))} markets in {len(uni)} classes; largest daily difference from the stored baseline: {(base - D['rule'].reindex(base.index)).abs().max():.1e}")"""),

M(r"""## 2. How weighting methods choose

### 2.1 Three speeds in one market, by hand

SPY's EWMA crossover at 43, 89 and 179 days, with the correlations measured at the end of 2025. Minimum variance, long only, solved by brute force over a grid of weights, and equal risk contributions by iteration, against the weights stored by `l27_optimisers.py`. With nearly equal volatilities, minimum variance drops the middle speed: it overlaps most with the other two."""),
C(r"""O = result("optimisers.json"); Cs = np.array(O["SPY"]["corr_end2025"]); stored = O["SPY"]["weights"]["2025"]
grid = [(a, b, 1 - a - b) for a in np.linspace(0, 1, 201) for b in np.linspace(0, 1, 201) if a + b <= 1 + 1e-12]
mv = min(grid, key=lambda w: np.array(w) @ Cs @ np.array(w))                             # minimum variance on the correlation matrix
w = np.ones(3) / 3
for _ in range(500): w = 0.5 * w + 0.5 * (1 / (Cs @ w)) / (1 / (Cs @ w)).sum()          # equal risk contributions, fixed-point iteration
print("correlations, end 2025:\n", Cs.round(3))
print(f"minimum variance by hand: {np.round(mv, 2)}; stored: {np.round(stored['Minimum variance, long only'], 2)}")
print(f"equal risk contributions by hand: {w.round(3)}; stored: {np.round(stored['Equal risk contributions'], 3)}; risk shares {(w * (Cs @ w) / (w @ Cs @ w)).round(3)}")"""),
M(r"""### 2.2 Ten methods on the same three speeds

The weights each method chose at the end-2025 review, and how they did out of sample, 2013-2026, for SPY, oil (USO) and long Treasuries (TLT)."""),
C(r"""display(pd.DataFrame({k: np.round(v, 2) for k, v in stored.items()}, index=["43 days", "89 days", "179 days"]).T)
display(pd.DataFrame({t: {k: v["sharpe"] for k, v in O[t]["oos"].items()} for t in O}).round(3))"""),
M(r"""### 2.3 Forty-three markets, and weights under resampling

Each method's Sharpe ratio difference to equal risk contributions across the 43 markets with enough history (median, quartiles, how many lie outside their 90% band), and how far the weights move when history is resampled."""),
C(r"""OM = result("optimisers_many.json")
display(pd.DataFrame(OM["summary"]).T[["median", "q1", "q3", "share_above", "above_band", "below_band"]].round(3))
run("l27_optimisers_charts.py")
pictures("27_opt_resampled")"""),

M(r"""## 3. Speeds inside a market

### 3.1 Overlap by speed ratio

The pooled correlation of the 36 streams at the end-2025 review (each class the same weight), averaged over pairs of the same rule by ratio of speeds, and over different rules at the same speed."""),
C(r"""S = result("speeds.json"); Cr = pd.DataFrame(S["reviews"]["2025"]["corr"])
pairs = [(int(b.split("_")[1]) / int(a.split("_")[1]), a.split("_")[0], Cr.loc[a, b]) for r in L26.RULES for a, b in combinations([f"{r}_{h}" for h in L26.SPEEDS], 2)]
P = pd.DataFrame(pairs, columns=["ratio", "rule", "corr"]); P["ratio band"] = pd.cut(P.ratio, [1, 1.5, 2.5, 5, 10, 60], labels=["1.4", "2", "3-4", "6-8", "11-46"])
display(P.pivot_table(index="rule", columns="ratio band", values="corr", aggfunc="mean", observed=True).round(2))
same = [Cr.loc[f"{a}_{h}", f"{b}_{h}"] for h in (61, 89, 127, 179, 251, 359) for a, b in combinations(L26.RULES, 2)]
print(f"different rules at the same speed (61-359 days): {np.mean(same):.2f}")"""),
M(r"""### 3.2 Equal risk contributions and independent bets, by hand

For the held streams at the end-2025 review: the weights of `l27_speeds.erc`, then each stream's risk contribution $w_i (Cw)_i$ computed by hand (they should be equal), and the number of independent bets $(\sum_i w_i)^2 / w^\top C w$ for equal weights and for equal risk contributions."""),
C(r"""import l27_speeds as SP
held = S["reviews"]["2025"]["held"]; Ch = Cr.loc[held, held].to_numpy()
w, _ = SP.erc(Ch, np.ones(len(held))); rc = w * (Ch @ w); rc = rc / rc.sum(); eq = np.ones(len(held)) / len(held)
print(f"weights {w.min():.3f} to {w.max():.3f} (equal: {1 / len(held):.3f}); risk contributions {rc.min():.4f} to {rc.max():.4f} (equal: {1 / len(held):.4f})")
print(f"stored weights match: {np.allclose(w, pd.Series(S['reviews']['2025']['weights']['correlation'])[held].to_numpy(), atol=1e-3)}")
print(f"independent bets: equal weights {eq.sum() ** 2 / (eq @ Ch @ eq):.2f}, equal risk contributions {w.sum() ** 2 / (w @ Ch @ w):.2f}; average pairwise correlation {Ch[np.triu_indices(len(held), 1)].mean():.2f}")"""),
M(r"""### 3.3 The blends out of sample

Sharpe ratio after costs 2013-2026 for each blend, and the streams maximum Sharpe ratio picked at three reviews."""),
C(r"""display(pd.Series(S["oos"]).rename("Sharpe ratio, 2013-2026").round(3).to_frame())
for y in ("2012", "2018", "2025"):
    ms = {k: round(v, 2) for k, v in S["reviews"][y]["weights"]["max_sharpe"].items() if v > 0.01}
    print(f"{y}: maximum Sharpe ratio holds {len(ms)} of {len(S['reviews'][y]['held'])} streams: {ms}")"""),
M(r"""### 3.4 The examples: grids, even speeds, a bunch, and random grids

Risk shares by region of speed for each example of the lecture (three even speeds, a bunch of near-copies, a near-copy), the spacing patterns, and 1,000 random grids: how far each method's risk split is from fair, and how far the weights move when one correlation moves by 0.01. Then the stability chart."""),
C(r"""E = result("edge_cases.json")
for case, methods in E.items():
    print(case); display(pd.DataFrame({m: {"weights": v["weights"], "risk by region": v["region_risk"], "largest move": v["max_move"]} for m, v in methods.items()}).T)
SPC = result("spacing.json")
display(pd.DataFrame({k: {m: v[m] for m in v if m not in ("speeds", "per_third")} for k, v in SPC.items()}).T)
display(pd.DataFrame(result("random_grids.json")).T.round(3))
run("l27_bunch_stability_chart.py")
pictures("27_bunch_stability")"""),

M(r"""## 4. Markets and classes

### 4.1 Equal risk, not equal capital; 4.2 classes or groups found in the data

Equal risk against equal capital inside the classes, and the classes against groups found in the data, from the daily returns; then the tests and each class's share of capital and of risk."""),
C(r"""dd = lambda x: ((1 + x).cumprod() / (1 + x).cumprod().cummax() - 1).min()
gross = D.gross_U * D.ctot
display(pd.DataFrame({"equal risk (baseline)": {"Sharpe": L26.sharpe(D.rule), "volatility": D.rule.std() * np.sqrt(252), "worst drawdown": dd(D.rule), "gross, median": gross.median()},
                      "equal capital": {"Sharpe": L26.sharpe(D.equal_capital), "volatility": D.equal_capital.std() * np.sqrt(252), "worst drawdown": dd(D.equal_capital), "gross, median": D.gross_eqcap.median()},
                      "groups, Ward": {"Sharpe": L26.sharpe(D.ward), "volatility": D.ward.std() * np.sqrt(252), "worst drawdown": dd(D.ward)},
                      "groups, average linkage": {"Sharpe": L26.sharpe(D.groups), "volatility": D.groups.std() * np.sqrt(252), "worst drawdown": dd(D.groups)}}).T.round(3))
print(f"correlation of daily returns, equal capital with the baseline: {D.rule.corr(D.equal_capital):.3f}")
X = result("tests.json"); display(pd.DataFrame({k: {"difference": v["diff"], "band 5%": v["ci90"][0], "band 95%": v["ci90"][1]} for k, v in X["tests"].items()}).T.round(3))
print("passes Benjamini-Hochberg:", {k: v for k, v in X["bh"].items()})
L = result("leverage.json"); sh = L["class_shares"]
display(pd.DataFrame({k: {"capital": np.mean([sh[y][k]["capital"] for y in sh]), "risk": np.mean([sh[y][k]["risk"] for y in sh])} for k in L26.CLASSES}).T.round(3))
CS = result("corr_stress.json")
display(pd.DataFrame({k: {m: v.get(m) for m in ("median_agreement", "accepted", "bets_flat", "bets_split")} for k, v in CS["split"].items()}).T)"""),
M(r"""### 4.3 When correlations across classes change regime

Monthly class returns and their trend streams, 1973-2024, in eight regime windows: the stock-bond correlation of the assets and of the trend streams, the average absolute correlation, and the chart."""),
C(r"""G = result("regimes.json")
display(pd.DataFrame({k: {m: v[m] for m in ("months", "stock_bond_assets", "stock_bond_trend", "avg_abs_assets", "avg_abs_trend")} for k, v in G["windows"].items()}).T.round(2))
run("l27_regimes_chart.py")
pictures("27_regimes")"""),
M(r"""### 4.4 The correlations to assume, and a stress test

The baseline's 10% total under each correlation scenario: what the same positions would have carried."""),
C(r"""display(pd.Series(CS["stress_total_pct"]).rename("volatility of the 10% book, %").round(1).to_frame())
run("l27_corr_stress_chart.py")
pictures("27_corr_stress")"""),
M(r"""### 4.5 Weighing when correlations are unstable

Six ways of weighing the five classes, each applied in the eight regimes: the risk the 10% book would have carried in its worst and best regime."""),
C(r"""run("l27_unstable_corr.py")
U = result("unstable_corr.json")
display(pd.DataFrame({k: {"worst": v["worst"], "best": v["best"], "worst regime": v["worst_window"]} | {f"weight: {c}": v["weights"][c] for c in U["classes"]} for k, v in U["methods"].items()}).T.round(3))
pictures("27_unstable_corr")"""),
M(r"""### 4.6 Is correlation that important for a trend book? Losing together

How often four or more of the five class trend streams lose in the same month, against what independence would give; and their correlation in down and up months."""),
C(r"""LT = result("lose_together.json")
display(pd.Series({k: v for k, v in LT.items() if not isinstance(v, (dict, list))}).to_frame("value"))"""),

M(r"""## 5. The total

Volatility target against constant leverage: the chart, the profile and the Sharpe ratio difference; then the daily rescaling lesson."""),
C(r"""run("l27_charts.py")
pictures("27_total")
display(pd.DataFrame(L["profile"]).round(3))
print("Sharpe difference, constant leverage minus volatility target:", {k: np.round(v, 3) for k, v in L["sharpe_difference"].items()})
yr = lambda x, y: (1 + x.loc[str(y)]).prod() - 1
print(f"scaled daily on today's positions: Sharpe {L26.sharpe(D.vol_daily):.2f}, volatility {D.vol_daily.std() * np.sqrt(252):.1%}; 2023: {yr(D.vol_daily, 2023):+.1%} against {yr(D.rule, 2023):+.1%} for the baseline")"""),

M(r"""## 6. Today's portfolio in past crises

The end-2025 portfolio replayed through each S&P 500 fall of more than 15%, with and without the take-profit of Lecture 8 §4.8."""),
C(r"""pictures("27_crisis_today")
ST = result("stress.json")
pd.DataFrame({f"{e['peak'][:7]} to {e['trough'][:7]}": {"S&P 500": e["spx"], "markets": f"{e['plain']['markets']} of {e['plain']['of']}", "return": e["plain"]["ret"], "with take-profit 4": e["take-profit 4"]["ret"],
              "drawdown": e["plain"]["drawdown"], "worst day": e["plain"]["worst_day"]} | {f"class: {k}": v for k, v in e["plain"]["by_class"].items()} for e in ST["episodes"]}).T"""),
M(r"""**The take-profit rule, by hand.** SPY's EWMA crossover at 89 days with a take-profit at k = 4, written as a plain Python loop: the open gain since the signal last changed, in units of daily volatility at entry times the square root of the speed; flat above four units until the signal changes. Against the compiled `run` of Lecture 8's `takeprofit.py`."""),
C(r"""import takeprofit as TP
t, h, k = "SPY", 89, 4.0
c = close[t].dropna(); x = L26.excess(c, high[t].reindex(c.index), low[t].reindex(c.index), rf)[0]
r = x.pct_change().fillna(0).to_numpy(); vol = np.sqrt((x.pct_change() ** 2).ewm(span=L26.VOL_SPAN, min_periods=60).mean() * 252).to_numpy()
sig = L26.signals(x.to_frame("x"), x.to_frame("x"), x.to_frame("x"), h)["ewma"]["x"].to_numpy().astype(float)
pos, prev, gain, unit, flat, out, exits = 0.0, 0.0, 0.0, np.nan, False, np.zeros(len(r)), 0
for i in range(1, len(r)):
    out[i] = pos * r[i]; s = 0.0 if (np.isnan(sig[i]) or np.isnan(vol[i])) else sig[i]
    if s != prev: flat, gain, unit, prev = False, 0.0, vol[i] / np.sqrt(252) * np.sqrt(h), s      # a new trade
    else:
        gain += s * r[i]
        if not flat and gain > k * unit: flat, exits = True, exits + 1                             # take the profit
    target = 0.0 if (flat or s == 0 or np.isnan(vol[i])) else s * 0.10 / vol[i]
    new = pos + 0.1 * (target - pos); out[i] -= 5e-4 * abs(new - pos); pos = new
lib = TP.run(sig, r, vol, float(h), k, False, L26.LAMBDA, L26.VOL_TARGET, L26.COST_BP / 1e4)
print(f"{exits} take-profits; largest daily difference from the library: {np.abs(out - lib).max():.1e}")"""),

M(r"""## 7. Shipped against recomputed

With `RUN_ALL`, the rerun's key numbers against the shipped results. With the same download they match exactly; a later download can differ slightly, since Yahoo revises adjusted prices when funds pay distributions."""),
C(r"""rows = [dict(number=f"Sharpe, {v}", shipped=result("portfolios.json", SHIPPED)["summary"][v]["sharpe"], recomputed=result("portfolios.json")["summary"][v]["sharpe"])
        for v in ("rule", "equal_capital", "constant_leverage", "ward")]
rows += [dict(number=f"speed blend, {v}", shipped=result("speeds.json", SHIPPED)["oos"][v], recomputed=result("speeds.json")["oos"][v]) for v in ("correlation", "max_sharpe")]
rows += [dict(number=f"stress, {v}", shipped=result("corr_stress.json", SHIPPED)["stress_total_pct"][v], recomputed=result("corr_stress.json")["stress_total_pct"][v])
         for v in ("Crisis (highest of 2008-09, 2020, 2022)", "Every correlation at 1 (bound)")]
pd.DataFrame(rows).round(4)"""),
M(r"""**A test of your own.** Change one part of the baseline and judge it against the rest: the volatility target (`TARGET` in `scripts/l27.py`), the window of the scales (the `hist` slices), the speeds of the optimiser example (`SPEEDS` in `scripts/l27_optimisers.py`), or the correlation scenarios of the stress test (`scripts/l27_corr_stress.py`). Rerun with `RUN_ALL`. Any change made after looking at results should be dated in `results/hypotheses.md` before it is judged on later data, as every change of this lecture was."""),
]
nb = nbf.v4.new_notebook(); nb["cells"] = cells
nb["metadata"] = {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python"}}
nbf.write(nb, OUT); print("written", OUT)
