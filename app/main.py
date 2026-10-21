from __future__ import annotations

import logging
import shutil
import threading
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, Header, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .models import CreateJobRequest, ErrorResponse, JobAccepted, JobState, JobStatus
from .services.pipeline import run_job
from .store import JobStore

logging.basicConfig(level=logging.INFO, format='{"timestamp":"%(asctime)s","level":"%(levelname)s","message":"%(message)s"}')
app = FastAPI(title="IncuBrix B-roll Engine", version="0.1.0", openapi_url="/api/v1/openapi.json")
store = JobStore(settings.database_path)

# CORS for frontend
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

# Serve rendered artifacts
settings.artifact_dir.mkdir(parents=True, exist_ok=True)
app.mount("/artifacts", StaticFiles(directory=str(settings.artifact_dir)), name="artifacts")


def error(code: str, message: str, status: int, retryable: bool = False, details: dict | None = None) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message, "retryable": retryable, "details": details or {}}})


@app.middleware("http")
async def correlation(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-Id", str(uuid.uuid4()))
    response = await call_next(request)
    response.headers["X-Correlation-Id"] = correlation_id
    return response


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError):
    return error("VALIDATION_ERROR", "Request validation failed", 422, details={"errors": exc.errors()})


@app.get("/health")
def health(): return {"status": "ok"}


@app.get("/ready")
def ready(): return {"status": "ready", "storage": "local-development"}


@app.post("/api/v1/broll/jobs", status_code=202, response_model=JobAccepted, responses={422: {"model": ErrorResponse}})
def create_job(payload: CreateJobRequest, idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    if not idempotency_key or len(idempotency_key) > 255:
        return error("IDEMPOTENCY_KEY_REQUIRED", "Idempotency-Key header is required", 400)
    job_id, reused = store.create_or_get(idempotency_key, payload.model_dump(mode="json"))
    if not reused:
        threading.Thread(target=run_job, args=(store, job_id), daemon=True).start()
    return JobAccepted(job_id=job_id, status=JobState.queued if not reused else JobState(store.get(job_id)["state"]), reused=reused)


@app.post("/api/v1/broll/jobs/upload", status_code=202, response_model=JobAccepted)
async def create_job_upload(
    audio: UploadFile = File(...),
    script: str | None = Form(default=None),
    voice: str = Form(default="en-IN-female"),
    aspect_ratios: str = Form(default="16:9"),
    style: str = Form(default="bright, modern, real-world footage"),
    avoid: str = Form(default=""),
    burn_in: bool = Form(default=True),
    srt: bool = Form(default=True),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    """Multipart upload endpoint for audio files (MP3, WAV, M4A)."""
    if not idempotency_key or len(idempotency_key) > 255:
        return error("IDEMPOTENCY_KEY_REQUIRED", "Idempotency-Key header is required", 400)

    # Validate file type
    allowed_types = {"audio/mpeg", "audio/wav", "audio/x-wav", "audio/mp4", "audio/m4a",
                     "audio/x-m4a", "audio/mp3", "application/octet-stream"}
    content_type = audio.content_type or ""
    suffix = Path(audio.filename or "").suffix.lower()
    allowed_suffixes = {".mp3", ".wav", ".m4a"}

    if suffix not in allowed_suffixes and content_type not in allowed_types:
        return error("UNSUPPORTED_AUDIO_FORMAT", f"Only MP3, WAV, M4A files are accepted. Got: {content_type}", 422)

    # Save uploaded file
    upload_dir = settings.work_dir / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"{uuid.uuid4().hex}{suffix or '.mp3'}"
    upload_path = upload_dir / safe_name

    file_size = 0
    with open(upload_path, "wb") as f:
        while chunk := await audio.read(65536):
            file_size += len(chunk)
            if file_size > settings.max_upload_bytes:
                upload_path.unlink(missing_ok=True)
                return error("FILE_TOO_LARGE", f"File exceeds {settings.max_upload_bytes} bytes limit", 422)
            f.write(chunk)

    if file_size < 100:
        upload_path.unlink(missing_ok=True)
        return error("FILE_TOO_SMALL", "Audio file is too small or empty", 422)

    # Parse aspect ratios
    ratios = [r.strip() for r in aspect_ratios.split(",") if r.strip()]
    valid_ratios = {"16:9", "9:16", "1:1"}
    for r in ratios:
        if r not in valid_ratios:
            upload_path.unlink(missing_ok=True)
            return error("INVALID_ASPECT_RATIO", f"Invalid aspect ratio: {r}", 422)

    # Build request dict
    avoid_list = [a.strip() for a in avoid.split(",") if a.strip()]
    request_data = {
        "audio_upload_path": str(upload_path),
        "script": script,
        "voice": voice,
        "aspect_ratios": ratios,
        "style": style,
        "avoid": avoid_list,
        "captions": {"burn_in": burn_in, "srt": srt},
    }

    job_id, reused = store.create_or_get(idempotency_key, request_data)
    if not reused:
        threading.Thread(target=run_job, args=(store, job_id), daemon=True).start()
    return JobAccepted(
        job_id=job_id,
        status=JobState.queued if not reused else JobState(store.get(job_id)["state"]),
        reused=reused
    )


@app.get("/api/v1/jobs/{job_id}", response_model=JobStatus, responses={404: {"model": ErrorResponse}})
def get_job(job_id: str):
    job = store.get(job_id)
    if not job:
        return error("JOB_NOT_FOUND", "Job does not exist", 404)
    return JobStatus(job_id=job_id, status=JobState(job["state"]), progress=job["progress"], error=job["error_json"], result_links=job["results_json"] or {}, warnings=job["warnings_json"] or [])


# Serve frontend UI at root if built
frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if frontend_dist.is_dir():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
