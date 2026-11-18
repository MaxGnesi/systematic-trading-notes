"""Builds lectures/24-a-live-trend-bot/24_live_trend_bot.ipynb. Usage: python make_nb24.py <output path>."""
import sys
from pathlib import Path
import nbformat as nbf

OUT = Path(sys.argv[1])
M, C = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
cells = [
M(r"""# Lecture 24 notebook: a live trend bot

This notebook replays Lecture 24. The lecture's code is the capstone itself, in `capstone/` at the root of the repository; this notebook runs its offline tests, checks the inverse contract's accounting by hand, shows the stored backtest behind the lecture's tables and redraws the two figures as `figures/nb_*.png`. Nothing here connects to an exchange with keys or places an order: the live bot is started from the command line, as §10 explains, never from a notebook.

The backtest uses Deribit's public minute candles and funding of BTC-PERPETUAL since 2019, downloaded once by `capstone/backtest/download.py` into `capstone/data/history` (not committed, about 15 minutes). `RUN_ALL` downloads what is missing and reruns the backtest, writing to `capstone/data/l24_results`; recomputed results never overwrite the shipped ones.

| § | Content | Lecture |
|---|---|---|
| 0 | Settings | |
| 1 | The offline tests: order book, bars, database, keys rule; signature login and the gateway's safety rules; settings, take profit and inverse accounting | §2-§8 |
| 2 | The inverse contract, by hand | §8 |
| 3 | The backtest: the strategy and its rivals | §9 |
| 4 | The figures | §4, §9 |
| 5 | Shipped against recomputed | |"""),
M("## 0. Settings"),
C(r"""import json, os, subprocess, sys, time
from pathlib import Path
import pandas as pd
from IPython.display import Image, display

HERE = Path.cwd(); REPO = HERE.parents[1]; FIG = HERE / "figures"
SHIPPED = HERE / "results" / "backtest.json"; WORK = REPO / "capstone" / "data" / "l24_results"; WORK.mkdir(parents=True, exist_ok=True)
HISTORY = REPO / "capstone" / "data" / "history"
RUN_ALL = False                                                            # True: download the history if missing and rerun the backtest
pd.set_option("display.width", 200); pd.set_option("display.max_columns", 20)


def run(*args, show=False):
    "Run a module or script from the repository root in a fresh process; figures as nb_*, the backtest to WORK."
    t0 = time.time()
    env = {**os.environ, "L24_PREFIX": "nb_", "L24_BACKTEST_OUT": str(WORK / "backtest.json"), "PYTHONIOENCODING": "utf-8"}
    p = subprocess.run([sys.executable, *args], cwd=REPO, capture_output=True, text=True, encoding="utf-8", env=env)
    if p.returncode:
        print(p.stdout[-2000:], p.stderr[-4000:]); raise RuntimeError(f"{' '.join(args)} failed")
    print(f"{' '.join(args)}: {time.time() - t0:.0f} s")
    if show: print((p.stdout + p.stderr)[-3000:])


def pictures(*names):
    for nm in names:
        f = FIG / f"nb_{nm}.png"
        display(Image(filename=str(f))) if f.exists() else print("not drawn yet:", f.name)


print("repository:", REPO, "| history:", HISTORY, "exists" if HISTORY.exists() else "missing", "| recomputed results:", WORK)"""),
M(r"""## 1. The offline tests

Three test files, none of which touches the network: step 1 checks the local order book (snapshots, changes, gaps), the hourly bars, the database and its migrations, and that no key file is ever tracked by git; step 2 checks the Ed25519 signature login and the gateway's safety rules (the size limit, no market orders unless allowed, reads retried, orders never retried); step 3 checks the settings, the take profit and the backtest's inverse accounting."""),
C(r"""for step in (1, 2, 3):
    run("-m", f"capstone.tests.test_step{step}", show=True)"""),
M(r"""## 2. The inverse contract, by hand

BTC-PERPETUAL is an inverse contract: the position is a number of US dollars, and profit and loss are paid in bitcoin, $A\,(1/p_0 - 1/p_1)$ for a long of $A$ dollars from price $p_0$ to $p_1$. The same move up and down is not symmetric in bitcoin."""),
C(r"""A, p0 = 10_000, 50_000
for p1 in (55_000, 45_000):
    btc = A * (1 / p0 - 1 / p1)
    print(f"long {A:,} USD from {p0:,} to {p1:,}: {btc:+.6f} BTC, worth {btc * p1:+,.2f} USD at the exit price")
print("the test of step 3 checks the engine against the first line: +0.018182 BTC")"""),
M(r"""## 3. The backtest: the strategy and its rivals

The stored results behind the lecture's tables: the strategy as fixed (speeds of 2 and 7 days, 5-sigma take profit, taker orders, decisions at :23 with a random delay) and its rivals, on Deribit 2019-2026, account in BTC; then each rival's monthly Sharpe ratio and skew against the strategy, with 90% bands from a block bootstrap of months."""),
C(r"""B = json.loads(SHIPPED.read_text(encoding="utf-8"))
print("history:", B["history"], "|", B["hours"], "decision hours")
cols = ["sharpe", "ann_return", "ann_vol", "max_drawdown", "worst_month", "month_skew", "fees_per_year", "funding_per_year"]
display(pd.DataFrame({k: {c: v[c] for c in cols} for k, v in B["variants"].items()}).T.round(3))
display(pd.DataFrame(B["differences_vs_base_monthly"]).T)
display(pd.DataFrame({k: v["sharpe_by_year"] for k, v in B["variants"].items()}).round(2))"""),
M(r"""**Running everything.** With `RUN_ALL` the cell below downloads the history if it is missing and reruns the backtest of all variants (a few minutes once the history is there)."""),
C(r"""if RUN_ALL:
    if not HISTORY.exists() or len(list(HISTORY.glob("candles_1m_*.parquet"))) < 80: run("-m", "capstone.backtest.download", show=True)
    run("-m", "capstone.backtest.run_backtest", show=True)"""),
M(r"""## 4. The figures

The architecture diagram (§4) and the equity of the strategy and its rivals (§9). The second is recomputed from the minute history with the capstone's own engine, so it needs the history."""),
C(r"""if HISTORY.exists():
    run("lectures/24-a-live-trend-bot/scripts/l24_charts.py")
    pictures("24_architecture", "24_backtest")
else:
    print("history missing: set RUN_ALL = True to download it; showing the lecture's figures")
    for nm in ("24_architecture", "24_backtest"): display(Image(filename=str(FIG / f"{nm}.png")))"""),
M(r"""## 5. Shipped against recomputed

With `RUN_ALL`, the rerun's key numbers against the shipped ones. With the same history they match exactly; Deribit's history does not change, but a later download adds months."""),
C(r"""R = WORK / "backtest.json"
if R.exists():
    N = json.loads(R.read_text(encoding="utf-8"))
    display(pd.DataFrame({k: {"shipped": B["variants"][k]["sharpe"], "recomputed": N["variants"][k]["sharpe"]} for k in B["variants"]}).T.round(4))
else:
    print("nothing recomputed yet: set RUN_ALL = True")"""),
M(r"""**A test of your own.** Change one setting in `capstone/strategies/trend/params.toml` (the speeds, the take-profit threshold, the decision minute) and rerun with `RUN_ALL`. As §9 says, write the change and its reason in `results/hypotheses.md` before looking at the result, and remember that every setting you try is one more try (toolkit card 8)."""),
]
nb = nbf.v4.new_notebook(); nb["cells"] = cells
nb["metadata"] = {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python"}}
nbf.write(nb, OUT); print("written", OUT)
