# Mizan — ميزان

> **Autonomous AI case officer for Housing Loan Arrears Rescheduling**
> Built for **MOEI / Sheikh Zayed Housing Programme**.

*Mizan* (Arabic: **مِيزان**, "the balance / the scale") weighs each beneficiary's
hardship against policy and affordability — instantly, consistently, and with a
full audit trail. It is **not a chatbot**. It is a governed, straight-through
case-processing engine that behaves like a government officer reviewing arrears
rescheduling requests, and escalates only the exceptional cases to a human.

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

- A **deterministic policy engine** enforces the hard rules in code
  (20% income cap, original-period cap, active-request conflict, document
  completeness) — *never* free-form LLM reasoning.
- A **candidate-plan solver** generates concrete repayment options
  (update installment / transfer arrears / maintain / request info / reject /
  refer), filters out anything that violates a rule, and ranks the survivors by
  **sustainability** and **citizen burden**.
- A **confidence score** decides straight-through vs. human review. Anything
  ambiguous, suspicious, low-confidence, or hardship-sensitive is **escalated to
  an officer** with a written reason and the supporting evidence.
- Every step writes a typed **audit event** with `rule_ids` and `evidence_ids`,
  and produces a **bilingual (EN/AR) rationale memo**.
- LLMs are used **only** for document field extraction, document classification,
  bilingual memo generation, and exception summarisation — always returning
  **Pydantic-validated structured output**. With no API key, a deterministic
  `MockLLM` keeps the whole app reproducible.

The orchestration is a **LangGraph** state machine over a single shared,
strongly-typed `CaseState`.

## 3. Architecture

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

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and
[docs/DECISION_LOGIC.md](docs/DECISION_LOGIC.md) for the full design.

## 4. Repository layout

```
backend/
  app/
    main.py          FastAPI app + routes
    config.py        settings (env-driven)
    schemas/         Pydantic v2 models (the shared CaseState + all sub-models)
    graph/           LangGraph spine: state, builder, router, nodes/
    policies/        rules.py (hard caps) + solver.py (candidate plans)
    scoring/         affordability.py, risk.py, confidence.py
    services/        llm.py (MockLLM), audit.py, explain.py, mocks/ connectors
    db/              SQLite store (Postgres-ready repository pattern)
    fixtures/        synthetic JSON cases (8 scenarios) + loader
  tests/             pytest suite
web/                 React + Vite + TypeScript workflow UI ("Paper" design system)
docs/                ARCHITECTURE, DECISION_LOGIC, API_CONTRACT, DEMO_SCRIPT, SLIDES_OUTLINE
```

## 5. Setup

Requires **Python 3.12** (and `pip`). If you don't have it:
- Windows: install from [python.org/downloads](https://www.python.org/downloads/)
  (tick *"Add python.exe to PATH"*), or `winget install Python.Python.3.12`.
- macOS: `brew install python@3.12`  ·  Linux: `apt install python3.12 python3.12-venv`

```bash
# from the repo root
python -m venv .venv
# Windows:  .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r backend/requirements.txt

cp .env.example .env        # optional: add ANTHROPIC_API_KEY to use a real model
```

> The app runs fully **without** any API key — `MockLLM` provides deterministic
> extraction and memos. Add `ANTHROPIC_API_KEY` to `.env` only if you want live
> model output.

## 6. Run

Two commands, two terminals (or use the Makefile / docker-compose):

```bash
# Terminal 1 — backend API  (http://localhost:8000, docs at /docs)
make backend         # or: uvicorn app.main:app --reload --app-dir backend

# Terminal 2 — React workflow UI  (http://localhost:5173)
cd web && npm install && npm run dev
```

Vite proxies `/api` and `/` to the backend on :8000. Set `VITE_API_BASE` to
point at a non-proxied backend for a production build (`npm run build`).
See [web/README.md](web/README.md) for details.

Or run both tiers with a single command from the repo root:

```bash
npm run setup        # one-time: create .venv, install backend + web deps
npm run dev:all      # backend :8000 + React UI :5173 together
```

Seed the SQLite DB with the 8 demo fixtures:

```bash
make seed            # or: cd backend && python -m app.fixtures.loader
                     # (the backend also auto-seeds on first startup)
```

Run the tests:

```bash
make test            # or: pytest backend/tests -q
```

Docker (one shot):

```bash
docker-compose up --build      # backend :8000 · React UI :8080
```

## 7. Demo

Follow [docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md). It walks five cases end to end:
clean approval → missing documents → unemployment hardship → suspicious-document
human review → proactive risk alert (bonus).

## 8. Trade-offs

- **React + Vite UI on a UI-agnostic API**: the frontend is a React + TypeScript
  app (the "Paper" design system) talking to a clean FastAPI contract. The engine
  is fully decoupled from the front end — any client speaking the same contract works.
- **No-interest loan math**: Sheikh Zayed housing assistance is profit-free, so
  the solver uses simple principal arithmetic. An interest/profit term can be
  injected into `policies/solver.py` without changing the node graph.
- **SQLite, not Postgres**: zero-setup for local demo. All DB access goes through
  a thin repository so a Postgres driver swaps in cleanly.
- **scikit-learn risk model** is trained on a small *synthetic, seeded* dataset
  at startup — illustrative, deterministic, and falls back to a transparent
  heuristic if sklearn is absent. Not a production credit model.
- **Decisions are deterministic, LLMs are advisory**: the recommendation can
  never be hallucinated; the LLM only reads documents and writes prose.

## 9. Future improvements

- Real UAE PASS OIDC + MOEI core-banking connectors behind the same mock
  interfaces.
- Postgres + Alembic migrations; event-sourced audit log.
- Officer feedback loop to retrain the risk model on real (masked) outcomes.
- Document OCR pipeline feeding the extraction node.
- Policy versioning so historical cases replay against the rules in force at the time.

---

*Synthetic data only. No real personal identifiers are used anywhere in this repo.*
