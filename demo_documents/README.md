# Document Pack

> Beneficiary document pack for the MOEI / Sheikh Zayed Housing Programme
> *AI Agent for Housing Loan Arrears Rescheduling*. All beneficiary records,
> identifiers and references in these PDFs are fictional and created for this
> prototype; entity names (employer, bank, clinic) are generic placeholders.

> **Synthetic citizen profiles generated from historical patterns in the
> organizer dataset. No real citizen identities are displayed.** These demo
> documents remain **synthetic but data-informed** — their figures and request
> mix are mapped onto real patterns from the organizer-provided historical Excel
> (`data/RescheduleArrears.xlsx`, 2023–2025), so the pack looks like production
> traffic while exposing no real personal data. See
> [docs/organizer-data.md](../docs/organizer-data.md).

## How to regenerate

```bash
python scripts/generate_demo_documents.py            # all cases
python scripts/generate_demo_documents.py --case SZHP-1001
python scripts/generate_demo_documents.py --list     # list cases
```

Regenerating overwrites the files in place. Generation is deterministic — no randomness,
no network, no system clock is used for content (all dates live in `data/demo_cases.json`).

Dependencies: `reportlab` (required), plus `arabic-reshaper` + `python-bidi` for Arabic
rendering (English still renders if they are absent).

## Using these in the portal

In the running portal, each beneficiary uploads documents in the **"2 · Documents"**
step. Upload the matching PDFs from the folder below, then run the assessment to see
the agent's decision.

## Scenarios & expected results

| Case ID | Beneficiary | Scenario | Expected status | Confidence | Human review |
|---|---|---|---|---|---|
| SZHP-1001 | Ahmed Al Mansoori | clean_approval | Approved | 0.94 | No |
| SZHP-1002 | Fatima Al Suwaidi | missing_documents | Additional Information Required | 0.41 | No |
| SZHP-1003 | Khalid Al Hosani | unemployment_hardship | Hardship Plan — Conditional Officer Review | 0.82 | Yes |
| SZHP-1004 | Mariam Al Zaabi | medical_hardship | Temporary Hardship Plan — Officer Approval Recommended | 0.86 | Yes |
| SZHP-1005 | Saeed Al Nuaimi | high_obligations | Maintain Installment — Refer to Human Officer | 0.73 | Yes |
| SZHP-1006 | Noura Al Shamsi | active_request_conflict | Blocked / Rejected | 0.98 | No |
| SZHP-1007 | Omar Al Balushi | suspicious_document | Human Review Required | 0.46 | Yes |

### What each scenario demonstrates

- **SZHP-1001** — **Clean approval** — complete docs, stable income, 18.1% deduction (under the 20% cap), within the original period → straight-through approval. *Show: salary certificate, MOEI loan statement, **final recommendation memo**, **audit trail**.*
- **SZHP-1002** — **Missing documents** — salary certificate, income statement and obligations letter absent → *Additional Information Required* with a deadline, no escalation. *Show: missing-documents notice, audit trail.*
- **SZHP-1003** — **Unemployment hardship** — verified job loss, AED 0 income, 4 dependents → defer arrears / hold installment; conditional officer review. *Show: unemployment letter, family status, memo.*
- **SZHP-1004** — **Medical hardship** — documented 6-month treatment abroad → temporary hardship plan, hold installment, reassess; officer approval recommended. *Show: medical letter, memo.*
- **SZHP-1005** — **High obligations** — 65% obligation-to-income ratio → maintain installment, refer to officer (don't aggressively raise). *Show: obligations letter, memo, audit trail.*
- **SZHP-1006** — **Active request conflict** — an active application (APP-2026-4412) is under review → blocked/rejected, no analysis. *Show: active-request record, block notice.*
- **SZHP-1007** — **Suspicious document** — salary mismatch, missing reference/QR, stale issue date, employer & Emirates-ID mismatch → human review, low confidence (0.46). *Show: suspicious salary certificate, income mismatch, **human review notice**, audit trail.*

## How this supports the AI-Agent challenge rubric

- **Autonomous data retrieval** — UAE PASS profile, MOEI loan/arrears, bank income & obligations are pulled in automatically.
- **Document validation** — Document checklist, freshness, and authenticity checks (see suspicious case).
- **20% policy enforcement** — Deduction-cap rule shown and computed in every memo & audit trail.
- **Original period constraint** — Legal Clock agent guards the original approved repayment period.
- **Active request validation** — Noura's case is blocked on an existing active application.
- **Audit trail** — Per-case audit report with agent lineage, rule results, and calculations.
- **Confidence scoring** — Every case carries a 0–1 confidence score driving escalation.
- **Human escalation** — Low-confidence / suspicious / ambiguous cases route to an officer.
- **Explainability** — Bilingual (EN + AR) reasoning on every decision document.
- **Proactive / fraud detection (bonus)** — Five concrete red flags surfaced in Omar's case.

## Generated files

Total: **70** PDFs across **7** cases. See `document_index.json` for the
machine-readable map of case → documents.

- `ahmed_clean_approval/` — 11 documents (Ahmed Al Mansoori)
- `fatima_missing_documents/` — 7 documents (Fatima Al Suwaidi)
- `khalid_unemployment_hardship/` — 11 documents (Khalid Al Hosani)
- `mariam_medical_hardship/` — 12 documents (Mariam Al Zaabi)
- `saeed_high_obligations/` — 11 documents (Saeed Al Nuaimi)
- `noura_active_request_conflict/` — 7 documents (Noura Al Shamsi)
- `omar_suspicious_document/` — 11 documents (Omar Al Balushi)
