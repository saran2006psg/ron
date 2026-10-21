from app.services.planner import plan_scenes

def test_planner_keeps_sentence_boundaries_and_ambiguity_warning():
    scenes = plan_scenes("Cloud computing is useful. A bank can be digital.")
    assert len(scenes) == 2
    assert scenes[0]["start"] == 0
    assert "AMBIGUOUS_TERM_REQUIRES_CONTEXT" in scenes[0]["warnings"]
    assert scenes[-1]["end"] > scenes[0]["end"]

