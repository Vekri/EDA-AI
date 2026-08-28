"""Feature-prep recommendations and a cautious model-ready preview."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from .profile import column_kinds, infer_id_columns
from .quality import class_balance, inconsistent_categories


def recommend_prep(df: pd.DataFrame, target: str | None, quality: dict[str, Any]) -> list[dict[str, str]]:
    recs: list[dict[str, str]] = []
    kinds = column_kinds(df)
    ids = infer_id_columns(df)

    if quality["duplicate_rows"]:
        recs.append(
            {
                "step": "Remove duplicates",
                "detail": f"Drop {quality['duplicate_rows']} duplicate rows before any split.",
            }
        )
    if ids:
        recs.append(
            {
                "step": "Drop identifiers",
                "detail": "Remove " + ", ".join(f"`{c}`" for c in ids) + " from the feature matrix.",
            }
        )
    leak = [f for f in quality["leakage"] if f.get("severity") == "critical"]
    if leak:
        cols = sorted({f["column"] for f in leak})
        recs.append(
            {
                "step": "Block leakage",
                "detail": "Do not use "
                + ", ".join(f"`{c}`" for c in cols)
                + " as a feature. Fit preprocessing on train only — never on the full table or the test fold.",
            }
        )

    miss = quality["missing"]
    if len(miss):
        for _, row in miss.head(12).iterrows():
            col = row["column"]
            if col in kinds["numeric"]:
                s = pd.to_numeric(df[col], errors="coerce")
                method = "median" if abs(float(s.skew(skipna=True) or 0)) > 1 else "mean"
                recs.append(
                    {
                        "step": f"Impute `{col}`",
                        "detail": f"{row['missing_pct']}% missing. Prefer {method} imputation fitted on the training fold.",
                    }
                )
            else:
                recs.append(
                    {
                        "step": f"Impute `{col}`",
                        "detail": f"{row['missing_pct']}% missing. Fill with training-fold mode or an explicit 'Unknown' level.",
                    }
                )

    for issue in inconsistent_categories(df)[:8]:
        recs.append(
            {
                "step": f"Normalize `{issue['column']}`",
                "detail": "Merge variants: " + ", ".join(f"'{v}'" for v in issue["variants"]) + ".",
            }
        )

    if len(quality["outliers"]):
        for _, row in quality["outliers"].head(6).iterrows():
            recs.append(
                {
                    "step": f"Treat outliers in `{row['column']}`",
                    "detail": f"{row['outlier_pct']}% beyond the IQR fences. Winsorize, log-transform, or use a robust scaler.",
                }
            )

    for col in kinds["numeric"]:
        if target and col == target:
            continue
        s = pd.to_numeric(df[col], errors="coerce").dropna()
        if len(s) < 8:
            continue
        skew = float(s.skew())
        if abs(skew) >= 1.0 and (s.min() >= 0):
            recs.append(
                {
                    "step": f"Un-skew `{col}`",
                    "detail": f"Skewness = {skew:.2f}. Try log1p or a Yeo-Johnson transform on the training fold.",
                }
            )

    for col in kinds["categorical"]:
        if target and col == target:
            continue
        nunq = int(df[col].nunique(dropna=True))
        if nunq <= 1:
            continue
        if nunq <= 12:
            recs.append(
                {
                    "step": f"Encode `{col}`",
                    "detail": f"{nunq} levels — one-hot encode (fit categories on train only).",
                }
            )
        else:
            recs.append(
                {
                    "step": f"Encode `{col}`",
                    "detail": f"{nunq} levels — too wide for one-hot. Use ordinal, target, or frequency encoding on train.",
                }
            )

    num_feats = [c for c in kinds["numeric"] if c != target and c not in ids]
    if num_feats:
        recs.append(
            {
                "step": "Scale numeric features",
                "detail": "Use RobustScaler if outliers remain, otherwise StandardScaler. Fit on train, transform test.",
            }
        )

    bal = class_balance(df, target)
    if bal and bal.get("kind") == "classification":
        recs.append(
            {
                "step": "Stratified 70/30 split",
                "detail": f"Imbalance risk is {bal['imbalance_risk']}. Stratify on `{target}`. "
                + (
                    "Consider class weights or resampling after the split."
                    if bal["imbalance_risk"] != "low"
                    else "Class mix is usable as-is."
                ),
            }
        )
    else:
        recs.append(
            {
                "step": "Hold out a test fold",
                "detail": "Use a 70/30 split (or grouped split if rows are not independent). Fit every transformer on train only.",
            }
        )
    return recs


def preview_model_ready(df: pd.DataFrame, target: str | None) -> tuple[pd.DataFrame, pd.DataFrame | None, pd.DataFrame | None]:
    """Lightweight cleaned preview — not a production pipeline."""
    work = df.copy()
    work = work.drop_duplicates()
    kinds = column_kinds(work)
    drop_cols = infer_id_columns(work)
    leak_name_hits = [
        c
        for c in work.columns
        if c != target and any(tok in c.lower() for tok in ("score", "prediction", "pred_proba"))
    ]
    drop_cols = list(dict.fromkeys(drop_cols + leak_name_hits))
    work = work.drop(columns=[c for c in drop_cols if c in work.columns], errors="ignore")

    for col in work.columns:
        if col in kinds["categorical"] or work[col].dtype == object:
            work[col] = work[col].astype(str).str.strip()
            work.loc[work[col].isin(["nan", "None", "NaN"]), col] = np.nan

    for col in work.select_dtypes(include=[np.number]).columns:
        if work[col].isna().any():
            work[col] = work[col].fillna(work[col].median())
    for col in work.select_dtypes(exclude=[np.number]).columns:
        if work[col].isna().any():
            mode = work[col].mode()
            work[col] = work[col].fillna(mode.iloc[0] if len(mode) else "Unknown")

    train = test = None
    if target and target in work.columns and len(work) >= 20:
        stratify = None
        y = work[target]
        if y.nunique() > 1 and y.nunique() <= 20:
            stratify = y
        try:
            train, test = train_test_split(
                work, test_size=0.3, random_state=42, stratify=stratify
            )
        except ValueError:
            train, test = train_test_split(work, test_size=0.3, random_state=42)
    return work, train, test
