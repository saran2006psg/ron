from __future__ import annotations

import re
import wave
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, urlparse


@dataclass(frozen=True)
class AudioTiming:
    duration_seconds: float
    transcript: str | None
    segments: list[dict]
    provider: str
    model: str
    warnings: list[str]


class AudioValidationError(ValueError):
    pass


class MockNarrationProvider:
    """Offline deterministic timing adapter. It intentionally does not synthesize a production voice."""
    provider_name = "mock-narration"
    model_name = "word-rate-v1"

    def synthesize(self, script: str, voice: str) -> AudioTiming:
        text = script.strip()
        if not text:
            raise AudioValidationError("EMPTY_SCRIPT")
        words = re.findall(r"\S+", text)
        duration = max(1.0, len(words) / 2.5)
        return AudioTiming(duration, text, _segments(text, duration), self.provider_name, self.model_name,
                           ["Mock timing is for local tests only; configure commercial TTS for production."])

    def transcribe_url(self, url: str) -> AudioTiming:
        parsed = urlparse(url)
        duration = float(parse_qs(parsed.query).get("duration", ["0"])[0])
        if not 0 < duration <= 600:
            raise AudioValidationError("INVALID_AUDIO_DURATION")
        transcript = parse_qs(parsed.query).get("transcript", [None])[0]
        return AudioTiming(duration, transcript, _segments(transcript or "", duration), self.provider_name,
                           self.model_name, ["Mock URL timing is for local tests only."])


def inspect_wav(path: Path, max_seconds: int) -> AudioTiming:
    try:
        with wave.open(str(path), "rb") as stream:
            frames, rate, channels = stream.getnframes(), stream.getframerate(), stream.getnchannels()
    except (wave.Error, OSError) as exc:
        raise AudioValidationError("CORRUPT_OR_UNSUPPORTED_AUDIO") from exc
    duration = frames / rate if rate else 0
    if channels < 1 or not 0 < duration <= max_seconds:
        raise AudioValidationError("INVALID_AUDIO_DURATION")
    return AudioTiming(duration, None, [], "local-wav-inspector", "stdlib-wave", [])


def _segments(text: str, duration: float) -> list[dict]:
    sentences = [item.strip() for item in re.split(r"(?<=[.!?])\s+", text) if item.strip()] or ([text] if text else [])
    if not sentences:
        return []
    weights = [max(1, len(re.findall(r"\S+", item))) for item in sentences]
    start, output = 0.0, []
    for index, (sentence, weight) in enumerate(zip(sentences, weights)):
        span = duration * weight / sum(weights)
        output.append({"id": f"segment-{index + 1:03d}", "text": sentence, "start": round(start, 3), "end": round(start + span, 3)})
        start += span
    return output
