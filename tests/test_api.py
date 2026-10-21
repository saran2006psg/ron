import uuid

import pytest
from pydantic import ValidationError

from app.main import create_job, get_job, health, ready
from app.models import CreateJobRequest

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

