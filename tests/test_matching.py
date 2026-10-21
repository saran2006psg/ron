from app.providers.footage import FootageCandidate
from app.services.matching import select_clip


def item(url: str, rationale: str, commercial: bool = True):
    return FootageCandidate(url, "test", "Test", "https://example.test/license", None, None, commercial, True, False, commercial, rationale)


def test_matching_requires_eligible_relevant_unrepeated_asset():
    scene = {"text": "A cloud computing server", "query": "cloud computing server"}
    match = select_clip(scene, [item("a", "cloud computing server room"), item("b", "bank cash")], set())
    assert match.candidate and match.candidate.asset_url == "a"
    repeated = select_clip(scene, [item("a", "cloud computing server room")], {"a"})
    assert repeated.candidate is None


def test_matching_never_accepts_failed_rights():
    result = select_clip({"text": "cloud", "query": "cloud"}, [item("a", "cloud", commercial=False)], set())
    assert result.reason == "NO_ELIGIBLE_UNREPEATED_CANDIDATE"
