"""JSON payloads for the React EDA UI."""

from __future__ import annotations

import json
from typing import Any

import pandas as pd

from .charts import (
    boxplot,
    category_bar,
    corr_vs_target,
    correlation_heatmap,
    grouped_box,
    histogram_kde,
    missing_bar,
    scatter,
    scatter_matrix,
    target_bar,
)
from .features import preview_model_ready, recommend_prep
from .profile import (
    column_kinds,
    compact_head,
    likely_target_columns,
    memory_mb,
    structure_table,
    summary_statistics,
)
from .quality import build_quality_report
from .theme import apply_plotly_theme

apply_plotly_theme()


def records(df: pd.DataFrame | None, n: int | None = None) -> list[dict[str, Any]]:
    if df is None or len(df) == 0:
        return []
    view = df if n is None else df.head(n)
    return json.loads(view.to_json(orient="records", date_format="iso"))


def fig_json(fig) -> dict[str, Any] | None:
    if fig is None:
        return None
    return json.loads(fig.to_json())


def serialize_quality(quality: dict[str, Any]) -> dict[str, Any]:
    return {
        "n_rows": quality["n_rows"],
        "n_cols": quality["n_cols"],
        "duplicate_rows": quality["duplicate_rows"],
        "score": quality["score"],
        "status": quality["status"],
        "missing": records(quality["missing"]),
        "outliers": records(quality["outliers"]),
        "inconsistent": quality["inconsistent"],
        "invalid": quality["invalid"],
        "leakage": quality["leakage"],
        "constant": quality["constant"],
        "near_constant": quality["near_constant"],
        "ids": quality["ids"],
        "balance": quality["balance"],
    }


def build_profile(df: pd.DataFrame, source_name: str, target: str | None) -> dict[str, Any]:
    kinds = column_kinds(df)
    guesses = likely_target_columns(df)
    if target is None and guesses:
        target = guesses[0]
    if target == "":
        target = None
    quality = build_quality_report(df, target)
    stats = summary_statistics(df)
    miss = quality["missing"]
    cat_opts = [c for c in kinds["categorical"] if c not in quality["ids"]] or kinds["categorical"]

    charts: dict[str, Any] = {
        "missing": fig_json(missing_bar(miss)) if len(miss) else None,
        "heatmap": fig_json(correlation_heatmap(df)),
        "target": None,
        "corr_vs_target": fig_json(corr_vs_target(df, target)) if target else None,
        "pair": None,
    }
    if target and quality["balance"]:
        if quality["balance"].get("kind") == "classification":
            charts["target"] = fig_json(target_bar(quality["balance"]))
        else:
            charts["target"] = fig_json(histogram_kde(df[target], target))
    pair_cols = kinds["numeric"][:6]
    if len(pair_cols) >= 2:
        charts["pair"] = fig_json(
            scatter_matrix(df, pair_cols, color=target if target in df.columns else None)
        )

    return {
        "source_name": source_name,
        "n_rows": int(df.shape[0]),
        "n_cols": int(df.shape[1]),
        "memory_mb": memory_mb(df),
        "columns": [str(c) for c in df.columns],
        "kinds": kinds,
        "ids": quality["ids"],
        "target": target,
        "target_guesses": guesses,
        "cat_opts": cat_opts,
        "preview": records(compact_head(df, 12)),
        "structure": records(structure_table(df)),
        "stats": records(stats),
        "quality": serialize_quality(quality),
        "recommendations": recommend_prep(df, target, quality),
        "charts": charts,
    }


def univariate_payload(df: pd.DataFrame, column: str) -> dict[str, Any]:
    kinds = column_kinds(df)
    stats = summary_statistics(df)
    if column in kinds["numeric"]:
        row = stats[stats["column"] == column] if len(stats) else pd.DataFrame()
        return {
            "kind": "numeric",
            "histogram": fig_json(histogram_kde(df[column], column)),
            "box": fig_json(boxplot(df[column], column)),
            "table": records(row),
        }
    vc = df[column].astype(str).value_counts(dropna=False).rename_axis("level").reset_index(name="count")
    vc["pct"] = (100 * vc["count"] / vc["count"].sum()).round(2)
    return {
        "kind": "categorical",
        "bar": fig_json(category_bar(df[column], column)),
        "table": records(vc),
    }


def relations_payload(
    df: pd.DataFrame,
    x: str | None,
    y: str | None,
    color: str | None,
    gnum: str | None,
    gcat: str | None,
) -> dict[str, Any]:
    out: dict[str, Any] = {"scatter": None, "grouped_box": None}
    if x and y and x != y:
        out["scatter"] = fig_json(scatter(df, x, y, color or None))
    if gnum and gcat:
        out["grouped_box"] = fig_json(grouped_box(df, gnum, gcat))
    return out


def prepare_payload(df: pd.DataFrame, target: str | None) -> dict[str, Any]:
    quality = build_quality_report(df, target)
    cleaned, train, test = preview_model_ready(df, target)
    mix = []
    if (
        train is not None
        and test is not None
        and target
        and target in train.columns
        and quality["balance"]
        and quality["balance"].get("kind") == "classification"
    ):
        mix_df = (
            pd.DataFrame(
                {
                    "train_pct": (train[target].astype(str).value_counts(normalize=True) * 100).round(2),
                    "test_pct": (test[target].astype(str).value_counts(normalize=True) * 100).round(2),
                }
            )
            .fillna(0)
            .reset_index()
            .rename(columns={"index": "class"})
        )
        mix = records(mix_df)
    return {
        "recommendations": recommend_prep(df, target, quality),
        "cleaned_preview": records(cleaned, 10),
        "cleaned_csv": cleaned.to_csv(index=False),
        "train_rows": None if train is None else int(len(train)),
        "test_rows": None if test is None else int(len(test)),
        "class_mix": mix,
    }
