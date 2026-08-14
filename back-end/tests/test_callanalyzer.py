"""Unit tests for the coercive-call pattern classifier app/callanalyzer.py."""

import json
from pathlib import Path
from app.callanalyzer import analyze


def test_call_1421_sarita_transcript():
    """CALL-1421 transcript hits all 4 patterns -> is_coercive=True, confidence=0.93."""
    calls_path = Path(__file__).resolve().parent.parent / "seed" / "calls.json"
    with open(calls_path, "r", encoding="utf-8") as f:
        calls = json.load(f)

    call_1421 = next(c for c in calls if c["id"] == "CALL-1421")
    verdict = analyze(call_1421["transcript"])

    assert verdict["is_coercive"] is True
    assert verdict["confidence"] == 0.93
    assert verdict["patterns_found"] == ["impersonation", "isolation", "urgency", "control"]
    assert "4 coercive pattern(s)" in verdict["summary"]


def test_clean_transcript():
    """Benign conversation with zero patterns -> is_coercive=False, confidence=0.0."""
    transcript = [
        "Friend: Hey, are you free this weekend?",
        "User: Yes, let's meet for lunch at 1 PM.",
        "Friend: Sounds good, see you!",
    ]
    verdict = analyze(transcript)
    assert verdict["is_coercive"] is False
    assert verdict["confidence"] == 0.0
    assert verdict["patterns_found"] == []
    assert verdict["summary"] == "No coercive patterns detected."


def test_single_pattern_sub_threshold():
    """Transcript with only 1 pattern (urgency: weight 0.25) -> is_coercive=False, confidence=0.23."""
    transcript = [
        "Boss: Please send the meeting notes now, it is urgent.",
    ]
    verdict = analyze(transcript)
    assert verdict["is_coercive"] is False
    assert verdict["confidence"] == 0.23  # round(0.93 * 0.25, 2) = 0.23
    assert verdict["patterns_found"] == ["urgency"]


def test_two_patterns_reaching_fifty_weight():
    """Two patterns: impersonation (0.30) + isolation (0.25) = 0.55 >= 0.50 -> is_coercive=True."""
    transcript = [
        "Caller: This is the police department regarding a case number.",
        "Caller: You must stay alone and do not tell anyone.",
    ]
    verdict = analyze(transcript)
    assert verdict["is_coercive"] is True
    assert verdict["confidence"] == 0.51  # round(0.93 * 0.55, 2) = 0.51
    assert verdict["patterns_found"] == ["impersonation", "isolation"]


def test_two_patterns_below_fifty_weight():
    """Two patterns: urgency (0.25) + control (0.20) = 0.45 < 0.50 -> is_coercive=False."""
    transcript = [
        "Friend: Please transfer the money now.",
    ]
    verdict = analyze(transcript)
    assert verdict["is_coercive"] is False
    assert verdict["confidence"] == 0.42  # round(0.93 * 0.45, 2) = 0.42
    assert verdict["patterns_found"] == ["urgency", "control"]


def test_three_patterns_any_weight():
    """Three patterns: isolation (0.25) + urgency (0.25) + control (0.20) = 0.70 -> is_coercive=True (count >= 3)."""
    transcript = [
        "Caller: Don't tell anyone, click this link now.",
    ]
    verdict = analyze(transcript)
    assert verdict["is_coercive"] is True
    assert verdict["confidence"] == 0.65  # round(0.93 * 0.70, 2) = 0.65
    assert verdict["patterns_found"] == ["isolation", "urgency", "control"]


def test_case_insensitivity():
    """Case variations must match properly via casefold()."""
    transcript = [
        "Caller: CUSTOMS NOTICE! A WARRANT has been issued!",
        "Caller: You are ALONE! SAFE ACCOUNT TRANSFER NOW!",
    ]
    verdict = analyze(transcript)
    assert verdict["is_coercive"] is True
    assert verdict["confidence"] == 0.93
    assert verdict["patterns_found"] == ["impersonation", "isolation", "urgency", "control"]
