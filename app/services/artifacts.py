from __future__ import annotations

import json
from pathlib import Path


def write_audit_artifacts(output_dir: Path, job_id: str, scenes: list[dict], selections: list[tuple],
                          narration: dict, request: dict, warnings: list[str]) -> dict[str, Path]:
    """Write only observed pipeline facts; callers must not substitute placeholders as evidence."""
    output_dir.mkdir(parents=True, exist_ok=True)
    selected = {scene["id"]: (candidate, score, reason) for scene, candidate, score, reason in selections}
    timeline_scenes = []
    for scene in scenes:
        candidate, score, reason = selected[scene["id"]]
        timeline_scenes.append({
            "scene_id": scene["id"], "narration_text": scene["text"], "start": scene["start"], "end": scene["end"],
            "visual_query": scene["query"], "warnings": scene["warnings"], "clip": {
                "asset_url": candidate.asset_url, "provider": candidate.provider, "license_name": candidate.license_name,
                "license_url": candidate.license_url, "creator": candidate.creator, "attribution": candidate.attribution,
                "commercial_use": candidate.commercial_use, "watermark_free": candidate.watermark_free,
                "ai_generated": candidate.ai_generated, "rights_verified": candidate.rights_verified,
            }, "selection_reason": reason, "relevance_score": score,
        })
    timeline = {"job_id": job_id, "scenes": timeline_scenes, "duration": scenes[-1]["end"] if scenes else 0}
    manifest = {"job_id": job_id, "providers": {"narration": narration}, "settings": {
        "aspect_ratios": request.get("aspect_ratios"), "style": request.get("style"), "avoid": request.get("avoid"),
        "captions": request.get("captions"),
    }, "warnings": warnings, "cost_estimate": {"value": None, "status": "unavailable"},
                "render": {"status": "not_rendered"}}
    paths = {"timeline": output_dir / "timeline.json", "manifest": output_dir / "manifest.json", "captions": output_dir / "captions.srt"}
    paths["timeline"].write_text(json.dumps(timeline, indent=2), encoding="utf-8")
    paths["manifest"].write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    paths["captions"].write_text(_srt(scenes), encoding="utf-8")
    return paths


def _srt(scenes: list[dict]) -> str:
    blocks = []
    for number, scene in enumerate(scenes, 1):
        blocks.append(f"{number}\n{_timestamp(scene['start'])} --> {_timestamp(scene['end'])}\n{scene['text']}\n")
    return "\n".join(blocks)


def _timestamp(seconds: float) -> str:
    milliseconds = round(seconds * 1000)
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    whole_seconds, milliseconds = divmod(milliseconds, 1000)
    return f"{hours:02}:{minutes:02}:{whole_seconds:02},{milliseconds:03}"
