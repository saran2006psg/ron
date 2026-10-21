# Remaining Work: IncuBrix B-roll Engine

This file is the authoritative execution checklist for unfinished assessment work. Do not change an item to complete without the specified proof.

## 1. Connect narration to real audio

1. Choose commercially usable TTS and transcription services; record versions, terms, pricing, and the date checked in `SOURCES.md`.
2. Implement adapters behind configuration; keep the mock adapter for no-key tests.
3. Add file upload support for MP3/WAV/M4A and URL downloading with size/type/duration checks.
4. Use transcription word/segment timestamps for provided audio, reject silent/music-only/corrupt audio with clear error codes, and write real narration audio to job storage.
5. Prove it with fixtures and tests for all supported formats, empty script, silence, music-only audio, corruption, and provider failures.

## 2. Finish commercial footage retrieval

1. Configure `PEXELS_API_KEY` or another provider key through the deployment secret store; never commit it.
2. Confirm current provider/API terms and capture the selected asset’s source URL, licence URL/name, creator, attribution, watermark check, commercial-use decision, and review timestamp in `timeline.json`.
3. Add a second verified footage source or an explicit safe fallback to satisfy the provider-outage must-have and Advanced criterion.
4. Add content-safety filtering for people, logos, brands, sensitive events, and the user `avoid` list. Failed or uncertain checks must reject the asset.
5. Prove outages/no-result/corrupt-download behaviour and ensure no mock/unverified asset ever renders.

## 3. Complete the renderer

1. Download only approved selected clips into an isolated per-job workspace and validate them with FFprobe.
2. Obtain actual narration audio, call `app/services/renderer.py` for every requested ratio, and persist MP4/SRT/timeline/manifest outputs.
3. Add intelligent clip trimming/pacing that exactly covers narration; detect and reject black/frozen frames and duration drift.
4. Test 16:9, 9:16, 1:1, captions on/off, missing media, corrupt media, timeouts, and real FFprobe output checks.
5. Add an end-to-end test using legally usable committed fixtures or a documented test-media download step.

## 4. Complete job reliability and storage

1. Replace the in-process thread with a durable worker/queue (for example Celery/RQ/Arq) and a persistent production database.
2. Store input/output files in S3-compatible MinIO locally and return signed or controlled download URLs.
3. Implement retry policy, timeouts, cancellation policy, callback HMAC signing, concurrent-job isolation, restart recovery, and accurate stage-based progress.
4. Prove duplicate idempotency requests never cause a second render and provider failure uses the documented alternate/fallback path.

## 5. Complete API, frontend, and Integration Standard

1. Add multipart upload endpoint/schema and regenerate/review `openapi.yaml` so it matches the running API exactly.
2. Expand the frontend for audio upload, structured scenes, style/avoid/voice/caption controls, real polling, result preview, and downloads.
3. Replace local development storage with configurable S3 storage in Compose; add PostgreSQL and worker services.
4. Add structured JSON log fields: timestamp, level, job_id, and `X-Correlation-Id`.
5. Verify `docker compose up` and a single no-key test command from a clean machine.

## 6. Evidence, Core level, and submission

1. Build ten varied end-to-end Core inputs (20 seconds to 5 minutes) and preserve inputs, output packs, logs, failures, and an index.
2. Test every assessment hard case, including ambiguous terms, names/brands, sensitive news, vertical subject positioning, provider outage, and concurrent submissions.
3. Measure cold/warm 60-second turnaround, cost/minute with assumptions, coverage, human relevance, success/repeat rate, memory, and GPU time when applicable. Never estimate measured metrics.
4. Complete `README.md`, `REPORT.md`, `SOURCES.md`, `AI_USE.md`, the Excel Submission Form, private repository review access, live demo, and an unedited <=8-minute demo recording.
5. Deploy only after local end-to-end evidence passes. Verify the live URL, readiness, output retention, rate limits, CORS, secrets, and reviewer access, then record proof.

## Current implementation boundary

The renderer helper exists and Docker installs FFmpeg, but there is no verified production narration/footage input in this workspace. Therefore no licence-clean MP4 has been produced or claimed. The next safe implementation action is to add configured real provider adapters and legally usable integration fixtures, then execute the renderer end to end.
