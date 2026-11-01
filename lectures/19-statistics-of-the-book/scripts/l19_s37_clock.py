"""Lecture 19 §3.7, H19-H23 (results/hypotheses.md, fixed 2026-10-31): does the book have a clock? Round-time slots of Lecture 13 §7 on the book.
Per second on all days, one timeline: spread wider than one tick, depth in the best 5 levels (q_bid5 + q_ask5), depth asymmetry
(q_bid5 - q_ask5) and mid at the end of each second (carried forward over seconds without an update), from L19_OUT/state; book updates and
pulls per second (Lecture 18, L18_OUT/pulls); net taker flow per second (trades). H19-H22: per occurrence of a slot or control, the measure in
its window and its baseline over the hour ending 5 minutes before the slot; per day ratio = sum of window values / sum of baselines;
d = ratio(slot) - ratio(control); mean d over the days other than 10 Oct, one-sided bootstrap over days, Benjamini-Hochberg over 22 tests.
H23: at the start s of minutes :00/:30 and of the controls, rank correlation per day of the return from s - 30 min to s - 5 s with the change
in depth asymmetry (s - 5 s to s + 10 s) and with net taker flow over [s, s + 10 s); slot minus control, bootstrap over days, BH over 2 tests.
Output: L19_OUT/l19_s37_stats.json, l19_s37_profile.parquet (around each slot), l19_s37_second.parquet (by second of the minute)."""
import json, sys, time
from pathlib import Path
import numpy as np, polars as pl, psutil
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l19 as L19
OUT = L19.OUT; CASC = L19.CASC; N = 86_400
DAYS = L19.days(); T0 = int(np.datetime64(f"{DAYS[0]}T00:00:00", "s").astype(np.int64)); S = N * len(DAYS)
wide = np.full(S, np.nan, np.float32); depth = np.full(S, np.nan, np.float32); asym = np.full(S, np.nan, np.float32); mid = np.full(S, np.nan)
upd = np.zeros(S, np.float32); pull = np.zeros(S, np.float32); ti = np.zeros(S, np.float32)
for i, d in enumerate(DAYS):
    while psutil.virtual_memory().available < 0.2e9: print("waiting for free memory", flush=True); time.sleep(20)
    o = i * N; inday = (pl.col("s") >= o) & (pl.col("s") < o + N)
    st = pl.read_parquet(L19.STATE / f"{d}.parquet", columns=["ts", "bid", "ask", "q_bid5", "q_ask5"]).group_by((pl.col("ts") // 1000 - T0).alias("s")).agg(
        ((pl.col("ask") - pl.col("bid")).last() > 1).cast(pl.Float32).alias("w"), (pl.col("q_bid5") + pl.col("q_ask5")).last().alias("q"),
        (pl.col("q_bid5") - pl.col("q_ask5")).last().alias("a"), ((pl.col("bid") + pl.col("ask")) / 2).last().alias("m")).filter(inday)
    ix = st["s"].to_numpy(); wide[ix] = st["w"].to_numpy(); depth[ix] = st["q"].to_numpy(); asym[ix] = st["a"].to_numpy(); mid[ix] = st["m"].to_numpy()
    pu = pl.read_parquet(L19.PULLS / f"{d}.parquet", columns=["ts", "pull"]).group_by((pl.col("ts") // 1000 - T0).alias("s")).agg(
        pl.len().alias("n"), pl.col("pull").sum().alias("p")).filter(inday)
    upd[pu["s"].to_numpy()] = pu["n"].to_numpy(); pull[pu["s"].to_numpy()] = pu["p"].to_numpy()
    tr = pl.read_parquet(L19.TRADES / f"{d}.parquet", columns=["ts", "side", "size"]).group_by((pl.col("ts") // 1000 - T0).alias("s")).agg(
        (pl.col("side") * pl.col("size")).sum().alias("x")).filter(inday)
    ti[tr["s"].to_numpy()] = tr["x"].to_numpy()
    print(d, flush=True)
for a in (wide, depth, asym, mid):                                          # carry the last state forward over seconds without an update
    m = np.isnan(a); ix = np.where(~m, np.arange(S), 0); np.maximum.accumulate(ix, out=ix); a[:] = a[ix]
cs = {k: np.concatenate([[0.0], np.cumsum(v, dtype=np.float64)]) for k, v in (("wide", wide), ("depth", depth), ("upd", upd), ("pull", pull), ("ti", ti))}
win = lambda k, a, b: cs[k][b] - cs[k][a]                                  # sum over seconds [a, b)

SLOTS = {"funding_00": lambda h, m: m == 0 and h in (0, 8, 16), "other_00": lambda h, m: m == 0 and h not in (0, 8, 16), "m30": lambda h, m: m == 30,
         "m15_45": lambda h, m: m in (15, 45), "m59": lambda h, m: m == 59, "control": lambda h, m: m in (7, 17, 37, 47)}
starts = {k: [(d, i * N + h * 3600 + m * 60) for i, d in enumerate(DAYS) for h in range(24) for m in range(60) if f(h, m)] for k, f in SLOTS.items()}
MEAS = {"H19_spread": ("wide", 0, 60), "H20a_depth": ("depth", 0, 60), "H20b_depth_before": ("depth", -10, 0), "H21_pulls": ("pull", 0, 60)}


def ratio_by_day(k, meas, a0, a1):
    """Per day: sum of window values / sum of baselines, each baseline the hour ending 5 minutes before the slot, scaled to the window length."""
    out = {}
    for d in DAYS:
        s = np.array([x for dd, x in starts[k] if dd == d]); s = s[s - 3900 >= 0]
        if not len(s): continue
        if meas == "pull":
            v = win("pull", s + a0, s + a1).sum() / max(win("upd", s + a0, s + a1).sum(), 1)
            b = win("pull", s - 3900, s - 300).sum() / win("upd", s - 3900, s - 300).sum()
        else:
            v = win(meas, s + a0, s + a1).sum() / (len(s) * (a1 - a0)); b = win(meas, s - 3900, s - 300).sum() / (len(s) * 3600)
        out[d] = v / b
    return out


DD = [d for d in DAYS if d != CASC]; INS = [d for d in DD if d < CASC]; OOS = [d for d in DD if d > CASC]
R = {"tests": {}, "levels": {}, "H23": {}}


def boot_test(rng, x_by_day, expect_pos):
    x = np.array([x_by_day[d] for d in DD]); bs = np.array([x[rng.integers(0, len(x), len(x))].mean() for _ in range(2000)])
    p = max(float(np.mean(bs <= 0) if expect_pos else np.mean(bs >= 0)), 1 / 2001)
    return dict(mean_d=float(x.mean()), ci=np.quantile(bs, [0.025, 0.975]).tolist(), p=p, expect="+" if expect_pos else "-", days_pos=int((x > 0).sum()),
                ins=float(np.mean([x_by_day[d] for d in INS])), oos=float(np.mean([x_by_day[d] for d in OOS])), casc=x_by_day.get(CASC))


def bh(tests):
    p = {k: v["p"] for k, v in tests.items()}; m = len(p); order = sorted(p, key=p.get)
    kmax = max([i + 1 for i, h in enumerate(order) if p[h] <= (i + 1) / m * 0.05], default=0)
    for i, h in enumerate(order): tests[h].update(rank=i + 1, limit=(i + 1) / m * 0.05, holds=i < kmax)


# ---- H19-H22 ----
rng = np.random.default_rng(1937); D = {}
for mname, (meas, a0, a1) in MEAS.items():
    ctrl = ratio_by_day("control", meas, a0, a1)
    for k in SLOTS:
        if k == "control": continue
        r = ratio_by_day(k, meas, a0, a1); diff = {d: r[d] - ctrl[d] for d in r if d in ctrl}; D[(mname, k)] = diff
        R["levels"][f"{mname}|{k}"] = dict(slot=float(np.mean([r[d] for d in DD])), control=float(np.mean([ctrl[d] for d in DD])))
        R["tests"][f"{mname}|{k}"] = boot_test(rng, diff, meas in ("wide", "pull"))
for mname, pos in (("H19_spread", True), ("H20a_depth", False)):
    a, b = D[(mname, "funding_00")], D[(mname, "other_00")]
    R["tests"][f"H22|{mname}"] = boot_test(rng, {d: a[d] - b[d] for d in a if d in b}, pos)
bh(R["tests"])
# the spread in plain shares: seconds with a spread wider than one tick, slot minutes and control minutes, all days but 10 Oct
R["wide_share"] = {}
for k in SLOTS:
    s = np.array([x for dd, x in starts[k] if dd != CASC]); R["wide_share"][k] = dict(seconds=int(win("wide", s, s + 60).sum()), of=int(60 * len(s)),
                                                                                     days=int(len({dd for dd, x in starts[k] if dd != CASC and win("wide", x, x + 60) > 0})))

# ---- H23 ----
rows = []
for k, lab in (("other_00", "round"), ("funding_00", "round"), ("m30", "round"), ("control", "control")):
    for d, s in starts[k]:
        if (k == "control" and (s // 60) % 60 not in (7, 17, 37, 47)) or s - 1800 < 0 or s + 11 > S: continue
        rows.append(dict(day=d, s=s, slot=lab, r=1e4 * np.log(mid[s - 5] / mid[s - 1800]), dasym=float(asym[s + 10] - asym[s - 5]), flow=float(win("ti", s, s + 10))))
X = pl.DataFrame(rows).sort("s").drop_nans()
sp = lambda a, b: float(np.corrcoef(pl.Series(a).rank().to_numpy(), pl.Series(b).rank().to_numpy())[0, 1])
C = {}
for (d, k), g in X.group_by("day", "slot"): C.setdefault(d, {})[k] = dict(depth=sp(g["r"], g["dasym"]), flow=sp(g["r"], g["flow"]))
rng = np.random.default_rng(1923)
for part, key in (("H23a", "depth"), ("H23b", "flow")):
    R["H23"][part] = boot_test(rng, {d: C[d]["round"][key] - C[d]["control"][key] for d in C}, True)
    R["H23"][part].update(corr_round=float(np.mean([C[d]["round"][key] for d in DD])), corr_control=float(np.mean([C[d]["control"][key] for d in DD])),
                          casc_round=C[CASC]["round"][key] if CASC in C else None)
bh(R["H23"])
R["H23_size"] = X.filter(pl.col("day") != CASC).group_by("slot").agg(pl.col("flow").abs().mean().alias("abs_flow_btc"), pl.len().alias("n")).to_dicts()

# ---- descriptive: around each slot (-60..+60 s), and by second of the minute ----
rows = []
for k in SLOTS:
    s = np.array([x for dd, x in starts[k] if dd != CASC]); s = s[(s - 3900 >= 0) & (s + 61 < S)]
    bw, bq = win("wide", s - 3900, s - 300).sum() / (len(s) * 3600), win("depth", s - 3900, s - 300).sum() / (len(s) * 3600)
    bp = win("pull", s - 3900, s - 300).sum() / win("upd", s - 3900, s - 300).sum()
    for t in range(-60, 61):
        rows.append(dict(slot=k, t=t, wide=float(wide[s + t].mean() / bw), depth=float(depth[s + t].mean() / bq), pulls=float(pull[s + t].sum() / max(upd[s + t].sum(), 1) / bp)))
pl.DataFrame(rows).write_parquet(OUT / "l19_s37_profile.parquet")
keep = np.ones(S, bool); keep[DAYS.index(CASC) * N:(DAYS.index(CASC) + 1) * N] = False
sec = np.arange(S); hr = sec // 3600; qh = (np.bincount(hr, depth, minlength=hr.max() + 1) / np.bincount(hr, minlength=hr.max() + 1))[hr]
F = pl.DataFrame(dict(sec=(sec % 60)[keep], grp=np.where(np.isin((sec // 60) % 60, [0, 30]), "minute :00 or :30", "other minutes")[keep],
                      q=(depth / qh)[keep], p=pull[keep], n=upd[keep]))
rate = float(F["p"].sum() / F["n"].sum())
F.group_by("grp", "sec").agg(pl.col("q").mean().alias("depth"), (pl.col("p").sum() / pl.col("n").sum() / rate).alias("pulls")).sort("grp", "sec").write_parquet(
    OUT / "l19_s37_second.parquet")
(OUT / "l19_s37_stats.json").write_text(json.dumps(R, default=float))
for h, v in sorted({**R["tests"], **R["H23"]}.items(), key=lambda x: x[1]["p"]):
    print(f"{h:32s} d {v['mean_d']:+.4f} [{v['ci'][0]:+.4f}, {v['ci'][1]:+.4f}] in {v['ins']:+.4f} out {v['oos']:+.4f} p {v['p']:.4f} {'HOLDS' if v['holds'] else 'fails'}")
print(R["wide_share"]); print(R["H23_size"])
