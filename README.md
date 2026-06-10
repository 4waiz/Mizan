# Mizan — ميزان

> **Autonomous AI case officer for Housing Loan Arrears Rescheduling**
> Built for **MOEI / Sheikh Zayed Housing Programme**.

> **Mizan is not just a chatbot. It is a governed AI officer that combines
> organizer-provided historical arrears data, deterministic policy enforcement,
> document intelligence, explainable recommendations, and human escalation for
> exceptional cases.**

*Mizan* (Arabic: **مِيزان**, "the balance / the scale") weighs each beneficiary's
hardship against policy and affordability — instantly, consistently, and with a
full audit trail. It behaves like a government officer reviewing arrears
rescheduling requests, and escalates only the exceptional cases to a human.

---

## Table of contents

1. [Problem statement](#1-problem-statement)
2. [Solution overview](#2-solution-overview)
3. [Historical Intelligence (organizer data)](#3-historical-intelligence-organizer-data)
4. [Architecture](#4-architecture)
5. [The pipeline, node by node](#5-the-pipeline-node-by-node)
6. [Policy rules (deterministic)](#6-policy-rules-deterministic)
7. [Confidence & escalation](#7-confidence--escalation)
8. [LLM providers (mock / Groq / Anthropic)](#8-llm-providers-mock--groq--anthropic)
9. [Repository layout](#9-repository-layout)
10. [API reference](#10-api-reference)
11. [Demo fixtures & login credentials](#11-demo-fixtures--login-credentials)
12. [Setup](#12-setup)
13. [Run](#13-run)
14. [Configuration (environment variables)](#14-configuration-environment-variables)
15. [Tests](#15-tests)
16. [Deployment](#16-deployment)
17. [Trade-offs](#17-trade-offs)
18. [Future improvements](#18-future-improvements)

---

## 1. Problem statement

When a Sheikh Zayed Housing Programme beneficiary falls into arrears and requests
a rescheduling of their housing loan, the case today moves through a **manual,
~5 working-day** review: an officer pulls the loan record, checks income and
documents, validates against policy, drafts repayment options, and writes a
recommendation. The process is slow, inconsistent between officers, hard to
audit, and does not scale.

## 2. Solution overview

Mizan converts that 5-day manual review into a **near-instant, explainable,
rule-compliant recommendation**:

- A **deterministic policy engine** ([`policies/rules.py`](backend/app/policies/rules.py))
  enforces the hard rules in code (20% income cap, original-period cap,
  active-request conflict, document completeness, hardship evidence, high
  obligations, suspicious documents) — *never* free-form LLM reasoning.
- A **candidate-plan solver** ([`policies/solver.py`](backend/app/policies/solver.py))
  generates concrete repayment options (update installment / transfer arrears /
  maintain / request info / reject / refer), filters out anything that violates a
  rule, and ranks the survivors by **sustainability** and **citizen burden**.
- A **confidence score** ([`scoring/confidence.py`](backend/app/scoring/confidence.py))
  decides straight-through vs. human review. Anything ambiguous, suspicious,
  low-confidence, or hardship-sensitive is **escalated to an officer** with a
  written reason and the supporting evidence.
- Every step writes a typed **audit event** with `rule_ids` and `evidence_ids`,
  and produces a **bilingual (EN/AR) rationale memo**.
- LLMs are used **only** for document field extraction, document classification,
  bilingual memo generation, and exception summarisation — always returning
  **Pydantic-validated structured output**. With no API key, a deterministic
  `MockLLM` keeps the whole app reproducible.

The orchestration is a **LangGraph** state machine over a single shared,
strongly-typed `CaseState`. If `langgraph` is not installed, an equivalent
in-process sequential runner drives the **same node functions** over the **same
state**, so the app always runs (`engine` reports `langgraph` or
`sequential-fallback`).

## 3. Historical Intelligence (organizer data)

Mizan reads the **organizer-provided historical arrears Excel** placed at
[`data/RescheduleArrears.xlsx`](data/RescheduleArrears.xlsx) (real 2023–2025
rescheduling cases, 3 sheets, ~2158 rows). This dataset is used **only** for:

- **Aggregated insights** — medians, counts, and percentages that describe how
  arrears cases actually behave (salary, overdue amounts, overdue months, EMI
  changes, request-type split, approval durations).
- **Risk calibration** — historical overdue-month distributions calibrate the
  risk-score thresholds and the risk buckets used across the engine.
- **Demo realism** — synthetic demo documents remain fully synthetic, but are
  now **data-informed**: their figures are mapped to real organizer patterns so
  the demo looks like production traffic (see `/api/demo-scenarios`).
- **Policy edge-case analysis** — e.g. how often current installments already
  exceed the **20% deduction cap**, surfacing where automation matters most.

Privacy is preserved end to end. **Raw personal data is never exposed in the
UI** — only aggregates, risk buckets, and anonymized/banded patterns leave the
backend. Identifier columns are **dropped at ingestion** before any aggregation.
Crucially, **final decisions are governed by the deterministic policy rules, not
by historical averages** — the historical layer calibrates and explains, it does
not decide.

See [docs/organizer-data.md](docs/organizer-data.md) for the full data
documentation (columns, cleaning, anonymization, and the verified metrics), and
the **Historical Intelligence dashboard** at `/insights` for the live view.

**Run the historical-insights pipeline** to (re)generate the processed artifacts:

```bash
python scripts/analyze_organizer_excel.py --input "data/RescheduleArrears.xlsx"
# writes: data/processed/organizer_insights.json
#         data/processed/risk_buckets.json
#         data/processed/proactive_scan.json
```

> If `data/RescheduleArrears.xlsx` is absent, the organizer endpoints respond
> gracefully with `{ "loaded": false }` and the rest of the app runs unchanged.

## 4. Architecture

```
                       ┌──────────────────────────────────────────────┐
  Beneficiary UI ─────▶│  FastAPI  (/api/cases, /api/officer, ...)     │
  (React + Vite)       │                                               │
  Officer UI ─────────▶│   builds & runs the LangGraph case pipeline    │
                       └───────────────────────┬──────────────────────┘
                                               │  shared typed CaseState
       ┌───────────────────────────────────────┼───────────────────────────────┐
       ▼            ▼            ▼              ▼            ▼          ▼         ▼
  intake_and   document_   fraud_and_     affordability  risk_     policy_   rationale_
  _retrieve    audit       dedupe_check   _analysis      forecast  solver    generator
                                                                      │
                                            human_review_gate ◀───────┘────▶ finalize_case
       │ mocks: UAE PASS · MOEI loan · salary · bank · doc store
       └─ deterministic: policies/rules.py · policies/solver.py · scoring/*
```

- **Frontend (primary):** React + Vite + TypeScript SPA in [`web/`](web/) — the
  "Paper" design system. Vite proxies `/api` to the backend on `:8000` in dev.
- **Frontend (legacy/secondary):** a Streamlit app in [`streamlit_app/`](streamlit_app/)
  that talks to the same API.
- **Backend:** FastAPI in [`backend/app/`](backend/app/) over a LangGraph
  pipeline plus deterministic `policies/` and `scoring/`.
- **Persistence:** SQLite via a thin repository (Postgres-ready), auto-seeded
  with the demo fixtures on first launch.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and
[docs/DECISION_LOGIC.md](docs/DECISION_LOGIC.md) for the full design.

## 5. The pipeline, node by node

The graph (`backend/app/graph/builder.py`) runs these nodes in order over a
single `CaseState`:

| # | Node | Responsibility |
|---|------|----------------|
| 1 | `intake_and_retrieve` | Pull the beneficiary + loan record (mock UAE PASS / MOEI loan system / salary / bank connectors). |
| 2 | `document_audit` | Classify and read the uploaded documents; extract income and other fields (LLM or MockLLM, structured output). |
| 3 | `fraud_and_dedupe_check` | Detect duplicate/active applications and suspicious-document signals. A duplicate/active conflict short-circuits to immediate reject (affordability & risk skipped). |
| 4 | `affordability_analysis` | Compute income, obligations, data completeness, affordable installment headroom. |
| 5 | `risk_forecast` | Transparent re-default risk score, calibrated on the historical overdue-month distribution. |
| 6 | `policy_solver` | Generate candidate plans, drop rule-violating ones, rank survivors by sustainability and burden. |
| 7 | `human_review_gate` | Set `needs_human_review` from confidence + hard escalation triggers. |
| 8 | `rationale_generator` | Write the bilingual (EN/AR) rationale memo. Both auto and escalated branches produce a memo. |
| 9 | `finalize_case` | Persist the final outcome, status, and audit trail. |

The `/api/cases/{id}/run/stream` endpoint emits these as **Server-Sent Events**
so the UI shows a live progress bar ("Auditing documents", "Checking for
fraud", …); the final `complete` event carries the persisted case.

## 6. Policy rules (deterministic)

Enforced in code with stable `rule_id`s ([`policies/rules.py`](backend/app/policies/rules.py)):

| Rule | Meaning |
|------|---------|
| **SZHP-R1** | Monthly deduction must not exceed **20%** of beneficiary income (`MIZAN_MAX_DEDUCTION_RATIO`, default `0.20`). |
| **SZHP-R2** | Proposed schedule must not exceed the original approved repayment period. |
| **SZHP-R3** | An existing active application blocks a new straight-through decision. |
| **SZHP-R4** | All required documents must be present and current (salary certificate freshness window: **90 days**). |
| **SZHP-R5** | Arrears transfer / postponement requires a valid hardship justification (termination letter for unemployment, medical report for medical hardship). |
| **SZHP-R6** | High external obligations (≥ **50%** of income) reduce aggressiveness and may trigger review. |
| **SZHP-R7** | Suspicious documents are **referred to a human, never auto-rejected**. |

Required documents depend on the situation: Emirates ID always; salary
certificate + bank statement if employed/self-employed; termination letter if
unemployment hardship; medical report if medical hardship.

## 7. Confidence & escalation

`scoring/confidence.py` blends five components into a single `[0,1]` score:

| Component | Weight |
|-----------|--------|
| Data completeness | 0.20 |
| Document-extraction confidence | 0.15 |
| Fraud cleanliness | 0.25 |
| Policy clarity (FAILs/WARNs reduce it) | 0.20 |
| Solver decisiveness (gap between best & 2nd-best plan) | 0.20 |

Bands: **high** ≥ 0.75, **medium** ≥ 0.5, else **low**. The straight-through
threshold is `MIZAN_AUTO_APPROVE_CONFIDENCE` (default `0.75`). Any hard
escalation trigger (e.g. suspicious document, policy failure) routes to the
officer queue regardless of score.

## 8. LLM providers (mock / Groq / Anthropic)

Configured via `LLM_PROVIDER` / `MIZAN_LLM_PROVIDER` ([`config.py`](backend/app/config.py)):

- **`mock`** (default) — deterministic `MockLLM`. No key, fully reproducible.
- **`groq`** — live inference (`langchain-groq`), default model
  `llama-3.3-70b-versatile`. Needs `GROQ_API_KEY`.
- **`anthropic`** — live inference (`langchain-anthropic`), default model
  `claude-opus-4-8`. Needs `ANTHROPIC_API_KEY`.

A real provider is used **only when its key is present**; otherwise the app
silently falls back to `MockLLM`. The active provider/model is surfaced at
`GET /` and `GET /api/health`.

## 9. Repository layout

```
backend/
  app/
    main.py              FastAPI app + all routes
    config.py            settings (env-driven; LLM provider/model, policy knobs)
    __init__.py          __version__
    schemas/             Pydantic v2 models — the shared CaseState + all sub-models
                         (api, analysis, beneficiary, case, documents, enums, loan)
    graph/               LangGraph spine: state, builder, router, stream (SSE), nodes/
    policies/            rules.py (hard caps) + solver.py (candidate plans)
    scoring/             affordability.py, risk.py, confidence.py
    data/                organizer_dataset.py (organizer Excel ingestion, PII dropped at load)
    services/            llm.py (MockLLM + provider wiring), audit.py, explain.py,
                         case_factory.py, demo_scenarios.py, replay.py, pdf_extract.py,
                         historical_insights_service.py (aggregates: medians/counts/buckets),
                         risk_forecaster.py (transparent risk scoring calibrated on history),
                         mocks/ (uae_pass, moei_loan_system, salary_verifier,
                                 bank_verifier, document_store, registry)
    db/                  SQLite store (Postgres-ready repository pattern)
    fixtures/            9 synthetic JSON cases + loader (auto-seeds on startup)
  tests/                 pytest suite (9 test modules)
  requirements.txt       pinned backend deps
  .python-version        3.12.7
scripts/
  analyze_organizer_excel.py   ingest data/RescheduleArrears.xlsx → data/processed/*.json
  generate_demo_documents.py   build synthetic, data-informed demo documents
data/
  RescheduleArrears.xlsx       organizer historical arrears Excel (2023–2025)
  demo_cases.json              demo case definitions
  processed/                   generated insights (aggregates only, no PII)
demo_documents/                synthetic per-beneficiary document sets + index
web/                           React + Vite + TypeScript SPA ("Paper" design system)
  src/pages/                   Home, CitizenLogin, OfficerLogin, NewRequest, MyCase,
                               OfficerQueue, OfficerCase, Proactive, Replay,
                               Insights (/insights), Telemetry
  src/api.ts, session.ts, i18n.tsx, App.tsx, components/, styles.css
  vite.config.ts               dev server :5173, proxies /api → :8000
streamlit_app/                 legacy Streamlit UI (same API): pages 1–7
docs/                          ARCHITECTURE, DECISION_LOGIC, API_CONTRACT, DEMO_SCRIPT,
                               SLIDES_OUTLINE, organizer-data.md
.github/workflows/keep-alive.yml   pings Render /api/health every 10 min (free-tier warm-keep)
Dockerfile · docker-compose.yml · render.yaml · vercel.json · Makefile · package.json
```

## 10. API reference

Base URL: `http://localhost:8000`. Interactive docs at `/docs`.

### Meta

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | App info: version, engine, LLM provider/model/live, max deduction ratio, fixtures, disclaimer. |
| GET | `/api/health` | Same payload as `/`, under `/api` for the dev proxy. |
| GET | `/api/fixtures` | Demo fixtures with expected outcomes and the historical pattern each mirrors. |
| GET | `/api/demo-scenarios` | How the synthetic demo cases map to real organizer-data patterns. |

### Beneficiary flow

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/cases/intake` | Create a case from a fixture/beneficiary. |
| POST | `/api/cases/{id}/documents` | Attach pre-built `Document` records. |
| POST | `/api/cases/{id}/documents/by-type` | Attach the on-file document(s) for the given types. |
| POST | `/api/cases/{id}/documents/upload` | **Real upload**: browser sends bytes; pypdf extracts text, type is inferred, raw text attached. |
| GET | `/api/cases/{id}/documents/required` | Required / present / missing document types. |
| POST | `/api/cases/{id}/run` | Run the full pipeline; returns outcome, straight-through, confidence, case. |
| POST | `/api/cases/{id}/run/stream` | Run node-by-node, streaming progress as **SSE**. |
| GET | `/api/cases/{id}` | Get one case. |
| GET | `/api/cases` | List all cases. |
| GET | `/api/cases/{id}/audit` | SLA + full typed audit event log. |

### Officer flow

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/officer/queue` | Cases awaiting human review. |
| POST | `/api/officer/{id}/approve` | Approve the recommendation. |
| POST | `/api/officer/{id}/override` | Override with an edited plan (recomputes deduction ratio). |
| POST | `/api/officer/{id}/reject` | Reject the case. |

### Replay, proactive & organizer intelligence (aggregates only — no PII)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/replay/summary` | Replay/backtest summary over fixtures. |
| GET | `/api/proactive/alerts` | Proactive re-default alerts with drivers + suggested action. |
| GET | `/api/proactive-scan` | Organizer-calibrated risk scan; top anonymized high-risk patterns. |
| GET | `/api/organizer-insights` | Full aggregated insight object for the dashboard. |
| GET | `/api/organizer-insights/risk-buckets` | Overdue-month risk-bucket counts and percentages. |
| GET | `/api/organizer-insights/policy-edge-cases` | 20%-cap and policy edge-case stats. |
| GET | `/api/organizer-insights/sample-patterns` | Anonymized/banded sample patterns. |

See [docs/API_CONTRACT.md](docs/API_CONTRACT.md) for full request/response shapes.

## 11. Demo fixtures & login credentials

The backend seeds **9 synthetic fixtures** (`backend/app/fixtures/cases/`):

`01_clean_approval` · `02_missing_documents` · `03_unemployment_hardship` ·
`04_medical_hardship` · `05_high_obligations` · `06_active_request_conflict` ·
`07_suspicious_document` · `08_proactive_alert` · `09_duplicate_application`.

**Demo logins** (intentionally simple — synthetic data only):

| Role | Username | Password | Maps to |
|------|----------|----------|---------|
| Citizen | `ahmed` | `123` | clean approval (documents pre-seeded) |
| Citizen | `fatima` | `123` | unemployment hardship |
| Citizen | `mariam` | `123` | missing documents |
| Citizen | `saeed` | `123` | duplicate application (rejected at dedupe) |
| Officer | `OfficerAwaiz` | `Officer123` | officer dashboard |

Citizens can also "sign in with UAE PASS" (mocked). Ahmed arrives with his
documents already on file so judges can go straight to "Start assessment";
everyone else uploads via the portal.

## 12. Setup

Requires **Python 3.12** (pinned to `3.12.7`) and **Node 18+**. If you don't
have Python 3.12:

- Windows: [python.org/downloads](https://www.python.org/downloads/) (tick
  *"Add python.exe to PATH"*), or `winget install Python.Python.3.12`.
- macOS: `brew install python@3.12`  ·  Linux: `apt install python3.12 python3.12-venv`

```bash
# from the repo root
python -m venv .venv
# Windows:      .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate
pip install -r backend/requirements.txt
```

> The app runs fully **without** any API key — `MockLLM` provides deterministic
> extraction and memos. Add a provider + key to `.env` only for live model output.

## 13. Run

**Two tiers, one command** (from the repo root):

```bash
npm run setup        # one-time: create .venv, install backend + web deps
npm run dev:all      # backend :8000 + React UI :5173 together (concurrently)
```

Or run each tier yourself:

```bash
# Terminal 1 — backend API (http://localhost:8000, docs at /docs)
make backend         # or: uvicorn app.main:app --reload --app-dir backend

# Terminal 2 — React workflow UI (http://localhost:5173)
cd web && npm install && npm run dev
```

Vite proxies `/api` to the backend on `:8000`. For a production build set
`VITE_API_BASE` to a non-proxied backend, then `npm run build` (output:
`web/dist`). See [web/README.md](web/README.md).

**Open** `http://localhost:5173`, and the Historical Intelligence dashboard at
`http://localhost:5173/insights`.

Seed the DB manually (it also auto-seeds on first startup):

```bash
make seed            # or: cd backend && python -m app.fixtures.loader
```

**Legacy Streamlit UI** (optional, same API):

```bash
make frontend        # streamlit run streamlit_app/app.py  (http://localhost:8501)
```

**Docker (one shot):**

```bash
docker-compose up --build
# backend :8000 · React UI :8080 · legacy Streamlit :8501
```

## 14. Configuration (environment variables)

All settings are env-driven with safe defaults. Both `MIZAN_`-prefixed and the
standard unprefixed forms are accepted where noted. Put them in `.env`.

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` / `MIZAN_LLM_PROVIDER` | `mock` | `mock` · `groq` · `anthropic`. |
| `LLM_MODEL` / `MIZAN_LLM_MODEL` | `claude-opus-4-8` | Anthropic model name. |
| `MIZAN_GROQ_MODEL` | `llama-3.3-70b-versatile` | Groq model name. |
| `ANTHROPIC_API_KEY` / `MIZAN_ANTHROPIC_API_KEY` | — | Enables the Anthropic provider. |
| `GROQ_API_KEY` / `MIZAN_GROQ_API_KEY` | — | Enables the Groq provider. |
| `MIZAN_DATABASE_URL` | `sqlite:///./mizan.db` | DB connection string. |
| `MIZAN_MAX_DEDUCTION_RATIO` | `0.20` | SZHP-R1 income-deduction cap. |
| `MIZAN_SLA_WORKING_DAYS` | `5` | SLA target used in audit. |
| `MIZAN_AUTO_APPROVE_CONFIDENCE` | `0.75` | Straight-through confidence threshold. |
| `MIZAN_API_BASE_URL` | `http://localhost:8000` | Backend base for the Streamlit client. |
| `VITE_API_BASE` | — | Backend base for a non-proxied web build. |

## 15. Tests

```bash
make test            # or: pytest backend/tests -q  (pytest.ini sets pythonpath=backend)
```

The suite covers the happy path, missing documents, active/duplicate requests,
policy caps, human review, organizer insights, replay, and that the engine is
**fully deterministic with no API key**.

## 16. Deployment

- **Backend → Render** ([`render.yaml`](render.yaml)): Python web service,
  `rootDir: backend`, pinned `PYTHON_VERSION=3.12.7`, health check
  `/api/health`, SQLite on the ephemeral disk (auto-seeds on every boot).
- **Frontend → Vercel** ([`vercel.json`](vercel.json)): builds `web/`, outputs
  `web/dist`, SPA rewrites all non-`/api` paths to `index.html`.
- **Keep-alive** ([`.github/workflows/keep-alive.yml`](.github/workflows/keep-alive.yml)):
  pings the Render `/api/health` every 10 minutes so the free-tier backend
  doesn't cold-start during a demo. Set repo Actions variable `BACKEND_URL`.
- **Docker**: `Dockerfile` (backend image, Python 3.12-slim) +
  `docker-compose.yml` (backend + React + legacy Streamlit).

## 17. Trade-offs

- **React + Vite UI on a UI-agnostic API**: the engine is fully decoupled from
  the front end — any client speaking the same FastAPI contract works (the
  legacy Streamlit UI is proof).
- **No-interest loan math**: Sheikh Zayed housing assistance is profit-free, so
  the solver uses simple principal arithmetic. An interest/profit term can be
  injected into `policies/solver.py` without changing the node graph.
- **SQLite, not Postgres**: zero-setup for local demo. All DB access goes
  through a thin repository so a Postgres driver swaps in cleanly.
- **scikit-learn risk model** is trained on a small *synthetic, seeded* dataset
  at startup — illustrative, deterministic, and falls back to a transparent
  heuristic if sklearn is absent. Not a production credit model.
- **LangGraph with a sequential fallback**: the same nodes run either way, so a
  missing `langgraph` install never breaks the app.
- **Decisions are deterministic, LLMs are advisory**: the recommendation can
  never be hallucinated; the LLM only reads documents and writes prose.

## 18. Future improvements

- Real UAE PASS OIDC + MOEI core-banking connectors behind the same mock interfaces.
- Postgres + Alembic migrations; event-sourced audit log.
- Officer feedback loop to retrain the risk model on real (masked) outcomes.
- Document OCR pipeline feeding the extraction node (for scanned/image uploads).
- Policy versioning so historical cases replay against the rules in force at the time.
- Full Arabic i18n coverage across every page (currently a partial dictionary).

---

*Synthetic data only. No real personal identifiers are used anywhere in this repo.*
</content>
</invoke>
