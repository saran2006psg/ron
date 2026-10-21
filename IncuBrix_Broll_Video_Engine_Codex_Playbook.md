# IncuBrix PS3: Script and Voiceover to B-roll Video Engine

## Purpose and guardrails

This is a standalone implementation handoff for the IncuBrix Engineering Assessment 3. It translates the assessment brief into a practical, phase-by-phase build plan and copy-ready Codex prompts.

Use it with the assessment brief open. The brief remains authoritative if it conflicts with this document. Do not publish the brief or its contents; it is confidential. Do not make a claim in the Submission Form, README, report, demo, or this project’s documentation unless it is backed by reproducible evidence.

### Assessment success gates

The default path must deliver a containerised service and live demo that accepts both narration audio (MP3, WAV, M4A, up to 10 minutes) and text, produces requested 16:9, 9:16, and/or 1:1 B-roll videos, captions, `timeline.json`, and `manifest.json`.

All mandatory requirements must pass:

1. Audio and text input both work.
2. Meaningful, narration-timed scenes cover all narration time.
3. Each selected clip is commercially usable and records source, licence, attribution, and link; watermarks are excluded and AI media is flagged.
4. Output is normalised, H.264/AAC, 30 fps, 1080p-class, with no black/frozen frames or audio drift.
5. Clips are not repeated within a video and match meaning rather than keywords.
6. The output is safe: no unauthorised real-person faces/voices/content, invented logos, or insensitive treatment of sensitive content.
7. Jobs are backgrounded with progress and survive a footage-provider failure via an alternate source or explicit fallback.
8. The Integration Standard and working live demo are provided for the review period.

Core additionally requires ten varied usable test inputs and reviewer relevance averaging at least 3.5/5. Advanced and Outstanding work are optional until Core is verified. The submission must honestly report cold/warm turnaround, cost per minute, coverage, relevance, reliability, repeat rate (must be zero), and measurable resources.

### Architecture target

- **API:** Python/FastAPI, versioned under `/api/v1`, Pydantic schemas, OpenAPI 3.1.
- **Workers:** persistent database-backed job records plus a queue/worker suitable for FFmpeg work; job states are `queued`, `running`, `succeeded`, and `failed`.
- **Providers:** adapters for TTS, transcription/timestamps, footage, storage, semantic ranking, and optional evaluation. All external services must be configuration-selected and have deterministic local mocks.
- **Media:** FFmpeg worker pipeline; S3-compatible storage (MinIO locally); immutable per-job working directories.
- **Client:** a simple functional React/TypeScript UI is enough; the engine and evidence matter more than visual polish.
- **Evidence:** `README.md`, `REPORT.md`, `SOURCES.md`, `AI_USE.md`, `openapi.yaml`, test pack, logs, video pack, and implementation status must reflect only completed work.

### Rights and licensing policy

Treat every provider result as untrusted until verified. A candidate is eligible only when its asset-level commercial-use status is documented and its provenance includes provider, original asset URL, licence name/identifier, licence/terms URL, creator and required attribution when available, watermark status, AI-generated status, retrieval time, and rights-verification result. Reject unknown, non-commercial, restricted, watermarked, or otherwise unverifiable assets. Never infer commercial rights from public accessibility or fabricate a licence record. Keep production media distinct from test fixtures. Use commercial-compatible code/models/dependencies; credit them and avoid AGPL in the shipped service.

## Master prompt for Codex

Copy this as the first prompt in the repository task.

```text
You are the lead engineer for the IncuBrix PS3 Script and Voiceover to B-roll Video Engine assessment. First inspect the existing repository completely (including current docs, tests, configuration, and git state) and read the supplied IncuBrix assessment brief in full. The assessment brief is authoritative. Preserve unrelated existing work; do not reset, overwrite, delete, or rename files merely to simplify the task.

Create and maintain docs/IMPLEMENTATION_STATUS.md containing a requirement-to-evidence checklist. Classify requirements as Must-have, Core, Advanced, Outstanding, Integration Standard, hard case, and submission deliverable. For every item use only: NOT STARTED, PARTIAL, VERIFIED, BLOCKED, or NOT VERIFIED. Never say a requirement is implemented unless code and relevant verification exist.

Work one phase at a time. Before changing files, state: the phase, requirements addressed, design choices, files you expect to touch, and verification plan. Implement only the requested phase. Run relevant formatting, linting, type checks, unit/integration/end-to-end tests, and media/API checks. Fix failures caused by your changes. Then update the status document with real commands, results, evidence paths, limitations, external prerequisites, and exact manual verification steps. Stop and wait for my explicit approval before the next phase.

Prioritise the assessment must-haves and Core level. Build a maintainable, provider-swappable design: API, worker/job state, media pipeline, provider adapters, evaluation, frontend, and storage must be separated. Use environment configuration, never hard-code secrets or local paths, use structured JSON logs with job_id and X-Correlation-Id, and use deterministic mocks so tests run without API keys.

The required HTTP contract includes POST /api/v1/broll/jobs (202 for long-running work), GET /api/v1/jobs/{job_id}, /health, and /ready; routes belong under /api/v1 except health/readiness as specified by the brief. Respect the brief’s exact request fields and output contracts. Every POST needs Idempotency-Key behaviour: the same key returns the same job and never duplicates work. Errors must be JSON in this form: {"error":{"code":"UPPER_SNAKE_CASE","message":"...","retryable":false,"details":{}}}. Use openapi.yaml (OpenAPI 3.1) that matches the running service exactly. Support uploads and URLs where the brief requires them. Include optional signed callbacks only when implemented, using HMAC-SHA256 and X-IncuBrix-Signature.

Commercial provenance is mandatory. Do not use an asset, model, dependency, voice, face, music, dataset, or code whose commercial-use terms cannot be confirmed for the default path. For every selected media asset record provider, source URL, licence identifier/name, documentation/terms URL, creator/attribution requirements, commercial-use decision, watermark result, AI-generated flag, retrieval time, and verification evidence. Reject unknown rights. Do not fabricate licence facts, costs, model versions, provenance, relevance scores, timing, logs, test results, or deployment status.

Media requirements are non-negotiable: narration timing determines scene timing; full narration coverage; no repeated clip in a video; semantic rather than keyword matching; requested 16:9, 9:16, 1:1 rendering; H.264/AAC, 30 fps, 1080p-class; normalised video/pixel format; no unintended black/frozen frames or drift; captions/SRT as requested; timeline.json and manifest.json created from actual processing data. Handle hard cases explicitly with warnings/errors instead of silent failure.

Keep SOURCES.md and AI_USE.md accurate. Keep failed attempts and failure outputs in the test pack. Only pursue Advanced/Outstanding after the mandatory requirements and Core evidence are verified. If credentials or hosted services are unavailable, implement a real adapter plus deterministic mock path, document the limitation, and mark hosted behaviour NOT VERIFIED. Do not claim deployment, reviewer access, a completed Excel form, or a demo recording unless actually confirmed.

Start by producing the requirements checklist and then execute only the phase I name. After each phase, stop.
```

## Phase sequence and copy-ready prompts

Use exactly one prompt at a time after the master prompt. Replace `Phase N` only when the preceding phase is verified or intentionally documented as partial.

### Phase 1 - Setup and foundation

```text
Implement Phase 1 only. Inspect the assessment brief and existing repository, then establish the project foundation without implementing retrieval, semantic ranking, TTS, or rendering. Create or align a maintainable backend, worker, frontend, test, docs, infrastructure, and media-workspace structure; environment templates; .gitignore; dependency manifests; Docker Compose; local development instructions; basic FastAPI /health and /ready; and a minimal frontend that starts. Add initial tests and docs/IMPLEMENTATION_STATUS.md. Make docker compose up start what exists locally. Verify startup and tests, record actual evidence, then stop.
```

### Phase 2 - API contracts and validation

```text
Implement Phase 2 only. Add the assessment-accurate POST /api/v1/broll/jobs and GET /api/v1/jobs/{job_id} schemas/routes, input modes (audio URL/upload where supported, script, and IncuBrix scene list), aspect ratios, style, avoid list, captions, voice, standard errors, correlation IDs, initial persistent job record, and safe Idempotency-Key handling. Return 202 for job creation. Validate mutually exclusive/empty inputs, empty script, audio formats/duration limits, malformed URLs/uploads, ratios, caption options, and duplicate keys. Update openapi.yaml if present. Test valid and invalid cases and idempotency; do not add planning, TTS, retrieval, or rendering. Update evidence/status and stop.
```

### Phase 3 - Scene planning

```text
Implement Phase 3 only. Build a deterministic, replaceable scene-planning interface that turns scripts into meaningful narration scenes and preserves user-provided scenes and visual hints. Scene changes must prefer sentence/phrase boundaries, never distort meaning, and expose stable IDs, narration text, durations when available, visual search queries, entities, ambiguity/safety warnings, and planned evidence. Handle abstract lines, statistics, named people/brands, and ambiguous terms (value, bank, cloud, mouse, Python) safely without inventing facts. Add fixtures and unit tests. Do not add TTS, footage retrieval, or rendering. Update status/evidence and stop.
```

### Phase 4 - Narration and audio

```text
Implement Phase 4 only. Add replaceable TTS and transcription/timestamp adapters with deterministic mocks. Accept assessment-supported MP3/WAV/M4A audio up to 10 minutes; validate readability, stream presence, type, size, duration, silent audio, music-only audio, corrupt data, and provider failures. For scripts, generate narration through the adapter. Align scene timing to measured duration or actual timestamps, not equal slices. Persist actual provider/model/version/settings/timing/warnings for later manifest generation. Add tests. Do not retrieve footage or render final video. Update status/evidence and stop.
```

### Phase 5 - Licensed footage retrieval

```text
Implement Phase 5 only. Create provider-independent footage search/retrieval and a deterministic offline mock. Integrate a real provider only after documenting current commercial terms and asset-level licence evidence. Require each candidate to carry source URL, provider, licence ID/name, terms URL, creator/attribution, commercial eligibility, watermark status, AI-generated flag, retrieval time, and verified rights decision. Reject assets with missing/uncertain rights; never invent provenance. Handle no results, rate limits, outages, corrupt downloads, duplicates, and retries. Add rights, failure, fallback, and mock tests. Do not render final video. Update SOURCES.md/status and stop.
```

### Phase 6 - Semantic matching

```text
Implement Phase 6 only. Build a replaceable semantic ranking and clip-selection component, separate from retrieval and rights checks. Choose only commercially compatible models/dependencies and document them. Produce explainable relevance results, configurable threshold, no-match state, ambiguity/safety handling, and a strict no-repeat rule per output. Rights failure always disqualifies a candidate regardless of relevance. Test abstract language, statistics, named people/brands, sensitive news, ambiguous words, poor matches, and human-labelled fixture cases. Run a real small evaluation before reporting any metric; otherwise state it is not measured. Update status and stop.
```

### Phase 7 - Rendering

```text
Implement Phase 7 only. Use FFmpeg to build output from actual narration, scene timing, and selected clips. Produce requested 16:9, 9:16, and 1:1 H.264/AAC, 30-fps, 1080p-class outputs; normalise resolution, frame rate, and pixel format; preserve narration sync; cover all narration; avoid unnecessary repeats, stretching, black/frozen frames, and drift. Generate/burn captions and SRT when requested. Use sensible crop/subject handling when evidence exists. Validate command results plus output duration, codecs, streams, fps, dimensions, and playable media. Test failed/corrupt/missing media and timeout cases with legal fixtures. Update status/evidence and stop.
```

### Phase 8 - Timeline and manifest

```text
Implement Phase 8 only. Generate timeline.json, manifest.json, and captions.srt from actual pipeline data. The timeline must contain each scene’s text/times, selected clip, source, licence, attribution, AI flag, decision reason, and relevance score/evidence. The manifest must contain actual providers/models/versions/settings/seeds where relevant, timings, costs or documented estimates, warnings, and rights records. Validate timestamp consistency, full coverage, no unexplained gaps, and provenance completeness. Mark unavailable values explicitly; fabricate nothing. Add schemas and consistency tests. Update status and stop.
```

### Phase 9 - Background jobs and reliability

```text
Implement Phase 9 only. Add a persistent worker/queue architecture for operations over two seconds. Implement real queued/running/succeeded/failed transitions, progress 0-100 based on actual stages, timestamps, errors, retries, timeouts, recovery after worker restart, safe concurrency, isolated workspaces, and S3-compatible result storage/download links. Ensure idempotency prevents duplicate rendering. If a footage provider fails, use a verified alternative or explicit safe fallback and record it. Test transitions, outages, retry/recovery, duplicates, concurrency, and rendering failure. Update status and stop.
```

### Phase 10 - Integration Standard

```text
Implement Phase 10 only. Audit all ten Integration Standard points against the brief. Complete gaps in one-command Compose start and no-key test command, OpenAPI 3.1, API versioning, background job contract, Idempotency-Key, standard errors, environment configuration, upload/URL inputs, S3-compatible outputs, structured JSON logs with job_id and X-Correlation-Id, health/readiness, manifest, and batch runner. Implement signed callback only if supported, safely using X-IncuBrix-Signature. Prove every checked point with commands/tests; mark unproven items NOT VERIFIED. Update status and stop.
```

### Phase 11 - Frontend

```text
Implement Phase 11 only. Build a functional, responsive React/TypeScript client connected to the real API: script/audio/scene input, voice/ratio/style/avoid/caption options, client validation, submission, non-fake backend progress, errors, result preview, and downloads for video/SRT/timeline/manifest. Prevent accidental duplicate submissions and handle network failures, empty/loading/success/failure states. The UI may be simple but must be usable. Test key flows and errors. Update status and stop.
```

### Phase 12 - Evaluation and testing

```text
Implement Phase 12 only. Build a reproducible test pack and evaluation runner. Cover ten varied Core inputs and the assessment hard cases: abstract/statistical lines, names/brands, ambiguous words, sensitive news, vertical crops, five-minute audio, silent/music-only/wrong/corrupt input, provider outage/no results, corrupt download, and concurrent users. Include deterministic mock end-to-end tests; check output media, sync, captions, timeline/provenance, error contract, and no-match behaviour. Capture raw results/config/logs and report real turnaround, cost assumptions, coverage, human relevance, success/repeat rate, and measurable resource use. Do not fabricate ratings/results. Update status and stop.
```

### Phase 13 - Deployment

```text
Implement Phase 13 only. Prepare deployment for frontend, API, database, worker, and object storage. Select services after checking their limits/costs and document persistence, timeouts, CORS, secrets, output retention, rate limiting, cold start, recovery, and expected costs. Deploy only with my approval/credentials. Verify health/readiness and one real smoke test before marking anything live. Prepare private repository/reviewer-access instructions, but do not claim access, deployment, or public availability without confirmation. Update status and stop.
```

### Phase 14 - Advanced and Outstanding

```text
Implement Phase 14 only after every must-have and Core item is VERIFIED. Identify the highest-value unfinished Advanced/Outstanding criterion, explain its assessment value and measurable acceptance test, then implement only that feature. Candidates: two footage sources with measurable choice rule and timeline rationale; partial scene rerender demonstrably faster than full render; cross-source colour/pacing normalisation; independent vision-language scoring compared against human ratings; Hindi/Tamil narration; production capacity/time/cost measures. Preserve contracts and Core behavior. Report only measured evidence. Update status and stop.
```

### Phase 15 - Final submission

```text
Implement Phase 15 only. Audit the repository against every must-have, Core/Advanced/Outstanding item, Integration Standard point, hard case, and submission deliverable. Prepare/verify README.md, openapi.yaml, REPORT.md, SOURCES.md, AI_USE.md, Docker Compose, .env.example, test/video packs, batch-run instructions, Excel-form completion checklist, reviewer-access checklist, live-demo checklist, and an unedited <=8-minute demo-recording plan. Run the complete suite. Produce a requirement matrix marked PASS, FAIL, PARTIAL, or NOT VERIFIED with evidence links and honest limitations. Keep failure evidence. Do not fabricate the Excel form, demo video, deployment, or permissions. Stop after the final report.
```

## Suggested evidence map

| Claim | Evidence to retain |
|---|---|
| Mandatory media correctness | Input, output MP4 probe/validation, timeline, manifest, captions, test log |
| Licence-clean clips | Per-asset provenance in timeline, provider/terms records, attribution decision in SOURCES.md |
| Job resilience | Provider-outage test, worker/job logs, status responses, alternate/fallback record |
| Core relevance | Ten-input pack, reviewer rubric/raw ratings, calculation and outputs |
| Integration Standard | Compose/test commands, OpenAPI contract test, batch output, health/readiness, log samples |
| Deployment/live demo | Verified URL, cold-start note, smoke-test record, rate-limit and access instructions |

## Completion discipline

Before moving forward, confirm: the phase’s tests passed; prior tests still pass; evidence links resolve; no secret appears in source/logs/screenshots; real providers and mocks are clearly differentiated; rights are verified asset by asset; and every limitation is written down. A smaller, verified Core submission is materially stronger than an unverified feature list.
