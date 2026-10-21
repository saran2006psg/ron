from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import httpx

log = logging.getLogger(__name__)


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
    retrieval_time: str | None = None


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


# ---------------------------------------------------------------------------
# Pexels provider (primary)
# ---------------------------------------------------------------------------

class PexelsVideoProvider:
    """Production adapter. The caller must still apply topic/rights safety checks."""
    license_url = "https://www.pexels.com/license/"

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ValueError("PEXELS_API_KEY is required")
        self.api_key = api_key

    def search(self, query: str, avoid: list[str]) -> list[FootageCandidate]:
        retrieval_time = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        try:
            response = httpx.get("https://api.pexels.com/v1/videos/search", params={"query": query, "per_page": 15},
                                 headers={"Authorization": self.api_key}, timeout=20)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            log.warning("Pexels API error: %s", exc)
            raise ProviderUnavailableError(f"PROVIDER_UNAVAILABLE: Pexels - {exc}") from exc
        candidates = []
        avoid_lower = {a.lower() for a in avoid}
        for video in response.json().get("videos", []):
            # Skip videos that contain avoided terms in the URL or tags
            video_text = (video.get("url", "") + " " + str(video.get("tags", ""))).lower()
            if any(term in video_text for term in avoid_lower):
                continue
            link = next((f.get("link") for f in video.get("video_files", [])
                         if f.get("file_type") == "video/mp4" and f.get("height", 0) >= 720), None)
            if not link:
                # Try any MP4 file
                link = next((f.get("link") for f in video.get("video_files", [])
                             if f.get("file_type") == "video/mp4"), None)
            if not link:
                continue
            candidates.append(FootageCandidate(
                asset_url=link, provider="pexels", license_name="Pexels License",
                license_url=self.license_url, creator=video.get("user", {}).get("name"),
                attribution=None, commercial_use=True, watermark_free=True,
                ai_generated=False, rights_verified=True,
                rationale=f"Pexels API result for '{query}'",
                retrieval_time=retrieval_time))
        return candidates


# ---------------------------------------------------------------------------
# Pixabay provider (secondary / failover)
# ---------------------------------------------------------------------------

class PixabayVideoProvider:
    """Secondary footage source for failover and multi-source Advanced criterion."""
    license_url = "https://pixabay.com/service/license-summary/"

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ValueError("PIXABAY_API_KEY is required")
        self.api_key = api_key

    def search(self, query: str, avoid: list[str]) -> list[FootageCandidate]:
        retrieval_time = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        try:
            response = httpx.get("https://pixabay.com/api/videos/",
                                 params={"key": self.api_key, "q": query, "per_page": 15, "safesearch": "true"},
                                 timeout=20)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            log.warning("Pixabay API error: %s", exc)
            raise ProviderUnavailableError(f"PROVIDER_UNAVAILABLE: Pixabay - {exc}") from exc
        candidates = []
        avoid_lower = {a.lower() for a in avoid}
        for hit in response.json().get("hits", []):
            tags = hit.get("tags", "").lower()
            if any(term in tags for term in avoid_lower):
                continue
            videos = hit.get("videos", {})
            # Prefer "large" size, fallback to "medium" or "small"
            video_data = videos.get("large") or videos.get("medium") or videos.get("small")
            if not video_data or not video_data.get("url"):
                continue
            candidates.append(FootageCandidate(
                asset_url=video_data["url"], provider="pixabay",
                license_name="Pixabay Content License",
                license_url=self.license_url,
                creator=hit.get("user"),
                attribution=None, commercial_use=True, watermark_free=True,
                ai_generated=False, rights_verified=True,
                rationale=f"Pixabay API result for '{query}'",
                retrieval_time=retrieval_time))
        return candidates


# ---------------------------------------------------------------------------
# Multi-source provider with automatic failover
# ---------------------------------------------------------------------------

class ProviderUnavailableError(RuntimeError):
    pass


class MultiSourceFootageProvider:
    """Queries primary first, falls back to secondary on failure or empty results."""

    def __init__(self, primary, secondary=None) -> None:
        self.primary = primary
        self.secondary = secondary

    def search(self, query: str, avoid: list[str]) -> list[FootageCandidate]:
        candidates = []
        source_used = "primary"
        try:
            candidates = self.primary.search(query, avoid)
        except (ProviderUnavailableError, Exception) as exc:
            log.warning("Primary footage provider failed: %s, trying secondary", exc)
            source_used = "secondary"

        if not candidates and self.secondary:
            try:
                candidates = self.secondary.search(query, avoid)
                source_used = "secondary"
            except (ProviderUnavailableError, Exception) as exc:
                log.warning("Secondary footage provider also failed: %s", exc)
                raise ProviderUnavailableError(
                    f"PROVIDER_UNAVAILABLE: Both footage providers failed for '{query}'") from exc

        return candidates


# ---------------------------------------------------------------------------
# Content safety filter
# ---------------------------------------------------------------------------

SAFETY_TERMS = {
    "nudity", "nude", "naked", "explicit", "gore", "blood", "violence",
    "drug", "drugs", "weapon", "weapons", "gun", "guns",
}


def apply_safety_filter(candidates: list[FootageCandidate], avoid: list[str]) -> list[FootageCandidate]:
    """Remove candidates that match safety blocklist or user avoid list."""
    avoid_lower = {a.lower() for a in avoid}
    blocked = SAFETY_TERMS | avoid_lower
    safe = []
    for c in candidates:
        text = (c.rationale + " " + c.asset_url + " " + (c.creator or "")).lower()
        if any(term in text for term in blocked):
            continue
        safe.append(c)
    return safe


# ---------------------------------------------------------------------------
# Download helper
# ---------------------------------------------------------------------------

def download_clip(url: str, dest: Path, timeout: int = 60) -> Path:
    """Download a video clip to a local path with validation."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        with httpx.stream("GET", url, timeout=timeout, follow_redirects=True) as r:
            r.raise_for_status()
            content_type = r.headers.get("content-type", "")
            if "video" not in content_type and "octet-stream" not in content_type:
                raise RuntimeError(f"INVALID_CONTENT_TYPE: {content_type}")
            with open(dest, "wb") as f:
                for chunk in r.iter_bytes(chunk_size=65536):
                    f.write(chunk)
    except httpx.HTTPError as exc:
        raise RuntimeError(f"DOWNLOAD_FAILED: {exc}") from exc
    if not dest.is_file() or dest.stat().st_size < 1000:
        dest.unlink(missing_ok=True)
        raise RuntimeError("DOWNLOAD_CORRUPT_OR_EMPTY")
    return dest
