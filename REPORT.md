# Engineering Report (working draft)

## Chosen approach

The service separates API validation, durable job state, planning, provider adapters, semantic selection, renderer, storage, and UI. This keeps externally licensed providers replaceable and lets deterministic mocks cover offline tests.

## Current facts

The request API, idempotency, standard errors, status model, basic health checks, scene planner, mock fixtures, frontend starter, Compose configuration, and batch client are implemented. Rendering and successful audio jobs remain blocked until a configured adapter produces measured timings and a verified commercial footage provider supplies asset-level rights evidence. This is intentional: rendering mock or unverifiable assets would violate the assessment.

## Next verification work

Enable commercial providers only after their current terms and asset-level provenance are captured in `SOURCES.md`; then add FFmpeg composition, output validation, S3 storage, a queue worker, end-to-end video fixtures, and measured evaluation. Record actual cold/warm turnaround, cost, relevance, coverage, repeat rate, and resources before submission.

