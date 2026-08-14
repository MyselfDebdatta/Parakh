"""Unit tests for the Isolation Forest anomaly detector app/forest.py."""

from app.forest import (
    build_background,
    calculate_hour_anomaly,
    normalize_scores,
    train_and_score_stars,
    train_forest,
    STAR_IDS,
)
import numpy as np


def test_hour_anomaly_circular_distance():
    """Verify circular 24-hour anomaly distance from typical hours window center."""
    # Window "08:00–20:00" -> center is 14:00 (14.0 hours)
    typical_hours = "08:00\u201320:00"

    # 14:00 -> distance 0.0
    assert calculate_hour_anomaly("14:00", typical_hours) == 0.0

    # 16:30 -> distance 2.5
    assert calculate_hour_anomaly("16:30", typical_hours) == 2.5

    # 02:00 -> direct dist 12.0, circular 24 - 12 = 12.0
    assert calculate_hour_anomaly("02:00", typical_hours) == 12.0

    # 00:00 -> direct dist 14.0, circular min(14, 10) = 10.0
    assert calculate_hour_anomaly("00:00", typical_hours) == 10.0


def test_build_background_and_training():
    """Background generator builds baseline rows with exact feature dimensionality."""
    users = [
        {"id": "U1", "medianAmount": 1000, "typicalHours": "08:00\u201320:00"},
        {"id": "U2", "medianAmount": 5000, "typicalHours": "07:00\u201322:00"},
    ]
    background_rows, user_stats = build_background(users, n=200, rng=np.random.default_rng(42))

    assert len(background_rows) == 200
    assert len(background_rows[0]) == 6
    assert "U1" in user_stats
    assert "U2" in user_stats

    model = train_forest(background_rows)
    preds = model.predict(background_rows)
    assert len(preds) == 200


def test_normalize_scores_calibration():
    """Linear mapping min->55 / p90->0 clipped to 0-100."""
    raw_min = -0.20
    p90 = 0.10

    raw_scores = np.array([p90, raw_min, 0.20, -0.40])
    scores = normalize_scores(raw_scores, raw_min, p90)

    # at p90 -> 0
    assert scores[0] == 0
    # at raw_min -> 55
    assert scores[1] == 55
    # above p90 -> 0 (clipped)
    assert scores[2] == 0
    # below raw_min -> > 55
    assert scores[3] > 55


def test_star_scores_parity_contract():
    """Verify parity contract: T-1421 fused >= 70 and scam group strictly beats soft group."""
    model, star_scores = train_and_score_stars()
    assert len(star_scores) == 7

    rules = [95, 65, 50, 35, 25, 20, 0]
    fused_scores = {}
    for t_id, r_pts, f_score in zip(STAR_IDS, rules, star_scores):
        fused = min(100, round(0.6 * r_pts + 0.4 * f_score))
        fused_scores[t_id] = fused

    # 1. T-1421 >= 70 (RED)
    assert fused_scores["T-1421"] >= 70

    # 2. Scam group beats soft group
    scam_scores = [fused_scores["T-1421"], fused_scores["T-1187"], fused_scores["T-2903"]]
    soft_scores = [fused_scores["T-3376"], fused_scores["T-5108"], fused_scores["T-0742"], fused_scores["T-1422"]]

    assert min(scam_scores) > max(soft_scores)
