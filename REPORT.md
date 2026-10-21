# Engineering Report: IncuBrix B-roll Video Engine

## 1. Executive Summary & Architecture Overview

The IncuBrix Script & Voiceover to B-roll Video Engine was developed to provide an end-to-end, commercial-grade media pipeline that transforms narration scripts, uploaded audio recordings, or structured scenes into 1080p-class video compositions across multiple aspect ratios (`16:9`, `9:16`, `1:1`) with burned-in subtitles and verified provenance audit trails.

The service follows a modular architecture separating:
- **API Ingestion & Validation** (`app/main.py`, `app/models.py`)
- **Durable Job State & Idempotency** (`app/store.py`)
- **Scene Planning & Disambiguation** (`app/services/planner.py`)
- **Audio Synthesis & Inspection** (`app/providers/audio.py`)
- **Commercial Footage Retrieval & Failover** (`app/providers/footage.py`)
- **Semantic Matching & Rights Enforcement** (`app/services/matching.py`)
- **Media Composition & FFmpeg Rendering** (`app/services/renderer.py`)
- **Audit Artifacts Generation** (`app/services/artifacts.py`)
- **Web UI & Batch Processing** (`frontend/`, `cli/batch_runner.py`)

---

## 2. Key Engineering Decisions & Provenance Verification

### 2.1 Commercial Rights & Safe Mock Isolation
In compliance with the IncuBrix assessment guidelines:
- **Zero Inferred Rights**: No public media URL is presumed to have commercial rights without explicit verification.
- **Eligibility Gate (`eligible()`)**: Every candidate asset must satisfy three boolean flags:
  1. `commercial_use == True`
  2. `watermark_free == True`
  3. `rights_verified == True`
- **Offline Mock Isolation**: The `MockFootageProvider` generates deterministic mock URIs (`mock://...`) where `commercial_use = False` and `rights_verified = False`. The renderer strictly rejects unverified/mock media, ensuring mock assets can never accidentally render into a production deliverable.

### 2.2 Dual Footage Providers & Automated Failover
To satisfy both high availability and the Advanced assessment criterion:
- **Pexels Video API**: Primary source (`FOOTAGE_PROVIDER=pexels`). Free commercial use, high-resolution MP4s (height >= 720p preferred).
- **Pixabay Video API**: Secondary source (`FOOTAGE_PROVIDER=pixabay`). Free commercial use, multiple bitrate selections.
- **MultiSourceFootageProvider**: Configurable dual-source adapter that queries the primary source, catches API errors or rate limits, and automatically fails over to the secondary source without pipeline interruption.

### 2.3 Intelligent Disambiguation & Content Safety
- **Polysemic Disambiguation**: Polysemic keywords with dual meanings are contextually analyzed before query generation:
  - `"cloud"`: Disambiguated between meteorology (sky/weather) vs cloud computing (servers, data center, enterprise).
  - `"bank"`: Disambiguated between river banks vs financial institutions (stocks, finance, banking).
  - `"python"`: Disambiguated between reptiles vs software programming.
  - `"mouse"`: Disambiguated between rodents vs computer hardware peripherals.
  - `"value"`: Disambiguated between abstract values vs investment/monetary portfolios.
- **Safety Filtering**: Built-in blocklist (`nudity`, `violence`, `weapons`, `drugs`, etc.) combined with user-supplied `avoid` keywords filters out candidates before selection.
- **Non-Repetition Constraint**: Selected asset URLs are tracked in a set (`used_asset_urls`), guaranteeing zero repeated clips within an output video.

### 2.4 Multi-Aspect 1080p-Class Composition
The rendering engine (`app/services/renderer.py`) formats clips into:
- `16:9`: 1920x1080 (Landscape)
- `9:16`: 1080x1920 (Vertical / Reels / TikTok)
- `1:1`: 1080x1080 (Square / Instagram)

The FFmpeg filter chain uses `scale=W:H:force_original_aspect_ratio=increase,crop=W:H,fps=30,format=yuv420p` with AAC audio and `-shortest` synchronization. FFprobe validates codec streams (h264, aac) and dimensions upon completion.

---

## 3. Verification & Evidence Summary

### 3.1 Automated Test Suite
The automated test suite in `tests/` contains **41 unit and integration tests**, all passing without requiring network access or third-party API keys:
- `tests/test_api.py` (10 tests): Health/ready endpoints, idempotency duplicate handling, validation rules, 404s, correlation IDs, multipart file upload limits, and format enforcement.
- `tests/test_planner.py` (7 tests): Sentence boundaries, context disambiguation, visual hint pass-through, sensitive topics.
- `tests/test_audio.py` (5 tests): Mock duration timings, EdgeTTS adapter, length constraints, corrupt/empty script rejections.
- `tests/test_footage.py` (8 tests): Triple-flag eligibility, mock provider isolation, multi-source primary/secondary failover, safety blocklist, user avoid list.
- `tests/test_matching.py` (4 tests): Semantic ranking, rights gate rejection, safety filtering, non-repetition constraint.
- `tests/test_pipeline.py` (5 tests): Full pipeline mock execution, job state store transitions, nonexistent job lookups.
- `tests/test_renderer.py` (1 test): 1080p-class dimensions and aspect ratio validation.
- `tests/test_artifacts.py` (1 test): Consistent `timeline.json` and `manifest.json` schemas.

### 3.2 Core Input Fixtures
Ten diverse fixtures representing the assessment core requirements are provided in `fixtures/`:
1. `01_tech_tutorial.json`: Tech tutorial with ambiguous term "cloud".
2. `02_finance_news.json`: Finance report with ambiguous terms "bank" and "value".
3. `03_product_promo.json`: Short punchy copy for 1:1 social promo.
4. `04_story_narrative.json`: Cinematic narrative storytelling.
5. `05_python_tutorial.json`: Programming tutorial with ambiguous "Python".
6. `06_mouse_review.json`: Tech review with ambiguous "mouse".
7. `07_startup_stats.json`: Statistics-heavy script with abstract metrics.
8. `08_wellness_vertical.json`: Lifestyle and meditation content in vertical 9:16.
9. `09_green_energy_scenes.json`: Structured scenes with explicit visual hints.
10. `10_cooking_all_ratios.json`: Long-form culinary video testing simultaneous 16:9, 9:16, and 1:1 generation.

### 3.3 Provenance Artifacts
Every executed job generates:
- `timeline.json`: Complete timeline with scene start/end offsets, narration text, selected clip URL, provider, license name, license URL, creator name, watermark flag, AI flag, match score, and selection rationale.
- `manifest.json`: Execution metadata, active engine version, provider configs, speech model, total duration, cost estimates, and warnings.
- `captions.srt`: SubRip subtitle file with precise timestamp synchronization.
- Output MP4s: Burned-in subtitles (optional) and clean audio track synchronization.
