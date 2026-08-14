"""Rules-based risk scoring engine with ML fusion for the PARAKH backend.

Pure functions only, zero I/O. Evaluates 6 deterministic fraud detection rules,
fuses rule points with optional Isolation Forest score, and produces structured
reasons for human-in-the-loop explanation.
"""

from app.schemas import tier_of


def minutes_between(hhmm_a: str, hhmm_b: str) -> int:
    """Difference in minutes between two 'HH:mm' times: b - a."""
    h1, m1 = map(int, hhmm_a.split(":"))
    h2, m2 = map(int, hhmm_b.split(":"))
    return (h2 * 60 + m2) - (h1 * 60 + m1)


def parse_window(typical_hours: str) -> tuple[int, int]:
    """Parse 'HH:mm\u2013HH:mm' window (split on en-dash) to start and end minutes."""
    start_str, end_str = typical_hours.split("\u2013")
    h1, m1 = map(int, start_str.split(":"))
    h2, m2 = map(int, end_str.split(":"))
    return h1 * 60 + m1, h2 * 60 + m2


def score_transaction(
    txn: dict,
    user: dict,
    recent_coercive_call: dict | None,
    velocity_10min: int,
    forest_score: int | None = None,
) -> dict:
    """Score a transaction using 6 deterministic rules and optional ML fusion."""
    amount = txn.get("amount", 0)
    median_amount = user.get("median_amount", 1)
    device = txn.get("device", "")
    hour = txn.get("hour", "00:00")
    payee = txn.get("payee", "")
    typical_hours = user.get("typical_hours", "00:00\u201323:59")
    is_new_payee = txn.get("is_new_payee", True)

    fired_rules: list[tuple[int, dict]] = []

    # Rule 1: Call linkage (+35 points)
    if recent_coercive_call is not None and bool(recent_coercive_call.get("is_coercive", True)):
        call_at = recent_coercive_call.get("at") or recent_coercive_call.get("call_at", "")
        call_id = recent_coercive_call.get("id") or recent_coercive_call.get("call_id", "")
        confidence = recent_coercive_call.get("confidence", 0.0)
        diff = minutes_between(call_at, hour)
        if 0 <= diff <= 5:
            fired_rules.append((
                1,
                {
                    "label": f"Flagged coercive call {diff} min before",
                    "points": 35,
                    "evidence": f"{call_id} \u00b7 {call_at} \u00b7 confidence {confidence}",
                },
            ))

    # Rule 2: New payee (+20 points)
    if is_new_payee and amount > 2 * median_amount:
        fired_rules.append((
            2,
            {
                "label": "Payee never seen before",
                "points": 20,
                "evidence": f"{payee} \u00b7 first txn",
            },
        ))

    # Rule 3: Device change (+15 points)
    if "new" in device.lower():
        label = "Device changed today" if "new today" in device.lower() else "Device changed yesterday"
        fired_rules.append((
            3,
            {
                "label": label,
                "points": 15,
                "evidence": f"{device} \u00b7 first use {hour}",
            },
        ))

    # Rule 4: Amount spike (+15 points)
    if amount > 3 * median_amount:
        mult = amount / median_amount
        mult_str = f"{mult:.1f}".removesuffix(".0")
        fired_rules.append((
            4,
            {
                "label": f"Amount {mult_str}\u00d7 median",
                "points": 15,
                "evidence": f"\u20b9{amount:,} vs median \u20b9{median_amount:,}",
            },
        ))

    # Rule 5: Hours anomaly (+5 points)
    start_min, end_min = parse_window(typical_hours)
    h_txn, m_txn = map(int, hour.split(":"))
    txn_min = h_txn * 60 + m_txn
    if txn_min < start_min or txn_min >= end_min:
        fired_rules.append((
            5,
            {
                "label": "Outside typical hours",
                "points": 5,
                "evidence": f"usual window {typical_hours}",
            },
        ))

    # Rule 6: Velocity (+10 points)
    if velocity_10min >= 3:
        fired_rules.append((
            6,
            {
                "label": "High velocity",
                "points": 10,
                "evidence": f"{velocity_10min} txns in 10 min",
            },
        ))

    # Compute raw rule sum
    rules_total = sum(r[1]["points"] for r in fired_rules)

    # Fusion formula (§8)
    if forest_score is not None:
        fused = min(100, round(0.6 * rules_total + 0.4 * forest_score))
    else:
        fused = min(100, rules_total)

    tier = tier_of(fused)

    # Sort reasons: highest points desc, then rule index asc
    fired_rules.sort(key=lambda item: (-item[1]["points"], item[0]))
    reasons = [item[1] for item in fired_rules]

    return {
        "rules": rules_total,
        "forest": forest_score,
        "fused": fused,
        "tier": tier,
        "reasons": reasons,
    }
