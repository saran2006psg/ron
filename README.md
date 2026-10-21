# IncuBrix Script and Voiceover to B-roll Video Engine

This repository is a safety-first implementation scaffold for the IncuBrix PS3 assessment. It exposes a versioned FastAPI job API, idempotent SQLite-backed job records, structured error responses, deterministic scene planning, a deliberately non-production mock footage provider, a React client, Docker Compose, and a batch runner.

## Honest implementation status

The API and safety gates are runnable. A licence-clean rendered video is **not** produced until a verified commercial footage provider and a commercial TTS/transcription adapter are configured. The mock provider is intentionally rejected by the pipeline because it is a test fixture, not licensed production media. See `docs/IMPLEMENTATION_STATUS.md` before making assessment claims.

## Run locally

1. Copy `.env.example` to `.env`.
2. Create a virtual environment and install `pip install -r requirements-dev.txt`.
3. Run `uvicorn app.main:app --reload`.
4. Open `http://localhost:8000/docs`.
5. Run `pytest`.
6. For containers, run `docker compose up --build`.

The test command requires no API keys. The UI can be started from `frontend` with `npm install && npm run dev`.

## API

`POST /api/v1/broll/jobs` requires `Idempotency-Key` and returns `202`. `GET /api/v1/jobs/{job_id}` returns `queued`, `running`, `succeeded`, or `failed`, progress, errors, warnings, and result links. Health checks are `/health` and `/ready`. The contract file is `openapi.yaml`.

## Rights policy

No public asset is presumed commercial-use eligible. Each selected production clip must retain source, licence, licence link, creator/attribution, AI/watermark status, and a positive verification decision. Unknown rights are rejected. Current provider terms must be checked before enabling a provider.

## Batch runner

`python cli/batch_runner.py fixtures output --base-url http://localhost:8000`

## Submission material

See `REPORT.md`, `SOURCES.md`, `AI_USE.md`, and the status tracker. Do not mark a requirement complete unless the listed evidence exists.

