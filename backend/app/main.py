"""Mizan FastAPI application — the public contract for the workflow UIs.

The beneficiary UI drives intake -> documents -> run -> status. The officer UI
drives queue -> case detail -> approve/override. Decisions come from the
deterministic graph; these routes are thin orchestration + persistence.
"""
from __future__ import annotations

import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from . import __version__
from .config import get_settings
from .db import get_repository
from .graph import engine_name, run_pipeline
from .graph.stream import run_stream
from .schemas import (
    AuditEventType,
    CandidatePlan,
    CaseState,
    CaseStatus,
    Document,
    DocumentType,
    OfficerDecision,
    OutcomeType,
)
from .schemas.api import (
    DocumentTypeUploadRequest,
    DocumentUploadRequest,
    IntakeRequest,
    IntakeResponse,
    OfficerActionRequest,
    OverrideRequest,
    ProactiveAlert,
    QueueItem,
    RequiredDocumentsResponse,
    RunResponse,
)
from .policies import rules
from .services import (
    audit,
    case_factory,
    demo_scenarios,
    historical_insights_service,
    pdf_extract,
    risk_forecaster,
)
from .services.mocks import mock_document_store, registry
from .services.replay import replay_summary


@asynccontextmanager
async def lifespan(app: FastAPI):
    repo = get_repository()
    # Seed demo data on first launch so the queues are populated.
    if not repo.list_all():
        from .fixtures.loader import seed_database

        seed_database()
    yield


app = FastAPI(
    title="Mizan — Arrears Rescheduling Case Officer",
    description="Autonomous, auditable case processing for MOEI / Sheikh Zayed Housing Programme.",
    version=__version__,
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _repo():
    return get_repository()


def _load(case_id: str) -> CaseState:
    case = _repo().get(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
    return case


# ── meta ─────────────────────────────────────────────────────────────────────
@app.get("/")
def root() -> dict:
    s = get_settings()
    return {
        "app": "Mizan",
        "version": __version__,
        "engine": engine_name(),
        "llm_provider": "anthropic" if s.use_real_llm else "mock",
        "max_deduction_ratio": s.max_deduction_ratio,
        "fixtures": sorted(registry.all_fixtures().keys()),
        "synthetic_data_disclaimer": demo_scenarios.SYNTHETIC_DATA_DISCLAIMER,
    }


@app.get("/api/health")
def health() -> dict:
    # Same payload as root, but under /api so a SPA dev proxy can reach it.
    return root()


@app.get("/api/fixtures")
def list_fixtures() -> list[dict]:
    out = []
    for fid, rec in sorted(registry.all_fixtures().items()):
        pattern = demo_scenarios.SCENARIO_PATTERN_MAP.get(fid, {})
        out.append(
            {
                "fixture_id": fid,
                "beneficiary_id": rec.get("beneficiary", {}).get("beneficiary_id"),
                "name_en": rec.get("beneficiary", {}).get("full_name_en"),
                "trigger_type": rec.get("trigger_type", "application"),
                "expected_outcome": rec.get("expected_outcome"),
                "note": rec.get("scenario_note"),
                # Data-informed framing: which historical pattern this synthetic
                # case mirrors (no real identity is ever used).
                "data_informed_pattern": pattern.get("pattern"),
                "historical_basis": pattern.get("historical_basis"),
                "synthetic": True,
            }
        )
    return out


@app.get("/api/demo-scenarios")
def demo_scenarios_endpoint() -> dict:
    """How the synthetic demo cases map to real organizer-data patterns."""
    return demo_scenarios.demo_scenarios_payload()


# ── beneficiary flow ─────────────────────────────────────────────────────────
@app.post("/api/cases/intake", response_model=IntakeResponse)
def intake(req: IntakeRequest) -> IntakeResponse:
    try:
        case = case_factory.create_case(
            fixture_id=req.fixture_id,
            beneficiary_id=req.beneficiary_id,
            trigger_type=req.trigger_type,
            seed_documents=False,  # citizen uploads documents via the portal
        )
    except (ValueError, PermissionError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _repo().save(case)
    return IntakeResponse(case_id=case.case_id, status=case.status)


@app.post("/api/cases/{case_id}/documents", response_model=CaseState)
def add_documents(case_id: str, req: DocumentUploadRequest) -> CaseState:
    case = _load(case_id)
    existing = {d.document_id: d for d in case.document_inventory.documents}
    for d in req.documents:
        existing[d.document_id] = d
    case.document_inventory.documents = list(existing.values())
    audit.record(
        case,
        AuditEventType.DOCUMENT_RECEIVED,
        f"Received {len(req.documents)} uploaded document(s).",
        node="api",
        evidence_ids=[d.document_id for d in req.documents],
    )
    _repo().save(case)
    return case


@app.post("/api/cases/{case_id}/documents/by-type", response_model=CaseState)
def upload_documents_by_type(case_id: str, req: DocumentTypeUploadRequest) -> CaseState:
    """Citizen portal upload. For each requested document type, attach the
    matching record on file from the source fixture (with its readable content)
    so the assessment has data to read. Unknown types are attached as present
    but empty (they will simply not contribute extracted fields)."""
    case = _load(case_id)
    record = registry.get_by_fixture_id(case.source_fixture_id) if case.source_fixture_id else None
    on_file = {d.doc_type.value: d for d in mock_document_store.get_documents(record or {})}

    existing = {d.document_id: d for d in case.document_inventory.documents}
    attached: list[str] = []
    file_names = req.file_names or []
    for i, dtype in enumerate(req.doc_types):
        src = on_file.get(dtype)
        if src is not None:
            doc = src.model_copy(deep=True)
            if i < len(file_names) and file_names[i]:
                doc.file_name = file_names[i]
            doc.uploaded_on = audit.now_iso()[:10]
        else:
            # type not on this beneficiary's record — still register the upload
            valid = dtype in {t.value for t in DocumentType}
            doc = Document(
                document_id=f"UPL-{dtype}-{len(existing) + i}",
                doc_type=dtype if valid else DocumentType.UNKNOWN.value,
                status="present",
                file_name=(file_names[i] if i < len(file_names) else f"{dtype}.pdf"),
                uploaded_on=audit.now_iso()[:10],
            )
        existing[doc.document_id] = doc
        attached.append(doc.doc_type.value)

    case.document_inventory.documents = list(existing.values())
    audit.record(
        case,
        AuditEventType.DOCUMENT_RECEIVED,
        f"Beneficiary uploaded {len(attached)} document(s): {', '.join(attached)}.",
        node="api",
        evidence_ids=[d for d in existing],
    )
    _repo().save(case)
    return case


@app.post("/api/cases/{case_id}/documents/upload", response_model=CaseState)
async def upload_documents(case_id: str, files: list[UploadFile] = File(...)) -> CaseState:
    """Citizen portal upload — the *real* path. The browser sends the actual file
    bytes; we extract the readable text from each (pypdf for text PDFs), classify
    the document type from its name + content, and attach a Document whose
    raw_text is what was genuinely read off the file. The assessment then reads
    income and other figures from the uploaded document itself."""
    case = _load(case_id)
    existing = {d.document_id: d for d in case.document_inventory.documents}
    attached: list[str] = []

    for i, up in enumerate(files):
        data = await up.read()
        name = up.filename or f"document_{i}.pdf"
        text = pdf_extract.extract_text(data, name)
        dtype = pdf_extract.infer_doc_type(name, text)
        # No text layer (image/scanned/PNG) → mark unreadable so the confidence
        # node and the citizen both see that nothing could be parsed.
        status = "present" if text else "unreadable"
        doc = Document(
            document_id=f"UPL-{dtype.value}-{len(existing) + i}",
            doc_type=dtype,
            status=status,
            file_name=name,
            uploaded_on=audit.now_iso()[:10],
            raw_text=text or None,
        )
        existing[doc.document_id] = doc
        attached.append(f"{name} → {dtype.value}" + ("" if text else " (no text layer)"))

    case.document_inventory.documents = list(existing.values())
    audit.record(
        case,
        AuditEventType.DOCUMENT_RECEIVED,
        f"Beneficiary uploaded {len(attached)} file(s): {', '.join(attached)}.",
        node="api",
        evidence_ids=[d for d in existing],
    )
    _repo().save(case)
    return case


@app.get("/api/cases/{case_id}/documents/required", response_model=RequiredDocumentsResponse)
def required_documents(case_id: str) -> RequiredDocumentsResponse:
    """What documents this case requires, plus what's present and still missing."""
    case = _load(case_id)
    required = rules.required_documents_for(case)
    present = case.document_inventory.present_types
    missing = [t for t in required if t not in present]
    return RequiredDocumentsResponse(
        required=[t.value for t in required],
        present=[t.value for t in present],
        missing=[t.value for t in missing],
    )


@app.post("/api/cases/{case_id}/run", response_model=RunResponse)
def run_case(case_id: str) -> RunResponse:
    case = _load(case_id)
    case = run_pipeline(case)
    _repo().save(case)
    rec = case.recommendation
    return RunResponse(
        case_id=case.case_id,
        status=case.status,
        outcome_type=rec.outcome_type if rec else None,
        straight_through=rec.straight_through if rec else False,
        needs_human_review=case.needs_human_review,
        confidence=case.confidence.value if case.confidence else None,
        case=case,
    )


@app.post("/api/cases/{case_id}/run/stream")
def run_case_stream(case_id: str) -> StreamingResponse:
    """Run the pipeline node-by-node, streaming progress as Server-Sent Events.

    The UI shows a live load bar ("Auditing documents", "Checking for fraud", …)
    and, on a duplicate/active-application conflict, the request is rejected
    immediately — affordability and risk forecasting are skipped. The final
    `complete` event carries the persisted case.
    """
    case = _load(case_id)

    def event_source():
        final_case = None
        for event in run_stream(case):
            if event["type"] == "complete":
                final_case = event["case"]
            yield f"data: {json.dumps(event)}\n\n"
        # Persist whatever final state the stream produced.
        if final_case is not None:
            _repo().save(CaseState.model_validate(final_case))

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # disable proxy buffering (nginx)
        },
    )


@app.get("/api/cases/{case_id}", response_model=CaseState)
def get_case(case_id: str) -> CaseState:
    return _load(case_id)


@app.get("/api/cases", response_model=list[CaseState])
def list_cases() -> list[CaseState]:
    return _repo().list_all()


@app.get("/api/cases/{case_id}/audit")
def get_audit(case_id: str) -> dict:
    case = _load(case_id)
    return {
        "case_id": case_id,
        "sla": case.sla.model_dump() if case.sla else None,
        "events": [e.model_dump() for e in case.audit_events],
    }


# ── officer flow ─────────────────────────────────────────────────────────────
@app.get("/api/officer/queue", response_model=list[QueueItem])
def officer_queue() -> list[QueueItem]:
    out: list[QueueItem] = []
    for c in _repo().list_queue():
        out.append(
            QueueItem(
                case_id=c.case_id,
                beneficiary_name_en=c.beneficiary.full_name_en if c.beneficiary else "—",
                status=c.status,
                escalation_reason=c.escalation_reason,
                confidence=c.confidence.value if c.confidence else None,
                arrears_amount_aed=c.arrears.arrears_amount_aed if c.arrears else None,
                created_at=c.sla.created_at if c.sla else None,
            )
        )
    return out


@app.post("/api/officer/{case_id}/approve", response_model=CaseState)
def officer_approve(case_id: str, req: OfficerActionRequest) -> CaseState:
    case = _load(case_id)
    case.officer_decision = OfficerDecision(
        officer_id=req.officer_id,
        action="approve",
        notes=req.notes,
        edited_plan=case.recommendation.selected_plan if case.recommendation else None,
        decided_at=audit.now_iso(),
    )
    case.needs_human_review = False
    case.status = CaseStatus.OFFICER_APPROVED
    audit.record(
        case,
        AuditEventType.OFFICER_ACTION,
        f"Officer {req.officer_id} approved the recommendation."
        + (f" Notes: {req.notes}" if req.notes else ""),
        node="officer",
        actor=f"officer:{req.officer_id}",
    )
    _repo().save(case)
    return case


@app.post("/api/officer/{case_id}/override", response_model=CaseState)
def officer_override(case_id: str, req: OverrideRequest) -> CaseState:
    case = _load(case_id)
    income = case.beneficiary.monthly_income_aed if case.beneficiary else 0.0
    ratio = round(req.new_installment_aed / income, 4) if (req.new_installment_aed and income) else None
    edited = CandidatePlan(
        outcome_type=req.outcome_type,
        label_en=f"Officer override — {req.outcome_type.value}",
        label_ar=f"تجاوز الموظف — {req.outcome_type.value}",
        new_installment_aed=req.new_installment_aed,
        new_term_months=req.new_term_months,
        deduction_ratio=ratio,
        is_valid=True,
        rule_ids=["officer_override"],
        rationale=req.notes or "Manual officer decision.",
    )
    case.officer_decision = OfficerDecision(
        officer_id=req.officer_id,
        action="override",
        notes=req.notes,
        edited_plan=edited,
        decided_at=audit.now_iso(),
    )
    if case.recommendation:
        case.recommendation.selected_plan = edited
        case.recommendation.outcome_type = req.outcome_type
        case.recommendation.decision_label_en = edited.label_en
        case.recommendation.decision_label_ar = edited.label_ar
    case.needs_human_review = False
    case.status = CaseStatus.OFFICER_OVERRIDDEN
    audit.record(
        case,
        AuditEventType.OFFICER_ACTION,
        f"Officer {req.officer_id} overrode to {req.outcome_type.value}."
        + (f" Notes: {req.notes}" if req.notes else ""),
        node="officer",
        actor=f"officer:{req.officer_id}",
    )
    _repo().save(case)
    return case


@app.post("/api/officer/{case_id}/reject", response_model=CaseState)
def officer_reject(case_id: str, req: OfficerActionRequest) -> CaseState:
    case = _load(case_id)
    case.officer_decision = OfficerDecision(
        officer_id=req.officer_id, action="reject", notes=req.notes, decided_at=audit.now_iso()
    )
    case.needs_human_review = False
    case.status = CaseStatus.OFFICER_REJECTED
    audit.record(
        case,
        AuditEventType.OFFICER_ACTION,
        f"Officer {req.officer_id} rejected the case."
        + (f" Notes: {req.notes}" if req.notes else ""),
        node="officer",
        actor=f"officer:{req.officer_id}",
    )
    _repo().save(case)
    return case


# ── replay + proactive ───────────────────────────────────────────────────────
@app.get("/api/replay/summary")
def replay() -> dict:
    return replay_summary()


# ── organizer historical intelligence ────────────────────────────────────────
# Aggregated, anonymized insights over the organizer-provided historical dataset
# (data/RescheduleArrears.xlsx, 2023–2025). These endpoints never return raw
# identifiable records — only medians, counts, percentages, risk buckets, and
# anonymized bucketed patterns. Final policy decisions remain rule-based.
@app.get("/api/organizer-insights")
def organizer_insights() -> dict:
    """Full aggregated insight object for the Historical Intelligence dashboard."""
    return historical_insights_service.compute_insights()


@app.get("/api/organizer-insights/risk-buckets")
def organizer_risk_buckets() -> dict:
    """Overdue-month risk bucket counts and percentages."""
    return historical_insights_service.risk_buckets()


@app.get("/api/organizer-insights/policy-edge-cases")
def organizer_policy_edge_cases() -> dict:
    """Anonymized aggregate stats about 20%-deduction-cap edge cases."""
    return historical_insights_service.policy_edge_cases()


@app.get("/api/organizer-insights/sample-patterns")
def organizer_sample_patterns() -> dict:
    """Anonymized example patterns — never raw personal records."""
    return historical_insights_service.sample_patterns()


@app.get("/api/proactive-scan")
def proactive_scan() -> dict:
    """Run the organizer-calibrated risk scoring across the cleaned historical
    data and return top anonymized high-risk patterns."""
    return risk_forecaster.proactive_scan()


@app.get("/api/proactive/alerts", response_model=list[ProactiveAlert])
def proactive_alerts() -> list[ProactiveAlert]:
    out: list[ProactiveAlert] = []
    for c in _repo().list_proactive():
        if c.risk is None:
            continue
        suggested = (
            c.recommendation.decision_label_en
            if c.recommendation
            else "Early intervention recommended"
        )
        out.append(
            ProactiveAlert(
                case_id=c.case_id,
                beneficiary_name_en=c.beneficiary.full_name_en if c.beneficiary else "—",
                redefault_probability=c.risk.redefault_probability,
                drivers=c.risk.drivers,
                suggested_action=suggested,
            )
        )
    return out
