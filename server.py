"""FastAPI backend for EDA Studio (React frontend)."""

from __future__ import annotations

import base64
import io
import os
import uuid
from typing import Any
from urllib.parse import unquote

import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, UploadFile
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
    expose_headers=["*"],
)

SESSIONS: dict[str, dict[str, Any]] = {}
MAX_UPLOAD_BYTES = 4 * 1024 * 1024


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


def _session(session_id: str) -> dict[str, Any]:
    item = SESSIONS.get(session_id)
    if not item:
        raise HTTPException(404, "Session expired. Upload the CSV again.")
    return item


def _store(df: pd.DataFrame, name: str, source_bytes: int = 0) -> str:
    sid = str(uuid.uuid4())
    SESSIONS[sid] = {"df": df, "name": name, "source_bytes": int(source_bytes or 0)}
    if len(SESSIONS) > 24:
        oldest = next(iter(SESSIONS))
        if oldest != sid:
            SESSIONS.pop(oldest, None)
    return sid


def _profile_from_item(item: dict[str, Any], target: str | None, session_id: str) -> dict[str, Any]:
    profile = build_profile(item["df"], item["name"], target, source_bytes=item.get("source_bytes", 0))
    profile["session_id"] = session_id
    return profile


def _safe_filename(name: str | None) -> str:
    cleaned = os.path.basename(unquote(name or "upload.csv")).strip() or "upload.csv"
    return cleaned.replace("\r", "").replace("\n", "")


def _read_csv_bytes(raw: bytes) -> pd.DataFrame:
    last_err: Exception | None = None
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        for kwargs in ({}, {"sep": None, "engine": "python"}):
            try:
                df = pd.read_csv(io.BytesIO(raw), encoding=encoding, **kwargs)
                if df.shape[1] == 0:
                    raise ValueError("No columns found.")
                return df
            except Exception as exc:  # noqa: BLE001 — try the next encoding/parser
                last_err = exc
    raise HTTPException(400, f"Could not read CSV: {last_err}") from last_err


async def _read_upload(request: Request) -> tuple[bytes, str]:
    ctype = (request.headers.get("content-type") or "").lower()
    if "multipart/form-data" in ctype:
        form = await request.form()
        upload = form.get("file")
        if not isinstance(upload, UploadFile):
            raise HTTPException(400, "Please upload a .csv file.")
        raw = await upload.read()
        return raw, _safe_filename(upload.filename)
    if "application/json" in ctype:
        data = await request.json()
        name = _safe_filename(str(data.get("filename") or "upload.csv"))
        if data.get("content_b64"):
            try:
                raw = base64.b64decode(data["content_b64"])
            except Exception as exc:
                raise HTTPException(400, "Could not decode the CSV payload.") from exc
        else:
            raw = str(data.get("content") or "").encode("utf-8")
        return raw, name
    raw = await request.body()
    name = _safe_filename(request.headers.get("x-filename") or "upload.csv")
    return raw, name


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
    sid = _store(df, path.name, path.stat().st_size)
    return _profile_from_item(SESSIONS[sid], None, sid)


@app.post("/api/upload")
async def upload_csv(request: Request) -> dict[str, Any]:
    raw, filename = await _read_upload(request)
    if not raw:
        raise HTTPException(400, "The CSV is empty.")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            413,
            f"CSV is {len(raw) / (1024 * 1024):.2f} MB. Maximum upload size is 4 MB.",
        )
    lower = filename.lower()
    if lower.endswith((".xlsx", ".xls", ".ods")):
        raise HTTPException(400, "Please save the sheet as a .csv file, then upload it.")
    if "." in lower and not lower.endswith(".csv"):
        raise HTTPException(400, "Please upload a .csv file.")
    df = _read_csv_bytes(raw)
    if df.empty:
        raise HTTPException(400, "The CSV has headers but no data rows.")
    sid = _store(df, filename, len(raw))
    return _profile_from_item(SESSIONS[sid], None, sid)


@app.post("/api/profile")
def refresh_profile(body: TargetBody) -> dict[str, Any]:
    item = _session(body.session_id)
    target = _clean_target(item["df"], body.target)
    return _profile_from_item(item, target, body.session_id)


@app.post("/api/univariate")
def univariate(body: UnivariateBody) -> dict[str, Any]:
    item = _session(body.session_id)
    if body.column not in item["df"].columns:
        raise HTTPException(400, f"Unknown column: {body.column}")
    return univariate_payload(item["df"], body.column)


@app.post("/api/relations")
def relations(body: RelationsBody) -> dict[str, Any]:
    item = _session(body.session_id)
    return relations_payload(item["df"], body.x, body.y, body.color, body.gnum, body.gcat)


@app.post("/api/prepare")
def prepare(body: TargetBody) -> dict[str, Any]:
    item = _session(body.session_id)
    target = _clean_target(item["df"], body.target)
    return prepare_payload(item["df"], target)


@app.post("/api/insights")
def insights(body: InsightsBody) -> dict[str, str]:
    item = _session(body.session_id)
    df = item["df"]
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
