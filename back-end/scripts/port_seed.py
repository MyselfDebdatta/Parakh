"""Generate all 6 seed JSON files for the PARAKH backend.

Ports literal data byte-identical from the engineering spec (§5.1–§5.7)
and generates pad transactions (9) and cohort rows (500) using the exact
formulas specified in §5.4 and §5.5. No randomness, no current time.
Run: python scripts/port_seed.py
"""

import json
import math
from pathlib import Path

SEED_DIR = Path(__file__).resolve().parent.parent / "seed"


def tier_of(score):
    """Return risk tier for a score: >70 red, >=40 yellow, else green."""
    if score > 70:
        return "red"
    if score >= 40:
        return "yellow"
    return "green"


# -------------------------------------------------------------------------
# §5.1 — 6 user profiles (users.json)
# -------------------------------------------------------------------------

USERS = [
    {"id": "C-4421", "name": "Sarita Verma", "phone": "+91 98447 62140",
     "bank": "SBI \u00b7 Bhubaneswar Main", "medianAmount": 4100,
     "typicalHours": "08:00\u201321:00", "knownDevices": 1, "knownPayees": 14,
     "typicalVelocity": "1.2 txns/hr"},
    {"id": "C-1187", "name": "Ramesh Iyer", "phone": "+91 98220 11473",
     "bank": "HDFC \u00b7 MG Road", "medianAmount": 7900,
     "typicalHours": "07:00\u201322:00", "knownDevices": 2, "knownPayees": 31,
     "typicalVelocity": "0.8 txns/hr"},
    {"id": "C-2903", "name": "K. Singh", "phone": "+91 98100 55384",
     "bank": "ICICI \u00b7 Sector 18", "medianAmount": 2700,
     "typicalHours": "06:00\u201323:00", "knownDevices": 1, "knownPayees": 9,
     "typicalVelocity": "0.6 txns/hr"},
    {"id": "C-3376", "name": "L. Fernandes", "phone": "+91 98338 90211",
     "bank": "Axis \u00b7 Andheri", "medianAmount": 4000,
     "typicalHours": "07:00\u201321:00", "knownDevices": 2, "knownPayees": 22,
     "typicalVelocity": "1.1 txns/hr"},
    {"id": "C-5108", "name": "M. Khan", "phone": "+91 98999 22840",
     "bank": "Kotak \u00b7 Rohini", "medianAmount": 2900,
     "typicalHours": "08:00\u201320:00", "knownDevices": 2, "knownPayees": 17,
     "typicalVelocity": "0.9 txns/hr"},
    {"id": "C-0742", "name": "A. Patil", "phone": "+91 98220 76180",
     "bank": "Canara \u00b7 Kothrud", "medianAmount": 1000,
     "typicalHours": "07:00\u201322:00", "knownDevices": 1, "knownPayees": 11,
     "typicalVelocity": "0.5 txns/hr"},
]


# -------------------------------------------------------------------------
# §5.2 — 1 call record (calls.json)
# -------------------------------------------------------------------------

CALLS = [{
    "id": "CALL-1421",
    "userId": "C-4421",
    "transcript": [
        "Caller: This is inspector Sharma from the Customs Department."
        " Your Aadhaar is linked to a money-laundering case.",
        "Sarita: What? I have not done anything. Please check again.",
        "Caller: There is a warrant out. Do not tell ANYONE about this"
        " call \u2014 not your family, nobody.",
        "Sarita: But what do I do?",
        "Caller: Everything will be clear if you transfer your savings"
        " to the safe account now. It is urgent."
        " The warrant closes at 2 PM.",
        "Sarita: Okay\u2026 which account do I send it to?",
    ],
    "flaggedLines": [0, 2, 4],
    "patterns": ["impersonation", "isolation", "urgency", "control"],
    "isCoercive": True,
    "confidence": 0.93,
    "durationSec": 431,
    "at": "14:02",
}]


# -------------------------------------------------------------------------
# §5.3 — 7 star transactions (verbatim, byte-identical)
# -------------------------------------------------------------------------

STARS = [
    # T-1421 — Sarita's coercion case (score 95, RED, pending)
    {
        "txnId": "T-1421", "userId": "C-4421",
        "customerId": "C-4421", "customerName": "Sarita Verma",
        "payee": "safeguard-account@okaxis", "payeeName": "S. Chaudhary",
        "amount": 49500, "channel": "PhonePe",
        "device": "OnePlus 12 \u00b7 new today", "hour": "14:06",
        "velocity10Min": 3, "score": 95, "tier": "red",
        "reason": "Transfer 4 min after a flagged coercive call"
                  " \u00b7 12\u00d7 usual amount",
        "reasons": [
            {"label": "Flagged coercive call 4 min before", "points": 35,
             "evidence": "CALL-1421 \u00b7 14:02 \u00b7 confidence 0.93"},
            {"label": "Payee never seen before", "points": 20,
             "evidence": "safeguard-account@okaxis \u00b7 first txn"},
            {"label": "Amount 12\u00d7 median", "points": 15,
             "evidence": "\u20b949,500 vs median \u20b94,100"},
            {"label": "Device changed today", "points": 15,
             "evidence": "OnePlus 12 \u00b7 first use 11:04"},
            {"label": "High velocity", "points": 10,
             "evidence": "3 txns in 12 min"},
        ],
        "narrative": 'A call from "Customs" kept Sarita on the line for'
            " 7 minutes, forbid contact with family, and demanded an urgent"
            ' transfer to a "safe account". Four minutes after that call was'
            " flagged coercive (0.93 confidence), a \u20b949,500 transfer to"
            " a never-seen payee from a brand-new device was attempted."
            " Every layer of the engine agrees: call linkage +35, new"
            " payee +20, amount 12\u00d7 median +15, new device +15,"
            " velocity +10.",
        "callId": "CALL-1421",
        "status": "pending", "assignee": None, "resolution": None,
        "ageDays": 0, "generatedAt": "12 Aug, 14:06",
        "confidence": "High confidence",
        "series": [10, 10, 10, 12, 15, 15, 15, 15,
                   95, 95, 95, 95, 95, 95, 95, 95, 95, 95, 95, 95],
        "txnAt": 8, "callAt": 2,
    },
    # T-1187 — Ramesh velocity burst (score 90, RED, legit)
    {
        "txnId": "T-1187", "userId": "C-1187",
        "customerId": "C-1187", "customerName": "Ramesh Iyer",
        "payee": "quickcash@ibl", "payeeName": "Moneytree Services",
        "amount": 32000, "channel": "GPay",
        "device": "Samsung M35 \u00b7 new yesterday", "hour": "23:12",
        "velocity10Min": 3, "score": 90, "tier": "red",
        "reason": "Three transfers in 9 minutes to never-seen payees"
                  " from a new device",
        "reasons": [
            {"label": "Payee-network anomaly", "points": 25,
             "evidence": "Isolation Forest \u00b7 3 new payees, 1 cluster"},
            {"label": "Payee never seen before", "points": 20,
             "evidence": "quickcash@ibl \u00b7 first txn"},
            {"label": "Amount 4\u00d7 median", "points": 15,
             "evidence": "\u20b932,000 vs median \u20b97,900"},
            {"label": "Device changed yesterday", "points": 15,
             "evidence": "Samsung M35 \u00b7 bound 11 Aug"},
            {"label": "High velocity", "points": 10,
             "evidence": "3 txns in 9 min"},
            {"label": "Outside typical hours", "points": 5,
             "evidence": "usual window 07:00\u201322:00"},
        ],
        "narrative": "Two days after a new phone was bound to the account,"
            " three transfers left in nine minutes \u2014 all to payees with"
            " no payment history and amounts near the daily ceiling. The"
            " rules explain the device change and velocity; the Isolation"
            " Forest flags the payee cluster itself as anomalous.",
        "callId": None,
        "status": "legit", "assignee": None,
        "resolution": "Marked legitimate by citizen \u00b7 11 Aug \u00b7 cleared",
        "ageDays": 1, "generatedAt": "11 Aug, 23:21",
        "confidence": "High confidence",
        "series": [12, 12, 18, 18, 24, 30, 36, 44,
                   52, 58, 64, 70, 76, 82, 86, 90, 90, 90, 90, 90],
        "txnAt": 12, "callAt": None,
    },
    # T-2903 — K. Singh refund scam (score 80, RED, reviewing)
    {
        "txnId": "T-2903", "userId": "C-2903",
        "customerId": "C-2903", "customerName": "K. Singh",
        "payee": "refund-desk@ybl", "payeeName": "QuickKart Refunds",
        "amount": 21800, "channel": "Paytm",
        "device": "Xiaomi Redmi \u00b7 known", "hour": "00:03",
        "velocity10Min": 3, "score": 80, "tier": "red",
        "reason": '"Refund" link opened in a call, amount 8\u00d7 median'
                  " at 00:03",
        "reasons": [
            {"label": "Payee-network anomaly", "points": 25,
             "evidence": "Isolation Forest \u00b7 refund-spike cluster"},
            {"label": "Payee never seen before", "points": 20,
             "evidence": "refund-desk@ybl \u00b7 first txn"},
            {"label": "Amount 8\u00d7 median", "points": 15,
             "evidence": "\u20b921,800 vs median \u20b92,700"},
            {"label": "High velocity", "points": 10,
             "evidence": "2 txns in 6 min"},
            {"label": "Outside typical hours", "points": 5,
             "evidence": "usual window 06:00\u201323:00"},
            {"label": "Channel switch", "points": 5,
             "evidence": "first Paytm use in 41 days"},
        ],
        "narrative": 'A caller posing as QuickKart customer care pushed a'
            ' "refund" link minutes earlier. The linked UPI handle has no'
            " history and the transfer amount is 8\u00d7 this customer\u2019s"
            " median, landing at 00:03 \u2014 outside any pattern this"
            " account has ever shown.",
        "callId": None,
        "status": "reviewing", "assignee": "P. Nair", "resolution": None,
        "ageDays": 2, "generatedAt": "10 Aug, 00:03",
        "confidence": "Moderate confidence",
        "series": [8, 8, 8, 12, 16, 20, 26, 32,
                   40, 46, 52, 58, 62, 68, 72, 76, 80, 80, 80, 80],
        "txnAt": 14, "callAt": None,
    },
    # T-3376 — L. Fernandes lucky-draw (score 66, YELLOW, fraud)
    {
        "txnId": "T-3376", "userId": "C-3376",
        "customerId": "C-3376", "customerName": "L. Fernandes",
        "payee": "lucky-draw@paytm", "payeeName": "MVG Promotions",
        "amount": 12300, "channel": "Paytm",
        "device": "Samsung A15 \u00b7 known", "hour": "19:44",
        "velocity10Min": 2, "score": 66, "tier": "yellow",
        "reason": "First payment to a prize-collection merchant,"
                  " 3\u00d7 usual amount",
        "reasons": [
            {"label": "Payee never seen before", "points": 20,
             "evidence": "lucky-draw@paytm \u00b7 first txn"},
            {"label": "Payee-network anomaly", "points": 16,
             "evidence": "Isolation Forest \u00b7 promo cluster"},
            {"label": "Amount 3.1\u00d7 median", "points": 15,
             "evidence": "\u20b912,300 vs median \u20b94,000"},
            {"label": "High velocity", "points": 10,
             "evidence": "2 txns in 8 min"},
            {"label": "Outside typical hours", "points": 5,
             "evidence": "usual window 07:00\u201321:00"},
        ],
        "narrative": "A soft signal: a first-ever payment to a"
            " prize-collection handle at 3\u00d7 this customer\u2019s amount."
            " No device change, no call, normal hours. This is exactly the"
            " case the YELLOW tier exists for \u2014 warn with reasons, and"
            " let the human decide.",
        "callId": None,
        "status": "fraud", "assignee": "R. Das",
        "resolution": "Confirmed by R. Das \u00b7 9 Aug"
                      " \u00b7 funds frozen before settlement",
        "ageDays": 3, "generatedAt": "9 Aug, 19:44",
        "confidence": "Moderate confidence",
        "series": [14, 14, 14, 18, 22, 28, 34, 40,
                   46, 52, 58, 62, 66, 66, 66, 66, 66, 66, 66, 66],
        "txnAt": 9, "callAt": None,
    },
    # T-5108 — M. Khan plumber (score 58, YELLOW, pending)
    {
        "txnId": "T-5108", "userId": "C-5108",
        "customerId": "C-5108", "customerName": "M. Khan",
        "payee": "plumber-khan@icici", "payeeName": "Rafiq Plumbing",
        "amount": 8600, "channel": "GPay",
        "device": "OnePlus Nord \u00b7 known", "hour": "20:12",
        "velocity10Min": 2, "score": 58, "tier": "yellow",
        "reason": "New payee, 3\u00d7 usual amount, Friday evening"
                  " \u2014 soft signal",
        "reasons": [
            {"label": "Payee never seen before", "points": 20,
             "evidence": "plumber-khan@icici \u00b7 added 20:07"},
            {"label": "Amount 3\u00d7 median", "points": 15,
             "evidence": "\u20b98,600 vs median \u20b92,900"},
            {"label": "Payee-network anomaly", "points": 8,
             "evidence": "Isolation Forest \u00b7 weak signal"},
            {"label": "High velocity", "points": 10,
             "evidence": "2 txns in 5 min"},
            {"label": "Outside typical hours", "points": 5,
             "evidence": "usual window 08:00\u201320:00"},
        ],
        "narrative": "A watch-list case: a payee added five minutes ago, an"
            " amount 3\u00d7 this customer\u2019s median, on a Friday evening"
            " when velocity is historically elevated. On its own this is"
            " weak evidence \u2014 dispatch would be premature, a warning"
            " card is exactly right.",
        "callId": None,
        "status": "pending", "assignee": None, "resolution": None,
        "ageDays": 5, "generatedAt": "7 Aug, 20:12",
        "confidence": "Low confidence",
        "series": [10, 10, 10, 14, 18, 24, 30, 36,
                   42, 48, 54, 58, 58, 58, 58, 58, 58, 58, 58, 58],
        "txnAt": 10, "callAt": None,
    },
    # T-0742 — A. Patil kirana (score 46, YELLOW, pending)
    {
        "txnId": "T-0742", "userId": "C-0742",
        "customerId": "C-0742", "customerName": "A. Patil",
        "payee": "kraft@okhdfc", "payeeName": "Kraft Kirana",
        "amount": 2400, "channel": "BHIM",
        "device": "Realme 12 \u00b7 known", "hour": "09:31",
        "velocity10Min": 1, "score": 46, "tier": "yellow",
        "reason": "New payee at 2.4\u00d7 usual amount with no history"
                  " \u2014 monitoring",
        "reasons": [
            {"label": "Payee never seen before", "points": 15,
             "evidence": "kraft@okhdfc \u00b7 first txn"},
            {"label": "Payee-network anomaly", "points": 16,
             "evidence": "Isolation Forest \u00b7 weak signal"},
            {"label": "Amount 2.4\u00d7 median", "points": 10,
             "evidence": "\u20b92,400 vs median \u20b91,000"},
            {"label": "Outside typical hours", "points": 5,
             "evidence": "usual window 07:00\u201322:00"},
        ],
        "narrative": "A retained soft signal: a new payee, an amount"
            " 2.4\u00d7 this customer\u2019s median, and a channel (BHIM)"
            " not used since June. No call, no device change, normal hours."
            " Kept in YELLOW for trend monitoring rather than review.",
        "callId": None,
        "status": "pending", "assignee": None, "resolution": None,
        "ageDays": 7, "generatedAt": "5 Aug, 09:31",
        "confidence": "Low confidence",
        "series": [6, 6, 6, 10, 14, 18, 24, 30,
                   36, 42, 46, 46, 46, 46, 46, 46, 46, 46, 46, 46],
        "txnAt": 9, "callAt": None,
    },
    # T-1422 — Sarita's plumber payment, citizen "human wins" (score 52, YELLOW)
    {
        "txnId": "T-1422", "userId": "C-4421",
        "customerId": "C-4421", "customerName": "Sarita Verma",
        "payee": "rafiq-plumbing@icici", "payeeName": "Rafiq Plumbing",
        "amount": 3200, "channel": "GPay",
        "device": "OnePlus 12 \u00b7 known", "hour": "10:12",
        "velocity10Min": 1, "score": 52, "tier": "yellow",
        "reason": "New payee, amount 1.6\u00d7 usual \u2014 warning"
                  " card only",
        "reasons": [
            {"label": "Payee never seen before", "points": 20,
             "evidence": "rafiq-plumbing@icici \u00b7 first txn"},
            {"label": "Payee-network anomaly", "points": 17,
             "evidence": "Isolation Forest \u00b7 weak signal"},
            {"label": "Amount 1.6\u00d7 median", "points": 10,
             "evidence": "\u20b93,200 vs median \u20b92,050"},
            {"label": "Outside typical hours", "points": 5,
             "evidence": "usually pays after 12:00"},
        ],
        "narrative": "A normal-ish payment that trips a few rules: the payee"
            " has never been paid, and the amount is above this"
            " customer\u2019s median. Nothing else is off. This is the"
            " payment the demo deliberately lets through \u2014 the human"
            " presses continue, and the engine learns.",
        "callId": None,
        "status": "pending", "assignee": None, "resolution": None,
        "ageDays": 1, "generatedAt": "11 Aug, 10:12",
        "confidence": "Moderate confidence",
        "series": [8, 8, 8, 12, 16, 20, 26, 32,
                   38, 44, 50, 52, 52, 52, 52, 52, 52, 52, 52, 52],
        "txnAt": 10, "callAt": None,
    },
]


# -------------------------------------------------------------------------
# §5.4 — 9 pad transactions (formula-generated)
# -------------------------------------------------------------------------

_PAD_NAMES = ["N. Bose", "P. Menon", "T. Chauhan",
              "R. Kulkarni", "S. Gupta", "A. Joshi"]

_PAD_PAYEES = [
    ("merchant-ex@ybl",    "Ex Trade Hub",      14500, "GPay"),
    ("quickmart@paytm",    "QuickMart",          9200, "Paytm"),
    ("techhelp@ibl",       "TechDesk Care",      7300, "PhonePe"),
    ("courier-desk@icici", "ShipNow Couriers",   6800, "GPay"),
    ("invest-guru@ybl",    "WealthGuru",        21950, "PhonePe"),
    ("secur-kart@okhdfc",  "SecurKart",          5100, "Paytm"),
]

_PAD_HOURS = ["22:41", "23:05", "21:18", "22:02", "20:47", "23:31"]

_GENERIC_REASONS = [
    "New payee at 4\u00d7 usual amount, 11 minutes before midnight",
    "Device changed within 24 h and amount above daily ceiling",
    "Three payments in 10 minutes to never-seen handles",
    "Night-hour transfer far above median with a new payee",
]


def build_pads():
    """Generate 9 pad alert records using the exact formulas from §5.4."""
    pads = []
    for i in range(9):
        payee, payee_name, amount, channel = _PAD_PAYEES[i % 6]
        score = 74 + ((i * 7) % 24)
        pads.append({
            "txnId": f"T-2{str(100 + i)[1:]}{i}",
            "userId": None,
            "customerId": "C-" + str(2000 + i * 911),
            "customerName": _PAD_NAMES[i % 6],
            "payee": payee, "payeeName": payee_name,
            "amount": amount, "channel": channel,
            "device": "Xiaomi Redmi \u00b7 new today" if i % 2 == 0
                      else "Vivo V40 \u00b7 known",
            "hour": _PAD_HOURS[i % 6],
            "velocity10Min": 0,
            "score": score, "tier": tier_of(score),
            "reason": _GENERIC_REASONS[i % 4],
            "reasons": [
                {"label": "Payee never seen before", "points": 20,
                 "evidence": "first txn \u00b7 clustered"},
                {"label": "Payee-network anomaly", "points": score - 40,
                 "evidence": "Isolation Forest"},
                {"label": "Amount above ceiling", "points": 10,
                 "evidence": f"{amount} vs median"},
                {"label": "High velocity", "points": 10,
                 "evidence": "2 txns in 8 min"},
            ],
            "narrative": _GENERIC_REASONS[i % 4],
            "callId": None,
            "status": "pending", "assignee": None, "resolution": None,
            "ageDays": 1 + (i % 5),
            "generatedAt": "10 Aug, 22:41",
            "confidence": "Moderate confidence" if i % 2 == 0
                          else "Low confidence",
            "series": [round(18 + (score - 18) * (k / 19))
                       for k in range(20)],
            "txnAt": 9, "callAt": None,
        })
    return pads


# -------------------------------------------------------------------------
# §5.5 — 500-row cohort (formula-generated)
# -------------------------------------------------------------------------

_FIRST = ["Sarita", "Ramesh", "Kavita", "Anil", "Meera", "Rajesh", "Priya",
          "Vikram", "Sunita", "Deepak", "Lata", "Manoj", "Asha", "Nitin",
          "Rekha", "Suresh", "Neha", "Arun", "Pooja", "Sanjay"]

_LAST = ["Verma", "Iyer", "Singh", "Fernandes", "Khan", "Patil", "Sharma",
         "Reddy", "Nair", "Joshi", "Das", "Gupta", "Menon", "Chauhan",
         "Bose", "Kulkarni"]

_BANKS = ["SBI", "HDFC", "ICICI", "Axis", "Kotak", "Canara"]


def build_cohort():
    """Generate 500 cohort rows with the exact formula from §5.5."""
    rows = []
    for i in range(500):
        p = ((i * 7919) % 1000) / 1000
        if p < 0.78:
            score = math.floor((p / 0.78) * 38)
        elif p < 0.96:
            score = 40 + math.floor(((p - 0.78) / 0.18) * 28)
        else:
            score = 71 + math.floor(((p - 0.96) / 0.04) * 28)
        rows.append({
            "id": "C-" + str(1000 + i * 7 + (i % 13)).zfill(4),
            "name": _FIRST[i % 20] + " " + _LAST[(i * 3) % 16],
            "bank": _BANKS[i % 6],
            "score": score,
        })
    return rows


# -------------------------------------------------------------------------
# §5.7 — citizen persona (citizen.json)
# -------------------------------------------------------------------------

CITIZEN = {
    "customer": USERS[0],   # C-4421 = Sarita Verma
    "balance": 184320,
    "alerts": ["T-1421", "T-1422"],
    "transactions": [
        {"id": "T-1421", "at": "12 Aug \u00b7 14:06",
         "to": "S. Chaudhary", "note": "safeguard-account@okaxis",
         "amount": -49500, "status": "intercepted"},
        {"id": "T-1422", "at": "11 Aug \u00b7 10:12",
         "to": "Rafiq Plumbing", "note": "plumber \u00b7 new payee",
         "amount": -3200, "status": "watched"},
        {"id": "T-1390", "at": "11 Aug \u00b7 09:15",
         "to": "BSNL", "note": "broadband",
         "amount": -799, "status": "clear"},
        {"id": "T-1381", "at": "10 Aug \u00b7 19:20",
         "to": "Ration Mart", "note": "groceries",
         "amount": -1840, "status": "clear"},
        {"id": "T-1367", "at": "9 Aug \u00b7 08:05",
         "to": "TechnoFab", "note": "salary credit",
         "amount": 162000, "status": "credit"},
        {"id": "T-1342", "at": "8 Aug \u00b7 21:12",
         "to": "Ola", "note": "cab",
         "amount": -312, "status": "clear"},
        {"id": "T-1330", "at": "8 Aug \u00b7 12:40",
         "to": "QuickMart", "note": "monthly provisions",
         "amount": -5400, "status": "clear"},
        {"id": "T-1301", "at": "6 Aug \u00b7 18:03",
         "to": "Jio", "note": "recharge",
         "amount": -299, "status": "clear"},
    ],
}


# -------------------------------------------------------------------------
# §5.6 — display data (display.json)
# -------------------------------------------------------------------------

def build_display(active_alerts, avg_score):
    """Construct the display.json object with computed KPI fields."""
    return {
        "analysts": ["R. Das", "P. Nair", "S. Kulkarni",
                      "A. Bose", "V. Reddy"],
        "currentAnalyst": "R. Das",
        "ticker": [
            {"time": "14:04",
             "text": "C-1187 \u00b7 \u20b91,120 \u2192 kirana@ybl",
             "tier": "green"},
            {"time": "14:04",
             "text": "C-4421 \u00b7 call verdict cached"
                     " \u00b7 COERCIVE \u00b7 0.93",
             "tier": "red"},
            {"time": "14:05",
             "text": "C-3376 \u00b7 \u20b9340 \u2192 metro@paytm",
             "tier": "green"},
            {"time": "14:05",
             "text": "C-5108 \u00b7 \u20b92,700 \u2192 flipkart@ibl",
             "tier": "green"},
            {"time": "14:06",
             "text": "C-4421 \u00b7 \u20b949,500"
                     " \u2192 safeguard-account@okaxis",
             "tier": "red"},
            {"time": "14:06",
             "text": "Rule layer \u00b7 +35 call-linkage applied",
             "tier": "yellow"},
            {"time": "14:06",
             "text": "Risk engine \u00b7 T-1421 scored 95 \u00b7 RED",
             "tier": "red"},
            {"time": "14:07",
             "text": "C-0742 \u00b7 \u20b9180 \u2192 bsnl-bill@icici",
             "tier": "green"},
            {"time": "14:07",
             "text": "C-1187 \u00b7 \u20b9850 \u2192 zomato@ybl",
             "tier": "green"},
            {"time": "14:08",
             "text": "Isolation Forest \u00b7 pass complete \u00b7 214 ms",
             "tier": "green"},
        ],
        "scriptedAlerts": [
            {"id": "T-1421",
             "snippet": "Call linkage applied \u2014 score revised to 95",
             "at": "just now"},
            {"id": "T-2903",
             "snippet": "Refund-spike cluster flagged by Isolation Forest",
             "at": "just now"},
            {"id": "T-1187",
             "snippet": "Velocity rule tripped: 3 txns in 9 minutes",
             "at": "just now"},
        ],
        "kpi": {
            "customers": 500,
            "activeAlerts": active_alerts,
            "alertsToday": 3,
            "avgScore": avg_score,
            "interceptedLakh": 11.8,
            "interceptedPct": 2.4,
            "precision": 82,
            "recall": 74,
        },
        "analytics": {
            "actioned": 12, "actionedOf": 15,
            "confirmed": 14, "falsePositives": 5,
            "interceptedLakh": 11.8, "reviewCostSavedLakh": 0.4,
            "precision": 84, "recall": 76,
            "funnel": [
                {"label": "Payments scored", "value": 2.4, "unit": "L"},
                {"label": "Auto-flagged", "value": 86, "unit": ""},
                {"label": "Human-reviewed", "value": 54, "unit": ""},
                {"label": "Fraud intercepted", "value": 23.4,
                 "unit": "\u20b9L"},
            ],
            "lossTrend": [
                {"month": "Mar", "losses": 52.1, "intercepted": 1.2},
                {"month": "Apr", "losses": 49.4, "intercepted": 3.6},
                {"month": "May", "losses": 46.8, "intercepted": 6.1},
                {"month": "Jun", "losses": 44.2, "intercepted": 8.4},
                {"month": "Jul", "losses": 42.6, "intercepted": 11.8},
                {"month": "Aug", "losses": 39.9, "intercepted": 14.7},
            ],
            "scamTypes": [
                {"type": "Digital arrest / coercion",
                 "amount": 9.1, "confirmed": 5},
                {"type": "OTP & refund",
                 "amount": 7.8, "confirmed": 3},
                {"type": "QR swap",
                 "amount": 6.4, "confirmed": 3},
                {"type": "Investment fraud",
                 "amount": 5.2, "confirmed": 2},
                {"type": "Screen sharing",
                 "amount": 4.7, "confirmed": 1},
            ],
            "model": {
                "version": "Rules v1.3 + Isolation Forest v0.4",
                "retrained": "2 Aug",
                "trainingTxns": "2,40,000",
                "nextRetrain": "9 Aug",
            },
        },
    }


# -------------------------------------------------------------------------
# Write helper
# -------------------------------------------------------------------------

def write_json(filename, data):
    """Write data to a JSON file in seed/ with ensure_ascii=False."""
    SEED_DIR.mkdir(parents=True, exist_ok=True)
    filepath = SEED_DIR / filename
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    print(f"  wrote {filepath.name} ({filepath.stat().st_size:,} bytes)")


# -------------------------------------------------------------------------
# Main
# -------------------------------------------------------------------------

def main():
    """Generate all 6 seed files and run self-verification asserts."""
    print("Generating seed files...")

    # Build generated data
    pads = build_pads()
    transactions = STARS + pads
    cohort = build_cohort()

    # Compute derived KPI values (§5.9 step 3)
    active_statuses = {"pending", "assigned", "reviewing"}
    active_alerts = sum(1 for t in transactions
                        if t["status"] in active_statuses)
    avg_score = round(sum(c["score"] for c in cohort) / len(cohort))

    display = build_display(active_alerts, avg_score)

    # Write all 6 files
    write_json("users.json", USERS)
    write_json("transactions.json", transactions)
    write_json("calls.json", CALLS)
    write_json("citizen.json", CITIZEN)
    write_json("cohort.json", cohort)
    write_json("display.json", display)

    # -----------------------------------------------------------------
    # §5.9 — Self-verification asserts
    # -----------------------------------------------------------------
    assert len(cohort) == 500, f"cohort length {len(cohort)} != 500"
    assert len(transactions) == 16, f"txn count {len(transactions)} != 16"
    assert active_alerts == 14, f"active alerts {active_alerts} != 14"

    t1421 = next(t for t in transactions if t["txnId"] == "T-1421")
    assert t1421["score"] == 95, f"T-1421 score {t1421['score']} != 95"

    assert pads[0]["txnId"] == "T-2000", \
        f"pad[0] id {pads[0]['txnId']} != T-2000"

    assert CALLS[0]["confidence"] == 0.93, \
        f"CALL-1421 confidence {CALLS[0]['confidence']} != 0.93"

    assert CITIZEN["balance"] == 184320, \
        f"citizen balance {CITIZEN['balance']} != 184320"

    print(f"\nAll 7 asserts passed.")
    print(f"  cohort: {len(cohort)} rows, avgScore={avg_score}")
    print(f"  transactions: {len(transactions)} (7 stars + 9 pads)")
    print(f"  active alerts: {active_alerts}")
    print(f"  T-1421 score: {t1421['score']}")
    print(f"  CALL-1421 confidence: {CALLS[0]['confidence']}")
    print(f"  citizen balance: {CITIZEN['balance']}")


if __name__ == "__main__":
    main()
