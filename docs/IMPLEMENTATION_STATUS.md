# Implementation status

| Area | Status | Evidence / limitation |
|---|---|---|
| API job creation and validation | PARTIAL | FastAPI routes and tests exist; upload mode not yet implemented |
| Idempotency and job status | VERIFIED (local) | SQLite uniqueness plus `tests/test_api.py` |
| Script scene planning | PARTIAL | Deterministic sentence planner with ambiguity warnings; no model-backed planning |
| Audio / TTS / transcription | PARTIAL | Deterministic timing/TTS adapter and URL duration validation added; production TTS/transcription and upload path remain unverified |
| Licensed footage | PARTIAL | Pexels adapter added; no key/selected asset/run verified, mock remains intentionally ineligible |
| Semantic matching | PARTIAL | Explainable lexical baseline, rights gate, relevance threshold, and no-repeat rule tested; approved embedding/VLM evaluation remains unverified |
| FFmpeg output / captions | PARTIAL | FFmpeg/FFprobe renderer helper, ratio/caption handling, and output-stream validation implemented; no verified input media or end-to-end render run in this workspace |
| Timeline / manifest | PARTIAL | Audit-artifact writer produces provenance-rich timeline, manifest with unavailable-cost state, and SRT from actual input objects; renderer integration remains incomplete |
| Background reliability | PARTIAL | Persistent SQLite state and worker thread; production queue/recovery not complete |
| Integration Standard | PARTIAL | Compose, env template, OpenAPI starter, errors, health, batch runner present; requires full audit |
| Frontend | PARTIAL | Functional API submission/status UI; no uploads/scenes/downloads yet |
| Testing / evaluation | PARTIAL | Unit/API tests only; no video evaluation pack |
| Deployment / live demo | NOT VERIFIED | Not deployed |
| Advanced / outstanding | NOT STARTED | Must follow verified Core |
| Final submission | NOT STARTED | Do not submit until evidence is complete |

