# Remaining Work: IncuBrix B-roll Engine

This file is the authoritative execution checklist for assessment work.

## Completed Milestones

- [x] **Real TTS & Audio Uploads**: Integrated Microsoft Edge Neural TTS (`EdgeTTSProvider`) supporting English, Hindi, and Tamil voices with zero API key requirement; multipart upload endpoint for MP3/WAV/M4A with audio duration & format validation.
- [x] **Licensed Footage Retrieval**: Dual-source retrieval (`PixabayVideoProvider` + `PexelsVideoProvider`) with graceful fallback to `DemoFootageProvider`. Zero clip repetition, rights verification, and metadata logging in `timeline.json`.
- [x] **Video Normalization & Multi-Ratio Rendering**: Normalized 1080p rendering (16:9 1920x1080, 9:16 1080x1920, 1:1 1080x1080) at 30 fps, H.264/AAC. Per-scene clip trimming exactly matching narration timing.
- [x] **Broadcast Subtitle Overhaul**: Proportional phrase-chunked subtitles (`BorderStyle=1`, subtle outline & drop-shadow), positioned in lower-third safe zones tuned for each aspect ratio.
- [x] **Single-Clip Swap (Advanced Criterion)**: Implemented `POST /api/v1/jobs/{job_id}/swap` allowing users to replace any individual scene's clip with an accelerated re-render without re-generating full audio or unaffected scenes.
- [x] **Audit Deliverables & Integration Standard**: Full OpenAPI 3.1 specification (`openapi.yaml`), structured JSON logs (`X-Correlation-Id`), Idempotency-Key reuse, and automated test suite (43/43 passing offline with no API keys).
- [x] **Creator Studio Web UI**: Modern dark-mode React interface with multi-modal tabs (Script, Audio Upload, JSON Scenes), aspect ratio selection, voice options, live polling, and video preview.

## Final Submission Checklist

1. [ ] **Batch Evaluation Pack**: Execute all 10 Core fixtures via `cli/batch_runner.py fixtures/ output/` to produce all finished MP4s, SRTs, manifests, and timelines.
2. [ ] **Report Numbers**: Record measured turnaround, cost per minute ($0.00 using EdgeTTS + Pixabay), relevance, and reliability metrics in `REPORT.md`.
3. [ ] **Excel Submission Form**: Fill in the assessment spreadsheet with evidence links and measured metrics.
4. [ ] **Live Demo & Demo Video**: Expose port 8000 via a public tunnel / cloud host, and record an unedited <=8-minute screen recording demonstrating the core engine.

