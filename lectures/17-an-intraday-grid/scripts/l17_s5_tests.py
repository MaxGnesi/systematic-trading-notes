"""Lecture 17 §5: the tests of rules known in advance, pre-fixed. From l17_volswitch.parquet (always on; off while the last finished hour's volatility
exceeds K = 1.5, 2, 3 times its 28-day median) and l17_directions.parquet (rules on top of the switch with K = 2). Steps 25, 50, 100, 200 bp.
Q1, does the rule cut losses: daily net with the rule minus its baseline (always on for the switch; the switch for rules built on it), paired by day.
Q2, does it create an edge: gross > 0. t-statistics on daily values; one-sided p-values (Q1: difference > 0; Q2: gross > 0); Benjamini-Hochberg adjusted p-values (q)
within each question, an effect counting if q < 0.05 (as in Lectures 13 and 15), on 2021-24; 2025-26 reported as the out-of-sample check. Time-of-day blocks: Q2 only."""
import json
from pathlib import Path
import os, sys
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # tables print on any console; Jupyter handles its own
HERE = Path(__file__).resolve().parent                                     # lectures/17-.../scripts
sys.path[:0] = [str(HERE), str(HERE.parents[1] / "16-trend-on-the-tape" / "scripts"), str(HERE.parents[1] / "13-bars-not-cut-by-time" / "scripts"),
                str(HERE.parents[1] / "12-tick-data-the-tape"), str(HERE.parents[2])]
import tape
L17_RESULTS = Path(os.environ.get("L17_RESULTS", tape.ROOT / "interim" / "l17")); L17_RESULTS.mkdir(parents=True, exist_ok=True)   # results: in the data folder, never committed
ONE_YEAR = os.environ.get("L17_ONE_YEAR")                                # a check: run the tape scripts on one year only
FIG = Path(os.environ.get("L17_FIG", HERE.parent / "figures")); FIG.mkdir(parents=True, exist_ok=True)
PREFIX = os.environ.get("L17_PREFIX", "nb_")                               # "nb_": the lecture's own figures are never overwritten
import numpy as np, polars as pl
from scipy.stats import norm


V = pl.read_parquet(L17_RESULTS / "l17_volswitch.parquet").filter(pl.col("step") != 10).select("day", "step", "rule", "gross", "net", "year")
D = pl.read_parquet(L17_RESULTS / "l17_directions.parquet").filter(pl.col("rule") != "always on").select("day", "step", "rule", "gross", "net", "year")
X = pl.concat([V.with_columns(pl.col("day").cast(pl.Float64)), D.with_columns(pl.col("day").cast(pl.Float64))]).with_columns(
    pl.when(pl.col("year") <= 2024).then(pl.lit("IS")).otherwise(pl.lit("OOS")).alias("p"))
BASE = {"off above 1.5": "always on", "off above 2.0": "always on", "off above 3.0": "always on"}
for r in ("skew, sign", "skew, strong", "off in strong trend", "channel"): BASE[r] = "vol switch (base)"
t_of = lambda x: float(np.mean(x) / np.std(x, ddof=1) * np.sqrt(len(x)))
rows = []
for (st, rule), d in X.group_by("step", "rule"):
    for p in ("IS", "OOS"):
        e = d.filter(pl.col("p") == p).sort("day")
        rec = dict(step=st, rule=rule, p=p, gross=e["gross"].mean(), t_gross=t_of(e["gross"].to_numpy()),
                   sharpe=float(e["net"].mean() / e["net"].std() * np.sqrt(365)), w1=e["net"].quantile(0.01))
        if rule in BASE:
            b = X.filter((pl.col("step") == st) & (pl.col("rule") == BASE[rule]) & (pl.col("p") == p)).select("day", pl.col("net").alias("nb"))
            j = e.join(b, on="day"); dif = (j["net"] - j["nb"]).to_numpy()
            rec.update(diff=float(dif.mean()), t_diff=t_of(dif))
        rows.append(rec)
R = pl.DataFrame(rows)
def bh(df, tcol):
    """Benjamini-Hochberg: sort the m p-values, q_i = min over j >= i of p_j * m / j."""
    df = df.with_columns(pl.col(tcol).map_elements(lambda t: float(norm.sf(t)), return_dtype=pl.Float64).alias("pv")).sort("pv")
    p = df["pv"].to_numpy(); m = len(p); q = np.minimum.accumulate((p * m / np.arange(1, m + 1))[::-1])[::-1]
    return df.with_columns(pl.Series("q", np.minimum(q, 1.0)), pl.Series("bh", q < 0.05))
IS = R.filter(pl.col("p") == "IS")
Q1 = bh(IS.filter(pl.col("rule").is_in(list(BASE))), "t_diff"); Q2 = bh(IS.filter(~pl.col("rule").str.starts_with("maker") & (pl.col("rule") != "vol switch (base)")), "t_gross")   # the base is "off above 2.0"
O = R.filter(pl.col("p") == "OOS").select("step", "rule", pl.col("diff").alias("diff_oos"), pl.col("t_diff").alias("t_diff_oos"), pl.col("gross").alias("gross_oos"),
                                           pl.col("t_gross").alias("t_gross_oos"), pl.col("sharpe").alias("sharpe_oos"), pl.col("w1").alias("w1_oos"))
pl.Config.set_tbl_rows(100); pl.Config.set_tbl_width_chars(250); pl.Config.set_tbl_cols(20); pl.Config.set_float_precision(3)
print("Q1: does the rule cut losses (net vs baseline)?"); print(Q1.join(O, on=["step", "rule"]).select("step", "rule", "diff", "t_diff", "q", "bh", "diff_oos", "t_diff_oos").sort("rule", "step"))
print("Q2: does it create an edge (gross > 0)?"); print(Q2.join(O, on=["step", "rule"]).select("step", "rule", "gross", "t_gross", "q", "bh", "gross_oos", "t_gross_oos").filter(pl.col("t_gross") > 0).sort("t_gross", descending=True))
print("tests:", len(Q1), len(Q2))
R.write_parquet(L17_RESULTS / "l17_s5_tests.parquet")
(L17_RESULTS / "l17_s5_tests.json").write_text(json.dumps(dict(q1=Q1.join(O, on=["step", "rule"]).to_dicts(), q2=Q2.join(O, on=["step", "rule"]).to_dicts()), indent=1, default=float))
