from __future__ import annotations

import re
from dataclasses import dataclass

from ..providers.footage import FootageCandidate, eligible


@dataclass(frozen=True)
class MatchResult:
    candidate: FootageCandidate | None
    score: float
    reason: str


def select_clip(scene: dict, candidates: list[FootageCandidate], used_asset_urls: set[str], threshold: float = 0.12) -> MatchResult:
    """Small explainable baseline; replace with an approved embedding model in production."""
    query_words = _terms(scene.get("query") or scene["text"])
    ranked: list[tuple[float, FootageCandidate]] = []
    for item in candidates:
        if not eligible(item) or item.asset_url in used_asset_urls:
            continue
        asset_words = _terms(item.rationale + " " + item.asset_url)
        score = len(query_words & asset_words) / max(1, len(query_words | asset_words))
        ranked.append((score, item))
    if not ranked:
        return MatchResult(None, 0.0, "NO_ELIGIBLE_UNREPEATED_CANDIDATE")
    score, candidate = max(ranked, key=lambda pair: pair[0])
    if score < threshold:
        return MatchResult(None, round(score, 3), "NO_SEMANTIC_MATCH_ABOVE_THRESHOLD")
    return MatchResult(candidate, round(score, 3), "TOKEN_OVERLAP_BASELINE")


def _terms(value: str) -> set[str]:
    return {term.lower() for term in re.findall(r"[A-Za-z]{3,}", value)}
