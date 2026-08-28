"""Insights from a free open LLM (Groq Llama or local Ollama)."""

from __future__ import annotations

import json
import os
from typing import Any

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv(override=True)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODELS = [
    "openai/gpt-oss-20b",
    "qwen/qwen3.8-27b",
    "openai/gpt-oss-120b",
    "llama-3.1-8b-instant",
    "llama-3.3-70b-versatile",
]


def compact_eda_payload(
    df: pd.DataFrame,
    target: str | None,
    quality: dict[str, Any],
    stats: pd.DataFrame,
) -> dict[str, Any]:
    miss = quality["missing"]
    outliers = quality["outliers"]
    return {
        "shape": [int(df.shape[0]), int(df.shape[1])],
        "columns": list(map(str, df.columns[:40])),
        "dtypes": {str(k): str(v) for k, v in df.dtypes.astype(str).items()},
        "target": target,
        "quality_score": quality["score"],
        "quality_status": quality["status"],
        "duplicate_rows": quality["duplicate_rows"],
        "missing": miss.head(15).to_dict(orient="records") if len(miss) else [],
        "outliers": outliers.head(10).to_dict(orient="records") if len(outliers) else [],
        "inconsistent_categories": quality["inconsistent"][:12],
        "invalid": quality["invalid"],
        "leakage": quality["leakage"],
        "constant_columns": quality["constant"],
        "ids": quality["ids"],
        "class_balance": quality["balance"],
        "numeric_summary": stats.head(20).to_dict(orient="records") if len(stats) else [],
        "sample_rows": df.head(4).astype(str).to_dict(orient="records"),
    }


def _system_prompt() -> str:
    return (
        "You are a senior applied data scientist writing an EDA briefing. "
        "Use only the supplied profile. Be concrete: name columns, cite percents, "
        "correlations, and class shares. Never invent columns. "
        "Structure the reply in markdown with these headings:\n"
        "## Key insights\n"
        "## Data quality risks\n"
        "## Feature preparation\n"
        "## Model readiness\n"
        "## Watch-outs\n"
        "Under Model readiness, recommend 2–3 algorithm families, a metric, "
        "and a 70/30 stratified split when the target is categorical. "
        "Always warn that preprocessing must be fit on training data only."
    )


def _groq_chat(api_key: str, messages: list[dict[str, str]], model: str) -> str:
    resp = requests.post(
        GROQ_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 1400,
        },
        timeout=60,
    )
    if resp.status_code in (400, 404):
        for fallback in GROQ_MODELS:
            if fallback == model:
                continue
            retry = requests.post(
                GROQ_URL,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": fallback,
                    "messages": messages,
                    "temperature": 0.2,
                    "max_tokens": 1400,
                },
                timeout=60,
            )
            if retry.ok:
                return retry.json()["choices"][0]["message"]["content"].strip()
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"].strip()


def _ollama_chat(host: str, model: str, messages: list[dict[str, str]]) -> str:
    resp = requests.post(
        host.rstrip("/") + "/api/chat",
        json={"model": model, "messages": messages, "stream": False},
        timeout=180,
    )
    resp.raise_for_status()
    return resp.json()["message"]["content"].strip()


def generate_insights(
    payload: dict[str, Any],
    provider: str,
    groq_key: str,
    groq_model: str,
    ollama_host: str,
    ollama_model: str,
    extra_question: str | None = None,
) -> str:
    user = (
        "EDA profile (JSON):\n"
        + json.dumps(payload, default=str)[:14000]
        + "\n\nWrite the briefing now."
    )
    if extra_question:
        user += "\n\nAlso answer this follow-up from the analyst:\n" + extra_question.strip()
    messages = [
        {"role": "system", "content": _system_prompt()},
        {"role": "user", "content": user},
    ]

    if provider == "Groq (Llama, free API)":
        key = groq_key.strip() or os.getenv("GROQ_API_KEY", "")
        if not key:
            raise RuntimeError(
                "Add a free Groq API key to the .env file (console.groq.com/keys) to use Llama."
            )
        return _groq_chat(key, messages, groq_model)
    if provider == "Ollama (local)":
        return _ollama_chat(ollama_host, ollama_model, messages)
    raise RuntimeError("Unknown LLM provider.")
