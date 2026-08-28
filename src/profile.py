"""Data overview, typing, and summary statistics."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def load_csv(uploaded) -> pd.DataFrame:
    return pd.read_csv(uploaded)


_DATE_HINTS = ("date", "time", "timestamp", "_at", "_on", "datetime", "dob")


def _looks_like_datetime(col: str, series: pd.Series) -> bool:
    if pd.api.types.is_datetime64_any_dtype(series):
        return True
    name = col.lower()
    sample = series.dropna().astype(str).head(30)
    if sample.empty:
        return False
    hinted = any(tok in name for tok in _DATE_HINTS)
    patterned = bool(sample.str.contains(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4}", regex=True).mean() > 0.7)
    if not (hinted or patterned):
        return False
    parsed = pd.to_datetime(series, errors="coerce")
    return bool(parsed.notna().mean() > 0.8 and series.nunique(dropna=True) > 3)


def column_kinds(df: pd.DataFrame) -> dict[str, list[str]]:
    numeric = df.select_dtypes(include=[np.number]).columns.tolist()
    datetime_cols = [c for c in df.columns if c not in numeric and _looks_like_datetime(c, df[c])]
    categorical = [c for c in df.columns if c not in numeric and c not in datetime_cols]
    return {"numeric": numeric, "categorical": categorical, "datetime": datetime_cols}


def infer_id_columns(df: pd.DataFrame) -> list[str]:
    ids = []
    n = len(df)
    for col in df.columns:
        nunq = df[col].nunique(dropna=True)
        name = col.lower()
        if nunq == n and n > 10:
            ids.append(col)
        elif any(tok in name for tok in ("_id", "id_", "uuid", "guid")) and nunq > 0.9 * n:
            ids.append(col)
    return ids


def structure_table(df: pd.DataFrame) -> pd.DataFrame:
    kinds = column_kinds(df)
    kind_map = {}
    for k, cols in kinds.items():
        for c in cols:
            kind_map[c] = k
    rows = []
    for col in df.columns:
        s = df[col]
        missing = int(s.isna().sum())
        rows.append(
            {
                "column": col,
                "dtype": str(s.dtype),
                "role": kind_map.get(col, "unknown"),
                "non_null": int(s.notna().sum()),
                "missing": missing,
                "missing_pct": round(100 * missing / max(len(df), 1), 2),
                "unique": int(s.nunique(dropna=True)),
                "sample": ", ".join(map(str, s.dropna().astype(str).head(3).tolist())),
            }
        )
    return pd.DataFrame(rows)


def summary_statistics(df: pd.DataFrame) -> pd.DataFrame:
    numeric = column_kinds(df)["numeric"]
    if not numeric:
        return pd.DataFrame()
    rows = []
    for col in numeric:
        s = pd.to_numeric(df[col], errors="coerce").dropna()
        if s.empty:
            continue
        mode = s.mode()
        rows.append(
            {
                "column": col,
                "count": int(s.count()),
                "mean": round(float(s.mean()), 4),
                "median": round(float(s.median()), 4),
                "mode": round(float(mode.iloc[0]), 4) if len(mode) else np.nan,
                "std": round(float(s.std(ddof=1)), 4) if len(s) > 1 else 0.0,
                "min": round(float(s.min()), 4),
                "q1": round(float(s.quantile(0.25)), 4),
                "q3": round(float(s.quantile(0.75)), 4),
                "max": round(float(s.max()), 4),
                "skew": round(float(s.skew()), 4) if len(s) > 2 else 0.0,
            }
        )
    return pd.DataFrame(rows)


def memory_mb(df: pd.DataFrame) -> float:
    return round(float(df.memory_usage(deep=True).sum()) / (1024 * 1024), 3)


def compact_head(df: pd.DataFrame, n: int = 8) -> pd.DataFrame:
    return df.head(n)


def likely_target_columns(df: pd.DataFrame) -> list[str]:
    exact = {"target", "label", "churn", "class", "outcome", "y", "survived", "default", "fraud"}
    parts = ("target", "label", "churn", "survived", "outcome", "fraud", "default")
    ranked = []
    for col in df.columns:
        name = col.lower().strip()
        score = 0
        if name in exact or name.endswith("_y"):
            score += 4
        score += 2 * sum(p in name for p in parts)
        nunq = df[col].nunique(dropna=True)
        if 2 <= nunq <= 8:
            score += 1
        if score:
            ranked.append((score, col))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    return [c for _, c in ranked]
