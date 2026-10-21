# Sources, Licences, and Provider Approval Record

Last verified: 2026-10-21

## 1. Runtime Dependencies & Packages

| Component | Category | Licence | Notes / Rights Status |
|---|---|---|---|
| **FastAPI** | Backend Framework | MIT | Commercial use permitted. Verified v0.115.0. |
| **Uvicorn** | ASGI Web Server | BSD 3-Clause | Commercial use permitted. Verified v0.30.6. |
| **Pydantic** | Schema Validation | MIT | Commercial use permitted. Verified v2.9.2. |
| **HTTPX** | Async HTTP Client | BSD 3-Clause | Commercial use permitted. Verified v0.27.2. |
| **edge-tts** | Neural TTS Adapter | MIT | Commercial use permitted. Python client wrapping Edge service. |
| **mutagen** | Audio Header Probing | LGPL-2.1+ / GPL-2.0 | Audio duration and metadata extraction. |
| **FFmpeg** | Media Processing | LGPL-2.1+ / GPL | Pre-installed in container. Used via CLI subprocess. |
| **React / React-DOM** | Frontend UI | MIT | Commercial use permitted. Verified v19+. |
| **Vite** | Frontend Bundler | MIT | Commercial use permitted. Verified v8.3. |

---

## 2. Production Footage Provider Approval Record

### Primary Source: Pexels Video API
- **Provider Name**: Pexels GmbH
- **Terms & Licence URL**: https://www.pexels.com/license/
- **Date Checked**: 2026-10-21
- **Commercial Use Decision**: **APPROVED**. Pexels license grants irrevocable, worldwide, non-exclusive rights to use video content for commercial and non-commercial purposes without attribution.
- **Attribution Policy**: Attribution is not strictly required but is automatically captured and preserved in `timeline.json`.
- **Restrictions & Safety Filters**: Identifiable people cannot be portrayed in an offensive or sensitive light; trademarks and logos must not imply endorsement. Enforced via the engine's `apply_safety_filter` and user `avoid` list.
- **Integration**: `app/providers/footage.py` (`PexelsVideoProvider`).

### Secondary / Failover Source: Pixabay Video API
- **Provider Name**: Pixabay / Canva
- **Terms & Licence URL**: https://pixabay.com/service/license-summary/
- **Date Checked**: 2026-10-21
- **Commercial Use Decision**: **APPROVED**. Pixabay Content License permits free commercial and non-commercial use across digital formats without attribution.
- **Attribution Policy**: Not required. Captured in `timeline.json`.
- **Restrictions & Safety Filters**: No selling of unaltered copies, no depiction of identifiable individuals in bad light, trademark restrictions enforced via keyword safety gating.
- **Integration**: `app/providers/footage.py` (`PixabayVideoProvider`), configured via `MultiSourceFootageProvider` for automated failover.

---

## 3. Production Narration / TTS Approval Record

### Microsoft Edge Neural TTS (edge-tts)
- **Service Name**: Microsoft Edge Neural Speech Engine
- **Client Library**: `edge-tts` (v7.0+, MIT License)
- **Date Checked**: 2026-10-21
- **Commercial Use Decision**: **APPROVED for assessment & commercial prototype evaluation**. Free, high-fidelity neural voices with zero API key requirement.
- **Supported Voices**:
  - `en-IN-NeerjaNeural` (English India, Female)
  - `en-IN-PrabhatNeural` (English India, Male)
  - `en-US-JennyNeural` (English US, Female)
  - `en-US-GuyNeural` (English US, Male)
  - `hi-IN-SwaraNeural` (Hindi India, Female)
  - `hi-IN-MadhurNeural` (Hindi India, Male)
  - `ta-IN-PallaviNeural` (Tamil India, Female)
  - `ta-IN-ValluvarNeural` (Tamil India, Male)
- **Integration**: `app/providers/audio.py` (`EdgeTTSProvider`).

---

## 4. Test Fixtures & Offline Mock Media

- **Mock Narration**: `MockNarrationProvider` generates synthetic timing estimates using natural word rates (approx. 2.6 words/sec) without requiring external network connectivity.
- **Mock Footage**: `MockFootageProvider` returns deterministic test URIs (`mock://generated-test-pattern/...`) with `commercial_use: false` and `rights_verified: false`. These are strictly prohibited from rendering in production workflows by the eligibility gate (`eligible()`).
- **Core Input Fixtures**: 10 varied input fixtures stored in `fixtures/01_*.json` through `fixtures/10_*.json` for reproducible testing and evaluation.
