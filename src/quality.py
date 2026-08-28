"""Automated data-quality flags with a traffic-light score."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .profile import column_kinds, infer_id_columns


def _iqr_bounds(s: pd.Series) -> tuple[float, float]:
    q1, q3 = float(s.quantile(0.25)), float(s.quantile(0.75))
    iqr = q3 - q1
    return q1 - 1.5 * iqr, q3 + 1.5 * iqr


def missing_report(df: pd.DataFrame) -> pd.DataFrame:
    n = max(len(df), 1)
    rows = []
    for col in df.columns:
        miss = int(df[col].isna().sum())
        if miss == 0:
            continue
        rows.append(
            {
                "column": col,
                "missing": miss,
                "missing_pct": round(100 * miss / n, 2),
            }
        )
    return pd.DataFrame(rows).sort_values("missing_pct", ascending=False) if rows else pd.DataFrame(
        columns=["column", "missing", "missing_pct"]
    )


def outlier_report(df: pd.DataFrame) -> pd.DataFrame:
    numeric = column_kinds(df)["numeric"]
    rows = []
    for col in numeric:
        s = pd.to_numeric(df[col], errors="coerce").dropna()
        if s.nunique() < 4:
            continue
        lo, hi = _iqr_bounds(s)
        mask = (s < lo) | (s > hi)
        count = int(mask.sum())
        if count == 0:
            continue
        rows.append(
            {
                "column": col,
                "outliers": count,
                "outlier_pct": round(100 * count / len(s), 2),
                "lower_fence": round(lo, 4),
                "upper_fence": round(hi, 4),
                "example": ", ".join(map(str, s[mask].head(4).round(4).tolist())),
            }
        )
    return pd.DataFrame(rows).sort_values("outlier_pct", ascending=False) if rows else pd.DataFrame()


def inconsistent_categories(df: pd.DataFrame) -> list[dict[str, Any]]:
    cats = column_kinds(df)["categorical"]
    issues = []
    for col in cats:
        vals = df[col].dropna().astype(str)
        groups: dict[str, set[str]] = {}
        for v in vals.unique():
            key = " ".join(v.strip().lower().split())
            groups.setdefault(key, set()).add(v)
        for key, variants in groups.items():
            if len(variants) > 1:
                issues.append(
                    {
                        "column": col,
                        "normalized": key,
                        "variants": sorted(variants),
                        "count": int(vals.isin(variants).sum()),
                    }
                )
    return issues


def invalid_values(df: pd.DataFrame) -> list[dict[str, Any]]:
    flags = []
    for col in column_kinds(df)["numeric"]:
        s = pd.to_numeric(df[col], errors="coerce")
        name = col.lower()
        if any(tok in name for tok in ("age", "tenure", "count", "qty", "quantity", "duration")):
            neg = int((s < 0).sum())
            if neg:
                flags.append({"column": col, "issue": f"{neg} negative values", "severity": "warning"})
        if "age" in name:
            wild = int(((s < 0) | (s > 110)).sum())
            if wild:
                flags.append({"column": col, "issue": f"{wild} ages outside 0–110", "severity": "critical"})
        if any(tok in name for tok in ("pct", "percent", "rate", "ratio")):
            wild = int(((s < 0) | (s > 100)).sum())
            if wild:
                flags.append({"column": col, "issue": f"{wild} values outside 0–100", "severity": "warning"})
    return flags


def constant_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if df[c].nunique(dropna=True) <= 1]


def near_constant_columns(df: pd.DataFrame, thresh: float = 0.95) -> list[dict[str, Any]]:
    n = max(len(df), 1)
    out = []
    for col in df.columns:
        vc = df[col].value_counts(dropna=True, normalize=True)
        if vc.empty:
            continue
        top = float(vc.iloc[0])
        if top >= thresh and df[col].nunique(dropna=True) > 1:
            out.append({"column": col, "dominant_value": str(vc.index[0]), "share_pct": round(100 * top, 2)})
    return out


def leakage_flags(df: pd.DataFrame, target: str | None) -> list[dict[str, Any]]:
    flags = []
    ids = infer_id_columns(df)
    for col in ids:
        flags.append(
            {
                "column": col,
                "issue": "Looks like an identifier (unique per row). Drop before modeling.",
                "severity": "warning",
            }
        )
    if not target or target not in df.columns:
        return flags

    tname = target.lower()
    numeric = [c for c in column_kinds(df)["numeric"] if c != target]
    y = df[target]
    y_num = y
    if y.dtype == object or str(y.dtype).startswith("bool"):
        codes, _ = pd.factorize(y.astype(str).str.strip().str.lower())
        y_num = pd.Series(codes, index=df.index)

    for col in numeric:
        name = col.lower()
        if any(tok in name for tok in ("score", "prob", "prediction", "pred", "label", "target")) and col != target:
            flags.append(
                {
                    "column": col,
                    "issue": "Name suggests a model output or label proxy; possible leakage.",
                    "severity": "critical",
                }
            )
        s = pd.to_numeric(df[col], errors="coerce")
        if s.nunique(dropna=True) < 3:
            continue
        try:
            r = float(s.corr(pd.to_numeric(y_num, errors="coerce")))
        except Exception:
            continue
        if np.isfinite(r) and abs(r) >= 0.95:
            flags.append(
                {
                    "column": col,
                    "issue": f"Pearson r = {r:.3f} with `{target}` — almost a duplicate of the label.",
                    "severity": "critical",
                }
            )
        elif np.isfinite(r) and abs(r) >= 0.85 and any(tok in name for tok in ("score", "risk", "churn", tname)):
            flags.append(
                {
                    "column": col,
                    "issue": f"Strong correlation with target (r = {r:.3f}) plus a suspicious name.",
                    "severity": "critical",
                }
            )
    return flags


def class_balance(df: pd.DataFrame, target: str | None) -> dict[str, Any] | None:
    if not target or target not in df.columns:
        return None
    s = df[target].dropna().astype(str).str.strip()
    nuniq = s.nunique()
    if nuniq == 0:
        return None
    if nuniq > 20 or pd.api.types.is_numeric_dtype(df[target]) and nuniq > 12:
        return {
            "kind": "regression",
            "unique": int(nuniq),
            "imbalance_risk": "n/a",
            "minority_pct": None,
            "counts": None,
        }
    counts = s.value_counts()
    minority_pct = float(100 * counts.min() / counts.sum())
    if minority_pct < 10:
        risk = "high"
    elif minority_pct < 30:
        risk = "medium"
    else:
        risk = "low"
    return {
        "kind": "classification",
        "unique": int(nuniq),
        "imbalance_risk": risk,
        "minority_pct": round(minority_pct, 2),
        "counts": {str(k): int(v) for k, v in counts.items()},
    }


def quality_score(payload: dict[str, Any]) -> tuple[int, str]:
    score = 100
    miss = payload["missing"]
    if len(miss):
        worst = float(miss["missing_pct"].max())
        if worst >= 40:
            score -= 30
        elif worst >= 15:
            score -= 18
        elif worst >= 5:
            score -= 8
        score -= min(12, len(miss) * 2)
    dups = payload["duplicate_rows"]
    if dups:
        pct = 100 * dups / max(payload["n_rows"], 1)
        score -= 20 if pct >= 5 else 10
    if payload["inconsistent"]:
        score -= min(15, 4 * len(payload["inconsistent"]))
    crit_leak = [f for f in payload["leakage"] if f.get("severity") == "critical"]
    if crit_leak:
        score -= 25
    if payload["invalid"]:
        score -= min(12, 4 * len(payload["invalid"]))
    if payload["outliers"] is not None and len(payload["outliers"]):
        worst_out = float(payload["outliers"]["outlier_pct"].max())
        if worst_out >= 8:
            score -= 10
        elif worst_out >= 3:
            score -= 5
    score = int(max(0, min(100, score)))
    if score >= 80:
        status = "good"
    elif score >= 55:
        status = "warning"
    else:
        status = "critical"
    return score, status


def build_quality_report(df: pd.DataFrame, target: str | None) -> dict[str, Any]:
    missing = missing_report(df)
    outliers = outlier_report(df)
    inconsistent = inconsistent_categories(df)
    invalid = invalid_values(df)
    leakage = leakage_flags(df, target)
    payload = {
        "n_rows": int(len(df)),
        "n_cols": int(df.shape[1]),
        "duplicate_rows": int(df.duplicated().sum()),
        "missing": missing,
        "outliers": outliers,
        "inconsistent": inconsistent,
        "invalid": invalid,
        "leakage": leakage,
        "constant": constant_columns(df),
        "near_constant": near_constant_columns(df),
        "ids": infer_id_columns(df),
        "balance": class_balance(df, target),
    }
    score, status = quality_score(payload)
    payload["score"] = score
    payload["status"] = status
    return payload
