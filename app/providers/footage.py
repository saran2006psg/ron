from __future__ import annotations

from dataclasses import dataclass
import httpx


@dataclass(frozen=True)
class FootageCandidate:
    asset_url: str
    provider: str
    license_name: str
    license_url: str
    creator: str | None
    attribution: str | None
    commercial_use: bool
    watermark_free: bool
    ai_generated: bool
    rights_verified: bool
    rationale: str


class MockFootageProvider:
    """Deterministic test-only source. It never represents production footage."""
    def search(self, query: str, avoid: list[str]) -> list[FootageCandidate]:
        if "no footage" in query.lower():
            return []
        return [FootageCandidate(
            asset_url="mock://generated-test-pattern/" + str(abs(hash(query)) % 100000),
            provider="mock-generated-test-pattern", license_name="TEST_FIXTURE_ONLY",
            license_url="https://example.invalid/test-fixture", creator="IncuBrix test fixture",
            attribution="Not for production", commercial_use=False, watermark_free=True,
            ai_generated=True, rights_verified=False, rationale="Deterministic offline test fixture")]


def eligible(candidate: FootageCandidate) -> bool:
    return candidate.commercial_use and candidate.watermark_free and candidate.rights_verified


class PexelsVideoProvider:
    """Production adapter. The caller must still apply topic/rights safety checks."""
    license_url = "https://www.pexels.com/license/"

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ValueError("PEXELS_API_KEY is required")
        self.api_key = api_key

    def search(self, query: str, avoid: list[str]) -> list[FootageCandidate]:
        response = httpx.get("https://api.pexels.com/v1/videos/search", params={"query": query, "per_page": 15},
                             headers={"Authorization": self.api_key}, timeout=20)
        response.raise_for_status()
        candidates = []
        for video in response.json().get("videos", []):
            link = next((f.get("link") for f in video.get("video_files", []) if f.get("file_type") == "video/mp4"), None)
            if not link:
                continue
            candidates.append(FootageCandidate(asset_url=link, provider="pexels", license_name="Pexels License",
                license_url=self.license_url, creator=video.get("user", {}).get("name"), attribution=None,
                commercial_use=True, watermark_free=True, ai_generated=False, rights_verified=True,
                rationale=f"Pexels API result for {query}; provider licence record required in timeline"))
        return candidates

