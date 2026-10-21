from __future__ import annotations

import json
import subprocess
from pathlib import Path


RATIO_DIMENSIONS = {"16:9": (1920, 1080), "9:16": (1080, 1920), "1:1": (1080, 1080)}


class RenderError(RuntimeError):
    pass


def render_video(ffmpeg_bin: str, narration_audio: Path, clips: list[Path], scenes: list[dict], ratio: str,
                 output: Path, captions_srt: Path | None = None, burn_in: bool = False) -> None:
    """Compose an already-downloaded, rights-approved sequence with narration as the only audio source,
    ensuring each scene's clip is trimmed to its exact narration duration and transitions seamlessly."""
    if ratio not in RATIO_DIMENSIONS or len(clips) != len(scenes) or not clips:
        raise RenderError("Invalid render inputs")
    if not narration_audio.is_file() or any(not clip.is_file() for clip in clips):
        raise RenderError("Narration or selected footage file is missing")

    width, height = RATIO_DIMENSIONS[ratio]
    output.parent.mkdir(parents=True, exist_ok=True)
    temp_dir = output.parent / f"temp_{ratio.replace(':', 'x')}"
    temp_dir.mkdir(parents=True, exist_ok=True)

    trimmed_clips: list[Path] = []
    try:
        # Step 1: Trim and normalize each clip to its scene's exact duration and target aspect ratio
        for idx, (scene, clip) in enumerate(zip(scenes, clips)):
            scene_duration = max(0.5, round(scene["end"] - scene["start"], 3))
            trimmed_path = temp_dir / f"scene_{idx:03d}_{width}x{height}.mp4"

            trim_cmd = [
                ffmpeg_bin, "-y",
                "-stream_loop", "-1",
                "-ss", "0",
                "-t", str(scene_duration),
                "-i", str(clip),
                "-filter:v", f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},fps=30,format=yuv420p",
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "20", "-an",
                str(trimmed_path)
            ]
            res = subprocess.run(trim_cmd, capture_output=True, text=True, timeout=120)
            if res.returncode != 0 or not trimmed_path.is_file():
                raise RenderError(f"SCENE_TRIM_FAILED: scene {scene['id']} - {res.stderr[-500:]}")
            trimmed_clips.append(trimmed_path)

        # Step 2: Concat trimmed clips with audio and burned-in subtitles
        concat_file = output.with_suffix(".concat.txt")
        concat_file.write_text("".join(f"file '{tc.resolve().as_posix()}'\n" for tc in trimmed_clips), encoding="utf-8")

        sub_filter = ""
        if burn_in and captions_srt and captions_srt.is_file():
            srt_escaped = captions_srt.resolve().as_posix().replace(":", r"\:").replace("'", r"\'")
            if ratio == "9:16":
                font_size = 11
                margin_v = 45
            elif ratio == "1:1":
                font_size = 11
                margin_v = 35
            else:  # 16:9
                font_size = 12
                margin_v = 30

            sub_filter = (
                f",subtitles='{srt_escaped}':force_style="
                f"'FontName=Arial,FontSize={font_size},Bold=1,PrimaryColour=&H00FFFFFF,"
                f"OutlineColour=&H00000000,BorderStyle=1,Outline=1.0,Shadow=0.5,"
                f"Alignment=2,MarginV={margin_v}'"
            )

        command = [
            ffmpeg_bin, "-y",
            "-f", "concat", "-safe", "0", "-i", str(concat_file),
            "-i", str(narration_audio),
            "-filter:v", f"fps=30,format=yuv420p{sub_filter}",
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest", str(output)
        ]
        completed = subprocess.run(command, capture_output=True, text=True, timeout=600, check=False)
    except FileNotFoundError as exc:
        raise RenderError("FFmpeg is not installed or FFMPEG_BIN is wrong") from exc
    except subprocess.TimeoutExpired as exc:
        raise RenderError("RENDER_TIMEOUT") from exc
    finally:
        concat_file.unlink(missing_ok=True)
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

    if completed.returncode != 0 or not output.is_file() or output.stat().st_size == 0:
        raise RenderError(f"FFMPEG_RENDER_FAILED: {completed.stderr[-1000:]}")
    _validate_output(ffmpeg_bin, output, width, height)



def _validate_output(ffmpeg_bin: str, output: Path, width: int, height: int) -> None:
    import shutil
    ffprobe_bin = ffmpeg_bin.replace("ffmpeg", "ffprobe")
    streams = None
    if shutil.which(ffprobe_bin) or Path(ffprobe_bin).is_file():
        command = [ffprobe_bin, "-v", "error", "-show_streams", "-of", "json", str(output)]
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=30, check=True)
            streams = json.loads(result.stdout).get("streams", [])
        except Exception:
            streams = None

    if streams is None:
        res = subprocess.run([ffmpeg_bin, "-i", str(output)], capture_output=True, text=True, timeout=30)
        stderr = res.stderr
        has_video = "Video: h264" in stderr
        has_audio = "Audio: aac" in stderr
        has_dims = f"{width}x{height}" in stderr
        if not (has_video and has_audio):
            raise RenderError("INVALID_RENDERED_STREAMS")
        if not has_dims:
            raise RenderError("INVALID_RENDERED_DIMENSIONS")
        return

    video = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
    audio = next((stream for stream in streams if stream.get("codec_type") == "audio"), None)
    if not video or not audio or video.get("codec_name") != "h264" or audio.get("codec_name") != "aac":
        raise RenderError("INVALID_RENDERED_STREAMS")
    if int(video.get("width", 0)) != width or int(video.get("height", 0)) != height:
        raise RenderError("INVALID_RENDERED_DIMENSIONS")

