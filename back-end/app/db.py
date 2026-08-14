"""SQLite schema and query functions for the PARAKH backend.

Raw sqlite3, no ORM. Each public function opens and closes its own
connection. Parameterized SQL only. Rows returned as dicts keyed by
column name. DB path is overridable via PARAKH_DB env for test isolation.
"""

import json
import os
import sqlite3
from pathlib import Path

DB_PATH = Path(os.environ.get(
    "PARAKH_DB", str(Path(__file__).parent.parent / "parakh.db")))


# -------------------------------------------------------------------------
# Schema DDL (exact from §7 of the engine build plan)
# -------------------------------------------------------------------------

_SCHEMA = """\
CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY, name TEXT NOT NULL, phone TEXT, bank TEXT,
  median_amount INTEGER NOT NULL, typical_hours TEXT,
  known_devices INTEGER, known_payees INTEGER, typical_velocity TEXT
);

CREATE TABLE IF NOT EXISTS transactions (
  id TEXT PRIMARY KEY, user_id TEXT, payee TEXT, payee_name TEXT,
  amount INTEGER, channel TEXT, device TEXT, hour TEXT,
  generated_at TEXT, FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS alerts (
  id TEXT PRIMARY KEY, txn_id TEXT, customer_id TEXT, customer_name TEXT,
  payee TEXT, payee_name TEXT, amount INTEGER, channel TEXT, device TEXT,
  hour TEXT, score INTEGER, tier TEXT, reason TEXT,
  reasons_json TEXT,
  narrative TEXT, call_id TEXT,
  status TEXT DEFAULT 'pending', assignee TEXT, resolution TEXT,
  age_days INTEGER, generated_at TEXT, confidence TEXT,
  series_json TEXT,
  txn_at INTEGER, call_at INTEGER,
  rule_points INTEGER,
  forest_score INTEGER,
  fused_score INTEGER
);

CREATE TABLE IF NOT EXISTS calls (
  id TEXT PRIMARY KEY, user_id TEXT, transcript_json TEXT,
  flagged_lines_json TEXT, patterns_json TEXT,
  is_coercive INTEGER, confidence REAL, duration_sec INTEGER, at TEXT
);

CREATE TABLE IF NOT EXISTS resolutions (
  id INTEGER PRIMARY KEY AUTOINCREMENT, alert_id TEXT, decided_by TEXT,
  action TEXT,
  note TEXT, created_at TEXT
);
"""


# -------------------------------------------------------------------------
# Connection helper
# -------------------------------------------------------------------------

def _connect():
    """Open a connection with dict-keyed rows."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# -------------------------------------------------------------------------
# Lifecycle
# -------------------------------------------------------------------------

def init_db():
    """Create all tables if they do not exist."""
    conn = _connect()
    conn.executescript(_SCHEMA)
    conn.commit()
    conn.close()


def seed_if_empty():
    """Populate the DB from seed files if alerts table has 0 rows."""
    conn = _connect()
    count = conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
    conn.close()
    if count == 0:
        from app import seed_engine          # lazy: avoids circular ref
        seed_engine.run()


# -------------------------------------------------------------------------
# Inserts
# -------------------------------------------------------------------------

def insert_user(user):
    """Insert one user profile row."""
    conn = _connect()
    conn.execute(
        "INSERT OR REPLACE INTO users "
        "(id, name, phone, bank, median_amount, typical_hours, "
        "known_devices, known_payees, typical_velocity) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (user["id"], user["name"], user.get("phone"),
         user.get("bank"), user["median_amount"],
         user.get("typical_hours"), user.get("known_devices"),
         user.get("known_payees"), user.get("typical_velocity")))
    conn.commit()
    conn.close()


def insert_call(call):
    """Insert one call record with JSON-serialized sub-fields."""
    conn = _connect()
    conn.execute(
        "INSERT OR REPLACE INTO calls "
        "(id, user_id, transcript_json, flagged_lines_json, "
        "patterns_json, is_coercive, confidence, duration_sec, at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (call["id"], call.get("user_id"),
         call["transcript_json"], call["flagged_lines_json"],
         call["patterns_json"],
         1 if call.get("is_coercive") else 0,
         call["confidence"], call["duration_sec"], call["at"]))
    conn.commit()
    conn.close()


def insert_transaction(txn):
    """Insert one raw transaction row."""
    conn = _connect()
    conn.execute(
        "INSERT INTO transactions "
        "(id, user_id, payee, payee_name, amount, channel, device, "
        "hour, generated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (txn["id"], txn.get("user_id"), txn["payee"],
         txn["payee_name"], txn["amount"], txn["channel"],
         txn["device"], txn["hour"], txn.get("generated_at")))
    conn.commit()
    conn.close()


def insert_alert(alert_row):
    """Insert one alert row (reasons and series stored as JSON strings)."""
    conn = _connect()
    conn.execute(
        "INSERT INTO alerts "
        "(id, txn_id, customer_id, customer_name, payee, payee_name, "
        "amount, channel, device, hour, score, tier, reason, "
        "reasons_json, narrative, call_id, status, assignee, "
        "resolution, age_days, generated_at, confidence, "
        "series_json, txn_at, call_at, "
        "rule_points, forest_score, fused_score) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, "
        "?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (alert_row["id"], alert_row.get("txn_id"),
         alert_row["customer_id"], alert_row["customer_name"],
         alert_row["payee"], alert_row["payee_name"],
         alert_row["amount"], alert_row["channel"],
         alert_row["device"], alert_row["hour"],
         alert_row["score"], alert_row["tier"],
         alert_row["reason"], alert_row["reasons_json"],
         alert_row["narrative"], alert_row.get("call_id"),
         alert_row.get("status", "pending"),
         alert_row.get("assignee"), alert_row.get("resolution"),
         alert_row.get("age_days", 0), alert_row.get("generated_at"),
         alert_row.get("confidence"),
         alert_row["series_json"],
         alert_row.get("txn_at"), alert_row.get("call_at"),
         alert_row.get("rule_points"),
         alert_row.get("forest_score"),
         alert_row.get("fused_score")))
    conn.commit()
    conn.close()


# -------------------------------------------------------------------------
# Getters
# -------------------------------------------------------------------------

def get_user(user_id):
    """Fetch one user by id, or None."""
    conn = _connect()
    row = conn.execute(
        "SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_alert(alert_id):
    """Fetch one alert by id, or None."""
    conn = _connect()
    row = conn.execute(
        "SELECT * FROM alerts WHERE id = ?", (alert_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_call(call_id):
    """Fetch one call record by id, or None."""
    conn = _connect()
    row = conn.execute(
        "SELECT * FROM calls WHERE id = ?", (call_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


# -------------------------------------------------------------------------
# Listers
# -------------------------------------------------------------------------

def list_alerts(status=None, tier=None):
    """List alerts with optional status and tier filters."""
    conn = _connect()
    sql = "SELECT * FROM alerts"
    params = []
    clauses = []
    if status:
        if status == "open":
            clauses.append(
                "status IN ('pending', 'assigned', 'reviewing')")
        else:
            clauses.append("status = ?")
            params.append(status)
    if tier:
        clauses.append("tier = ?")
        params.append(tier)
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def list_calls_by_user(user_id):
    """List all call records for a given user."""
    conn = _connect()
    rows = conn.execute(
        "SELECT * FROM calls WHERE user_id = ?",
        (user_id,)).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def list_resolutions():
    """List all resolution records."""
    conn = _connect()
    rows = conn.execute("SELECT * FROM resolutions").fetchall()
    conn.close()
    return [dict(row) for row in rows]


# -------------------------------------------------------------------------
# Updaters
# -------------------------------------------------------------------------

def set_alert_status(alert_id, status, assignee=None, resolution=None):
    """Update an alert's workflow state."""
    conn = _connect()
    conn.execute(
        "UPDATE alerts SET status = ?, assignee = ?, resolution = ? "
        "WHERE id = ?",
        (status, assignee, resolution, alert_id))
    conn.commit()
    conn.close()


def add_resolution(alert_id, decided_by, action, note):
    """Record a resolution action for an alert."""
    conn = _connect()
    conn.execute(
        "INSERT INTO resolutions "
        "(alert_id, decided_by, action, note, created_at) "
        "VALUES (?, ?, ?, ?, datetime('now'))",
        (alert_id, decided_by, action, note))
    conn.commit()
    conn.close()


# -------------------------------------------------------------------------
# Converter
# -------------------------------------------------------------------------

def alert_to_json(row):
    """Map a DB alert row to the camelCase Alert contract."""
    return {
        "id": row["id"],
        "customerId": row["customer_id"],
        "customerName": row["customer_name"],
        "payee": row["payee"],
        "payeeName": row["payee_name"],
        "amount": row["amount"],
        "channel": row["channel"],
        "device": row["device"],
        "hour": row["hour"],
        "score": row["score"],
        "tier": row["tier"],
        "reason": row["reason"],
        "reasons": json.loads(row["reasons_json"])
                   if row["reasons_json"] else [],
        "narrative": row["narrative"],
        "callId": row["call_id"],
        "status": row["status"],
        "assignee": row["assignee"],
        "resolution": row["resolution"],
        "ageDays": row["age_days"],
        "generatedAt": row["generated_at"],
        "confidence": row["confidence"],
        "series": json.loads(row["series_json"])
                  if row["series_json"] else [],
        "txnAt": row["txn_at"],
        "callAt": row["call_at"],
    }
