"""Shared Plotly theme for the research notebooks.

Thin lines, recessive grid, and a fixed colour order so a series keeps its colour across charts.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots

INK, MUTED, GRID, SURFACE = "#0b0b0b", "#898781", "#e1e0d9", "#fcfcfb"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#e87ba4", "#eda100"]


def apply_theme() -> None:
    """Register and activate the 'research' Plotly template as the default."""
    pio.templates["research"] = go.layout.Template(
        layout=dict(
            paper_bgcolor=SURFACE,
            plot_bgcolor=SURFACE,
            font=dict(color=INK, size=12),
            colorway=SERIES,
            xaxis=dict(gridcolor=GRID, linecolor=GRID, zeroline=False),
            yaxis=dict(gridcolor=GRID, linecolor=GRID, zeroline=False),
            legend=dict(orientation="h", y=1.1, x=0),
            margin=dict(l=55, r=20, t=60, b=40),
            title=dict(x=0, font=dict(size=14)),
        )
    )
    pio.templates.default = "research"


def weights_heatmap(
    df: pd.DataFrame, title: str, separators: list[int] | None = None, width: int = 900
) -> go.Figure:
    """Assets x eigenvectors heatmap with the weight printed in each cell (NaN cells stay blank).

    `separators` are row positions (0-based, before which a line is drawn) that split asset blocks.
    """
    text = df.round(2).astype(str).where(df.notna(), "")
    fig = go.Figure(
        go.Heatmap(
            z=df.to_numpy(),
            x=list(df.columns),
            y=list(df.index),
            zmin=-1,
            zmax=1,
            zmid=0,
            colorscale="RdBu_r",
            text=text.to_numpy(),
            texttemplate="%{text}",
            textfont=dict(size=11),
            xgap=1,
            ygap=1,
            colorbar=dict(title="weight", thickness=12),
            hovertemplate="%{y} in %{x}: %{z:.3f}<extra></extra>",
        )
    )
    for row in separators or []:
        fig.add_hline(y=row - 0.5, line=dict(color=INK, width=1.5))
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(side="top")
    fig.update_layout(
        title=title,
        width=width,
        height=60 + 28 * len(df),
        hovermode="closest",
        margin=dict(l=60, r=20, t=90, b=20),
    )
    return fig


def eigenvector_bars(
    v: pd.DataFrame,
    cleaned: pd.DataFrame,
    titles: list[str],
    block_of: dict[str, str],
    cols: int = 4,
) -> go.Figure:
    """One bar chart of weights per eigenvector; assets outside the cleaned set are faded."""
    blocks = list(dict.fromkeys(block_of.values()))
    colour = {b: SERIES[i % len(SERIES)] for i, b in enumerate(blocks)}
    n = v.shape[1]
    rows = -(-n // cols)
    fig = make_subplots(
        rows=rows,
        cols=cols,
        subplot_titles=titles,
        shared_yaxes=True,
        vertical_spacing=0.09,
        horizontal_spacing=0.03,
    )
    for i, pc in enumerate(v):
        r, c = divmod(i, cols)
        keep = cleaned[pc].notna().to_numpy()
        fig.add_bar(
            x=list(v.index),
            y=v[pc].to_numpy(),
            showlegend=False,
            marker=dict(
                color=[colour[block_of[a]] for a in v.index], opacity=np.where(keep, 1.0, 0.18)
            ),
            hovertemplate="%{x}: %{y:.2f}<extra>" + pc + "</extra>",
            row=r + 1,
            col=c + 1,
        )
    for b in blocks:  # legend entries for the block colours
        fig.add_bar(
            x=[None], y=[None], name=b, marker_color=colour[b], showlegend=True, row=1, col=1
        )
    fig.update_yaxes(range=[-1, 1], zeroline=True, zerolinecolor=MUTED)
    fig.update_xaxes(tickangle=90, tickfont=dict(size=9))
    fig.update_annotations(font_size=11)
    fig.update_layout(
        height=250 * rows,
        width=1250,
        barmode="overlay",
        hovermode="closest",
        margin=dict(l=40, r=20, t=120, b=40),
        legend=dict(orientation="h", y=1.07, x=0),
    )
    return fig


def scores_vs_factors(items: list[dict]) -> go.Figure:
    """Per item {title, score, factor, sign}, two panels.

    Left: standardised cumulative score against the factor level. Right: weekly score against the
    weekly factor change, with the fitted line and correlation.
    """
    n = len(items)
    fig = make_subplots(
        rows=n,
        cols=2,
        column_widths=[0.62, 0.38],
        vertical_spacing=0.07,
        horizontal_spacing=0.08,
        subplot_titles=[t for it in items for t in (it["title"], "")],
    )
    for i, it in enumerate(items, start=1):
        score, level, sign = it["score"], it["factor"], it["sign"]
        level = level.reindex(score.index.union(level.index)).ffill().reindex(score.index)
        both = pd.concat([score.cumsum(), sign * level], axis=1, sort=True).dropna()
        both = (both - both.mean()) / both.std()
        fig.add_scatter(
            x=both.index,
            y=both.iloc[:, 0],
            name="cumulative score (standardised)",
            mode="lines",
            line=dict(width=1.3, color=SERIES[0]),
            showlegend=(i == 1),
            legendgroup="s",
            row=i,
            col=1,
        )
        fig.add_scatter(
            x=both.index,
            y=both.iloc[:, 1],
            name="factor level (standardised)",
            mode="lines",
            line=dict(width=1.3, color=SERIES[1]),
            showlegend=(i == 1),
            legendgroup="f",
            row=i,
            col=1,
        )
        wk = pd.concat(
            [score.resample("W-FRI").sum(), sign * level.resample("W-FRI").last().diff()],
            axis=1,
            sort=True,
        ).dropna()
        x, y = wk.iloc[:, 1].to_numpy(), wk.iloc[:, 0].to_numpy()
        slope, icpt = np.polyfit(x, y, 1)
        xs = np.array([x.min(), x.max()])
        fig.add_scatter(
            x=x,
            y=y,
            mode="markers",
            marker=dict(size=4, color=SERIES[0], opacity=0.45),
            showlegend=False,
            hovertemplate="factor chg %{x:.3f}, score %{y:.2f}<extra></extra>",
            row=i,
            col=2,
        )
        fig.add_scatter(
            x=xs,
            y=slope * xs + icpt,
            mode="lines",
            line=dict(width=1.5, color=INK),
            showlegend=False,
            row=i,
            col=2,
        )
        fig.add_annotation(
            text=f"weekly r = {np.corrcoef(x, y)[0, 1]:+.2f}  (n = {len(x)})",
            showarrow=False,
            xref=f"x{2 * i} domain",
            yref=f"y{2 * i} domain",
            x=0.02,
            y=0.96,
            xanchor="left",
            yanchor="top",
            font=dict(size=12),
        )
    fig.update_annotations(font_size=12, selector=dict(showarrow=None))
    fig.update_layout(
        height=280 * n,
        width=1250,
        hovermode="closest",
        margin=dict(l=50, r=20, t=130, b=40),
        legend=dict(orientation="h", y=1.05, x=0),
    )
    return fig


_BROWSERS = (
    "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
    "C:/Program Files/Microsoft/Edge/Application/msedge.exe",
    "C:/Program Files/Google/Chrome/Application/chrome.exe",
    "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
)


def _find_browser() -> str | None:
    for path in _BROWSERS:
        if Path(path).exists():
            return path
    return shutil.which("msedge") or shutil.which("google-chrome") or shutil.which("chromium")


def save_figure(fig: go.Figure, name: str, folder: str | Path, png: bool = True) -> Path:
    """Save a figure as interactive HTML and (if a Chromium browser is installed) a PNG.

    The HTML shares one plotly.min.js in the folder so files stay small and open offline. The PNG
    is a headless-browser screenshot of that HTML, sized from the figure's width and height.
    Returns the HTML path; a missing browser or a failed screenshot only skips the PNG.
    """
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    html = folder / f"{name}.html"
    fig.write_html(html, include_plotlyjs="directory", config={"displayModeBar": False})
    browser = _find_browser() if png else None
    if browser:
        width = int(fig.layout.width or 1000) + 40
        height = int(fig.layout.height or 500) + 70
        cmd = [
            browser,
            "--headless=new",
            "--disable-gpu",
            "--hide-scrollbars",
            f"--window-size={width},{height}",
            "--virtual-time-budget=8000",
            f"--screenshot={folder / (name + '.png')}",
            html.resolve().as_uri(),
        ]
        try:
            subprocess.run(cmd, capture_output=True, timeout=90, check=False)
        except (OSError, subprocess.TimeoutExpired):
            pass
    return html
