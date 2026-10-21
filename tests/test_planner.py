from app.services.planner import plan_scenes


def test_planner_keeps_sentence_boundaries_and_ambiguity_warning():
    scenes = plan_scenes("Cloud computing is useful. A bank can be digital.")
    assert len(scenes) == 2
    assert scenes[0]["start"] == 0
    assert "AMBIGUOUS_TERM_REQUIRES_CONTEXT" in scenes[0]["warnings"]
    assert scenes[-1]["end"] > scenes[0]["end"]


def test_planner_disambiguates_cloud_computing():
    """'Cloud' with 'computing' context should generate tech-related query."""
    scenes = plan_scenes("Cloud computing is transforming businesses.")
    assert "computing" in scenes[0]["query"].lower() or "server" in scenes[0]["query"].lower() or "data" in scenes[0]["query"].lower()


def test_planner_disambiguates_python_programming():
    """'Python' with 'programming' context should not show snakes."""
    scenes = plan_scenes("Python programming is great for data science.")
    query = scenes[0]["query"].lower()
    assert "programming" in query or "code" in query or "data" in query


def test_planner_uses_visual_hint_when_provided():
    scenes = plan_scenes(None, [{"text": "Solar panels on rooftop.", "visual_hint": "solar panels rooftop"}])
    assert scenes[0]["query"] == "solar panels rooftop"


def test_planner_handles_sensitive_topic():
    scenes = plan_scenes("The war affected many families.")
    assert "SENSITIVE_TOPIC_USE_RESPECTFUL_VISUALS" in scenes[0]["warnings"]


def test_planner_splits_on_sentence_boundaries():
    scenes = plan_scenes("First sentence here. Second sentence follows! Third one too?")
    assert len(scenes) == 3
    for i in range(len(scenes) - 1):
        assert scenes[i]["end"] == scenes[i + 1]["start"]


def test_planner_raises_on_empty():
    import pytest
    with pytest.raises(ValueError, match="No scenes could be planned"):
        plan_scenes("")
