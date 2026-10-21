from __future__ import annotations

import logging
import threading
import uuid

from fastapi import FastAPI, Header, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .config import settings
from .models import CreateJobRequest, ErrorResponse, JobAccepted, JobState, JobStatus
from .services.pipeline import run_job
from .store import JobStore

logging.basicConfig(level=logging.INFO, format='{"timestamp":"%(asctime)s","level":"%(levelname)s","message":"%(message)s"}')
app = FastAPI(title="IncuBrix B-roll Engine", version="0.1.0", openapi_url="/api/v1/openapi.json")
store = JobStore(settings.database_path)


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


@app.get("/api/v1/jobs/{job_id}", response_model=JobStatus, responses={404: {"model": ErrorResponse}})
def get_job(job_id: str):
    job = store.get(job_id)
    if not job:
        return error("JOB_NOT_FOUND", "Job does not exist", 404)
    return JobStatus(job_id=job_id, status=JobState(job["state"]), progress=job["progress"], error=job["error_json"], result_links=job["results_json"] or {}, warnings=job["warnings_json"] or [])

