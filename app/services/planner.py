from __future__ import annotations

import re

AMBIGUOUS = {"bank", "cloud", "mouse", "python", "value"}
SENSITIVE = {"death", "dead", "funeral", "war", "attack", "suicide", "disaster"}

# Disambiguation context hints: if an ambiguous word appears alongside these
# context words, refine the visual query to avoid wrong literal interpretation.
DISAMBIGUATION: dict[str, dict[str, str]] = {
    "cloud": {
        "tech": "cloud computing data center servers",
        "computing": "cloud computing data center servers",
        "server": "cloud computing server infrastructure",
        "storage": "cloud storage digital data",
        "service": "cloud service technology platform",
        "default": "sky clouds nature",
    },
    "bank": {
        "financial": "bank building financial institution",
        "money": "banking finance money transfer",
        "interest": "banking interest rate financial",
        "loan": "bank loan financial services",
        "river": "river bank nature waterside",
        "default": "bank building finance",
    },
    "python": {
        "programming": "python programming code laptop",
        "code": "python programming code editor",
        "data": "python data science programming",
        "machine": "python machine learning programming",
        "ai": "python artificial intelligence programming",
        "snake": "python snake reptile wildlife",
        "default": "python programming language code",
    },
    "mouse": {
        "computer": "computer mouse device desk",
        "click": "computer mouse clicking device",
        "wireless": "wireless mouse technology device",
        "ergonomic": "ergonomic mouse office device",
        "animal": "mouse animal rodent nature",
        "default": "computer mouse device",
    },
    "value": {
        "money": "financial value money investment",
        "stock": "stock market value investment",
        "portfolio": "portfolio value financial investment",
        "moral": "moral values ethics society",
        "family": "family values community",
        "default": "value growth chart business",
    },
}


def plan_scenes(script: str | None, supplied: list[dict] | None = None, duration: float | None = None) -> list[dict]:
    raw = supplied or [{"text": piece.strip(), "visual_hint": None}
                       for piece in re.split(r"(?<=[.!?])\s+", script or "") if piece.strip()]
    if not raw:
        raise ValueError("No scenes could be planned")
    durations = _durations(raw, duration)
    output, start = [], 0.0
    for index, (scene, seconds) in enumerate(zip(raw, durations), 1):
        text = scene["text"].strip()
        words = {word.lower() for word in re.findall(r"[A-Za-z]+", text)}
        warnings = []
        if words & AMBIGUOUS:
            warnings.append("AMBIGUOUS_TERM_REQUIRES_CONTEXT")
        if words & SENSITIVE:
            warnings.append("SENSITIVE_TOPIC_USE_RESPECTFUL_VISUALS")

        # Determine the visual query
        if scene.get("visual_hint"):
            query = scene["visual_hint"]
        else:
            query = _disambiguate_query(text, words)

        output.append({"id": f"scene-{index:03d}", "text": text, "visual_hint": scene.get("visual_hint"),
                       "start": round(start, 3), "end": round(start + seconds, 3), "duration": round(seconds, 3),
                       "query": query, "warnings": warnings})
        start += seconds
    return output


def _disambiguate_query(text: str, words: set[str]) -> str:
    """If text contains ambiguous words, try to refine the query using context clues."""
    text_lower = text.lower()
    for ambiguous_word in AMBIGUOUS:
        if ambiguous_word not in words:
            continue
        context_map = DISAMBIGUATION.get(ambiguous_word, {})
        # Check each context word
        for context_word, refined_query in context_map.items():
            if context_word == "default":
                continue
            if context_word in text_lower:
                # Found a contextual clue — replace the ambiguous part
                return refined_query
        # No context found — use default interpretation
        default = context_map.get("default")
        if default:
            # Replace just the ambiguous word in the query with the default
            return text
    return text


def _durations(scenes: list[dict], total: float | None) -> list[float]:
    weights = [max(1, len(re.findall(r"\w+", item["text"]))) for item in scenes]
    total = total if total and total > 0 else sum(max(2.0, weight / 2.5) for weight in weights)
    return [total * weight / sum(weights) for weight in weights]
