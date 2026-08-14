"""Seed-time orchestration pipeline for the PARAKH backend.

Loads all 6 seed files from seed/, populates SQLite database in dependency order,
computes and persists ML Isolation Forest + rule engine parity scores for the 7 star
transactions, preserves display truth verbatim, and prints the parity report.
"""

import json
from pathlib import Path
from app import db, engine, forest

SEED_DIR = Path(__file__).resolve().parent.parent / "seed"
STAR_IDS = ["T-1421", "T-1187", "T-2903", "T-3376", "T-5108", "T-0742", "T-1422"]
SCAM_GROUP = {"T-1421", "T-1187", "T-2903"}
SOFT_GROUP = {"T-3376", "T-5108", "T-0742", "T-1422"}


def load_seed_files() -> tuple[list[dict], list[dict], list[dict], dict, list[dict], dict]:
    """Load all 6 seed JSON files using standard library json."""
    with open(SEED_DIR / "users.json", "r", encoding="utf-8") as f:
        users = json.load(f)
    with open(SEED_DIR / "calls.json", "r", encoding="utf-8") as f:
        calls = json.load(f)
    with open(SEED_DIR / "transactions.json", "r", encoding="utf-8") as f:
        transactions = json.load(f)
    with open(SEED_DIR / "citizen.json", "r", encoding="utf-8") as f:
        citizen = json.load(f)
    with open(SEED_DIR / "cohort.json", "r", encoding="utf-8") as f:
        cohort = json.load(f)
    with open(SEED_DIR / "display.json", "r", encoding="utf-8") as f:
        display = json.load(f)

    return users, calls, transactions, citizen, cohort, display


def run():
    """Execute the full database seeding and parity scoring pipeline."""
    users, calls, transactions, citizen, cohort, display = load_seed_files()

    # Ensure tables exist
    db.init_db()

    conn = db._connect()
    cursor = conn.cursor()

    # 1. Idempotency: Clear existing rows in dependency order
    cursor.execute("DELETE FROM resolutions")
    cursor.execute("DELETE FROM alerts")
    cursor.execute("DELETE FROM transactions")
    cursor.execute("DELETE FROM calls")
    cursor.execute("DELETE FROM users")

    # 2. Insert users
    for u in users:
        cursor.execute(
            "INSERT INTO users "
            "(id, name, phone, bank, median_amount, typical_hours, "
            "known_devices, known_payees, typical_velocity) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                u["id"],
                u["name"],
                u.get("phone"),
                u.get("bank"),
                u["medianAmount"],
                u.get("typicalHours"),
                u.get("knownDevices"),
                u.get("knownPayees"),
                u.get("typicalVelocity"),
            ),
        )

    # 3. Insert calls
    for c in calls:
        cursor.execute(
            "INSERT INTO calls "
            "(id, user_id, transcript_json, flagged_lines_json, patterns_json, "
            "is_coercive, confidence, duration_sec, at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                c["id"],
                c.get("userId"),
                json.dumps(c["transcript"], ensure_ascii=False),
                json.dumps(c["flaggedLines"]),
                json.dumps(c["patterns"]),
                1 if c.get("isCoercive") else 0,
                c["confidence"],
                c["durationSec"],
                c["at"],
            ),
        )

    # 4. Insert raw transactions
    for t in transactions:
        cursor.execute(
            "INSERT INTO transactions "
            "(id, user_id, payee, payee_name, amount, channel, device, hour, generated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                t["txnId"],
                t.get("userId") or t.get("customerId"),
                t["payee"],
                t["payeeName"],
                t["amount"],
                t["channel"],
                t["device"],
                t["hour"],
                t.get("generatedAt"),
            ),
        )

    # 5. Train Isolation Forest and compute ML scores for the 7 stars
    _, star_forest_scores = forest.train_and_score_stars()
    forest_map = dict(zip(STAR_IDS, star_forest_scores))

    # 6. Map users & calls for engine scoring
    user_map = {u["id"]: u for u in users}
    user_calls: dict[str, list[dict]] = {}
    for c in calls:
        u_id = c.get("userId")
        if u_id:
            user_calls.setdefault(u_id, []).append(c)

    parity_rows = []

    # 7. Insert alerts with computed columns for 7 stars (preserve display truth)
    for t in transactions:
        t_id = t["txnId"]
        is_star = t_id in STAR_IDS

        rule_points = None
        forest_score = None
        fused_score = None

        if is_star:
            u_id = t.get("userId") or t.get("customerId")
            user_prof = user_map.get(u_id, {})
            # Adapt user profile keys for engine.score_transaction
            engine_user = {
                "median_amount": user_prof.get("medianAmount", 1000),
                "typical_hours": user_prof.get("typicalHours", "08:00\u201321:00"),
            }

            # Find matching coercive call within 5 minutes
            matched_call = None
            for call_obj in user_calls.get(u_id, []):
                if call_obj.get("isCoercive"):
                    diff = engine.minutes_between(call_obj["at"], t["hour"])
                    if 0 <= diff <= 5:
                        matched_call = call_obj
                        break

            f_score = forest_map.get(t_id, 0)
            score_res = engine.score_transaction(
                txn=t,
                user=engine_user,
                recent_coercive_call=matched_call,
                velocity_10min=t.get("velocity10Min", 0),
                forest_score=f_score,
            )

            rule_points = score_res["rules"]
            forest_score = f_score
            fused_score = score_res["fused"]

            parity_rows.append({
                "id": t_id,
                "authored": t["score"],
                "rules": rule_points,
                "forest": forest_score,
                "fused": fused_score,
                "group": "SCAM" if t_id in SCAM_GROUP else "SOFT",
            })

        cursor.execute(
            "INSERT INTO alerts "
            "(id, txn_id, customer_id, customer_name, payee, payee_name, "
            "amount, channel, device, hour, score, tier, reason, "
            "reasons_json, narrative, call_id, status, assignee, "
            "resolution, age_days, generated_at, confidence, "
            "series_json, txn_at, call_at, "
            "rule_points, forest_score, fused_score) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, "
            "?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                t["txnId"],
                t["txnId"],
                t.get("customerId") or t.get("userId"),
                t.get("customerName"),
                t["payee"],
                t["payeeName"],
                t["amount"],
                t["channel"],
                t["device"],
                t["hour"],
                t["score"],
                t["tier"],
                t["reason"],
                json.dumps(t.get("reasons", []), ensure_ascii=False),
                t.get("narrative", ""),
                t.get("callId"),
                t.get("status", "pending"),
                t.get("assignee"),
                t.get("resolution"),
                t.get("ageDays", 0),
                t.get("generatedAt"),
                t.get("confidence"),
                json.dumps(t.get("series", [])),
                t.get("txnAt"),
                t.get("callAt"),
                rule_points,
                forest_score,
                fused_score,
            ),
        )

    conn.commit()
    conn.close()

    # 8. Print Parity Report
    print("\n" + "=" * 70)
    print("PARAKH ENGINE SEED PARITY REPORT (§11 & §12)")
    print("=" * 70)
    print(f"{'ID':<8} | {'Authored':<8} | {'Rules':<6} | {'Forest':<6} | {'Fused':<6} | {'Group':<6} | {'Group-OK?':<9}")
    print("-" * 70)

    scam_fused = [r["fused"] for r in parity_rows if r["group"] == "SCAM"]
    soft_fused = [r["fused"] for r in parity_rows if r["group"] == "SOFT"]
    min_scam = min(scam_fused) if scam_fused else 0
    max_soft = max(soft_fused) if soft_fused else 0

    group_ok = min_scam > max_soft

    for r in parity_rows:
        ok_str = "PASS" if (r["group"] == "SCAM" and r["fused"] > max_soft) or (r["group"] == "SOFT" and r["fused"] < min_scam) else "FAIL"
        print(f"{r['id']:<8} | {r['authored']:<8} | {r['rules']:<6} | {r['forest']:<6} | {r['fused']:<6} | {r['group']:<6} | {ok_str:<9}")

    print("-" * 70)
    t1421_fused = next(r["fused"] for r in parity_rows if r["id"] == "T-1421")
    print(f"Invariant 1: T-1421 Fused Score >= 70 (RED): {t1421_fused} -> {'PASS' if t1421_fused >= 70 else 'FAIL'}")
    print(f"Invariant 2: Scam Group (min {min_scam}) > Soft Group (max {max_soft}): -> {'PASS' if group_ok else 'FAIL'}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    run()
