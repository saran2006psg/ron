from __future__ import annotations

import json
import logging
import shutil
import subprocess
import time
from pathlib import Path

from ..config import settings
from ..models import JobState
from ..providers.audio import AudioTiming, AudioValidationError, EdgeTTSProvider, MockNarrationProvider
from ..providers.footage import (
    DemoFootageProvider, FootageCandidate, MockFootageProvider,
    MultiSourceFootageProvider, PexelsVideoProvider, PixabayVideoProvider,
    ProviderUnavailableError, apply_safety_filter, download_clip, eligible,
)
from ..services.artifacts import write_audit_artifacts
from ..services.matching import select_clip
from ..services.planner import plan_scenes
from ..services.renderer import RenderError, render_video
from ..store import JobStore

log = logging.getLogger(__name__)


def _get_narration_provider():
    """Select narration provider based on config."""
    if settings.tts_provider == "edge-tts":
        return EdgeTTSProvider(settings.work_dir)
    return MockNarrationProvider()


def _get_footage_provider():
    """Select footage provider based on config, with dual-source failover."""
    if settings.footage_provider == "demo":
        return DemoFootageProvider(settings.work_dir, settings.ffmpeg_bin)
    elif settings.footage_provider == "pexels":
        primary = PexelsVideoProvider(settings.pexels_api_key)
        secondary = None
        if settings.pixabay_api_key:
            secondary = PixabayVideoProvider(settings.pixabay_api_key)
        return MultiSourceFootageProvider(primary, secondary)
    elif settings.footage_provider == "pixabay":
        primary = PixabayVideoProvider(settings.pixabay_api_key)
        secondary = PexelsVideoProvider(settings.pexels_api_key) if settings.pexels_api_key else DemoFootageProvider(settings.work_dir, settings.ffmpeg_bin)
        return MultiSourceFootageProvider(primary, secondary)
    elif settings.footage_provider == "multi":
        providers = []
        primary = None
        secondary = None
        if settings.pexels_api_key:
            primary = PexelsVideoProvider(settings.pexels_api_key)
        if settings.pixabay_api_key:
            secondary = PixabayVideoProvider(settings.pixabay_api_key)
        if primary:
            return MultiSourceFootageProvider(primary, secondary)
        elif secondary:
            return MultiSourceFootageProvider(secondary)
        return MockFootageProvider()
    return MockFootageProvider()


def run_job(store: JobStore, job_id: str) -> None:
    record = store.get(job_id)
    if not record:
        return
    request = record["request_json"]
    warnings: list[str] = []
    job_work_dir = settings.work_dir / job_id
    job_work_dir.mkdir(parents=True, exist_ok=True)
    try:
        store.update(job_id, state=JobState.running, progress=5)

        # ---------------------------------------------------------------
        # Stage 1: Narration / Audio (5% → 25%)
        # ---------------------------------------------------------------
        narration = _get_narration_provider()
        audio: AudioTiming

        if request.get("audio_url"):
            audio = narration.transcribe_url(request["audio_url"])
            if not audio.transcript:
                raise RuntimeError("AUDIO_TRANSCRIPT_UNAVAILABLE: audio requires a transcription adapter or transcript")
            scenes = plan_scenes(audio.transcript, None, audio.duration_seconds)
        elif request.get("audio_upload_path"):
            # File was uploaded and saved by the API endpoint
            audio = narration.transcribe_file(Path(request["audio_upload_path"]), settings.max_audio_seconds)
            if not audio.transcript:
                # Use script from scenes if available, otherwise use a placeholder
                script_text = " ".join(scene["text"] for scene in request.get("scenes", []))
                scenes = plan_scenes(script_text or None, request.get("scenes"), audio.duration_seconds)
            else:
                scenes = plan_scenes(audio.transcript, None, audio.duration_seconds)
        else:
            script = request.get("script") or " ".join(scene["text"] for scene in request.get("scenes", []))
            audio = narration.synthesize(script, request.get("voice", "en-IN-female"))
            scenes = plan_scenes(request.get("script"), request.get("scenes"), audio.duration_seconds)

        warnings.extend(audio.warnings)
        store.update(job_id, progress=25)

        # ---------------------------------------------------------------
        # Stage 2: Footage search & selection (25% → 55%)
        # ---------------------------------------------------------------
        provider = _get_footage_provider()
        selections: list[tuple[dict, FootageCandidate, float, str]] = []
        used_asset_urls: set[str] = set()

        for i, scene in enumerate(scenes):
            try:
                candidates = provider.search(scene["query"], request.get("avoid", []))
                # Apply content safety filter
                candidates = apply_safety_filter(candidates, request.get("avoid", []))
            except ProviderUnavailableError as exc:
                warnings.append(f"Provider outage for scene {scene['id']}: {exc}")
                candidates = []

            match = select_clip(scene, candidates, used_asset_urls)
            if not match.candidate:
                raise RuntimeError(f"NO_SEMANTIC_LICENSED_FOOTAGE: {scene['id']} - {match.reason}")

            used_asset_urls.add(match.candidate.asset_url)
            selections.append((scene, match.candidate, match.score, match.reason))

            # Update progress proportionally
            progress = 25 + int(30 * (i + 1) / len(scenes))
            store.update(job_id, progress=progress)

        store.update(job_id, progress=55)

        # ---------------------------------------------------------------
        # Stage 3: Download clips (55% → 70%)
        # ---------------------------------------------------------------
        clips_dir = job_work_dir / "clips"
        clips_dir.mkdir(parents=True, exist_ok=True)
        clip_paths: list[Path] = []

        for i, (scene, candidate, score, reason) in enumerate(selections):
            clip_path = clips_dir / f"{scene['id']}.mp4"
            if candidate.asset_url.startswith("mock://"):
                # For mock provider, create a minimal test file
                warnings.append(f"Mock clip used for {scene['id']} — not production media")
                # Create a tiny placeholder — renderer will fail on this, which is correct behavior
                clip_path.write_bytes(b"MOCK_VIDEO_PLACEHOLDER")
            else:
                try:
                    download_clip(candidate.asset_url, clip_path)
                except RuntimeError as exc:
                    raise RuntimeError(f"CLIP_DOWNLOAD_FAILED: {scene['id']} - {exc}") from exc
            clip_paths.append(clip_path)
            progress = 55 + int(15 * (i + 1) / len(selections))
            store.update(job_id, progress=progress)

        store.update(job_id, progress=70)

        # ---------------------------------------------------------------
        # Stage 4: Write audit artifacts (70% → 75%)
        # ---------------------------------------------------------------
        output_dir = settings.artifact_dir / job_id
        narration_info = {"provider": audio.provider, "model": audio.model,
                          "duration": audio.duration_seconds, "voice": request.get("voice")}
        artifact_paths = write_audit_artifacts(output_dir, job_id, scenes, selections, narration_info, request, warnings)
        store.update(job_id, progress=75)

        # ---------------------------------------------------------------
        # Stage 5: Render video(s) (75% → 95%)
        # ---------------------------------------------------------------
        aspect_ratios = request.get("aspect_ratios", ["16:9"])
        captions_cfg = request.get("captions", {})
        burn_in = captions_cfg.get("burn_in", True) if isinstance(captions_cfg, dict) else True
        srt_requested = captions_cfg.get("srt", True) if isinstance(captions_cfg, dict) else True

        result_links: dict[str, str] = {}
        narration_audio_path = audio.audio_path

        if narration_audio_path and narration_audio_path.is_file():
            for ratio_idx, ratio in enumerate(aspect_ratios):
                ratio_slug = ratio.replace(":", "x")
                output_path = output_dir / f"output_{ratio_slug}.mp4"
                srt_path = artifact_paths.get("captions")
                try:
                    render_video(
                        settings.ffmpeg_bin, narration_audio_path, clip_paths, scenes, ratio,
                        output_path, captions_srt=srt_path if burn_in else None, burn_in=burn_in
                    )
                    result_links[f"video_{ratio_slug}"] = f"{settings.public_base_url}/artifacts/{job_id}/output_{ratio_slug}.mp4"
                except RenderError as exc:
                    warnings.append(f"Render failed for {ratio}: {exc}")

                progress = 75 + int(20 * (ratio_idx + 1) / len(aspect_ratios))
                store.update(job_id, progress=progress)
        else:
            warnings.append("No narration audio file available — rendering skipped. Configure TTS_PROVIDER=edge-tts or upload audio.")

        # Add artifact links
        if artifact_paths.get("timeline") and artifact_paths["timeline"].is_file():
            result_links["timeline"] = f"{settings.public_base_url}/artifacts/{job_id}/timeline.json"
        if artifact_paths.get("manifest") and artifact_paths["manifest"].is_file():
            result_links["manifest"] = f"{settings.public_base_url}/artifacts/{job_id}/manifest.json"
        if srt_requested and artifact_paths.get("captions") and artifact_paths["captions"].is_file():
            result_links["captions"] = f"{settings.public_base_url}/artifacts/{job_id}/captions.srt"

        store.update(job_id, progress=95)

        # ---------------------------------------------------------------
        # Stage 6: Finalize (95% → 100%)
        # ---------------------------------------------------------------
        store.update(job_id, state=JobState.succeeded, progress=100, results=result_links, warnings=warnings)
        log.info("job_succeeded", extra={"job_id": job_id, "result_count": len(result_links)})

    except Exception as exc:
        code, _, detail = str(exc).partition(":")
        error = {
            "code": code if code.isupper() else "JOB_FAILED",
            "message": detail.strip() or str(exc),
            "retryable": code in {"PROVIDER_UNAVAILABLE", "RENDER_TIMEOUT"},
            "details": {},
        }
        warnings.append("Job failed safely; no unverified media was rendered.")
        store.update(job_id, state=JobState.failed, progress=100, error=error, warnings=warnings)
        log.exception("job_failed", extra={"job_id": job_id})
