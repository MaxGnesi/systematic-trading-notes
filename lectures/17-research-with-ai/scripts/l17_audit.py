"""Lecture 17: the audit of the course's own record (Lectures 1-16).

Input: results/audit.csv, one row per error that reached a results entry, a figure or the lecture text, classified as fixed in
results/hypotheses.md (type, found by, stage, silent, cost). Output: figures/17_key.png (errors by type, coloured by what found them),
figures/17_stage.png (errors by stage, coloured by what fixing them cost) and results/audit.json (the counts quoted in the text).
"""
import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

from trading_models.plotting import MUTED, SERIES, apply_theme, save_figure

HERE = Path(__file__).resolve().parent
RES, FIG = HERE.parent / "results", HERE.parent / "figures"

TYPES = ["method", "claim", "data", "comparison", "reference"]
FOUND = {  # what found the error -> colour; order = stacking order
    "user review": ("the user's review", SERIES[0]),
    "check of a source or an intermediate result": ("a check of a source or an intermediate result", SERIES[2]),
    "hand check": ("a hand check in the notebook", SERIES[4]),
    "redrawing a figure": ("redrawing a figure", SERIES[3]),
    "verification agent": ("a verification agent", SERIES[1]),
    "later reuse of the data": ("a later lecture reusing the data", MUTED),
    "not recorded": ("not recorded", "#c9c7bf"),
}
STAGES = ["before the result", "after results (before merging)", "after merging", "not recorded"]
COST = {  # what fixing it cost -> class
    "none": "nothing: caught before it was used",
    "text": "text or a table", "table and text": "text or a table", "text and haircut table": "text or a table",
    "in-sample tables redone": "results rerun", "rule and tests rerun": "results rerun", "all streams and tests rerun": "results rerun",
    "three lectures rerun": "results rerun", "all futures results rerun": "results rerun",
    "new data and group rebuilt": "new data, part rebuilt",
}
COST_COL = {"nothing: caught before it was used": "#c9c7bf", "text or a table": SERIES[4], "results rerun": SERIES[1],
            "new data, part rebuilt": SERIES[0]}


def stacked(df, rows, by, colours, labels, title, ytitle, name, height):
    fig = go.Figure()
    for key, (label, col) in ((k, (labels[k], colours[k])) for k in colours):
        n = [int(((df[rows[0]] == r) & (df[by] == key)).sum()) for r in rows[1]]
        fig.add_bar(y=rows[1], x=n, orientation="h", name=label, marker=dict(color=col, line=dict(color="#fcfcfb", width=2)),
                    text=[str(v) if v else "" for v in n], textposition="inside", insidetextanchor="middle", textfont=dict(color="#0b0b0b"))
    fig.update_layout(barmode="stack", title=title, height=height, width=1000, margin=dict(t=90, l=200, r=30, b=150),
                      legend=dict(orientation="h", y=-0.32, x=0, traceorder="normal"), bargap=0.35)
    fig.update_yaxes(autorange="reversed", title_text="")
    fig.update_xaxes(title_text=ytitle, dtick=1)
    save_figure(fig, name, FIG)


if __name__ == "__main__":
    apply_theme()
    df = pd.read_csv(RES / "audit.csv")
    df["cost_class"] = df["cost"].map(COST)
    assert df["cost_class"].notna().all() and df["found_by"].isin(FOUND).all() and df["stage"].isin(STAGES).all() and df["type"].isin(TYPES).all()
    n = len(df)
    stacked(df, ("type", TYPES), "found_by", {k: v[1] for k, v in FOUND.items()}, {k: v[0] for k, v in FOUND.items()},
            f"{n} errors that reached a result, a figure or the text, Lectures 1-16<br><sup>by type of error; colour = what found it; "
            "every one was silent: the code ran and the numbers looked plausible</sup>", "number of errors", "17_key", 500)
    stacked(df, ("stage", STAGES), "cost_class", COST_COL, {k: k for k in COST_COL},
            "When an error was found, and what fixing it cost<br><sup>same errors; colour = the work the fix needed</sup>",
            "number of errors", "17_stage", 450)
    out = {
        "n": n, "silent": int((df["silent"] == "yes").sum()),
        "by_type": df["type"].value_counts().to_dict(), "by_found": df["found_by"].value_counts().to_dict(),
        "by_stage": df["stage"].value_counts().to_dict(), "by_cost": df["cost_class"].value_counts().to_dict(),
        "type_x_found": {t: df.loc[df["type"] == t, "found_by"].value_counts().to_dict() for t in TYPES},
        "stage_x_cost": {s: df.loc[df["stage"] == s, "cost_class"].value_counts().to_dict() for s in STAGES},
        "rule_or_verdict_changed": df.loc[df["rule_or_verdict_changed"] == "yes", "id"].tolist(),
        "logged_in_plan_files": int(df["source"].str.startswith("plan").sum()),
    }
    (RES / "audit.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))
