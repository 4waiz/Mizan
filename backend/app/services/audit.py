"""Audit-trail helpers. Every node records a typed AuditEvent so the whole
decision is reconstructable after the fact."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from ..schemas import AuditEvent, AuditEventType, CaseState


def now_iso() -> str:
    # Microsecond precision so the SLA clock can show real sub-second processing.
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def new_id(prefix: str = "evt") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def record(
    state: CaseState,
    event_type: AuditEventType,
    message: str,
    *,
    node: str | None = None,
    rule_ids: list[str] | None = None,
    evidence_ids: list[str] | None = None,
    actor: str = "system",
) -> AuditEvent:
    event = AuditEvent(
        event_id=new_id(),
        event_type=event_type,
        node=node,
        message=message,
        rule_ids=rule_ids or [],
        evidence_ids=evidence_ids or [],
        timestamp=now_iso(),
        actor=actor,
    )
    state.add_audit(event)
    return event
