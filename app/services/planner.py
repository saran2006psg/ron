from __future__ import annotations

import re

AMBIGUOUS = {"bank", "cloud", "mouse", "python", "value"}
SENSITIVE = {"death", "dead", "funeral", "war", "attack", "suicide", "disaster"}


def plan_scenes(script: str | None, supplied: list[dict] | None = None, duration: float | None = None) -> list[dict]:
    raw = supplied or [{"text": piece.strip(), "visual_hint": None}
                       for piece in re.split(r"(?<=[.!?])\s+", script or "") if piece.strip()]
    if not raw:
        raise ValueError("No scenes could be planned")
    durations = _durations(raw, duration)
    output, start = [], 0.0
    for index, (scene, seconds) in enumerate(zip(raw, durations), 1):
        text = scene["text"].strip()
        words = {word.lower() for word in re.findall(r"[A-Za-z]+", text)}
        warnings = []
        if words & AMBIGUOUS:
            warnings.append("AMBIGUOUS_TERM_REQUIRES_CONTEXT")
        if words & SENSITIVE:
            warnings.append("SENSITIVE_TOPIC_USE_RESPECTFUL_VISUALS")
        output.append({"id": f"scene-{index:03d}", "text": text, "visual_hint": scene.get("visual_hint"),
                       "start": round(start, 3), "end": round(start + seconds, 3), "duration": round(seconds, 3),
                       "query": scene.get("visual_hint") or text, "warnings": warnings})
        start += seconds
    return output


def _durations(scenes: list[dict], total: float | None) -> list[float]:
    weights = [max(1, len(re.findall(r"\w+", item["text"]))) for item in scenes]
    total = total if total and total > 0 else sum(max(2.0, weight / 2.5) for weight in weights)
    return [total * weight / sum(weights) for weight in weights]

