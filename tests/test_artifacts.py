import json
import tempfile
from pathlib import Path

from app.providers.footage import FootageCandidate
from app.services.artifacts import write_audit_artifacts


def test_writes_consistent_audit_artifacts():
    scene = {"id": "scene-001", "text": "Cloud computing helps teams.", "start": 0.0, "end": 3.0,
             "query": "cloud computing", "warnings": []}
    clip = FootageCandidate("https://video.example/1.mp4", "test", "Test licence", "https://example/licence",
                            "Creator", "Credit Creator", True, True, False, True, "cloud computing")
    with tempfile.TemporaryDirectory(dir=Path.cwd()) as temp:
        paths = write_audit_artifacts(Path(temp), "job-1", [scene], [(scene, clip, 0.8, "TEST")],
                                      {"provider": "mock"}, {"aspect_ratios": ["16:9"]}, [])
        assert json.loads(paths["timeline"].read_text())["scenes"][0]["clip"]["rights_verified"] is True
        assert "00:00:00,000 --> 00:00:03,000" in paths["captions"].read_text()
        assert json.loads(paths["manifest"].read_text())["render"]["status"] == "not_rendered"
