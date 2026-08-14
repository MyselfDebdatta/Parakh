"""Shared Pydantic v2 contract for the PARAKH backend.

Defines all data models with camelCase JSON aliases and the tier_of helper.
No I/O, no side effects at import — data-only models.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict


# ---------------------------------------------------------------------------
# Shared literal types
# ---------------------------------------------------------------------------

Tier = Literal["green", "yellow", "red"]
TaskStatus = Literal["pending", "assigned", "reviewing", "fraud", "legit"]
CitizenTxnStatus = Literal["clear", "watched", "intercepted", "credit"]


# ---------------------------------------------------------------------------
# CamelCase alias generator
# ---------------------------------------------------------------------------

def to_camel(s: str) -> str:
    """Convert snake_case to camelCase for JSON serialization."""
    parts = s.split("_")
    return parts[0] + "".join(p.title() for p in parts[1:])


class CamelModel(BaseModel):
    """Base model with camelCase JSON aliases and snake_case Python fields."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


# ---------------------------------------------------------------------------
# Tier helper
# ---------------------------------------------------------------------------

def tier_of(score: int) -> str:
    """Return the risk tier for a given score: >70 red, >=40 yellow, else green."""
    if score > 70:
        return "red"
    if score >= 40:
        return "yellow"
    return "green"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class Reason(CamelModel):
    """One explainability chip: a named rule, its points, and evidence text."""

    label: str
    points: int
    evidence: str


class CallRecord(CamelModel):
    """A stored call transcript with its coercion verdict."""

    id: str
    transcript: list[str]
    flagged_lines: list[int]
    patterns: list[str]
    is_coercive: bool
    confidence: float
    duration_sec: int
    at: str


class Alert(CamelModel):
    """A flagged transaction with its risk score, reasons, and review state."""

    id: str
    customer_id: str
    customer_name: str
    payee: str
    payee_name: str
    amount: int
    channel: str
    device: str
    hour: str
    score: int
    tier: Tier
    reason: str
    reasons: list[Reason]
    narrative: str
    call_id: str | None
    status: TaskStatus
    assignee: str | None
    resolution: str | None
    age_days: int
    generated_at: str
    confidence: str
    series: list[int]
    txn_at: int
    call_at: int | None


class Customer(CamelModel):
    """A bank customer profile used for rule comparisons."""

    id: str
    name: str
    phone: str
    bank: str
    median_amount: int
    typical_hours: str
    known_devices: int
    known_payees: int
    typical_velocity: str


class Kpi(CamelModel):
    """Key performance indicators for the operator overview screen."""

    customers: int
    active_alerts: int
    alerts_today: int
    avg_score: int
    intercepted_lakh: float
    intercepted_pct: float
    precision: int
    recall: int


class HistogramBucket(CamelModel):
    """One bucket of the risk-score histogram on the overview screen."""

    bucket: str
    count: int
    tier: Tier


class TickerEvent(CamelModel):
    """One event in the live-feed ticker on the overview screen."""

    time: str
    text: str
    tier: Tier


class CitizenTxn(CamelModel):
    """One row of the citizen's transaction history."""

    id: str
    at: str
    to: str
    note: str
    amount: int
    status: CitizenTxnStatus


class CallVerdict(CamelModel):
    """The strict JSON output of the call analyzer."""

    is_coercive: bool
    confidence: float
    patterns_found: list[str]
    summary: str
