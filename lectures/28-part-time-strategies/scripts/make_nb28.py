"""Builds lectures/28-part-time-strategies/28_part_time_strategies.ipynb. Usage: python make_nb28.py <output path>."""
import sys
from pathlib import Path
import nbformat as nbf

OUT = Path(sys.argv[1])
M, C = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
cells = [
M("""# Lecture 28 notebook: part-time strategies

This notebook replays Lecture 28. Every figure and number of the lecture comes from a script in `scripts/`, next to this notebook; each runs in a fresh process. The data are free: Lecture 27's baseline (built by its notebook), FRED series (VIX, VXO, the Fed's target, the yield curve, the dollar, Treasury yields, exchange rates, oil and gas prices), the Philadelphia Fed's Real-Time Data Set (industrial production and CPI as first published), equity indices from Yahoo Finance, and the capstone futures of Lecture 11 (local, not committed). Downloads are saved once in `data/raw/l28_realtime`.

By default the notebook builds the regime series if they are not there yet, redraws every figure of the lecture as `figures/nb_*.png` from the shipped results, and checks the lecture's mechanics by hand. `RUN_ALL` also reruns every analysis (one script at a time) and compares the key numbers with the shipped ones. Recomputed results never overwrite the shipped ones.

| § | Content | Lecture |
|---|---|---|
| 0 | Settings and data | |
| 1 | The key chart; the switch by hand | §1 |
| 2 | Comparing part-time with always-in: the six numbers, random filters and the square-root link by hand | §2 |
| 3 | Data as first published: the share of days in another quadrant, by hand | §3 |
| 4 | The scan | §4 |
| 5 | The filters against luck; Benjamini-Hochberg by hand | §5 |
| 6 | Why: Fed and dollar, level and direction, quadrants, clock, timeline, 1990-2005 | §6 |
| 7 | Commodity curves; one curve gap by hand | §7 |
| 8 | Shipped against recomputed; a test of your own | |"""),
M("## 0. Settings and data"),
C("""import json, os, re, shutil, subprocess, sys, time
from pathlib import Path
import numpy as np, pandas as pd
from IPython.display import Image, display

HERE = Path.cwd(); SCRIPTS, FIG = HERE / "scripts", HERE / "figures"
sys.path[:0] = [str(SCRIPTS)]
import l28 as L
import l28_filters as LF
L26, L25 = L.L26, L.L25
RUN_ALL = False                                                            # True: also rerun every analysis

SHIPPED = HERE / "results"; WORK = L25.DATA / "l28_results"               # recomputed results go to WORK, never over the shipped ones
if not WORK.exists(): shutil.copytree(SHIPPED, WORK)
pd.set_option("display.width", 200); pd.set_option("display.max_columns", 20)
FUTURES = L.FT.CACHE.exists()
print("data:", L.OUT, "| shipped results:", SHIPPED, "| recomputed results:", WORK, "| capstone futures found:", FUTURES)


def run(script, *args, show=False):
    "Run a script of this lecture in a fresh process; figures as nb_*, results to WORK."
    t0 = time.time()
    env = {**os.environ, "PORTFOLIO_DATA": str(L25.DATA), "L28_RESULTS": str(WORK), "L28_PREFIX": "nb_", "PYTHONIOENCODING": "utf-8"}
    p = subprocess.run([sys.executable, str(SCRIPTS / script), *args], capture_output=True, text=True, encoding="utf-8", env=env)
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
M("""**The data.** `l28.py` builds the two baselines' daily returns (ETFs from Lecture 27; the capstone futures with Lecture 27's rules) and every regime series, known the day before: macro data as first published and as revised today, the Fed on hold, and the market-state measures with their thresholds. It needs Lecture 27's daily results and the capstone futures."""),
C("""if not (L.OUT / "l28_base.parquet").exists(): run("l28.py", show=True)
B = pd.read_parquet(L.OUT / "l28_base.parquet")
for tag, start in (("etf", L.ETF_START), ("futures", L.FUT_START)):
    b = B[tag].dropna().loc[start:L.END[tag]]
    print(f"{tag}: {b.index[0].date()} to {b.index[-1].date()}, Sharpe ratio {L26.sharpe(b.ret):.3f}, volatility {b.ret.std() * np.sqrt(252):.1%}")"""),
M("""**Running everything.** With `RUN_ALL` the cell below reruns every analysis, one at a time: the data and regimes, the scan, the filters with their random switches, and the 1990-2005 check."""),
C("""if RUN_ALL:
    for s in ("l28.py", "l28_scan.py", "l28_filters.py", "l28_confirm.py"): run(s)
    B = pd.read_parquet(L.OUT / "l28_base.parquet")"""),
M("""## 1. The key chart

The baseline on the capstone futures, always in, against the same portfolio switched off while US growth stands still: as run, and scaled after the fact to the same risk."""),
C("""run("l28_key_chart.py")
pictures("28_key")"""),
M("""### 1.1 The switch by hand

Off means a target scale of 0, on a scale of 1; the scale moves a tenth of the way each day and every change costs 5 bp of the gross exposure moved. Written as a plain loop, against the compiled `switched` of `l28_filters.py`."""),
C("""base = B["futures"].dropna().loc[L.FUT_START:L.END["futures"]]
G = pd.read_parquet(L.OUT / "l28_regimes_futures.parquet").reindex(base.index)
off = LF.offs(G, LF.FIXED)["growth"]
s, out = 1.0, []
for r_, g_, o in zip(base.ret, base.gross, off):
    new = s + L.LAMBDA * ((0.0 if o else 1.0) - s)
    out.append(new * r_ - L.COST_BP / 1e4 * abs(new - s) * g_); s = new
part = pd.Series(out, base.index)
lib = LF.switched(base.ret.to_numpy(), base.gross.to_numpy(), off.to_numpy(), L.LAMBDA, L.COST_BP / 1e4)
print(f"growth filter off on {off.mean():.0%} of days; largest daily difference from the library: {np.abs(part.to_numpy() - lib).max():.1e}")"""),
M("""## 2. Comparing part-time with always-in

### 2.1 The six numbers by hand

The running example of §2.3: Sharpe ratio over all days and while on, volatility, return as run and scaled to the same risk, worst drawdown, alpha over always-in (intercept of a regression on always-in's daily returns)."""),
C("""dd = lambda x: ((1 + x).cumprod() / (1 + x).cumprod().cummax() - 1).min()
k = base.ret.std() / part.std()
X = np.column_stack([np.ones(len(part)), base.ret.to_numpy()]); beta = np.linalg.lstsq(X, part.to_numpy(), rcond=None)[0]
resid = part.to_numpy() - X @ beta; t_alpha = beta[0] / np.sqrt(resid.var(ddof=2) / len(part))
six = pd.DataFrame({"always in": {"share of days on": 1.0, "Sharpe, while on": L26.sharpe(base.ret), "Sharpe, all days": L26.sharpe(base.ret),
                                  "volatility": base.ret.std() * np.sqrt(252), "return a year, as run": base.ret.mean() * 252,
                                  "return a year, same risk": base.ret.mean() * 252, "worst drawdown, as run": dd(base.ret), "worst drawdown, same risk": dd(base.ret)},
                    "growth filter": {"share of days on": 1 - off.mean(), "Sharpe, while on": L26.sharpe(base.ret[~off]), "Sharpe, all days": L26.sharpe(part),
                                      "volatility": part.std() * np.sqrt(252), "return a year, as run": part.mean() * 252,
                                      "return a year, same risk": (part * k).mean() * 252, "worst drawdown, as run": dd(part), "worst drawdown, same risk": dd(part * k)}})
display(six.round(3))
print(f"scale to the same risk: x {k:.2f}; alpha {beta[0] * 252:.2%} a year, t-statistic {t_alpha:.2f}")
m = result("filters.json", SHIPPED)["datasets"]["futures"]["growth"]["0.33"]
print(f"shipped: Sharpe {m['sharpe']:.3f}, while on {m['sharpe_on']:.3f}, alpha {m['alpha']:.2%} (t {m['alpha_t']:.2f})")"""),
M("""### 2.2 Random filters by hand, and the square-root link

Random switches with the same share of time off and the same average spell lengths: a two-state Markov chain, leaving the off state with probability one over the mean off spell and the on state with one over the mean on spell. 200 draws here (the lecture uses 1,000), so the median and 95th percentile differ slightly from the shipped ones. Lecture 7's link: with no information, Sharpe over all days is about Sharpe while on times the square root of the share of days on."""),
C("""lo, ln = LF.spells(off); rng = np.random.default_rng(1); sh = []
for _ in range(200):
    st = rng.random() < off.mean(); x = np.empty(len(off), dtype=bool); u = rng.random(len(off))
    for i in range(len(off)):
        x[i] = st; st = (not (u[i] < 1 / lo)) if st else (u[i] < 1 / ln)
    sh.append(L26.sharpe(pd.Series(LF.switched(base.ret.to_numpy(), base.gross.to_numpy(), x, L.LAMBDA, L.COST_BP / 1e4))))
sh = np.array(sh); p = 1 - off.mean()
print(f"mean spells: off {lo:.0f} days, on {ln:.0f} days")
print(f"random filters: median {np.median(sh):.3f}, 95th percentile {np.quantile(sh, .95):.3f}; the filter beats {(L26.sharpe(part) > sh).mean():.0%} (shipped: {m['random_median']:.3f}, {m['random_p95']:.3f}, {m['beaten']:.0%})")
print(f"square-root link: always-in {L26.sharpe(base.ret):.3f} x sqrt({p:.2f}) = {L26.sharpe(base.ret) * np.sqrt(p):.3f}, against the random median {np.median(sh):.3f}")
print("Sharpe ratio needed while on to match always-in:", {f"{q:.0%}": round(float(1 / np.sqrt(q)), 2) for q in (0.9, 0.75, 0.6, 0.5)})"""),
M("""## 3. Data as first published

On each day, the growth × inflation quadrant (the sign of each 12-month change) from the vintage available that day and from today's revised data; the share of days on which they differ, and the trend portfolio's Sharpe ratio by quadrant on each."""),
C("""for tag, start in (("etf", L.ETF_START), ("futures", L.FUT_START)):
    b = B[tag].dropna().loc[start:L.END[tag]]; R = pd.read_parquet(L.OUT / f"l28_regimes_{tag}.parquet").reindex(b.index)
    q = {src: (np.sign(R[(f"growth{src}", "sign")]).astype(str) + np.sign(R[(f"inflation{src}", "sign")]).astype(str)) for src in ("", "_revised")}
    ok = R[("growth", "sign")].notna() & R[("growth_revised", "sign")].notna() & R[("inflation", "sign")].notna() & R[("inflation_revised", "sign")].notna()
    print(f"{tag}: {(q[''] != q['_revised'])[ok].mean():.1%} of days in a different quadrant (shipped: {result('scan.json', SHIPPED)[tag]['quadrant_disagreement']:.1%})")
S = result("scan.json", SHIPPED)
display(pd.DataFrame({f"{tag}, {src.replace('quadrant_', '').replace('_', ' ')}": {q: v["sharpe"] for q, v in S[tag][src].items()}
                      for tag in ("etf", "futures") for src in ("quadrant_first_published", "quadrant_revised")}).round(2))"""),
M("""## 4. The scan

Per variable, the baseline's Sharpe ratio on the days the filter would keep trend on and on the days it would switch trend off, and the difference with its 90% band. Nothing is switched."""),
C("""run("l28_charts.py")
pictures("28_scan")
display(pd.DataFrame({f"{tag}: {c}": {k: (v[c] if c != "band" else f"{v['ci90'][0]:+.2f} to {v['ci90'][1]:+.2f}") for k, v in S[tag].items() if isinstance(v, dict) and "diff" in v}
                      for tag in ("etf", "futures") for c in ("sharpe_on", "sharpe_off", "diff", "band")}).round(2))"""),
M("""## 5. The filters against luck

Each filter at its fixed threshold: share of days on, Sharpe ratio over all days, the share of its 1,000 random filters it beats, and the threshold grid."""),
C("""pictures("28_filters")
FR = result("filters.json", SHIPPED); fx = lambda k: LF.LEVELS[LF.KIND[k]][LF.FIXED] if k in LF.KIND else "third"
ks = [k for v in LF.FAMILIES.values() for k in v]
display(pd.DataFrame({LF.NAMES[k]: {f"{t}: {c}": FR["datasets"][t][k][fx(k)][c] for t in ("etf", "futures") for c in ("share_on", "sharpe", "beaten")} for k in ks}).T.round(2))
display(pd.DataFrame({LF.NAMES[k]: {f"{t}: {lev}": v["sharpe"] for t in ("etf", "futures") for lev, v in FR["datasets"][t][k].items()} for k in ks}).T.round(2))"""),
M("""### 5.1 Benjamini-Hochberg by hand

Within each family, each filter's p-value is the larger of its two (one minus the share of random filters beaten, on the ETFs and on the futures). Sorted from smallest, the $`i`$-th of $`m`$ passes if it and some larger one are at most $`0.10 \\cdot i / m`$."""),
C("""for fam, ks_ in LF.FAMILIES.items():
    p = pd.Series({k: max(1 - FR["datasets"][t][k][fx(k)]["beaten"] for t in ("etf", "futures")) for k in ks_}).sort_values()
    limit = 0.10 * np.arange(1, len(p) + 1) / len(p); passing = np.flatnonzero(p.to_numpy() <= limit)
    n = passing.max() + 1 if len(passing) else 0
    print(f"{fam}: " + ", ".join(f"{LF.NAMES[k]} p={v:.3f} (limit {l:.3f})" for (k, v), l in zip(p.items(), limit)) + f" -> {n} pass; shipped: {sum(v['bh'] for v in FR['verdict'][fam].values())}")"""),
M("""## 6. Why: exploring the patterns

### 6.1 Fed and dollar; level and direction

Which years and classes gave the Fed and dollar patterns (ETFs), and the baseline by the level (fifth of its history to date) and direction of volatility and correlation."""),
C("""run("l28_why.py")
pictures("28_volatility")
W = result("why.json", SHIPPED)
for k in ("fed", "dollar"):
    print(k); display(pd.DataFrame(W["etf"][k]["years"]).T.round(3))"""),
M("""### 6.2 Four quadrants, the clock and the timeline

The quadrant chart (the ETFs, the futures and 1990-2005), the volatility clock and the regime timeline. Then one cell by hand: the futures baseline on the days the VIX was above its average to date and had fallen over three months."""),
C("""run("l28_quadrants.py"); run("l28_regime_charts.py")
pictures("28_quadrants", "28_clock", "28_timeline")
vix = L.fred("VIXCLS").reindex(pd.bdate_range("1990-01-01", base.index[-1])).ffill()
lvl = vix.rolling(21).mean().shift(1); avg = lvl.expanding(1260).mean(); chg = (np.log(vix) - np.log(vix.shift(63))).shift(1)
cell = ((lvl > avg) & (chg < 0)).reindex(base.index, fill_value=False).astype(bool)
print(f"above average and falling: {cell.mean():.1%} of days, Sharpe ratio {L26.sharpe(base.ret[cell]):.3f} (shipped: {result('quadrants.json', SHIPPED)['futures']['volatility']['above falling']['sharpe']:.3f})")"""),
M("""### 6.3 The check on 1990-2005

The two statements fixed before these years were loaded, and what happened (`l28_confirm.py` builds the 12-market portfolio from free long series)."""),
C("""CF = result("confirm.json", SHIPPED)
print(f"1990-2005 portfolio: {len(CF['markets'])} markets, Sharpe ratio {CF['sharpe']:.2f}")
display(pd.DataFrame({k: {q: f"{v['sharpe']:+.2f} ({v['share']:.0%})" for q, v in CF[k].items()} for k in ("volatility", "correlation")}))
print("E1:", CF["E1"]); print("E2:", CF["E2"])"""),
M("""## 7. Commodity curves

Each commodity's trend stream in backwardation and in contango, and the sleeve. Then one curve gap by hand: crude oil on 1 July 2008, from the contract files."""),
C("""if FUTURES:
    run("l28_curves.py"); pictures("28_curves")
    import l28_curves as CV
    day = pd.Timestamp("2008-07-01"); C_ = []
    for f in (CV.KAGGLE / "nymex-cl").glob("*.csv"):
        mm = re.search(r"([FGHJKMNQUVXZ])(\\d{4})\\.csv$", f.name); x = pd.read_csv(f, index_col=0, parse_dates=True)["Close"].sort_index().dropna()
        if len(x) > 20: C_.append((int(mm.group(2)) * 12 + CV.CODES.index(mm.group(1)), f.name, x))
    C_.sort(key=lambda c: c[0])
    i = next(j for j, c in enumerate(C_) if c[2].index[-1] > day + pd.offsets.BDay(5))
    (_, fa, a), (_, fb, b) = C_[i], C_[i + 1]
    gap = np.log(a.loc[day] / b.loc[day]) * 365 / (b.index[-1] - a.index[-1]).days
    print(f"front {fa} {a.loc[day]:.2f}, next {fb} {b.loc[day]:.2f}: annualised gap {gap:+.1%} ({'backwardation' if gap > 0 else 'contango'}); library: {CV.curve('nymex-cl').loc[day]:+.1%}")
    display(pd.DataFrame(result("curves.json", SHIPPED)["markets"]).T[["name", "share_back", "sharpe_back", "sharpe_contango"]])
else: print("capstone futures not found: §7 skipped")"""),
M("""## 8. Shipped against recomputed

With `RUN_ALL`, the rerun's key numbers against the shipped results. With the same downloads they match; a later download can differ slightly, since Yahoo revises adjusted prices and FRED revises some series."""),
C("""rows = [dict(number=f"{t}: always in, Sharpe", shipped=result("filters.json", SHIPPED)["datasets"][t]["baseline"]["sharpe"], recomputed=result("filters.json")["datasets"][t]["baseline"]["sharpe"]) for t in ("etf", "futures")]
rows += [dict(number=f"{t}: growth still, random filters beaten", shipped=result("filters.json", SHIPPED)["datasets"][t]["growth"]["0.33"]["beaten"], recomputed=result("filters.json")["datasets"][t]["growth"]["0.33"]["beaten"]) for t in ("etf", "futures")]
rows += [dict(number="1990-2005: Sharpe", shipped=result("confirm.json", SHIPPED)["sharpe"], recomputed=result("confirm.json")["sharpe"])]
pd.DataFrame(rows).round(4)"""),
M("""**A test of your own.** Fix a regime variable and its unfavourable state with a reason, before looking: for example the size of the 12-month change in oil prices, or the share of markets at a 12-month high. Add it to `market_state` in `scripts/l28.py` and to `KIND` in `scripts/l28_filters.py`, rerun with `RUN_ALL`, and judge it by the six numbers of §2 and against its random filters on both datasets. Date the plan in `results/hypotheses.md` before you run it, as every step of this lecture was."""),
]
nb = nbf.v4.new_notebook(); nb["cells"] = cells
nb["metadata"] = {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python"}}
nbf.write(nb, OUT); print("written", OUT)
