"""FastAPI backend for EDA Studio (React frontend)."""

from __future__ import annotations

import io
import os
import uuid
from typing import Any

import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.llm import compact_eda_payload, generate_insights
from src.payload import build_profile, prepare_payload, relations_payload, univariate_payload
from src.profile import summary_statistics
from src.quality import build_quality_report
from src.sample_data import ensure_sample_csv
from src.theme import apply_plotly_theme

load_dotenv(override=True)
apply_plotly_theme()

ROOT = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(ROOT, "frontend", "dist")

app = FastAPI(title="EDA Studio")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SESSIONS: dict[str, dict[str, Any]] = {}


class TargetBody(BaseModel):
    session_id: str
    target: str | None = None


class UnivariateBody(TargetBody):
    column: str


class RelationsBody(TargetBody):
    x: str | None = None
    y: str | None = None
    color: str | None = None
    gnum: str | None = None
    gcat: str | None = None


class InsightsBody(TargetBody):
    extra_question: str | None = None
    provider: str = "Groq (Llama, free API)"
    groq_model: str = "openai/gpt-oss-20b"
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"


def _session(session_id: str) -> tuple[pd.DataFrame, str]:
    item = SESSIONS.get(session_id)
    if not item:
        raise HTTPException(404, "Session expired. Upload the CSV again.")
    return item["df"], item["name"]


def _store(df: pd.DataFrame, name: str) -> str:
    sid = str(uuid.uuid4())
    SESSIONS[sid] = {"df": df, "name": name}
    if len(SESSIONS) > 24:
        oldest = next(iter(SESSIONS))
        if oldest != sid:
            SESSIONS.pop(oldest, None)
    return sid


def _clean_target(df: pd.DataFrame, target: str | None) -> str | None:
    if not target or target in ("", "none"):
        return None
    if target not in df.columns:
        raise HTTPException(400, f"Unknown column: {target}")
    return target


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/sample")
def load_sample() -> dict[str, Any]:
    path = ensure_sample_csv()
    df = pd.read_csv(path)
    sid = _store(df, path.name)
    profile = build_profile(df, path.name, None)
    profile["session_id"] = sid
    return profile


@app.post("/api/upload")
async def upload_csv(file: UploadFile = File(...)) -> dict[str, Any]:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "Please upload a .csv file.")
    raw = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(raw))
    except Exception as exc:
        raise HTTPException(400, f"Could not read CSV: {exc}") from exc
    if df.empty:
        raise HTTPException(400, "The CSV has no rows.")
    sid = _store(df, file.filename)
    profile = build_profile(df, file.filename, None)
    profile["session_id"] = sid
    return profile


@app.post("/api/profile")
def refresh_profile(body: TargetBody) -> dict[str, Any]:
    df, name = _session(body.session_id)
    target = _clean_target(df, body.target)
    profile = build_profile(df, name, target)
    profile["session_id"] = body.session_id
    return profile


@app.post("/api/univariate")
def univariate(body: UnivariateBody) -> dict[str, Any]:
    df, _ = _session(body.session_id)
    if body.column not in df.columns:
        raise HTTPException(400, f"Unknown column: {body.column}")
    return univariate_payload(df, body.column)


@app.post("/api/relations")
def relations(body: RelationsBody) -> dict[str, Any]:
    df, _ = _session(body.session_id)
    return relations_payload(df, body.x, body.y, body.color, body.gnum, body.gcat)


@app.post("/api/prepare")
def prepare(body: TargetBody) -> dict[str, Any]:
    df, _ = _session(body.session_id)
    target = _clean_target(df, body.target)
    return prepare_payload(df, target)


@app.post("/api/insights")
def insights(body: InsightsBody) -> dict[str, str]:
    df, _ = _session(body.session_id)
    target = _clean_target(df, body.target)
    quality = build_quality_report(df, target)
    stats = summary_statistics(df)
    payload = compact_eda_payload(df, target, quality, stats)
    try:
        text = generate_insights(
            payload,
            provider=body.provider,
            groq_key=os.getenv("GROQ_API_KEY", ""),
            groq_model=body.groq_model,
            ollama_host=body.ollama_host or os.getenv("OLLAMA_HOST", "http://localhost:11434"),
            ollama_model=body.ollama_model or os.getenv("OLLAMA_MODEL", "llama3.2"),
            extra_question=body.extra_question,
        )
    except Exception as exc:
        raise HTTPException(502, str(exc)) from exc
    return {"markdown": text}


if os.path.isdir(DIST):
    if hasattr(app, "frontend"):
        app.frontend("/", directory=DIST, fallback="index.html", check_dir=False)
    else:
        app.mount("/assets", StaticFiles(directory=os.path.join(DIST, "assets")), name="assets")

        @app.get("/{full_path:path}")
        def spa(full_path: str):
            if full_path.startswith("api/"):
                raise HTTPException(404, "Not found")
            index = os.path.join(DIST, "index.html")
            file_path = os.path.join(DIST, full_path)
            if full_path and os.path.isfile(file_path):
                return FileResponse(file_path)
            return FileResponse(index)
