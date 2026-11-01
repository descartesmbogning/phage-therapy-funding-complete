"""Shared figure style and reusable plotting blocks.

Every function draws on a Matplotlib axis you pass in, so the same block can be
used in a single figure or in small multiples. Colours come from phagefund.PALETTE
(categorical, fixed order) and SEQ (one-hue amber ramp for heatmaps). Figures carry no logo
or credit line, for journal use.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap

import phagefund as pf

# Sequential amber ramp, light to dark
SEQ = ["#fbe9c7", "#f6cf85", "#eeb043", "#d98e0b", "#b87500", "#8f5a00", "#5f3c00"]
SEQ_CMAP = LinearSegmentedColormap.from_list("cognosx_amber", SEQ)
ENGAGEMENT_COLORS = dict(zip(pf.ENGAGEMENT_LABELS, pf.PALETTE[:4]))

STYLE = {
    "font.family": "sans-serif", "font.sans-serif": pf.FONT_SANS, "font.monospace": pf.FONT_MONO,
    "font.size": 10, "text.color": pf.INK, "axes.titlecolor": pf.INK, "axes.titlesize": 11, "axes.titleweight": "bold", "axes.titlelocation": "left",
    "axes.edgecolor": pf.INK2, "axes.labelcolor": pf.INK2, "xtick.color": pf.INK2, "ytick.color": pf.INK2,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "axes.axisbelow": True,
    "grid.color": pf.GRID, "grid.linewidth": 0.8, "figure.dpi": 110, "savefig.dpi": 300,
    "savefig.bbox": "tight", "legend.frameon": False,
}


def use_style() -> None:
    plt.rcParams.update(STYLE)


def save(fig, folder: Path, name: str) -> None:
    for ext in ("png", "pdf"):
        fig.savefig(Path(folder) / f"{name}.{ext}")


def heatmap(ax, table: pd.DataFrame, fmt: str = "{:.0f}", label: str = "", vmax: float | None = None,
            show_zero: bool = False, cbar: bool = True):
    """Annotated one-hue heatmap; zero cells are left white."""
    v = table.values.astype(float)
    cmap = SEQ_CMAP.copy()
    cmap.set_bad("white")                      # zero = empty cell, not the lightest blue
    shown = v if show_zero else np.ma.masked_equal(v, 0)
    im = ax.imshow(shown, cmap=cmap, aspect="auto", vmin=0, vmax=vmax or np.nanmax(v))
    ax.set_xticks(range(table.shape[1]), table.columns)
    ax.set_yticks(range(table.shape[0]), table.index)
    ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)
    hi = (vmax or np.nanmax(v)) * 0.55
    for i in range(v.shape[0]):
        for j in range(v.shape[1]):
            if v[i, j] or show_zero:
                ax.text(j, i, fmt.format(v[i, j]), ha="center", va="center", fontsize=7.5,
                        color="white" if v[i, j] > hi else pf.INK)
    if cbar:
        cb = ax.figure.colorbar(im, ax=ax, fraction=0.025, pad=0.02)
        cb.outline.set_visible(False)
        cb.ax.tick_params(labelsize=8)
        if label:
            cb.set_label(label, fontsize=8.5, color=pf.INK2)
    return im


def engagement_panel(ax, table: pd.DataFrame, title: str = "", legend: bool = False,
                     partial_year: int = pf.PARTIAL_YEAR):
    """Entities per year by engagement label, one line per label."""
    years = table.index.values
    for lab in pf.ENGAGEMENT_LABELS:
        ax.plot(years, table[lab].values, color=ENGAGEMENT_COLORS[lab], lw=2, label=lab)
    ax.axvspan(partial_year - 0.5, partial_year + 0.5, color=pf.GRID, alpha=0.6, lw=0)
    ax.set_xlim(years.min() - 0.5, years.max() + 0.5)
    ax.set_ylim(0, None)
    if title:
        ax.set_title(title)
    if legend:
        ax.legend(loc="upper left", fontsize=8.5, handlelength=1.5)
    return ax


def topic_dendrogram(ax, sim: pd.DataFrame):
    """Average-linkage dendrogram on 1 - Jaccard similarity."""
    from scipy.cluster.hierarchy import dendrogram, linkage
    from scipy.spatial.distance import squareform
    dist = squareform(1 - sim.values, checks=False)
    dendrogram(linkage(dist, "average"), labels=list(sim.index), orientation="right", ax=ax,
               color_threshold=0, above_threshold_color=pf.INK2)
    ax.grid(axis="y", visible=False)
    ax.tick_params(axis="y", labelsize=9, length=0)
    ax.set_xlabel("1 − Jaccard similarity")
    return ax


def sankey_html(flows: pd.DataFrame, path: Path, top: int = 25, title: str = "") -> pd.DataFrame:
    """Interactive funder-country -> recipient-country Sankey diagram.

    Keeps the `top` largest flows; returns the flows drawn so they can be tabled.
    """
    import plotly.graph_objects as go
    f = flows.nlargest(top, "usd_frac").copy()
    src = [f"{c} (funder)" for c in f["Funder Country"]]
    dst = [f"{c} (recipient)" for c in f["Recipient country"]]
    nodes = list(dict.fromkeys(src + dst))
    idx = {n: i for i, n in enumerate(nodes)}
    link_col = ["rgba(154,152,144,0.35)" if dom else "rgba(201,128,0,0.6)" for dom in f["domestic"]]
    fig = go.Figure(go.Sankey(
        node=dict(label=nodes, pad=12, thickness=12, color=[pf.PALETTE[0]] * len(nodes)),
        link=dict(source=[idx[s] for s in src], target=[idx[t] for t in dst],
                  value=(f["usd_frac"] / 1e6).round(2), color=link_col,
                  hovertemplate="%{source.label} → %{target.label}: USD %{value:.1f}M<extra></extra>")))
    fig.update_layout(title=title, font=dict(family="Inter, Helvetica Neue, Arial, sans-serif", size=12, color=pf.INK), height=700, margin=dict(l=10, r=10, t=50, b=10))
    fig.write_html(str(path), include_plotlyjs="cdn")
    return f
