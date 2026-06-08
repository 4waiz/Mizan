"""Build an initial CaseState from a fixture / beneficiary id.

Used by both the API intake endpoint and the fixture seeder so a case is always
constructed the same way: authenticate via UAE PASS, auto-fill the profile, load
documents on file, and start the SLA clock.
"""
from __future__ import annotations

import uuid

from ..schemas import (
    AuditEventType,
    CaseState,
    CaseStatus,
    SLAClock,
    TriggerType,
)
from . import audit
from .mocks import mock_document_store, mock_uae_pass, registry


def new_case_id() -> str:
    return f"SZHP-CASE-{uuid.uuid4().hex[:8].upper()}"


def create_case(
    *,
    fixture_id: str | None = None,
    beneficiary_id: str | None = None,
    trigger_type: TriggerType | None = None,
    case_id: str | None = None,
) -> CaseState:
    record = registry.resolve(fixture_id, beneficiary_id)
    if record is None:
        raise ValueError(
            f"No source record for fixture_id={fixture_id} beneficiary_id={beneficiary_id}"
        )

    identity = mock_uae_pass.authenticate(record)
    if not identity.get("authenticated"):
        raise PermissionError("UAE PASS authentication failed")

    profile = mock_uae_pass.get_profile(record)
    trigger = trigger_type or TriggerType(record.get("trigger_type", "application"))

    case = CaseState(
        case_id=case_id or new_case_id(),
        trigger_type=trigger,
        status=CaseStatus.INTAKE,
        beneficiary=profile,
        document_inventory=mock_document_store.build_inventory(record),
        sla=SLAClock(legacy_sla_working_days=5, created_at=audit.now_iso()),
    )
    audit.record(
        case,
        AuditEventType.CASE_CREATED,
        f"Case created for {profile.full_name_en} via UAE PASS "
        f"({trigger.value} trigger).",
        node="intake",
        evidence_ids=["uae_pass"],
    )
    return case
