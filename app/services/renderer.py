from __future__ import annotations

import json
import subprocess
from pathlib import Path


RATIO_DIMENSIONS = {"16:9": (1920, 1080), "9:16": (1080, 1920), "1:1": (1080, 1080)}


class RenderError(RuntimeError):
    pass


def render_video(ffmpeg_bin: str, narration_audio: Path, clips: list[Path], scenes: list[dict], ratio: str,
                 output: Path, captions_srt: Path | None = None, burn_in: bool = False) -> None:
    """Compose an already-downloaded, rights-approved sequence with narration as the only audio source."""
    if ratio not in RATIO_DIMENSIONS or len(clips) != len(scenes) or not clips:
        raise RenderError("Invalid render inputs")
    if not narration_audio.is_file() or any(not clip.is_file() for clip in clips):
        raise RenderError("Narration or selected footage file is missing")
    width, height = RATIO_DIMENSIONS[ratio]
    output.parent.mkdir(parents=True, exist_ok=True)
    concat_file = output.with_suffix(".concat.txt")
    concat_file.write_text("".join(f"file '{clip.resolve().as_posix()}'\n" for clip in clips), encoding="utf-8")
    filter_chain = f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},fps=30,format=yuv420p"
    if burn_in and captions_srt and captions_srt.is_file():
        filter_chain += f",subtitles='{captions_srt.resolve().as_posix().replace(':', r'\:')}'"
    command = [ffmpeg_bin, "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-i", str(narration_audio),
               "-filter:v", filter_chain, "-map", "0:v:0", "-map", "1:a:0", "-c:v", "libx264", "-preset", "medium",
               "-crf", "20", "-r", "30", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(output)]
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=600, check=False)
    except FileNotFoundError as exc:
        raise RenderError("FFmpeg is not installed or FFMPEG_BIN is wrong") from exc
    except subprocess.TimeoutExpired as exc:
        raise RenderError("RENDER_TIMEOUT") from exc
    finally:
        concat_file.unlink(missing_ok=True)
    if completed.returncode != 0 or not output.is_file() or output.stat().st_size == 0:
        raise RenderError(f"FFMPEG_RENDER_FAILED: {completed.stderr[-1000:]}")
    _validate_output(ffmpeg_bin, output, width, height)


def _validate_output(ffmpeg_bin: str, output: Path, width: int, height: int) -> None:
    command = [ffmpeg_bin.replace("ffmpeg", "ffprobe"), "-v", "error", "-show_streams", "-of", "json", str(output)]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=30, check=True)
        streams = json.loads(result.stdout).get("streams", [])
    except (FileNotFoundError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        raise RenderError("FFPROBE_VALIDATION_FAILED") from exc
    video = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
    audio = next((stream for stream in streams if stream.get("codec_type") == "audio"), None)
    if not video or not audio or video.get("codec_name") != "h264" or audio.get("codec_name") != "aac":
        raise RenderError("INVALID_RENDERED_STREAMS")
    if int(video.get("width", 0)) != width or int(video.get("height", 0)) != height:
        raise RenderError("INVALID_RENDERED_DIMENSIONS")
