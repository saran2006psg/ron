from __future__ import annotations

import io
import json
import re
import struct
import tempfile
import wave
from dataclasses import dataclass, field
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
    audio_path: Path | None = None


class AudioValidationError(ValueError):
    pass


# ---------------------------------------------------------------------------
# Edge-TTS production adapter (free Microsoft TTS, commercially usable)
# ---------------------------------------------------------------------------

# Voice mapping: voice identifier -> edge-tts voice name
VOICE_MAP: dict[str, str] = {
    "en-IN-female": "en-IN-NeerjaNeural",
    "en-IN-male": "en-IN-PrabhatNeural",
    "en-US-female": "en-US-JennyNeural",
    "en-US-male": "en-US-GuyNeural",
    "en-GB-female": "en-GB-SoniaNeural",
    "en-GB-male": "en-GB-RyanNeural",
    "hi-IN-female": "hi-IN-SwaraNeural",
    "hi-IN-male": "hi-IN-MadhurNeural",
    "ta-IN-female": "ta-IN-PallaviNeural",
    "ta-IN-male": "ta-IN-ValluvarNeural",
}


class EdgeTTSProvider:
    """Production TTS using Microsoft Edge TTS (free, commercially usable for assessment)."""
    provider_name = "edge-tts"
    model_name = "edge-tts-neural"

    def __init__(self, work_dir: Path) -> None:
        self.work_dir = work_dir
        self.work_dir.mkdir(parents=True, exist_ok=True)

    def synthesize(self, script: str, voice: str) -> AudioTiming:
        text = script.strip()
        if not text:
            raise AudioValidationError("EMPTY_SCRIPT")
        edge_voice = VOICE_MAP.get(voice, "en-IN-NeerjaNeural")
        output_path = self.work_dir / f"narration_{abs(hash(text)) % 10**8}.mp3"
        warnings: list[str] = []
        try:
            import asyncio
            import edge_tts
            async def _generate():
                communicate = edge_tts.Communicate(text, edge_voice)
                await communicate.save(str(output_path))
            asyncio.run(_generate())
        except Exception as exc:
            raise AudioValidationError(f"TTS_SYNTHESIS_FAILED: {exc}") from exc
        if not output_path.is_file() or output_path.stat().st_size < 100:
            raise AudioValidationError("TTS_OUTPUT_EMPTY")
        duration = _probe_duration(output_path)
        if duration <= 0:
            raise AudioValidationError("TTS_OUTPUT_INVALID_DURATION")
        segments = _segments(text, duration)
        warnings.append(f"Generated with {edge_voice} via edge-tts")
        return AudioTiming(duration, text, segments, self.provider_name, self.model_name, warnings, output_path)

    def transcribe_file(self, path: Path, max_seconds: int = 600) -> AudioTiming:
        """Validate and inspect an uploaded audio file."""
        _validate_audio_file(path, max_seconds)
        duration = _probe_duration(path)
        if duration <= 0 or duration > max_seconds:
            raise AudioValidationError("INVALID_AUDIO_DURATION")
        if duration < 0.5:
            raise AudioValidationError("AUDIO_TOO_SHORT")
        return AudioTiming(duration, None, [], "uploaded-file", "user-audio", [], path)


# ---------------------------------------------------------------------------
# Mock adapter (preserved for no-key offline tests)
# ---------------------------------------------------------------------------

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

    def transcribe_file(self, path: Path, max_seconds: int = 600) -> AudioTiming:
        """Mock file inspection for testing."""
        _validate_audio_file(path, max_seconds)
        duration = _probe_duration(path)
        if duration <= 0 or duration > max_seconds:
            raise AudioValidationError("INVALID_AUDIO_DURATION")
        return AudioTiming(duration, None, [], self.provider_name, self.model_name,
                           ["Mock file transcription for local tests only."], path)


# ---------------------------------------------------------------------------
# Audio file validation helpers
# ---------------------------------------------------------------------------

ALLOWED_MIME_SIGNATURES: dict[bytes, str] = {
    b"ID3": "audio/mpeg",           # MP3 with ID3 tag
    b"\xff\xfb": "audio/mpeg",      # MP3 MPEG1 Layer 3
    b"\xff\xf3": "audio/mpeg",      # MP3 MPEG2 Layer 3
    b"\xff\xf2": "audio/mpeg",      # MP3 MPEG2.5 Layer 3
    b"RIFF": "audio/wav",           # WAV
    b"ftyp": "audio/m4a",           # M4A (4 bytes in, after size)
}

MAX_UPLOAD_BYTES = 100 * 1024 * 1024  # 100 MB


def _validate_audio_file(path: Path, max_seconds: int = 600) -> None:
    """Validate that a file is a readable MP3, WAV, or M4A."""
    if not path.is_file():
        raise AudioValidationError("FILE_NOT_FOUND")
    size = path.stat().st_size
    if size < 100:
        raise AudioValidationError("CORRUPT_OR_EMPTY_AUDIO")
    if size > MAX_UPLOAD_BYTES:
        raise AudioValidationError("FILE_TOO_LARGE")
    header = path.read_bytes()[:12]
    detected = None
    for magic, mime in ALLOWED_MIME_SIGNATURES.items():
        if magic == b"ftyp":
            if header[4:8] == b"ftyp":
                detected = mime
                break
        elif header.startswith(magic):
            detected = mime
            break
    if not detected:
        raise AudioValidationError("UNSUPPORTED_AUDIO_FORMAT")


def _probe_duration(path: Path) -> float:
    """Try to get duration using mutagen, fallback to wave stdlib for WAV."""
    try:
        import mutagen
        audio = mutagen.File(str(path))
        if audio is not None and audio.info is not None:
            return float(audio.info.length)
    except Exception:
        pass
    # Fallback for raw WAV
    try:
        return _wav_duration(path)
    except Exception:
        pass
    # Last resort: estimate from file size for MP3 (128kbps assumed)
    suffix = path.suffix.lower()
    if suffix == ".mp3":
        return path.stat().st_size / (128 * 1024 / 8)
    return 0.0


def _wav_duration(path: Path) -> float:
    """Read WAV duration using stdlib wave module."""
    with wave.open(str(path), "rb") as stream:
        frames, rate = stream.getnframes(), stream.getframerate()
    if rate <= 0:
        return 0.0
    return frames / rate


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


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

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
