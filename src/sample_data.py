"""Synthetic customer-churn CSV with realistic quality issues for the demo."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

SAMPLE_PATH = Path(__file__).resolve().parent.parent / "sample_data" / "customer_churn.csv"


def build_sample(n: int = 480, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    contract = rng.choice(["Month-to-month", "One year", "Two year"], n, p=[0.55, 0.27, 0.18])
    internet = rng.choice(["Fiber optic", "DSL", "No"], n, p=[0.48, 0.34, 0.18])
    tenure = rng.integers(0, 73, n)
    monthly = np.round(rng.normal(65, 22, n).clip(18, 140), 2)
    total = np.round(monthly * tenure * rng.uniform(0.85, 1.12, n), 2)
    tickets = rng.poisson(1.4, n)
    age = rng.integers(18, 80, n)

    churn_prob = (
        0.08
        + 0.22 * (contract == "Month-to-month")
        + 0.12 * (internet == "Fiber optic")
        + 0.10 * (tickets >= 3)
        + 0.08 * (monthly > 90)
        - 0.12 * (tenure > 36)
    )
    churn_prob = np.clip(churn_prob, 0.04, 0.78)
    churn = np.where(rng.random(n) < churn_prob, "Yes", "No")

    # Leaky proxy of the label — should be flagged in quality checks.
    churn_score = np.round(
        np.clip(churn_prob * 100 + rng.normal(0, 6, n), 0, 100),
        1,
    )

    df = pd.DataFrame(
        {
            "customer_id": [f"C{10000 + i}" for i in range(n)],
            "age": age,
            "gender": rng.choice(["Female", "Male"], n),
            "tenure_months": tenure,
            "contract_type": contract,
            "internet_service": internet,
            "payment_method": rng.choice(
                ["Electronic check", "Mailed check", "Bank transfer", "Credit card"],
                n,
            ),
            "paperless_billing": rng.choice(["Yes", "No"], n, p=[0.62, 0.38]),
            "monthly_charges": monthly,
            "total_charges": total,
            "support_tickets": tickets,
            "churn_score": churn_score,
            "churn": churn,
        }
    )

    # Missing values
    miss_idx = rng.choice(n, 28, replace=False)
    df.loc[miss_idx[:12], "total_charges"] = np.nan
    df.loc[miss_idx[12:20], "internet_service"] = np.nan
    df.loc[miss_idx[20:28], "age"] = np.nan

    # Inconsistent category spelling / spacing
    messy = rng.choice(df.index[df["internet_service"] == "Fiber optic"], 9, replace=False)
    df.loc[messy[:4], "internet_service"] = "fiber optic"
    df.loc[messy[4:7], "internet_service"] = "Fiber Optic"
    df.loc[messy[7:], "internet_service"] = " Fiber optic"

    yes_messy = rng.choice(df.index[df["churn"] == "Yes"], 6, replace=False)
    df.loc[yes_messy[:3], "churn"] = "yes"
    df.loc[yes_messy[3:], "churn"] = "YES"

    # Outliers
    df.loc[rng.choice(n, 4, replace=False), "monthly_charges"] = [199.99, 210.5, 5.0, 188.0]
    df.loc[rng.choice(n, 3, replace=False), "support_tickets"] = [14, 18, 11]
    df.loc[rng.choice(n, 2, replace=False), "age"] = [120, 3]

    # Duplicate customers
    dup = df.iloc[[10, 25, 40]].copy()
    df = pd.concat([df, dup], ignore_index=True)
    return df


def ensure_sample_csv() -> Path:
    SAMPLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not SAMPLE_PATH.exists():
        build_sample().to_csv(SAMPLE_PATH, index=False)
    return SAMPLE_PATH
