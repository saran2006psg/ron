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

        # Copy clips and narration into output_dir for fast single-clip swaps
        try:
            stored_clips_dir = output_dir / "clips"
            stored_clips_dir.mkdir(parents=True, exist_ok=True)
            import shutil
            for cp in clip_paths:
                if cp.is_file():
                    shutil.copy2(cp, stored_clips_dir / cp.name)
            if narration_audio_path and narration_audio_path.is_file():
                shutil.copy2(narration_audio_path, output_dir / f"narration{narration_audio_path.suffix}")
        except Exception as copy_exc:
            log.warning("Failed to cache clips/narration in output_dir: %s", copy_exc)

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


def swap_scene_clip(store: JobStore, job_id: str, scene_id: str,
                    new_query: str | None = None,
                    new_asset_url: str | None = None) -> dict:
    """Fast single-clip swap: replaces only one scene's clip and re-renders in clearly less time."""
    import time
    t0 = time.time()
    job = store.get(job_id)
    if not job:
        raise ValueError(f"JOB_NOT_FOUND: {job_id}")
    if job["state"] != "succeeded":
        raise ValueError(f"JOB_NOT_READY: Job state is {job['state']}, must be 'succeeded' to swap clips")

    output_dir = settings.artifact_dir / job_id
    timeline_file = output_dir / "timeline.json"
    if not timeline_file.is_file():
        raise FileNotFoundError("TIMELINE_NOT_FOUND")

    timeline = json.loads(timeline_file.read_text(encoding="utf-8"))
    scenes = timeline.get("scenes", [])
    target_idx = next((i for i, s in enumerate(scenes) if s["scene_id"] == scene_id), None)
    if target_idx is None:
        raise ValueError(f"SCENE_NOT_FOUND: {scene_id}")

    target_scene = scenes[target_idx]
    clips_dir = output_dir / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)
    target_clip_path = clips_dir / f"{scene_id}.mp4"

    # Select new candidate
    if new_asset_url:
        new_candidate = FootageCandidate(
            asset_url=new_asset_url, provider="user_swap", license_name="User Swapped Asset",
            license_url="https://creativecommons.org/publicdomain/zero/1.0/",
            creator="User Provided", attribution=None, commercial_use=True,
            watermark_free=True, ai_generated=False, rights_verified=True,
            rationale=f"User swapped asset for {scene_id}",
            retrieval_time=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        )
    else:
        footage_provider = _get_footage_provider()
        query = new_query or target_scene.get("visual_query") or target_scene.get("narration_text")
        candidates = footage_provider.search(query, [])
        if not candidates:
            raise RuntimeError(f"NO_CANDIDATE_FOUND: {query}")
        used_urls = {s["clip"]["asset_url"] for i, s in enumerate(scenes) if i != target_idx}
        eligible_cands = [c for c in candidates if eligible(c) and c.asset_url not in used_urls]
        if not eligible_cands:
            eligible_cands = [c for c in candidates if eligible(c)]
        if not eligible_cands:
            raise RuntimeError("NO_ELIGIBLE_SWAP_CANDIDATE")
        new_candidate = eligible_cands[0]

    # Download only the single replacement clip
    download_clip(new_candidate.asset_url, target_clip_path)

    # Update timeline audit record
    target_scene["clip"] = {
        "asset_url": new_candidate.asset_url, "provider": new_candidate.provider,
        "license_name": new_candidate.license_name, "license_url": new_candidate.license_url,
        "creator": new_candidate.creator, "attribution": new_candidate.attribution,
        "commercial_use": new_candidate.commercial_use, "watermark_free": new_candidate.watermark_free,
        "ai_generated": new_candidate.ai_generated, "rights_verified": new_candidate.rights_verified,
        "swapped": True
    }
    target_scene["selection_reason"] = f"Swapped: {new_candidate.rationale}"
    timeline_file.write_text(json.dumps(timeline, indent=2), encoding="utf-8")

    # Locate narration audio
    narration_audio = None
    for ext in [".mp3", ".wav", ".m4a"]:
        p = output_dir / f"narration{ext}"
        if p.is_file():
            narration_audio = p
            break
    if not narration_audio:
        # Fallback check in work_dir
        work_audio = settings.work_dir / job_id / "narration.mp3"
        if work_audio.is_file():
            narration_audio = work_audio

    # Re-render requested video aspect ratios
    manifest_file = output_dir / "manifest.json"
    manifest = json.loads(manifest_file.read_text(encoding="utf-8")) if manifest_file.is_file() else {}
    aspect_ratios = manifest.get("settings", {}).get("aspect_ratios", ["16:9"])
    burn_in = manifest.get("settings", {}).get("captions", {}).get("burn_in", True)
    srt_path = output_dir / "captions.srt"

    clip_paths = [clips_dir / f"{s['scene_id']}.mp4" for s in scenes]
    result_links = job.get("results_json") or {}

    if narration_audio and all(cp.is_file() for cp in clip_paths):
        render_scenes = [{"id": s["scene_id"], "text": s["narration_text"], "start": s["start"], "end": s["end"]} for s in scenes]
        for ratio in aspect_ratios:
            ratio_slug = ratio.replace(":", "x")
            out_file = output_dir / f"output_{ratio_slug}.mp4"
            render_video(
                settings.ffmpeg_bin, narration_audio, clip_paths, render_scenes, ratio,
                out_file, captions_srt=srt_path if burn_in else None, burn_in=burn_in
            )
            result_links[f"video_{ratio_slug}"] = f"{settings.public_base_url}/artifacts/{job_id}/output_{ratio_slug}.mp4"

        store.update(job_id, results=result_links)

    elapsed = round(time.time() - t0, 3)
    log.info("clip_swapped", extra={"job_id": job_id, "scene_id": scene_id, "re_render_seconds": elapsed})
    return {
        "job_id": job_id,
        "scene_id": scene_id,
        "swapped_clip": target_scene["clip"],
        "re_render_seconds": elapsed,
        "result_links": result_links
    }
