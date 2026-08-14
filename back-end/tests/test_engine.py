"""Unit tests for the PARAKH 6-rule scoring engine and fusion logic.

Tests all 7 ground-truth star transactions, isolated rule triggers, exact
boundary conditions, risk tier assignments, ML score fusion, and reason ordering.
"""

import pytest
from app.engine import minutes_between, parse_window, score_transaction
from app.schemas import tier_of


# -------------------------------------------------------------------------
# Test Data Fixtures
# -------------------------------------------------------------------------

USERS = {
    "C-4421": {"median_amount": 4100, "typical_hours": "08:00\u201321:00"},
    "C-1187": {"median_amount": 7900, "typical_hours": "07:00\u201322:00"},
    "C-2903": {"median_amount": 2700, "typical_hours": "06:00\u201323:00"},
    "C-3376": {"median_amount": 4000, "typical_hours": "07:00\u201321:00"},
    "C-5108": {"median_amount": 2900, "typical_hours": "08:00\u201320:00"},
    "C-0742": {"median_amount": 1000, "typical_hours": "07:00\u201322:00"},
}

CALL_1421 = {
    "id": "CALL-1421",
    "user_id": "C-4421",
    "is_coercive": True,
    "confidence": 0.93,
    "at": "14:02",
}


# -------------------------------------------------------------------------
# 1. Seven Documented Star Transaction Rule Sums (§8 & §12)
# -------------------------------------------------------------------------

def test_star_t1421_sarita_coercion():
    """T-1421: Coercive call + new payee + new device + 12x amount + velocity -> 95 RED."""
    txn = {
        "id": "T-1421",
        "amount": 49500,
        "channel": "PhonePe",
        "device": "OnePlus 12 \u00b7 new today",
        "hour": "14:06",
        "payee": "safeguard-account@okaxis",
    }
    res = score_transaction(txn, USERS["C-4421"], CALL_1421, velocity_10min=3)
    assert res["rules"] == 95
    assert res["fused"] == 95
    assert res["tier"] == "red"
    assert len(res["reasons"]) == 5
    assert res["reasons"][0]["label"] == "Flagged coercive call 4 min before"
    assert res["reasons"][0]["points"] == 35


def test_star_t1187_ramesh_velocity():
    """T-1187: New payee + new device + 4x amount + outside hours + velocity -> 65 YELLOW."""
    txn = {
        "id": "T-1187",
        "amount": 32000,
        "channel": "GPay",
        "device": "Samsung M35 \u00b7 new yesterday",
        "hour": "23:12",
        "payee": "quickcash@ibl",
    }
    res = score_transaction(txn, USERS["C-1187"], None, velocity_10min=3)
    assert res["rules"] == 65
    assert res["fused"] == 65
    assert res["tier"] == "yellow"
    assert len(res["reasons"]) == 5


def test_star_t2903_singh_refund_scam():
    """T-2903: New payee + 8x amount + outside hours + velocity -> 50 YELLOW."""
    txn = {
        "id": "T-2903",
        "amount": 21800,
        "channel": "Paytm",
        "device": "Xiaomi Redmi \u00b7 known",
        "hour": "00:03",
        "payee": "refund-desk@ybl",
    }
    res = score_transaction(txn, USERS["C-2903"], None, velocity_10min=3)
    assert res["rules"] == 50
    assert res["fused"] == 50
    assert res["tier"] == "yellow"
    assert len(res["reasons"]) == 4


def test_star_t3376_fernandes_luckydraw():
    """T-3376: New payee + 3.1x amount -> 35 GREEN."""
    txn = {
        "id": "T-3376",
        "amount": 12300,
        "channel": "Paytm",
        "device": "Samsung A15 \u00b7 known",
        "hour": "19:44",
        "payee": "lucky-draw@paytm",
    }
    res = score_transaction(txn, USERS["C-3376"], None, velocity_10min=2)
    assert res["rules"] == 35
    assert res["fused"] == 35
    assert res["tier"] == "green"
    assert len(res["reasons"]) == 2


def test_star_t5108_khan_plumber():
    """T-5108: New payee + outside hours (20:12 outside 08:00-20:00) -> 25 GREEN."""
    txn = {
        "id": "T-5108",
        "amount": 8600,
        "channel": "GPay",
        "device": "OnePlus Nord \u00b7 known",
        "hour": "20:12",
        "payee": "plumber-khan@icici",
    }
    res = score_transaction(txn, USERS["C-5108"], None, velocity_10min=2)
    assert res["rules"] == 25
    assert res["fused"] == 25
    assert res["tier"] == "green"
    assert len(res["reasons"]) == 2


def test_star_t0742_patil_kirana():
    """T-0742: New payee (2400 > 2*1000) -> 20 GREEN."""
    txn = {
        "id": "T-0742",
        "amount": 2400,
        "channel": "BHIM",
        "device": "Realme 12 \u00b7 known",
        "hour": "09:31",
        "payee": "kraft@okhdfc",
    }
    res = score_transaction(txn, USERS["C-0742"], None, velocity_10min=1)
    assert res["rules"] == 20
    assert res["fused"] == 20
    assert res["tier"] == "green"
    assert len(res["reasons"]) == 1


def test_star_t1422_sarita_plumber():
    """T-1422: Legitimate payment (3200 <= 2*4100, known device, within hours) -> 0 GREEN."""
    txn = {
        "id": "T-1422",
        "amount": 3200,
        "channel": "GPay",
        "device": "OnePlus 12 \u00b7 known",
        "hour": "10:12",
        "payee": "rafiq-plumbing@icici",
    }
    res = score_transaction(txn, USERS["C-4421"], None, velocity_10min=1)
    assert res["rules"] == 0
    assert res["fused"] == 0
    assert res["tier"] == "green"
    assert len(res["reasons"]) == 0


# -------------------------------------------------------------------------
# 2. Individual Rules Isolation & Exact Boundaries (§8 & §12)
# -------------------------------------------------------------------------

def test_rule1_call_linkage_fires_and_silent():
    """Rule 1 (+35): Fires when coercive call <= 5 min before txn; silent otherwise."""
    user = {"median_amount": 5000, "typical_hours": "08:00\u201320:00"}
    txn = {"amount": 1000, "device": "Pixel \u00b7 known", "hour": "14:05", "payee": "known@bank", "is_new_payee": False}

    # Exactly 5 min before -> FIRES (+35)
    call_5m = {"id": "CALL-1", "is_coercive": True, "confidence": 0.9, "at": "14:00"}
    res = score_transaction(txn, user, call_5m, velocity_10min=0)
    assert res["rules"] == 35
    assert res["reasons"][0]["points"] == 35
    assert res["reasons"][0]["label"] == "Flagged coercive call 5 min before"
    assert "CALL-1 \u00b7 14:00 \u00b7 confidence 0.9" in res["reasons"][0]["evidence"]

    # 6 min before -> SILENT (+0)
    call_6m = {"id": "CALL-2", "is_coercive": True, "confidence": 0.9, "at": "13:59"}
    res_6m = score_transaction(txn, user, call_6m, velocity_10min=0)
    assert res_6m["rules"] == 0

    # Non-coercive call -> SILENT (+0)
    call_non_coercive = {"id": "CALL-3", "is_coercive": False, "confidence": 0.9, "at": "14:02"}
    res_nc = score_transaction(txn, user, call_non_coercive, velocity_10min=0)
    assert res_nc["rules"] == 0


def test_rule2_new_payee_boundaries():
    """Rule 2 (+20): Fires when is_new_payee AND amount > 2 * median; silent on <= 2 * median."""
    user = {"median_amount": 5000, "typical_hours": "08:00\u201320:00"}
    base_txn = {"device": "Pixel \u00b7 known", "hour": "12:00", "payee": "fresh@upi", "is_new_payee": True}

    # Boundary: amount == 2 * median (10000) -> SILENT (+0)
    res_exact = score_transaction({**base_txn, "amount": 10000}, user, None, velocity_10min=0)
    assert res_exact["rules"] == 0

    # Boundary: amount == 2 * median + 1 (10001) -> FIRES (+20)
    res_fire = score_transaction({**base_txn, "amount": 10001}, user, None, velocity_10min=0)
    assert res_fire["rules"] == 20
    assert res_fire["reasons"][0]["label"] == "Payee never seen before"
    assert res_fire["reasons"][0]["evidence"] == "fresh@upi \u00b7 first txn"

    # Known payee with high amount -> SILENT (+0 for rule 2)
    res_known = score_transaction({**base_txn, "amount": 11000, "is_new_payee": False}, user, None, velocity_10min=0)
    assert res_known["rules"] == 0


def test_rule3_device_change():
    """Rule 3 (+15): Fires on new device ('new today' or 'new yesterday'); silent on 'known'."""
    user = {"median_amount": 5000, "typical_hours": "08:00\u201320:00"}
    base_txn = {"amount": 1000, "hour": "12:00", "payee": "known@upi", "is_new_payee": False}

    # New today
    res_today = score_transaction({**base_txn, "device": "iPhone 15 \u00b7 new today"}, user, None, velocity_10min=0)
    assert res_today["rules"] == 15
    assert res_today["reasons"][0]["label"] == "Device changed today"
    assert res_today["reasons"][0]["evidence"] == "iPhone 15 \u00b7 new today \u00b7 first use 12:00"

    # New yesterday
    res_yest = score_transaction({**base_txn, "device": "iPhone 15 \u00b7 new yesterday"}, user, None, velocity_10min=0)
    assert res_yest["rules"] == 15
    assert res_yest["reasons"][0]["label"] == "Device changed yesterday"

    # Known device
    res_known = score_transaction({**base_txn, "device": "iPhone 15 \u00b7 known"}, user, None, velocity_10min=0)
    assert res_known["rules"] == 0


def test_rule4_amount_spike_boundaries_and_formatting():
    """Rule 4 (+15): Fires when amount > 3 * median; format mult with 1 decimal, trailing .0 stripped."""
    user = {"median_amount": 1000, "typical_hours": "08:00\u201320:00"}
    base_txn = {"device": "Pixel \u00b7 known", "hour": "12:00", "payee": "known@upi", "is_new_payee": False}

    # Boundary: amount == 3 * median (3000) -> SILENT (+0)
    res_exact = score_transaction({**base_txn, "amount": 3000}, user, None, velocity_10min=0)
    assert res_exact["rules"] == 0

    # Boundary: amount == 3 * median + 1 (3001) -> FIRES (+15)
    res_fire = score_transaction({**base_txn, "amount": 3001}, user, None, velocity_10min=0)
    assert res_fire["rules"] == 15
    assert res_fire["reasons"][0]["label"] == "Amount 3\u00d7 median"
    assert res_fire["reasons"][0]["evidence"] == "\u20b93,001 vs median \u20b91,000"

    # Fractional multiple: 3500 / 1000 = 3.5 -> "Amount 3.5× median"
    res_frac = score_transaction({**base_txn, "amount": 3500}, user, None, velocity_10min=0)
    assert res_frac["reasons"][0]["label"] == "Amount 3.5\u00d7 median"

    # Integer multiple: 4000 / 1000 = 4.0 -> "Amount 4× median"
    res_int = score_transaction({**base_txn, "amount": 4000}, user, None, velocity_10min=0)
    assert res_int["reasons"][0]["label"] == "Amount 4\u00d7 median"


def test_rule5_hours_window_boundaries():
    """Rule 5 (+5): Window is inclusive of start, exclusive of end."""
    user = {"median_amount": 5000, "typical_hours": "08:00\u201320:00"}
    base_txn = {"amount": 1000, "device": "Pixel \u00b7 known", "payee": "known@upi", "is_new_payee": False}

    # Hour == start (08:00) -> Inside window -> SILENT (+0)
    res_start = score_transaction({**base_txn, "hour": "08:00"}, user, None, velocity_10min=0)
    assert res_start["rules"] == 0

    # Hour == 19:59 -> Inside window -> SILENT (+0)
    res_in = score_transaction({**base_txn, "hour": "19:59"}, user, None, velocity_10min=0)
    assert res_in["rules"] == 0

    # Hour == end (20:00) -> Outside window (exclusive end) -> FIRES (+5)
    res_end = score_transaction({**base_txn, "hour": "20:00"}, user, None, velocity_10min=0)
    assert res_end["rules"] == 5
    assert res_end["reasons"][0]["label"] == "Outside typical hours"
    assert res_end["reasons"][0]["evidence"] == "usual window 08:00\u201320:00"

    # Hour == 07:59 -> Outside window -> FIRES (+5)
    res_early = score_transaction({**base_txn, "hour": "07:59"}, user, None, velocity_10min=0)
    assert res_early["rules"] == 5


def test_rule6_velocity_boundaries():
    """Rule 6 (+10): Fires when velocity_10min >= 3; silent on <= 2."""
    user = {"median_amount": 5000, "typical_hours": "08:00\u201320:00"}
    txn = {"amount": 1000, "device": "Pixel \u00b7 known", "hour": "12:00", "payee": "known@upi", "is_new_payee": False}

    # Velocity == 2 -> SILENT (+0)
    res_2 = score_transaction(txn, user, None, velocity_10min=2)
    assert res_2["rules"] == 0

    # Velocity == 3 -> FIRES (+10)
    res_3 = score_transaction(txn, user, None, velocity_10min=3)
    assert res_3["rules"] == 10
    assert res_3["reasons"][0]["label"] == "High velocity"
    assert res_3["reasons"][0]["evidence"] == "3 txns in 10 min"


# -------------------------------------------------------------------------
# 3. Risk Tier Boundaries (§6 & §12)
# -------------------------------------------------------------------------

@pytest.mark.parametrize(
    "score,expected_tier",
    [
        (0, "green"),
        (39, "green"),
        (40, "yellow"),
        (70, "yellow"),
        (71, "red"),
        (100, "red"),
    ],
)
def test_tier_boundaries(score, expected_tier):
    """Verify tier assignment: >70 red, 40-70 yellow, <40 green."""
    assert tier_of(score) == expected_tier


# -------------------------------------------------------------------------
# 4. Score Fusion & Reason Sorting (§8)
# -------------------------------------------------------------------------

def test_ml_fusion_formula():
    """Fusion formula: round(0.6 * rules + 0.4 * forest_score) capped at 100."""
    user = {"median_amount": 5000, "typical_hours": "08:00\u201320:00"}
    txn = {"amount": 1000, "device": "Pixel \u00b7 known", "hour": "12:00", "payee": "known@upi", "is_new_payee": False}

    # 1. Live path (forest_score is None) -> fused == rules
    res_live = score_transaction(txn, user, None, velocity_10min=3, forest_score=None)
    assert res_live["rules"] == 10
    assert res_live["forest"] is None
    assert res_live["fused"] == 10
    assert res_live["tier"] == "green"

    # 2. Hybrid path: rules=10, forest=90 -> round(0.6*10 + 0.4*90) = round(6 + 36) = 42 (yellow)
    res_hybrid = score_transaction(txn, user, None, velocity_10min=3, forest_score=90)
    assert res_hybrid["rules"] == 10
    assert res_hybrid["forest"] == 90
    assert res_hybrid["fused"] == 42
    assert res_hybrid["tier"] == "yellow"


def test_reasons_sorting_and_tie_breaking():
    """Reasons must be sorted by points descending, tie-broken by rule number (1->6)."""
    user = {"median_amount": 1000, "typical_hours": "08:00\u201320:00"}
    # Fires Rule 2 (20), Rule 3 (15), Rule 4 (15), Rule 5 (5), Rule 6 (10)
    txn = {
        "amount": 4000,
        "device": "Samsung \u00b7 new today",
        "hour": "22:00",
        "payee": "stranger@bank",
        "is_new_payee": True,
    }
    res = score_transaction(txn, user, None, velocity_10min=3)
    points_list = [r["points"] for r in res["reasons"]]
    labels_list = [r["label"] for r in res["reasons"]]

    assert points_list == [20, 15, 15, 10, 5]
    # Rule 3 (Device changed today) must precede Rule 4 (Amount 4× median) on 15-point tie
    assert labels_list[1] == "Device changed today"
    assert labels_list[2] == "Amount 4\u00d7 median"


# -------------------------------------------------------------------------
# 5. Helpers Verification (§8)
# -------------------------------------------------------------------------

def test_helpers():
    """Verify minutes_between and parse_window helper functions."""
    assert minutes_between("14:02", "14:06") == 4
    assert minutes_between("00:00", "01:15") == 75
    assert minutes_between("10:00", "10:00") == 0

    start_m, end_m = parse_window("07:30\u201321:45")
    assert start_m == 7 * 60 + 30
    assert end_m == 21 * 60 + 45
