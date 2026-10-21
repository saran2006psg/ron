from app.services.renderer import RATIO_DIMENSIONS


def test_required_aspect_ratios_are_1080p_class():
    assert RATIO_DIMENSIONS["16:9"] == (1920, 1080)
    assert RATIO_DIMENSIONS["9:16"] == (1080, 1920)
    assert RATIO_DIMENSIONS["1:1"] == (1080, 1080)
