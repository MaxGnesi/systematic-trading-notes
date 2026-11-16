"""Builds lectures/15-carry-and-value/15_carry_and_value.ipynb. Usage: python make_nb29.py <output path>."""
import sys
from pathlib import Path
import nbformat as nbf

OUT = Path(sys.argv[1])
M, C = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
cells = [
M("""# Lecture 15 notebook: carry and value

This notebook replays Lecture 15. Every figure and number of the lecture comes from a script in `scripts/`, next to this notebook; each runs in a fresh process. The data are free and kept local, never committed: FRED (exchange rates, OECD rates and yields, CPI, the bill rate), the BIS real exchange rates, the central banks' daily 10-year yields (sources in `results/bond_yield_sources.md`), Shiller's S&P 500 data, Yahoo Finance (country funds and their distributions), the World Bank (PPP, commodity prices), EIA and USDA (inventories), the AQR Data Library (a check only), and the capstone futures of Lecture 10.

By default the notebook shows the shipped figures and results and checks the lecture's mechanics by hand. `RUN_ALL` also reruns every analysis, one script at a time, into a separate folder, and compares the key numbers with the shipped ones. Recomputed results never overwrite the shipped ones.

| § | Content | Lecture |
|---|---|---|
| 0 | Settings and data | |
| 1 | The key chart | §1 |
| 3 | Our value against AQR's, by hand | §3 |
| 4 | Carry: a currency return and a carry score by hand | §4 |
| 5 | Value: price and fundamentals | §5 |
| 6 | Results: the number of tries and the deflated Sharpe ratio by hand; years needed; regimes | §6 |
| 7 | What did not add; the split by trend's position | §7 |
| 8 | Shipped against recomputed; a construction of your own | |"""),
M("## 0. Settings and data"),
C("""import json, os, shutil, subprocess, sys, time
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import norm
from IPython.display import Image, display

HERE = Path.cwd(); SCRIPTS, FIG = HERE / "scripts", HERE / "figures"
sys.path[:0] = [str(SCRIPTS)]
import l29 as L, l29_combined as MC, l29_bonds_g10 as G, l29_grids as GR
RUN_ALL = False                                                            # True: also rerun every analysis

SHIPPED = HERE / "results"; WORK = L.RAW / "l29_results"                  # recomputed results go to WORK, never over the shipped ones
if not WORK.exists(): shutil.copytree(SHIPPED, WORK)
pd.set_option("display.width", 200); pd.set_option("display.max_columns", 20)
FUTURES = L.FT.CACHE.exists()
print("shipped results:", SHIPPED, "| recomputed results:", WORK, "| capstone futures found:", FUTURES)


def run(script, *args, show=False):
    "Run a script of this lecture in a fresh process; figures as nb_*, results to WORK."
    t0 = time.time()
    env = {**os.environ, "PORTFOLIO_DATA": str(L.L28.L25.DATA), "L29_RESULTS": str(WORK), "L29_PREFIX": "nb_", "PYTHONIOENCODING": "utf-8"}
    p = subprocess.run([sys.executable, str(SCRIPTS / script), *args], capture_output=True, text=True, encoding="utf-8", env=env)
    if p.returncode:
        print(p.stdout[-2000:], p.stderr[-4000:]); raise RuntimeError(f"{script} failed")
    print(f"{script} {' '.join(args)}: {time.time() - t0:.0f} s")
    if show: print(p.stdout)


def result(name, where=None):
    return json.loads(((where or WORK) / name).read_text(encoding="utf-8"))"""),
M("""## 1. The key chart

Trend (Lecture 13's baseline across all its markets), carry (four groups) and the two at equal risk. `l29_key_chart.py` redraws it."""),
C("""if RUN_ALL: run("l29_key_chart.py")
f = FIG / ("nb_29_key.png" if RUN_ALL else "29_key.png"); display(Image(filename=str(f)))
K = result("key.json", SHIPPED)
pd.DataFrame({k: {m: round(v[m], 3) for m in ("sharpe", "ret", "maxdd", "calmar", "omega")} for k, v in K.items() if isinstance(v, dict)})"""),
M("""## 3. Our value against AQR's, by hand

The currency group with AQR's construction (the real exchange rate against its average 4.5 to 5.5 years earlier), against AQR's published currency value factor: the correlation of monthly returns, 2006 to October 2022. The lecture reports 0.78."""),
C("""Gs = MC.groups()
w = G.rank_centred(Gs["fx"]["Va"]); ours = G.stream(w, Gs["fx"]["R"]).loc["2006-01":"2022-10"]
A = G.aqr()["VALLS_VME_FX"]
print("correlation with AQR's currency value:", round(pd.concat([ours, A], axis=1).dropna().corr().iat[0, 1], 2))"""),
M("""## 4. Carry by hand

**A currency's return over cash.** The euro in one month: spot change plus the rate gap, against the built series."""),
C("""S, R, Cg = L.FX.build()
d0, d1 = pd.Timestamp("2015-06-30"), pd.Timestamp("2015-07-31")
spot = S["EUR"].loc[d0:d1]; gap = Cg["EUR"].loc[d0:d1]
by_hand = (spot.iloc[-1] / spot.iloc[0] - 1) + gap.iloc[1:].mean() * (d1 - d0).days / 365
built = (1 + R["EUR"].loc[d0 + pd.Timedelta(days=1):d1]).prod() - 1
print(f"euro, July 2015: by hand {by_hand:+.4%}, built series {built:+.4%} (small gap: daily compounding)")"""),
M("""**A carry score.** The currency group in one month: z-scores of the level and the 3-month change, half absolute and half per unit of risk (§4.2), against the script's score."""),
C("""Cfx, Rfx = Gs["fx"]["C"], Gs["fx"]["R"]; t = pd.Period("2015-06", "M")
vol = (Rfx.rolling(36, min_periods=24).std() * np.sqrt(12)).loc[t]
z = lambda x: (x - x.mean()) / x.std(ddof=0)
lev, chg = Cfx.loc[t], Cfx.loc[t] - Cfx.shift(3).loc[t]
by_hand = ((z(lev) + z(lev / vol)) / 2 + (z(chg) + z(chg / vol)) / 2) / 2
script = GR.sig(Cfx, Rfx).loc[t]
pd.DataFrame({"by hand": by_hand, "script": script, "weight": by_hand / by_hand.abs().sum()}).round(3)"""),
M("""## 5. Value: price and fundamentals"""),
C("""if RUN_ALL: run("l29_value_fund.py")
V = result("value_fund.json", SHIPPED)
pd.DataFrame({k: {g: round(V[k][g], 2) for g in ("fx", "commod", "bonds", "equity")} | {"all four": round(V[k]["2006-2022"]["value"], 2),
              "trend + value": round(V[k]["2006-2022"]["with_trend"], 2)} for k in ("price (rule)", "fundamental")})"""),
M("""## 6. Results

**The number of tries and the deflated Sharpe ratio by hand** (Bailey and López de Prado 2014), from the tries' monthly returns' summary in `results/tries.json`."""),
C("""if RUN_ALL: run("l29_tries.py")
T = result("tries.json", SHIPPED); r = T["rule"]
sr_all = np.array(list(T["sharpe"].values())) / np.sqrt(12); n = T["n_eff"]; g = 0.5772156649
sr0 = np.sqrt(np.var(sr_all, ddof=1)) * ((1 - g) * norm.ppf(1 - 1 / n) + g * norm.ppf(1 - 1 / (n * np.e)))
zz = (r["sr_month"] - sr0) * np.sqrt(r["T"] - 1) / np.sqrt(1 - r["skew"] * r["sr_month"] + (r["kurt"] - 1) / 4 * r["sr_month"] ** 2)
print(f"tries {T['tries']}, average correlation {T['avg_corr']:.2f}, effective tries {n:.1f}")
print(f"noise benchmark (annual) {sr0 * np.sqrt(12):.2f}; deflated Sharpe by hand {norm.cdf(zz):.3f}, shipped {r['dsr']:.3f}")"""),
M("""**Years of data needed** to clear 95% once, $`(1.65/\\text{SR})^2`$:"""),
C("""pd.Series({sr: round((1.65 / sr) ** 2) for sr in (1.0, 0.5, 0.3, 0.2)}, name="years").to_frame()"""),
M("""**Carry against trend in trend's weak regimes** (§6.4)."""),
C("""if RUN_ALL: run("l29_quadrants.py")
Q = result("quadrants.json", SHIPPED)
pd.DataFrame([dict(variable=k, quadrant=s, carry=round(v["carry"], 2), trend=round(v["trend"], 2), months=v["months"]) for k, d in Q.items() for s, v in d.items()])"""),
M("""## 7. What did not add; the split by trend's position"""),
C("""if RUN_ALL: run("l29_split_m.py")
pd.DataFrame(result("split.json", SHIPPED)).round(3)"""),
M("""## 8. Shipped against recomputed

With `RUN_ALL`, the rerun's key numbers against the shipped results. With the same downloads they match; a later download can differ slightly, since Yahoo and FRED revise some series."""),
C("""rows = [dict(number="trend + carry, Sharpe", shipped=result("key.json", SHIPPED)["Trend + carry (equal risk)"]["sharpe"], recomputed=result("key.json")["Trend + carry (equal risk)"]["sharpe"]),
        dict(number="deflated Sharpe ratio", shipped=result("tries.json", SHIPPED)["rule"]["dsr"], recomputed=result("tries.json")["rule"]["dsr"]),
        dict(number="value from fundamentals, Sharpe", shipped=result("value_fund.json", SHIPPED)["fundamental"]["2006-2022"]["value"], recomputed=result("value_fund.json")["fundamental"]["2006-2022"]["value"])]
pd.DataFrame(rows).round(4)"""),
M("""**A construction of your own.** Choose one group and one published construction (Asness, Moskowitz and Pedersen 2013 for value, Koijen et al. 2018 for carry). Write down every choice you must make to rebuild it from free data, fix them in a dated plan before looking at results, build it with the machinery of `scripts/l29_bonds_g10.py` (`stream`), and report its correlation with AQR's published series and the number of versions you tried."""),
]
nb = nbf.v4.new_notebook(); nb["cells"] = cells
nb["metadata"] = {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python"}}
nbf.write(nb, OUT); print("written", OUT)
