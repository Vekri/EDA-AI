"""Plotly chart builders for univariate, bivariate, and multivariate views."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from scipy.stats import gaussian_kde

from .theme import INK, LINE, RUST, TEAL, style_fig


def missing_bar(missing: pd.DataFrame) -> go.Figure:
    fig = px.bar(
        missing.sort_values("missing_pct"),
        x="missing_pct",
        y="column",
        orientation="h",
        labels={"missing_pct": "Missing (%)", "column": "Feature"},
    )
    fig.update_traces(marker_color=RUST)
    return style_fig(fig, "Missing values by feature", x="Missing (%)", y="Feature")


def histogram_kde(series: pd.Series, name: str) -> go.Figure:
    s = pd.to_numeric(series, errors="coerce").dropna()
    fig = go.Figure()
    fig.add_trace(
        go.Histogram(
            x=s,
            nbinsx=min(40, max(12, int(np.sqrt(len(s))))),
            marker_color=TEAL,
            opacity=0.72,
            name="Count",
            histnorm="",
        )
    )
    if len(s) >= 8 and s.nunique() > 5:
        xs = np.linspace(float(s.min()), float(s.max()), 200)
        try:
            kde = gaussian_kde(s.values.astype(float))
            dens = kde(xs)
            counts, edges = np.histogram(s, bins=min(40, max(12, int(np.sqrt(len(s))))))
            bin_w = edges[1] - edges[0]
            scaled = dens * len(s) * bin_w
            fig.add_trace(
                go.Scatter(
                    x=xs,
                    y=scaled,
                    mode="lines",
                    line=dict(color=INK, width=2),
                    name="KDE",
                    yaxis="y",
                )
            )
        except Exception:
            pass
    fig.update_layout(bargap=0.04)
    return style_fig(fig, f"Distribution of {name}", x=name, y="Count")


def boxplot(series: pd.Series, name: str) -> go.Figure:
    s = pd.to_numeric(series, errors="coerce")
    fig = go.Figure(
        go.Box(
            y=s,
            name=name,
            marker_color=TEAL,
            line_color=INK,
            boxmean=True,
        )
    )
    return style_fig(fig, f"Spread and outliers — {name}", y=name)


def grouped_box(df: pd.DataFrame, numeric: str, category: str) -> go.Figure:
    tmp = df[[numeric, category]].dropna()
    if tmp[category].nunique() > 16:
        top = tmp[category].value_counts().head(16).index
        tmp = tmp[tmp[category].isin(top)]
    fig = px.box(tmp, x=category, y=numeric, points="outliers")
    fig.update_traces(marker_color=TEAL, line_color=INK)
    return style_fig(fig, f"{numeric} by {category}", x=category, y=numeric)


def category_bar(series: pd.Series, name: str, max_levels: int = 20) -> go.Figure:
    vc = series.dropna().astype(str).value_counts().head(max_levels)
    fig = px.bar(
        x=vc.index.astype(str),
        y=vc.values,
        labels={"x": name, "y": "Count"},
    )
    fig.update_traces(marker_color=TEAL)
    return style_fig(fig, f"Class frequency — {name}", x=name, y="Count")


def scatter(df: pd.DataFrame, x: str, y: str, color: str | None = None) -> go.Figure:
    cols = [x, y] + ([color] if color and color in df.columns else [])
    tmp = df[cols].dropna()
    if len(tmp) > 2500:
        tmp = tmp.sample(2500, random_state=42)
    fig = px.scatter(tmp, x=x, y=y, color=color, opacity=0.7)
    return style_fig(fig, f"{y} vs {x}", x=x, y=y)


def correlation_heatmap(df: pd.DataFrame) -> go.Figure | None:
    num = df.select_dtypes(include=[np.number])
    if num.shape[1] < 2:
        return None
    corr = num.corr(numeric_only=True)
    fig = go.Figure(
        data=go.Heatmap(
            z=corr.values,
            x=list(corr.columns),
            y=list(corr.index),
            colorscale=[
                [0.0, "#9F2D00"],
                [0.5, "#F3EEE4"],
                [1.0, "#0F766E"],
            ],
            zmid=0,
            zmin=-1,
            zmax=1,
            colorbar=dict(title="r"),
            hovertemplate="%{y} × %{x}<br>r = %{z:.3f}<extra></extra>",
        )
    )
    fig.update_xaxes(tickangle=45)
    return style_fig(fig, "Pearson correlation heatmap", x="Feature", y="Feature")


def scatter_matrix(df: pd.DataFrame, columns: list[str], color: str | None = None) -> go.Figure:
    cols = [c for c in columns if c in df.columns][:6]
    tmp = df[cols + ([color] if color and color in df.columns and color not in cols else [])].dropna()
    if len(tmp) > 800:
        tmp = tmp.sample(800, random_state=42)
    fig = px.scatter_matrix(tmp, dimensions=cols, color=color)
    fig.update_traces(diagonal_visible=False, marker=dict(size=4, opacity=0.55))
    return style_fig(fig, "Pair plot (sampled if large)")


def target_bar(balance: dict) -> go.Figure:
    items = list(balance["counts"].items())
    fig = px.bar(x=[k for k, _ in items], y=[v for _, v in items])
    fig.update_traces(marker_color=TEAL)
    return style_fig(fig, "Target class distribution", x="Class", y="Count")


def corr_vs_target(df: pd.DataFrame, target: str) -> go.Figure | None:
    num = df.select_dtypes(include=[np.number]).copy()
    y = df[target]
    if target not in num.columns:
        codes, _ = pd.factorize(y.astype(str).str.strip().str.lower())
        num["_target_enc"] = codes
        tcol = "_target_enc"
    else:
        tcol = target
    if tcol not in num.columns:
        return None
    corr = num.corr(numeric_only=True)[tcol].drop(labels=[tcol], errors="ignore").dropna()
    corr = corr.reindex(corr.abs().sort_values(ascending=True).index)
    if corr.empty:
        return None
    fig = go.Figure(
        go.Bar(
            x=corr.values,
            y=corr.index.astype(str),
            orientation="h",
            marker_color=[TEAL if v >= 0 else RUST for v in corr.values],
        )
    )
    return style_fig(fig, f"Numeric correlation with {target}", x="Pearson r", y="Feature")
