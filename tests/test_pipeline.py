"""Integration tests for the full pipeline logic."""
import json
import os
import tempfile
import time
from pathlib import Path

import pytest

from app.models import JobState
from app.store import JobStore


@pytest.fixture
def tmp_store(tmp_path):
    """Create a JobStore in pytest's tmp_path (which handles cleanup properly on Windows)."""
    db_path = tmp_path / "test.db"
    return JobStore(db_path)


def test_pipeline_runs_with_mock_provider_and_fails_safely(tmp_store, monkeypatch):
    """Mock footage is intentionally ineligible — pipeline should fail with a clear error code."""
    from app.providers.footage import MockFootageProvider
    monkeypatch.setattr("app.services.pipeline._get_footage_provider", lambda: MockFootageProvider())
    request = {"script": "Cloud computing is changing everything.", "voice": "en-IN-female",
                "aspect_ratios": ["16:9"], "avoid": [], "captions": {"burn_in": True, "srt": True}}
    job_id, _ = tmp_store.create_or_get("test-pipe-1", request)

    # Import and run pipeline (uses mock provider by default)
    from app.services.pipeline import run_job
    run_job(tmp_store, job_id)

    job = tmp_store.get(job_id)
    # Mock provider footage is NOT eligible, so job should fail with NO_SEMANTIC_LICENSED_FOOTAGE
    assert job["state"] == JobState.failed.value
    assert job["error_json"]["code"] == "NO_SEMANTIC_LICENSED_FOOTAGE"
    assert job["progress"] == 100


def test_pipeline_handles_empty_job_id(tmp_store):
    """Pipeline should gracefully handle non-existent job ID."""
    from app.services.pipeline import run_job
    # Should return without error
    run_job(tmp_store, "nonexistent-job-id")


def test_store_create_and_retrieve(tmp_store):
    """Job store creates and retrieves jobs correctly."""
    job_id, reused = tmp_store.create_or_get("key-1", {"script": "test"})
    assert not reused
    assert len(job_id) > 0

    job_id2, reused2 = tmp_store.create_or_get("key-1", {"script": "test"})
    assert reused2
    assert job_id2 == job_id

    job = tmp_store.get(job_id)
    assert job is not None
    assert job["state"] == "queued"
    assert job["progress"] == 0


def test_store_update(tmp_store):
    """Job store updates state, progress, and results."""
    job_id, _ = tmp_store.create_or_get("key-update", {"script": "test"})

    tmp_store.update(job_id, state=JobState.running, progress=50)
    job = tmp_store.get(job_id)
    assert job["state"] == "running"
    assert job["progress"] == 50

    tmp_store.update(job_id, state=JobState.succeeded, progress=100,
                     results={"video": "http://test/video.mp4"},
                     warnings=["test warning"])
    job = tmp_store.get(job_id)
    assert job["state"] == "succeeded"
    assert job["results_json"]["video"] == "http://test/video.mp4"
    assert "test warning" in job["warnings_json"]


def test_store_nonexistent_job(tmp_store):
    """Getting a non-existent job returns None."""
    assert tmp_store.get("nonexistent") is None
