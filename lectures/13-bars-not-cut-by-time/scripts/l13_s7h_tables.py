"""Lecture 13 §7: results tables from l13_s7h.json, in one format: explicit headers, n, standard errors, q-values."""
import json
from pathlib import Path
import os, sys
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # tables print on any console; Jupyter handles its own
HERE = Path(__file__).resolve().parent                                     # lectures/13-.../scripts
sys.path[:0] = [str(HERE), str(HERE.parents[1] / "12-tick-data-the-tape"), str(HERE.parents[2])]   # this folder, tape.py, trading_models
import tape
L13_RESULTS = tape.ROOT / "interim" / "l13"; L13_RESULTS.mkdir(parents=True, exist_ok=True)          # results: in the data folder, never committed
FIG = Path(os.environ.get("L13_FIG", HERE.parent / "figures")); FIG.mkdir(parents=True, exist_ok=True)
PREFIX = os.environ.get("L13_PREFIX", "nb_")                               # "nb_": the lecture's own figures are never overwritten

S = {r["slot"]: r for r in json.loads((L13_RESULTS / "l13_s7h.json").read_text())["slots"]}
SH = {"Tokyo opening hour (9:00 Tokyo)": "Tokyo opening hour", "London opening hour (8:00 London)": "London opening hour",
      "New York opening hour (9:30 New York)": "New York opening hour", "Around the New York close (15:30 New York)": "New York close, 15:30–16:30",
      "New York night (2:00 New York)": "New York night, 2:00–3:00", "US public holiday on a weekday": "US holiday on a weekday",
      "First minute of the hour, funding (00, 08, 16 UTC)": "Minute :00, with funding", "First minute of the hour, other hours": "Minute :00, other hours",
      "First minute of the half hour (:30)": "Minute :30", "First minute of a quarter (:15, :45)": "Minutes :15 and :45", "Last minute of the hour (:59)": "Minute :59",
      "US inflation release (CPI, 8:30 New York)": "CPI release", "Fed decision (14:00 New York)": "Fed decision",
      "Quarterly expiry, settlement window (07:30-08:00 UTC)": "Quarterly expiry", "Monthly expiry, settlement window": "Monthly expiry",
      "Weekly expiry, settlement window": "Weekly expiry"}
name = lambda s: SH.get(s, s)
sg = lambda x, d=1: f"{x:+.{d}f}".replace("-", "−")
q = lambda x: "< 0.001" if x < 0.001 else f"{x:.3f}"


def ratio(r, k):
    v, c = r[k], r[k + "_ctl"]; se = (v / c) * ((r[k + "_se"] / v) ** 2 + (r[k + "_ctl_se"] / c) ** 2) ** 0.5
    return f"{v / c:.2f} ({v / c - 1.96 * se:.2f}–{v / c + 1.96 * se:.2f})"


def t_h12(slots):
    out = ["| Slot | n | Activity, slot ÷ control (95% interval) | q | Size of moves, slot ÷ control (95% interval) | q |", "|---|---|---|---|---|---|"]
    out += [f"| {name(s)} | {S[s]['n']:,} | {ratio(S[s], 'act')} | {q(S[s]['act_q'])} | {ratio(S[s], 'vol')} | {q(S[s]['vol_q'])} |" for s in slots]
    return "\n".join(out)


def t_h3(slots):
    out = ["| Slot | n | Net aggressive buying, % of dollars: slot (s.e.) | Control (s.e.) | q |", "|---|---|---|---|---|"]
    out += [f"| {name(s)} | {S[s]['n']:,} | {sg(S[s]['flow'])} ({S[s]['flow_se']:.1f}) | {sg(S[s]['flow_ctl'])} ({S[s]['flow_ctl_se']:.1f}) | {q(S[s]['flow_q'])} |" for s in slots]
    return "\n".join(out)


def t_h4(slots):
    d = lambda r, k: (lambda e: 2 if e < 0.1 else (1 if e < 1 else 0))(min(r[k + '_se'], r[k + '_ctl_se']))
    out = ["| Slot | n | Return in the window, bp: slot (s.e.) | Control (s.e.) | q | Return in the window before, bp: slot (s.e.) | Control (s.e.) | q |", "|---|---|---|---|---|---|---|---|"]
    for s in slots:
        r = S[s]
        out.append(f"| {name(s)} | {r['n']:,} | {sg(r['ret'], d(r, 'ret'))} ({r['ret_se']:.{d(r, 'ret')}f}) | {sg(r['ret_ctl'], d(r, 'ret'))} ({r['ret_ctl_se']:.{d(r, 'ret')}f}) | {q(r['ret_q'])} "
                   f"| {sg(r['before'], d(r, 'before'))} ({r['before_se']:.{d(r, 'before')}f}) | {sg(r['before_ctl'], d(r, 'before'))} ({r['before_ctl_se']:.{d(r, 'before')}f}) | {q(r['before_q'])} |")
    return "\n".join(out)


def t_h5(slots):
    out = ["| Slot | n | Correlation, return in the window with return in the next window: slot | Control | Share of occurrences in the same direction: slot | Control | q (slot ≠ control) |",
           "|---|---|---|---|---|---|---|"]
    out += [f"| {name(s)} | {S[s]['n']:,} | {sg(S[s]['follow'], 2)} | {sg(S[s]['follow_ctl'], 2)} | {S[s]['same']:.0%} | {S[s]['same_ctl']:.0%} | {q(S[s]['follow_vs_ctl_q'])} |" for s in slots]
    return "\n".join(out)


ALL = list(S)
SEL12 = ["New York opening hour (9:30 New York)", "Tokyo opening hour (9:00 Tokyo)", "London opening hour (8:00 London)", "New York night (2:00 New York)", "Saturday", "Sunday",
         "US public holiday on a weekday", "First minute of the hour, funding (00, 08, 16 UTC)", "First minute of the hour, other hours", "First minute of the half hour (:30)",
         "Last minute of the hour (:59)", "US inflation release (CPI, 8:30 New York)", "Fed decision (14:00 New York)", "Quarterly expiry, settlement window (07:30-08:00 UTC)",
         "Monthly expiry, settlement window", "Weekly expiry, settlement window"]
SEL3 = ["First minute of the hour, funding (00, 08, 16 UTC)", "Around the New York close (15:30 New York)", "First minute of the hour, other hours", "First minute of the half hour (:30)",
        "First minute of a quarter (:15, :45)", "US inflation release (CPI, 8:30 New York)", "Fed decision (14:00 New York)", "Quarterly expiry, settlement window (07:30-08:00 UTC)",
        "Monthly expiry, settlement window"]
SEL4 = ["First minute of the hour, funding (00, 08, 16 UTC)", "First minute of the half hour (:30)", "First minute of a quarter (:15, :45)", "Fed decision (14:00 New York)",
        "US inflation release (CPI, 8:30 New York)", "Quarterly expiry, settlement window (07:30-08:00 UTC)", "Monthly expiry, settlement window"]
SEL5 = ["US inflation release (CPI, 8:30 New York)", "Fed decision (14:00 New York)", "London opening hour (8:00 London)", "New York opening hour (9:30 New York)",
        "Around the New York close (15:30 New York)", "First minute of the hour, other hours", "First minute of the hour, funding (00, 08, 16 UTC)"]
T = dict(h12=t_h12(SEL12), h3=t_h3(SEL3), h4=t_h4(SEL4), h5=t_h5(SEL5), all12=t_h12(ALL), all3=t_h3(ALL), all4=t_h4(ALL), all5=t_h5(ALL))
(L13_RESULTS / "l13_s7h_tables.json").write_text(json.dumps(T, ensure_ascii=False, indent=1), encoding="utf-8")
if __name__ == "__main__":
    import sys; sys.stdout.reconfigure(encoding="utf-8")
    for k in ("h12", "h3", "h4", "h5"): print(T[k], "\n")
