"""Isolation Forest anomaly detection model for the PARAKH backend.

Trained once on synthetic normal transactions generated from customer baseline
profiles, scored on seed star transactions, and cached into SQLite. Deterministic
and seed-time only.
"""

import json
import os
import sys
from pathlib import Path
import numpy as np
from sklearn.ensemble import IsolationForest

from app.engine import parse_window

SEED_DIR = Path(__file__).resolve().parent.parent / "seed"


def parse_txn_hour(hour_str: str) -> float:
    """Convert 'HH:mm' to fractional hours from midnight (0.0 to 23.99)."""
    h, m = map(int, hour_str.split(":"))
    return h + m / 60.0


def calculate_hour_anomaly(txn_hour_str: str, typical_hours_str: str) -> float:
    """Calculate circular distance in hours from the window center."""
    start_min, end_min = parse_window(typical_hours_str)
    c = (start_min + end_min) / 2.0 / 60.0
    txn_hour = parse_txn_hour(txn_hour_str)
    d = abs(txn_hour - c)
    return min(d, 24.0 - d)


def build_background(users: list[dict], n: int = 2000, rng: np.random.Generator | None = None):
    """Generate synthetic normal background transactions for baseline feature statistics."""
    if rng is None:
        rng = np.random.default_rng(42)

    rows_per_user = n // len(users)
    background_rows: list[list[float]] = []
    user_stats: dict[str, dict[str, float]] = {}

    for user in users:
        u_id = user["id"]
        median = float(user.get("medianAmount") or user.get("median_amount", 1000))
        typical_hours = user.get("typicalHours") or user.get("typical_hours", "08:00\u201321:00")
        start_min, end_min = parse_window(typical_hours)

        # 1. Generate normal amounts and hours
        amounts = rng.uniform(median * 0.5, median * 1.5, size=rows_per_user)
        mean_amt = float(np.mean(amounts))
        std_amt = float(np.std(amounts))
        if std_amt == 0.0:
            std_amt = 1.0
        user_stats[u_id] = {"mean": mean_amt, "std": std_amt}

        start_h = start_min / 60.0
        end_h = end_min / 60.0
        hours = rng.uniform(start_h, end_h, size=rows_per_user)

        c = (start_min + end_min) / 2.0 / 60.0

        for amt, hr in zip(amounts, hours):
            amt_z = (amt - mean_amt) / std_amt
            d = abs(hr - c)
            hr_anom = min(d, 24.0 - d)
            # Normal background: velocity=0, payee_new=0, device_new=0, channel_entropy=0
            background_rows.append([amt_z, hr_anom, 0.0, 0.0, 0.0, 0.0])

    return background_rows, user_stats


def feature_row(txn: dict, user: dict, user_stats: dict[str, float], all_user_txns: list[dict]) -> list[float]:
    """Compute the 6 exact ML feature dimensions for a transaction."""
    u_id = user["id"]
    median_val = float(user.get("medianAmount") or user.get("median_amount", 1000))
    stats = user_stats.get(u_id, {"mean": median_val, "std": 1.0})
    amt = float(txn.get("amount", 0))
    amt_zscore = (amt - stats["mean"]) / stats["std"]

    typical_hours = user.get("typicalHours") or user.get("typical_hours", "08:00\u201321:00")
    hour_anomaly = calculate_hour_anomaly(txn.get("hour", "12:00"), typical_hours)

    velocity = 1.0 if txn.get("velocity10Min", 0) >= 2 else 0.0

    other_txns = [t for t in all_user_txns if t.get("txnId") != txn.get("txnId")]
    other_payees = {t.get("payee") for t in other_txns if t.get("payee")}
    payee_new = 1.0 if txn.get("payee") not in other_payees else 0.0

    device_new = 1.0 if "new" in txn.get("device", "").lower() else 0.0

    if other_txns:
        channels = [t.get("channel") for t in other_txns if t.get("channel")]
        if channels:
            most_common_channel = max(set(channels), key=channels.count)
            channel_entropy = 1.0 if txn.get("channel") != most_common_channel else 0.0
        else:
            channel_entropy = 0.0
    else:
        channel_entropy = 0.0

    return [amt_zscore, hour_anomaly, velocity, payee_new, device_new, channel_entropy]


def train_forest(background_rows: list[list[float]]) -> IsolationForest:
    """Train an IsolationForest model on normal background transaction features."""
    model = IsolationForest(n_estimators=100, random_state=42, contamination=0.05)
    model.fit(background_rows)
    return model


def normalize_scores(raw_scores: np.ndarray, raw_min: float, p90: float) -> list[int]:
    """Map raw decision scores to 0-100 risk score using min->55 / P90->0 linear mapping."""
    denom = p90 - raw_min if (p90 - raw_min) != 0 else 1.0
    normalized = (p90 - raw_scores) / denom * 55.0
    clipped = np.clip(np.round(normalized), 0, 100).astype(int)
    return [int(s) for s in clipped]


STAR_IDS = ["T-1421", "T-1187", "T-2903", "T-3376", "T-5108", "T-0742", "T-1422"]


def train_and_score_stars(users_file: Path | None = None, txns_file: Path | None = None) -> tuple[IsolationForest, list[int]]:
    """Train isolation forest and return calibrated scores for the 7 star transactions."""
    users_path = users_file or (SEED_DIR / "users.json")
    txns_path = txns_file or (SEED_DIR / "transactions.json")

    with open(users_path, "r", encoding="utf-8") as f:
        users = json.load(f)

    with open(txns_path, "r", encoding="utf-8") as f:
        all_txns = json.load(f)

    user_map = {u["id"]: u for u in users}
    txn_map = {t["txnId"]: t for t in all_txns}
    star_txns = [txn_map[t_id] for t_id in STAR_IDS if t_id in txn_map]

    # Build background
    background_rows, user_stats = build_background(users, n=2000, rng=np.random.default_rng(42))

    # Build feature rows for 7 stars
    star_feature_rows: list[list[float]] = []
    for txn in star_txns:
        u_id = txn["userId"] or txn["customerId"]
        user = user_map[u_id]
        user_txns = [t for t in star_txns if (t.get("userId") or t.get("customerId")) == u_id]
        star_feature_rows.append(feature_row(txn, user, user_stats, user_txns))

    # Fit model on background
    model = train_forest(background_rows)

    # Compute raw decision function on full set (background + stars)
    all_rows = np.vstack([background_rows, star_feature_rows])
    raw_all = model.decision_function(all_rows)

    raw_min = float(np.min(raw_all))
    p90 = float(np.percentile(raw_all, 90))

    raw_stars = model.decision_function(np.array(star_feature_rows))
    star_scores = normalize_scores(raw_stars, raw_min, p90)

    return model, star_scores


def main():
    """CLI endpoint for retraining and updating database forest scores."""
    if "--retrain" in sys.argv:
        from app import db
        print("Training Isolation Forest model on background baseline (seed=42)...")
        model, star_scores = train_and_score_stars()

        star_ids = ["T-1421", "T-1187", "T-2903", "T-3376", "T-5108", "T-0742", "T-1422"]
        print("\nCalculated Star Forest Scores:")

        conn = db._connect()
        for txn_id, f_score in zip(star_ids, star_scores):
            row = conn.execute("SELECT score, rule_points FROM alerts WHERE id = ?", (txn_id,)).fetchone()
            if row:
                rule_pts = row["rule_points"] or row["score"]
                fused = min(100, round(0.6 * rule_pts + 0.4 * f_score))
                conn.execute(
                    "UPDATE alerts SET forest_score = ?, fused_score = ? WHERE id = ?",
                    (f_score, fused, txn_id),
                )
                print(f"  {txn_id}: forest_score = {f_score}, rule_points = {rule_pts}, fused = {fused}")
            else:
                print(f"  {txn_id}: forest_score = {f_score}")

        conn.commit()
        conn.close()
        print("\nDatabase updated successfully.")


if __name__ == "__main__":
    main()
