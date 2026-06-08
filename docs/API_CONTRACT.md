# Mizan — API Contract

Base URL (local): `http://localhost:8000` · Interactive docs: `/docs`

All payloads are JSON. Schemas are defined in `backend/app/schemas/`. No
authentication in the prototype (mock UAE PASS identity is supplied at intake).

## Meta

### `GET /`
Health + configuration.
```json
{ "app": "Mizan", "version": "0.1.0", "engine": "langgraph",
  "llm_provider": "mock", "max_deduction_ratio": 0.2, "fixtures": ["clean_approval", ...] }
```

### `GET /api/fixtures`
List the synthetic source records (for the login dropdown / demo).

## Beneficiary flow

### `POST /api/cases/intake`
Create a case from a fixture or beneficiary id.
```json
// request
{ "fixture_id": "clean_approval", "trigger_type": "application" }
// response
{ "case_id": "SZHP-CASE-1A2B3C4D", "status": "intake" }
```

### `POST /api/cases/{id}/documents`
Add/replace uploaded documents (merged by `document_id`). Body:
`{ "documents": [ Document, ... ] }`. Returns the updated `CaseState`.

### `POST /api/cases/{id}/run`
Execute the full pipeline; persists and returns:
```json
{ "case_id": "...", "status": "auto_approved", "outcome_type": "UPDATE_INSTALLMENT",
  "straight_through": true, "needs_human_review": false, "confidence": 0.92,
  "case": { ...full CaseState... } }
```

### `GET /api/cases/{id}`
Full `CaseState`.

### `GET /api/cases`
All cases (officer/all view).

### `GET /api/cases/{id}/audit`
```json
{ "case_id": "...", "sla": { "processing_ms": 6.2, "legacy_sla_working_days": 5, ... },
  "events": [ { "event_type": "policy_check", "node": "affordability_analysis",
               "message": "SZHP-R1 → pass: ...", "rule_ids": ["SZHP-R1"],
               "evidence_ids": [...], "timestamp": "..." }, ... ] }
```

## Officer flow

### `GET /api/officer/queue`
Cases awaiting review.
```json
[ { "case_id": "...", "beneficiary_name_en": "Saeed Al Nuaimi",
    "status": "pending_human_review", "escalation_reason": "High external obligations ...",
    "confidence": 0.88, "arrears_amount_aed": 7500, "created_at": "..." } ]
```

### `POST /api/officer/{id}/approve`
`{ "officer_id": "officer-001", "notes": "..." }` → status `officer_approved`.

### `POST /api/officer/{id}/override`
```json
{ "officer_id": "officer-001", "outcome_type": "TRANSFER_ARREARS",
  "new_installment_aed": 1500, "new_term_months": 120, "notes": "..." }
```
→ status `officer_overridden`; the recommendation's selected plan is replaced.

### `POST /api/officer/{id}/reject`
`{ "officer_id": "officer-001", "notes": "..." }` → status `officer_rejected`.

## Insight

### `GET /api/replay/summary`
Runs every fixture through the pipeline and aggregates:
```json
{ "total_cases": 8, "straight_through": 5, "human_review": 3,
  "straight_through_rate": 0.625, "by_outcome": { "UPDATE_INSTALLMENT": 2, ... },
  "avg_processing_ms": 6.1, "legacy_sla_working_days": 5,
  "estimated_manual_working_days_saved": 25, "cases": [ ... ] }
```

### `GET /api/proactive/alerts`
```json
[ { "case_id": "...", "beneficiary_name_en": "Hessa Al Marri",
    "redefault_probability": 0.54, "drivers": ["currently unemployed", ...],
    "suggested_action": "Maintain installment" } ]
```

## Status values

`intake · processing · auto_approved · pending_human_review · officer_approved ·
officer_overridden · officer_rejected · info_requested · rejected`

## Outcome types

`UPDATE_INSTALLMENT · TRANSFER_ARREARS · MAINTAIN_INSTALLMENT · REQUEST_MORE_INFO ·
REJECT_ACTIVE_REQUEST · REFER_TO_OFFICER`
