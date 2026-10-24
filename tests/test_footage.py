"""Tests for footage provider logic, multi-source failover, and content safety."""
import pytest

from app.providers.footage import (
    FootageCandidate, MockFootageProvider, MultiSourceFootageProvider,
    ProviderUnavailableError, apply_safety_filter, eligible,
)


def _candidate(url="https://test.video/1.mp4", commercial=True, watermark_free=True,
               rights_verified=True, ai_generated=False, rationale="test clip"):
    return FootageCandidate(
        asset_url=url, provider="test", license_name="Test License",
        license_url="https://example.test/license", creator="Test Creator",
        attribution=None, commercial_use=commercial, watermark_free=watermark_free,
        ai_generated=ai_generated, rights_verified=rights_verified, rationale=rationale,
    )


def test_eligible_requires_all_three_flags():
    assert eligible(_candidate()) is True
    assert eligible(_candidate(commercial=False)) is False
    assert eligible(_candidate(watermark_free=False)) is False
    assert eligible(_candidate(rights_verified=False)) is False


def test_mock_provider_returns_ineligible_assets():
    results = MockFootageProvider().search("sunset", [])
    assert len(results) == 1
    assert results[0].commercial_use is False
    assert eligible(results[0]) is False


def test_mock_provider_returns_empty_for_no_footage():
    results = MockFootageProvider().search("no footage available", [])
    assert len(results) == 0


class FailingProvider:
    def search(self, query, avoid):
        raise ProviderUnavailableError("PROVIDER_UNAVAILABLE: test failure")


class WorkingProvider:
    def search(self, query, avoid):
        return [_candidate(rationale=f"working provider for {query}")]


def test_multi_source_failover_uses_secondary():
    multi = MultiSourceFootageProvider(FailingProvider(), WorkingProvider())
    results = multi.search("sunset", [])
    assert len(results) == 1
    assert "working provider" in results[0].rationale


def test_multi_source_both_fail_raises():
    multi = MultiSourceFootageProvider(FailingProvider(), FailingProvider())
    with pytest.raises(ProviderUnavailableError):
        multi.search("sunset", [])


def test_multi_source_primary_works():
    multi = MultiSourceFootageProvider(WorkingProvider(), FailingProvider())
    results = multi.search("sunset", [])
    assert len(results) == 1


def test_safety_filter_blocks_explicit_content():
    safe = _candidate(url="a", rationale="beautiful mountain landscape")
    unsafe = _candidate(url="b", rationale="blood and violence scene")
    filtered = apply_safety_filter([safe, unsafe], [])
    assert len(filtered) == 1
    assert filtered[0].asset_url == "a"


def test_safety_filter_respects_user_avoid():
    clips = [_candidate(url="a", rationale="cute puppies"), _candidate(url="b", rationale="cats sleeping")]
    filtered = apply_safety_filter(clips, ["cats"])
    assert len(filtered) == 1
    assert filtered[0].asset_url == "a"


def test_coverr_provider_requires_api_key():
    from app.providers.footage import CoverrVideoProvider
    with pytest.raises(ValueError, match="COVERR_API_KEY is required"):
        CoverrVideoProvider("")

