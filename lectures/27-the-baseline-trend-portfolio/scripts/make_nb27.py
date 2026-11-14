"""Builds lectures/27-the-baseline-trend-portfolio/27_baseline_portfolio.ipynb. Usage: python make_nb27.py <output path>."""
import sys
from pathlib import Path
import nbformat as nbf

OUT = Path(sys.argv[1])
M, C = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
cells = [
M("""# Lecture 27 notebook: the baseline trend portfolio

This notebook replays Lecture 27. Every figure and number of the lecture comes from a script in `scripts/`, next to this notebook; each runs in a fresh process. The data are free and the same as Lecture 26's: the daily prices of Lecture 25's ETFs from Yahoo Finance, the 3-month Treasury bill rate from FRED, and Lecture 26's 36 daily trend streams per market (built by Lecture 26's notebook or here if missing). The futures checks of §2.4, §5 and §6 also use the capstone futures of Lecture 11 (local, not committed) and two Treasury funds and the S&P 500 from Yahoo, saved once.

By default the notebook builds the baseline's daily returns if they are not there yet, redraws every figure of the lecture as `figures/nb_*.png` from the shipped results, and checks the lecture's mechanics by hand: the baseline rebuilt for one year, the equal-risk-contribution weights, the number of independent bets, the part-time statistics and the take-profit rule. `RUN_ALL` also reruns every analysis (about an hour, one script at a time) and compares the key numbers with the shipped ones. Recomputed results never overwrite the shipped ones.

| § | Content | Lecture |
|---|---|---|
| 0 | Settings and data | |
| 1 | The key chart; the baseline rebuilt for one year | §1 |
| 2 | Speeds inside a market: overlap by speed ratio, equal risk contributions by hand, the blends, part-time streams, timing | §2 |
| 3 | Markets and classes: equal capital, groups | §3 |
| 4 | The total: volatility target and constant leverage, daily rescaling | §4 |
| 5 | Taking profits, with the rule by hand | §5 |
| 6 | Crises and today's portfolio | §6 |
| 7 | Shipped against recomputed; a test of your own | |"""),
M("## 0. Settings and data"),
C("""import json, os, shutil, subprocess, sys, time
from itertools import combinations
from pathlib import Path
import numpy as np, pandas as pd
from IPython.display import Image, display

HERE = Path.cwd(); SCRIPTS, FIG = HERE / "scripts", HERE / "figures"
sys.path[:0] = [str(SCRIPTS)]
import l27 as M
L26, L25 = M.L26, M.L25
RUN_ALL = False                                                            # True: also rerun every analysis (about an hour)

SHIPPED = HERE / "results"; WORK = L25.DATA / "l27_results"               # recomputed results go to WORK, never over the shipped ones
if not WORK.exists(): shutil.copytree(SHIPPED, WORK)
pd.set_option("display.width", 200); pd.set_option("display.max_columns", 20)
print("data:", L25.DATA, "| streams:", L26.OUT / "streams", "| daily results:", M.OUT, "| shipped results:", SHIPPED, "| recomputed results:", WORK)


def run(script, *args, show=False):
    "Run a script of this lecture (or of Lectures 25-26) in a fresh process; figures as nb_*, results to WORK."
    t0 = time.time(); path = next(p for p in (SCRIPTS / script, M.REPO / "lectures" / "26-trend-speeds-by-asset-class" / "scripts" / script,
                                              M.REPO / "lectures" / "25-choosing-the-markets" / "scripts" / script) if p.exists())
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
M("""**The data.** Lecture 25's prices, the bill rate and Lecture 26's streams are fetched or built if missing. The baseline's daily out-of-sample returns, with its rivals, are built once by `l27.py` (about ten minutes)."""),
C("""if not L25.RAW.exists(): run("l25_fetch.py", show=True)
if not L26.RATE.exists(): run("l26_fetch_rate.py", show=True)
if len(list((L26.OUT / "streams").glob("*.parquet"))) < 100: run("l26_streams.py", show=True)
if not (M.OUT / "l27_daily.parquet").exists(): run("l27.py")
close, high, low, dv, rf = L26.load_daily(); D = pd.read_parquet(M.OUT / "l27_daily.parquet")
print(f"{close.shape[1]} ETFs to {close.index.max().date()}; baseline daily returns {D.index.min().date()} to {D.index.max().date()}, Sharpe ratio {L26.sharpe(D['rule']):.3f}")"""),
M("""**Running everything.** With `RUN_ALL` the cell below reruns every analysis of the lecture, one at a time: the baseline and its rivals, the tests, the speed blends, timing, scaling the total, the futures test, crises, take-profit and the stress test. The futures scripts need the capstone futures of Lecture 11 (`data/interim/l11_series99.pkl`); without them they are skipped."""),
C("""if RUN_ALL:
    for s in ("l27.py", "l27_tests.py", "l27_speeds.py", "l27_timing.py", "l27_leverage.py", "l27_states.py"): run(s)
    if (M.REPO / "data" / "interim" / "l11_series99.pkl").exists():
        for s in ("l27_futures_test.py", "l27_crisis.py", "l27_takeprofit.py", "l27_stress.py"): run(s)
    else: print("capstone futures not found: futures checks skipped")
    D = pd.read_parquet(M.OUT / "l27_daily.parquet")"""),
M("""## 1. The key chart

Left: the correlation of two streams in the same market against the ratio of their speeds. Right: each class's share of capital and of risk."""),
C("""run("l27_key_chart.py", show=True)
pictures("27_key")"""),
M("""### 1.1 The baseline rebuilt for one year

The baseline in one sentence (§1): speeds at equal weight in each market, markets at equal risk in each class, classes at equal risk, the total scaled to 10% on the past three years. Rebuilt here for 2026, chosen at the end-2025 review, from Lecture 26's net stream returns, against the stored daily returns."""),
C("""NET = {}
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
M("""## 2. Speeds inside a market

### 2.1 Overlap by speed ratio

The pooled correlation of the 36 streams at the end-2025 review (each class the same weight), averaged over pairs of the same rule by ratio of speeds, and over different rules at the same speed."""),
C("""S = result("speeds.json"); Cr = pd.DataFrame(S["reviews"]["2025"]["corr"])
pairs = [(int(b.split("_")[1]) / int(a.split("_")[1]), a.split("_")[0], Cr.loc[a, b]) for r in L26.RULES for a, b in combinations([f"{r}_{h}" for h in L26.SPEEDS], 2)]
P = pd.DataFrame(pairs, columns=["ratio", "rule", "corr"]); P["ratio band"] = pd.cut(P.ratio, [1, 1.5, 2.5, 5, 10, 60], labels=["1.4", "2", "3-4", "6-8", "11-46"])
display(P.pivot_table(index="rule", columns="ratio band", values="corr", aggfunc="mean", observed=True).round(2))
same = [Cr.loc[f"{a}_{h}", f"{b}_{h}"] for h in (61, 89, 127, 179, 251, 359) for a, b in combinations(L26.RULES, 2)]
print(f"different rules at the same speed (61-359 days): {np.mean(same):.2f}")"""),
M("""### 2.2 Equal risk contributions and independent bets, by hand

For the held streams at the end-2025 review: the weights of `l27_speeds.erc`, then each stream's risk contribution $`w_i (Cw)_i`$ computed by hand (they should be equal), and the number of independent bets $`(\\sum_i w_i)^2 / w^\\top C w`$ for equal weights and for equal risk contributions."""),
C("""import l27_speeds as SP
held = S["reviews"]["2025"]["held"]; Ch = Cr.loc[held, held].to_numpy()
w, _ = SP.erc(Ch, np.ones(len(held))); rc = w * (Ch @ w); rc = rc / rc.sum(); eq = np.ones(len(held)) / len(held)
print(f"weights {w.min():.3f} to {w.max():.3f} (equal: {1 / len(held):.3f}); risk contributions {rc.min():.4f} to {rc.max():.4f} (equal: {1 / len(held):.4f})")
print(f"stored weights match: {np.allclose(w, pd.Series(S['reviews']['2025']['weights']['correlation'])[held].to_numpy(), atol=1e-3)}")
print(f"independent bets: equal weights {eq.sum() ** 2 / (eq @ Ch @ eq):.2f}, equal risk contributions {w.sum() ** 2 / (w @ Ch @ w):.2f}; average pairwise correlation {Ch[np.triu_indices(len(held), 1)].mean():.2f}")"""),
M("""### 2.3 The blends out of sample

Sharpe ratio after costs 2013-2026 for each blend, and the streams maximum Sharpe ratio picked at three reviews."""),
C("""display(pd.Series(S["oos"]).rename("Sharpe ratio, 2013-2026").round(3).to_frame())
for y in ("2012", "2018", "2025"):
    ms = {k: round(v, 2) for k, v in S["reviews"][y]["weights"]["max_sharpe"].items() if v > 0.01}
    print(f"{y}: maximum Sharpe ratio holds {len(ms)} of {len(S['reviews'][y]['held'])} streams: {ms}")"""),
M("""### 2.4 Streams that are not always in the market

The held breakout streams of Lecture 25's end-2025 markets: the share of days with a signal, and the Sharpe ratio after costs over all days and on the days with a signal (the signal of the day before, which sets the position held), 2007-2026, median over markets; then Lecture 7's link, Sharpe while active times the square root of the share of time active."""),
C("""names = sorted({t for m in M.UNI["2025"]["sc_div"].values() for t in m}); bk = [k for k in M.SEL["2025"]["weights"]["one_set"] if k.startswith("breakout") and M.SEL["2025"]["weights"]["one_set"][k] >= 0.2]
rows = []
for t in names:
    c = close[t].dropna(); x, xh, xl = L26.excess(c, high[t].reindex(c.index), low[t].reindex(c.index), rf); r = net(t)
    for k in bk:
        s = L26.signals(x.to_frame("x"), xh.to_frame("x"), xl.to_frame("x"), int(k.split("_")[1]))["breakout"]["x"].shift(1)
        rr = r[k].dropna(); on = s.reindex(rr.index).fillna(0) != 0
        rows.append(dict(market=t, stream=k, share=on.mean(), all_days=L26.sharpe(rr), active=L26.sharpe(rr[on])))
PT = pd.DataFrame(rows); med = PT[["share", "all_days", "active"]].median()
display(PT.groupby("stream")[["share", "all_days", "active"]].median().round(2))
print(f"median: in the market {med.share:.0%} of days; Sharpe {med.all_days:.2f} on all days, {med.active:.2f} while active; {med.active:.2f} x sqrt({med.share:.2f}) = {med.active * np.sqrt(med.share):.2f}")"""),
M("""### 2.5 Timing the speeds

Momentum and reversal tilts within the held set, against equal weights (90% bands from a block bootstrap over months)."""),
C("""T = result("timing.json")
pd.DataFrame({k: {"Sharpe": v["sharpe"], "difference": v["diff"], "band 5%": (v["ci90"] or [np.nan])[0], "band 95%": (v["ci90"] or [np.nan, np.nan])[1]} for k, v in T.items()}).T.round(3)"""),
M("""## 3. Markets and classes

Equal risk against equal capital inside the classes, and the classes against groups found in the data, from the daily returns; then the tests."""),
C("""dd = lambda x: ((1 + x).cumprod() / (1 + x).cumprod().cummax() - 1).min()
gross = D.gross_U * D.ctot
display(pd.DataFrame({"equal risk (baseline)": {"Sharpe": L26.sharpe(D.rule), "volatility": D.rule.std() * np.sqrt(252), "worst drawdown": dd(D.rule), "gross, median": gross.median()},
                      "equal capital": {"Sharpe": L26.sharpe(D.equal_capital), "volatility": D.equal_capital.std() * np.sqrt(252), "worst drawdown": dd(D.equal_capital), "gross, median": D.gross_eqcap.median()},
                      "groups, Ward": {"Sharpe": L26.sharpe(D.ward), "volatility": D.ward.std() * np.sqrt(252), "worst drawdown": dd(D.ward)},
                      "groups, average linkage": {"Sharpe": L26.sharpe(D.groups), "volatility": D.groups.std() * np.sqrt(252), "worst drawdown": dd(D.groups)}}).T.round(3))
print(f"correlation of daily returns, equal capital with the baseline: {D.rule.corr(D.equal_capital):.3f}")
X = result("tests.json"); display(pd.DataFrame({k: {"difference": v["diff"], "band 5%": v["ci90"][0], "band 95%": v["ci90"][1]} for k, v in X["tests"].items()}).T.round(3))
print("passes Benjamini-Hochberg:", {k: v for k, v in X["bh"].items()})"""),
M("""Each class's share of capital and of risk (its contribution to the variance of the total), mean of the years."""),
C("""L = result("leverage.json"); sh = L["class_shares"]
pd.DataFrame({k: {"capital": np.mean([sh[y][k]["capital"] for y in sh]), "risk": np.mean([sh[y][k]["risk"] for y in sh])} for k in L26.CLASSES}).T.round(3)"""),
M("""## 4. The total

Volatility target against constant leverage: the chart, the profile and the Sharpe ratio difference; then the daily rescaling lesson."""),
C("""run("l27_charts.py")
pictures("27_total")
display(pd.DataFrame(L["profile"]).round(3))
print("Sharpe difference, constant leverage minus volatility target:", {k: np.round(v, 3) for k, v in L["sharpe_difference"].items()})
yr = lambda x, y: x.loc[str(y)].sum()
print(f"scaled daily on today's positions: Sharpe {L26.sharpe(D.vol_daily):.2f}, volatility {D.vol_daily.std() * np.sqrt(252):.1%}; 2023: {yr(D.vol_daily, 2023):+.1%} against {yr(D.rule, 2023):+.1%} for the baseline")"""),
M("""## 5. Taking profits

### 5.1 The rule by hand

SPY's EWMA crossover at 89 days with a take-profit at k = 4, written as a plain Python loop: the open gain since the signal last changed, in units of daily volatility at entry times the square root of the speed; flat above four units until the signal changes. Against the compiled `run` of `l27_takeprofit.py`."""),
C("""import l27_takeprofit as TP
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
M("""### 5.2 Results"""),
C("""pictures("27_takeprofit")
TPR = result("takeprofit.json")
for d in ("etf", "futures"):
    print(d); display(pd.DataFrame({k: {m: v[m] for m in ("sharpe", "vol", "dd_over_vol", "worst12_over_vol", "skew_monthly")} for k, v in TPR[d].items()}).round(3))
    print("bands:", {k: (round(v["diff"], 3), [round(b, 3) for b in v["ci90"]]) for k, v in TPR[d + "_bands"].items()})"""),
M("""## 6. Crises

### 6.1 Which speeds work in crises?

Each speed's return in each S&P 500 fall of more than 15%, and the share of the falls in which it beat the held set; a speed works in crises if it does so in two thirds of them on both datasets."""),
C("""pictures("27_crisis")
CR = result("crisis.json")
display(pd.DataFrame({f"{e['peak'][:7]} ({e['spx_fall']:.0%})": e["etf"]["by_speed"] | {"held set": e["etf"]["held"]} for e in CR["episodes"] if e.get("etf")}).T.round(3))
display(pd.DataFrame(CR["beat_share"]).drop(columns=["etf_n", "futures_n"], errors="ignore").round(2).T)
print("speeds that work in crises:", CR["works"] or "none")"""),
M("""### 6.2 Today's portfolio in past crises"""),
C("""ST = result("stress.json")
pd.DataFrame({f"{e['peak'][:7]} to {e['trough'][:7]}": {"S&P 500": e["spx"], "markets": f"{e['plain']['markets']} of {e['plain']['of']}", "return": e["plain"]["ret"], "with take-profit 4": e["take-profit 4"]["ret"],
              "drawdown": e["plain"]["drawdown"], "worst day": e["plain"]["worst_day"]} | {f"class: {k}": v for k, v in e["plain"]["by_class"].items()} for e in ST["episodes"]}).T"""),
M("""## 7. Shipped against recomputed

With `RUN_ALL`, the rerun's key numbers against the shipped results. With the same download they match exactly; a later download can differ slightly, since Yahoo revises adjusted prices when funds pay distributions."""),
C("""rows = [dict(number=f"Sharpe, {v}", shipped=result("portfolios.json", SHIPPED)["summary"][v]["sharpe"], recomputed=result("portfolios.json")["summary"][v]["sharpe"])
        for v in ("rule", "equal_capital", "constant_leverage", "ward")]
rows += [dict(number=f"speed blend, {v}", shipped=result("speeds.json", SHIPPED)["oos"][v], recomputed=result("speeds.json")["oos"][v]) for v in ("correlation", "max_sharpe")]
pd.DataFrame(rows).round(4)"""),
M("""**A test of your own.** Change one part of the baseline and judge it against the rest: the volatility target (`TARGET` in `scripts/l27.py`), the window of the scales (the `hist` slices), the take-profit grid (`KS` in `scripts/l27_takeprofit.py`), or the crisis threshold (`fall` in `scripts/l27_crisis.py`). Rerun with `RUN_ALL`. Any change made after looking at results should be dated in `results/hypotheses.md` before it is judged on later data, as every change of this lecture was."""),
]
nb = nbf.v4.new_notebook(); nb["cells"] = cells
nb["metadata"] = {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python"}}
nbf.write(nb, OUT); print("written", OUT)
