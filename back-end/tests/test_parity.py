"""End-to-end integration and parity verification test suite for the PARAKH backend.

Tests all backbone invariants specified in §11, §12, and §13 of the engine build plan:
1. Complete database seeding in an isolated temporary environment.
2. Parity Invariant 1: T-1421 fused score >= 70 (RED).
3. Parity Invariant 2: Scam group (T-1421, T-1187, T-2903) strictly beats soft group (T-3376, T-5108, T-0742, T-1422).
4. Computed columns populated for the 7 stars, strictly NULL for the 9 pads.
5. Display truth preservation: authored scores, reasons (+35 call linkage), and narratives intact.
6. System invariants: 16 alerts total, 14 active, 500 cohort records, computed avgScore.
7. Database schema integrity: 6 users, 1 call, 16 raw transactions.
"""

import json
from pathlib import Path
import pytest
from app import db, seed_engine

SEED_DIR = Path(__file__).resolve().parent.parent / "seed"
STAR_IDS = ["T-1421", "T-1187", "T-2903", "T-3376", "T-5108", "T-0742", "T-1422"]
SCAM_GROUP = ["T-1421", "T-1187", "T-2903"]
SOFT_GROUP = ["T-3376", "T-5108", "T-0742", "T-1422"]


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Set up an isolated temporary SQLite database for test execution."""
    temp_db = tmp_path / "parakh_test.db"
    monkeypatch.setenv("PARAKH_DB", str(temp_db))
    monkeypatch.setattr(db, "DB_PATH", temp_db)

    # Seed the isolated database
    seed_engine.run()

    yield temp_db


# -------------------------------------------------------------------------
# 1. Parity Guarantees (§12)
# -------------------------------------------------------------------------

def test_parity_t1421_fused_score_red():
    """Guarantee A: T-1421 fused score must be >= 70 (RED tier)."""
    alert = db.get_alert("T-1421")
    assert alert is not None, "T-1421 alert missing from database"
    assert alert["fused_score"] is not None
    assert alert["fused_score"] >= 70, f"T-1421 fused score {alert['fused_score']} < 70"


def test_parity_scam_group_strictly_beats_soft_group():
    """Guarantee B: Every scam-group fused score > every soft-group fused score."""
    scam_scores = []
    for t_id in SCAM_GROUP:
        row = db.get_alert(t_id)
        assert row is not None, f"Scam alert {t_id} missing"
        assert row["fused_score"] is not None
        scam_scores.append((t_id, row["fused_score"]))

    soft_scores = []
    for t_id in SOFT_GROUP:
        row = db.get_alert(t_id)
        assert row is not None, f"Soft alert {t_id} missing"
        assert row["fused_score"] is not None
        soft_scores.append((t_id, row["fused_score"]))

    min_scam = min(s[1] for s in scam_scores)
    max_soft = max(s[1] for s in soft_scores)

    # Strict inequality: every scam > every soft
    assert min_scam > max_soft, (
        f"Scam group min ({min_scam}) did not strictly beat soft group max ({max_soft}). "
        f"Scam: {scam_scores}, Soft: {soft_scores}"
    )


# -------------------------------------------------------------------------
# 2. Computed Columns vs Pads (§12)
# -------------------------------------------------------------------------

def test_computed_columns_populated_for_stars_only():
    """Guarantee C: 7 stars have integer computed columns; 9 pads have NULL."""
    all_alerts = db.list_alerts()
    assert len(all_alerts) == 16

    star_count = 0
    pad_count = 0

    for a in all_alerts:
        a_id = a["id"]
        if a_id in STAR_IDS:
            star_count += 1
            assert isinstance(a["rule_points"], int), f"Star {a_id} rule_points is not int"
            assert isinstance(a["forest_score"], int), f"Star {a_id} forest_score is not int"
            assert isinstance(a["fused_score"], int), f"Star {a_id} fused_score is not int"
        else:
            pad_count += 1
            assert a["rule_points"] is None, f"Pad {a_id} rule_points should be None"
            assert a["forest_score"] is None, f"Pad {a_id} forest_score should be None"
            assert a["fused_score"] is None, f"Pad {a_id} fused_score should be None"

    assert star_count == 7, f"Expected 7 stars, found {star_count}"
    assert pad_count == 9, f"Expected 9 pads, found {pad_count}"


# -------------------------------------------------------------------------
# 3. Display Truth Preservation (§11 & §12)
# -------------------------------------------------------------------------

def test_display_truth_intact():
    """Guarantee D: Authored scores, tiers, and reason structures are preserved verbatim."""
    t1421 = db.get_alert("T-1421")
    assert t1421["score"] == 95
    assert t1421["tier"] == "red"

    # Convert to camelCase Alert schema dict
    json_alert = db.alert_to_json(t1421)
    assert json_alert["score"] == 95
    assert json_alert["tier"] == "red"
    assert len(json_alert["reasons"]) == 5
    assert json_alert["reasons"][0]["points"] == 35
    assert json_alert["reasons"][0]["label"] == "Flagged coercive call 4 min before"
    assert "CALL-1421 \u00b7 14:02 \u00b7 confidence 0.93" in json_alert["reasons"][0]["evidence"]


# -------------------------------------------------------------------------
# 4. System & Database Invariants (§5 & §12)
# -------------------------------------------------------------------------

def test_database_table_counts_and_invariants():
    """Guarantee E: System invariants for counts, active statuses, and cohort stats."""
    conn = db._connect()

    # Table counts
    users_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    calls_count = conn.execute("SELECT COUNT(*) FROM calls").fetchone()[0]
    txns_count = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    alerts_count = conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]

    assert users_count == 6
    assert calls_count == 1
    assert txns_count == 16
    assert alerts_count == 16

    # Active alerts count: pending, assigned, reviewing == 14
    active_alerts = conn.execute(
        "SELECT COUNT(*) FROM alerts WHERE status IN ('pending', 'assigned', 'reviewing')"
    ).fetchone()[0]
    assert active_alerts == 14

    conn.close()

    # Cohort file checks
    with open(SEED_DIR / "cohort.json", "r", encoding="utf-8") as f:
        cohort = json.load(f)
    assert len(cohort) == 500

    # Display KPI avgScore matches rounded mean of cohort scores
    with open(SEED_DIR / "display.json", "r", encoding="utf-8") as f:
        display = json.load(f)

    expected_avg_score = round(sum(c["score"] for c in cohort) / len(cohort))
    assert display["kpi"]["avgScore"] == expected_avg_score
    assert display["kpi"]["customers"] == 500
    assert display["kpi"]["activeAlerts"] == 14


# -------------------------------------------------------------------------
# 5. Clean-Checkout Idempotency & seed_if_empty (§7 & §13)
# -------------------------------------------------------------------------

def test_seed_if_empty_clean_boot(tmp_path, monkeypatch):
    """Verify clean boot: an empty DB automatically seeds on seed_if_empty()."""
    clean_db = tmp_path / "clean_boot.db"
    monkeypatch.setenv("PARAKH_DB", str(clean_db))
    monkeypatch.setattr(db, "DB_PATH", clean_db)

    db.init_db()

    # Initially 0 alerts
    conn = db._connect()
    initial_count = conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
    conn.close()
    assert initial_count == 0

    # seed_if_empty boots the engine
    db.seed_if_empty()

    conn = db._connect()
    booted_count = conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
    conn.close()
    assert booted_count == 16
