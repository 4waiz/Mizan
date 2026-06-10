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

## Historical Intelligence (organizer data)

Read-only endpoints backed by the organizer-provided historical Excel
(`data/RescheduleArrears.xlsx`, 2023–2025), surfaced on the `/insights`
dashboard. **All five return aggregates only — no PII / no raw rows.**
Identifier columns are dropped at ingestion; only medians, counts, percentages,
risk buckets, and banded anonymized patterns are exposed. These calibrate risk
and demo realism — they do **not** make policy decisions.

> **Graceful degradation.** If `data/RescheduleArrears.xlsx` is absent (or not
> yet processed), every endpoint responds with HTTP 200 and
> `{ "loaded": false }` so the rest of the app runs unchanged.

### `GET /api/organizer-insights`
Top-line aggregated metrics (volume, medians, request-type split, approval
duration). Aggregates only.
```json
{ "loaded": true, "raw_records": 2158, "usable_records": 1933, "dropped": 225,
  "years": [2023, 2024, 2025],
  "medians": { "salary_aed": 26205, "overdue_amount_aed": 43119,
               "overdue_months": 11, "current_emi_aed": 3751, "new_emi_aed": 1004,
               "current_emi_salary_ratio": 0.15, "approval_duration_days": 11 },
  "request_type_split": { "UPDATE_INSTALLMENT": { "pct": 0.867, "count": 1676 },
                          "TRANSFER_ARREARS":   { "pct": 0.133, "count": 257 } } }
```

### `GET /api/organizer-insights/risk-buckets`
Overdue-month risk-bucket distribution (Low 0–2, Medium 3–6, High 7–12,
Severe 13–24, Critical 25+). Aggregates only.
```json
{ "loaded": true,
  "buckets": [ { "name": "Low", "overdue_months": "0-2", "pct": 0.131 },
               { "name": "Medium", "overdue_months": "3-6", "pct": 0.214 },
               { "name": "High", "overdue_months": "7-12", "pct": 0.187 },
               { "name": "Severe", "overdue_months": "13-24", "pct": 0.222 },
               { "name": "Critical", "overdue_months": "25+", "pct": 0.246 } ] }
```

### `GET /api/organizer-insights/policy-edge-cases`
Policy edge-case statistics — chiefly how often installments breach the 20%
deduction cap. Aggregates only.
```json
{ "loaded": true,
  "deduction_cap": 0.20,
  "current_emi_over_cap": { "pct": 0.130, "count": 252, "of": 1933 },
  "new_emi_over_cap":     { "pct": 0.030, "count": 57,  "of": 1873 } }
```

### `GET /api/organizer-insights/sample-patterns`
Anonymized / banded sample patterns (no identifiers; values bucketed into
bands). Aggregates only.
```json
{ "loaded": true,
  "patterns": [ { "salary_band": "20k-30k", "overdue_band": "13-24m",
                  "request_type": "UPDATE_INSTALLMENT", "deduction_band": "10-20%" } ] }
```

### `GET /api/proactive-scan`
Historical high-risk rows for proactive outreach, by risk band. Aggregates only.
```json
{ "loaded": true, "high_risk_rows": 406,
  "bands": { "Critical": 45, "Severe": 361, "High": 463, "Medium": 641, "Low": 423 } }
```

## Status values

`intake · processing · auto_approved · pending_human_review · officer_approved ·
officer_overridden · officer_rejected · info_requested · rejected`

## Outcome types

`UPDATE_INSTALLMENT · TRANSFER_ARREARS · MAINTAIN_INSTALLMENT · REQUEST_MORE_INFO ·
REJECT_ACTIVE_REQUEST · REFER_TO_OFFICER`
