# Sources and licences

## Current runtime sources

| Item | Use | Licence/rights status |
|---|---|---|
| FastAPI / Pydantic / Uvicorn | API runtime | Check exact package licence/notice before release |
| FFmpeg (container package) | Media processing | Check build configuration and licence obligations before release |
| Mock generated test pattern | Offline tests only | Not production media; deliberately rejected by production eligibility gate |

## Production-provider approval record

Pexels video search is implemented as an opt-in adapter (`FOOTAGE_PROVIDER=pexels`) and was checked on 2026-10-21 against https://www.pexels.com/license/ and its API documentation. Pexels describes commercial use and does not require attribution, but identifiable people, brands, sensitive contexts, and provider terms remain safety constraints. The adapter retains the provider/licence record; a reviewer must inspect selected asset content and the current terms before submission. No Pexels key or production output is included here.

No TTS, transcription, model, or other media provider is approved in this repository yet. Before enabling one, record the provider/asset, version, current terms URL, commercial-use decision, attribution requirement, restrictions, date checked, and evidence. Asset-level unknown rights are a rejection.

