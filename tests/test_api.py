import io
import uuid

import pytest
from pydantic import ValidationError
from starlette.testclient import TestClient

from app.main import app, create_job, get_job, health, ready
from app.models import CreateJobRequest

client = TestClient(app)


def test_health_and_ready():
    assert health()["status"] == "ok"
    assert ready()["status"] == "ready"


def test_requires_idempotency_key():
    response = create_job(CreateJobRequest(script="A clear sentence."), None)
    assert response.status_code == 400
    assert response.body.find(b"IDEMPOTENCY_KEY_REQUIRED") >= 0


def test_valid_request_and_idempotency():
    payload = CreateJobRequest(script="Saving money starts with small choices.", aspect_ratios=["16:9"])
    key = "test-" + str(uuid.uuid4())
    first = create_job(payload, key)
    second = create_job(payload, key)
    assert first.job_id == second.job_id
    assert second.reused is True
    assert get_job(first.job_id).job_id == first.job_id


def test_rejects_empty_or_multiple_input_modes():
    with pytest.raises(ValidationError):
        CreateJobRequest(script="")
    with pytest.raises(ValidationError):
        CreateJobRequest(script="x", scenes=[{"text": "y"}])


def test_job_not_found():
    response = client.get("/api/v1/jobs/nonexistent-uuid")
    assert response.status_code == 404
    data = response.json()
    assert data["error"]["code"] == "JOB_NOT_FOUND"


def test_correlation_id_header():
    cid = str(uuid.uuid4())
    response = client.get("/health", headers={"X-Correlation-Id": cid})
    assert response.headers.get("X-Correlation-Id") == cid


def test_upload_missing_idempotency_key():
    fake_audio = io.BytesIO(b"RIFF" + b"\x00" * 200)
    response = client.post(
        "/api/v1/broll/jobs/upload",
        files={"audio": ("sample.wav", fake_audio, "audio/wav")},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "IDEMPOTENCY_KEY_REQUIRED"


def test_upload_rejects_unsupported_format():
    fake_doc = io.BytesIO(b"Some text document content" * 10)
    response = client.post(
        "/api/v1/broll/jobs/upload",
        files={"audio": ("document.txt", fake_doc, "text/plain")},
        headers={"Idempotency-Key": f"test-upload-{uuid.uuid4()}"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "UNSUPPORTED_AUDIO_FORMAT"


def test_upload_rejects_too_small_file():
    tiny_audio = io.BytesIO(b"tiny")
    response = client.post(
        "/api/v1/broll/jobs/upload",
        files={"audio": ("tiny.mp3", tiny_audio, "audio/mpeg")},
        headers={"Idempotency-Key": f"test-upload-{uuid.uuid4()}"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "FILE_TOO_SMALL"


def test_upload_valid_audio_accepted():
    # 500 bytes of dummy mp3 content
    valid_bytes = io.BytesIO(b"\xff\xfb\x90\x44" + b"\x00" * 496)
    key = f"test-upload-{uuid.uuid4()}"
    response = client.post(
        "/api/v1/broll/jobs/upload",
        files={"audio": ("narration.mp3", valid_bytes, "audio/mpeg")},
        data={"aspect_ratios": "16:9,1:1", "style": "modern"},
        headers={"Idempotency-Key": key},
    )
    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert data["status"] in {"queued", "running"}
