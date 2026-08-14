"""Coercive-call pattern classifier for the PARAKH backend.

Analyzes phone call transcripts for scam patterns (impersonation, isolation,
urgency, control) using deterministic weighted keyword matching and calibrated
confidence scoring. Zero external I/O or LLM dependencies.
"""

PATTERNS = [
    (
        "impersonation",
        0.30,
        ["customs", "police", "warrant", "case number", "cbi", "cyber cell"],
    ),
    (
        "isolation",
        0.25,
        ["do not tell anyone", "alone", "don't tell"],
    ),
    (
        "urgency",
        0.25,
        ["now", "deadline", "blocked", "penalty", "urgent", "within hours"],
    ),
    (
        "control",
        0.20,
        ["transfer", "safe account", "click this link", "send the otp"],
    ),
]


def analyze(transcript: list[str]) -> dict:
    """Classify a call transcript for coercive scam patterns and return a CallVerdict dict."""
    full_text = " ".join(transcript).casefold()

    patterns_found: list[str] = []
    combined_weight = 0.0

    for name, weight, triggers in PATTERNS:
        if any(trigger in full_text for trigger in triggers):
            patterns_found.append(name)
            combined_weight += weight

    count = len(patterns_found)
    is_coercive = (count >= 2 and combined_weight >= 0.50) or (count >= 3)
    confidence = min(0.99, round(0.93 * combined_weight, 2))

    if patterns_found:
        summary = f"Call matches {count} coercive pattern(s): {', '.join(patterns_found)}."
    else:
        summary = "No coercive patterns detected."

    return {
        "is_coercive": is_coercive,
        "confidence": confidence,
        "patterns_found": patterns_found,
        "summary": summary,
    }
