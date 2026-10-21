import pytest

from app.providers.audio import AudioValidationError, MockNarrationProvider


def test_mock_tts_returns_measured_like_segments():
    timing = MockNarrationProvider().synthesize("One clear sentence. A second one.", "en-IN-female")
    assert timing.duration_seconds > 1
    assert len(timing.segments) == 2
    assert timing.segments[-1]["end"] == pytest.approx(timing.duration_seconds, abs=0.001)


def test_mock_url_rejects_duration_over_assessment_limit():
    with pytest.raises(AudioValidationError, match="INVALID_AUDIO_DURATION"):
        MockNarrationProvider().transcribe_url("https://example.test/audio.wav?duration=601")


def test_mock_synthesize_rejects_empty_script():
    with pytest.raises(AudioValidationError, match="EMPTY_SCRIPT"):
        MockNarrationProvider().synthesize("", "en-IN-female")


def test_mock_synthesize_rejects_whitespace_only():
    with pytest.raises(AudioValidationError, match="EMPTY_SCRIPT"):
        MockNarrationProvider().synthesize("   ", "en-IN-female")


def test_mock_url_accepts_valid_duration():
    timing = MockNarrationProvider().transcribe_url("https://example.test/audio.wav?duration=30&transcript=Hello+world")
    assert timing.duration_seconds == 30.0
    assert timing.transcript == "Hello world"
