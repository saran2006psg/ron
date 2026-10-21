from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path

from ..config import settings
from ..models import JobState
from ..providers.audio import AudioValidationError, MockNarrationProvider
from ..providers.footage import MockFootageProvider, PexelsVideoProvider, eligible
from ..services.matching import select_clip
from ..services.planner import plan_scenes
from ..store import JobStore

log = logging.getLogger(__name__)


def run_job(store: JobStore, job_id: str) -> None:
    record = store.get(job_id)
    if not record:
        return
    request = record["request_json"]
    warnings: list[str] = []
    try:
        store.update(job_id, state=JobState.running, progress=5)
        narration = MockNarrationProvider()
        if request.get("audio_url"):
            audio = narration.transcribe_url(request["audio_url"])
            if not audio.transcript:
                raise RuntimeError("AUDIO_TRANSCRIPT_UNAVAILABLE: audio requires a transcription adapter or transcript")
            scenes = plan_scenes(audio.transcript, None, audio.duration_seconds)
        else:
            script = request.get("script") or " ".join(scene["text"] for scene in request.get("scenes", []))
            audio = narration.synthesize(script, request.get("voice", "en-IN-female"))
            scenes = plan_scenes(request.get("script"), request.get("scenes"), audio.duration_seconds)
        warnings.extend(audio.warnings)
        store.update(job_id, progress=25)
        provider = PexelsVideoProvider(settings.pexels_api_key) if settings.footage_provider == "pexels" else MockFootageProvider()
        selections, used_asset_urls = [], set()
        for scene in scenes:
            candidates = provider.search(scene["query"], request.get("avoid", []))
            match = select_clip(scene, candidates, used_asset_urls)
            if not match.candidate:
                raise RuntimeError(f"NO_SEMANTIC_LICENSED_FOOTAGE: {scene['id']} - {match.reason}")
            used_asset_urls.add(match.candidate.asset_url)
            selections.append((scene, match.candidate, match.score, match.reason))
        store.update(job_id, progress=55)
        # Rendering is intentionally blocked for mock-only selections: passing a mock as production media would violate rights rules.
        raise RuntimeError("RENDERER_NOT_IMPLEMENTED: selected footage is verified but FFmpeg composition/timeline artifacts are pending")
    except Exception as exc:
        code, _, detail = str(exc).partition(":")
        error = {"code": code if code.isupper() else "JOB_FAILED", "message": detail.strip() or str(exc),
                 "retryable": code in {"PROVIDER_UNAVAILABLE", "RENDER_TIMEOUT"}, "details": {}}
        warnings.append("Job failed safely; no unverified media was rendered.")
        store.update(job_id, state=JobState.failed, progress=100, error=error, warnings=warnings)
        log.exception("job_failed", extra={"job_id": job_id})

