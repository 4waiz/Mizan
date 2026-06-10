# Mizan — Architecture

## 1. Principles

1. **Decisions are deterministic.** Every recommendation is produced by the
   policy engine (`policies/rules.py` + `policies/solver.py`) and the scoring
   modules. The LLM never decides an outcome.
2. **LangGraph is the spine.** A single typed `CaseState` flows through nine
   nodes. Each node reads and writes only structured state.
3. **LLM is structured-only and optional.** Used for document extraction,
   classification, bilingual memo, and exception summary — always returning a
   Pydantic model. With no API key, a deterministic `MockLLM` is used.
4. **Everything is auditable.** Each node emits typed `AuditEvent`s carrying
   `rule_ids` and `evidence_ids`. The decision is reconstructable end to end.
5. **Escalate only the exceptional.** A confidence score plus explicit triggers
   route ambiguous / suspicious / low-confidence cases to a human.

## 2. Component map

```
backend/app/
├── main.py                FastAPI routes (beneficiary + officer + replay + proactive)
├── config.py              Env-driven settings (policy knobs, LLM, DB)
├── schemas/               Pydantic v2 models — CaseState and all sub-models
│   ├── enums.py           TriggerType, OutcomeType, CaseStatus, ...
│   ├── beneficiary.py     BeneficiaryProfile, FamilySnapshot, ObligationSummary
│   ├── loan.py            LoanSnapshot, ArrearsSnapshot, PaymentHistorySummary
│   ├── documents.py       DocumentInventory, ExtractedDocumentFields
│   ├── analysis.py        Affordability, Risk, CandidatePlan, PolicyCheck, ...
│   ├── case.py            CaseState (the shared object) + OfficerDecision
│   └── api.py             Request/response contract
├── graph/
│   ├── state.py           GraphState channel wrapper
│   ├── builder.py         LangGraph compile + sequential fallback runner
│   ├── router.py          Conditional routing helpers
│   └── nodes/             The 9 nodes (each: run(CaseState) -> CaseState)
├── policies/
│   ├── rules.py           Hard rules SZHP-R1..R7 (pure verdict functions)
│   └── solver.py          Candidate generation, hard-rule filtering, ranking
├── scoring/
│   ├── affordability.py   20%-cap features, disposable income, completeness
│   ├── risk.py            sklearn logistic (seeded) + heuristic fallback
│   └── confidence.py      Blended confidence -> straight-through vs review
├── services/
│   ├── llm.py             MockLLM + structured Anthropic path
│   ├── audit.py           Audit event helpers + clock
│   ├── explain.py         Explanation (rule_ids + evidence_ids) builder
│   ├── case_factory.py    Build a CaseState from a fixture/beneficiary
│   ├── replay.py          Batch replay summary
│   └── mocks/             UAE PASS, MOEI loan, salary, bank, document store
├── db/                    SQLite store behind a repository (Postgres-ready)
└── fixtures/              8 synthetic JSON cases + loader/seeder
```

## 3. The case pipeline (LangGraph)

```
START
  → intake_and_retrieve      pull loan/arrears/history/family/obligations/docs
  → document_audit           LLM extract + SZHP-R4 completeness/freshness
  → fraud_and_dedupe_check   income mismatch, suspicious doc, duplicate/active
  → affordability_analysis   20%-cap features + full policy sweep (R3/R4/R5/R6)
  → risk_forecast            re-default probability (sklearn/heuristic)
  → policy_solver            generate candidates → filter by hard rules → rank
                             → select outcome (precedence) → confidence → recommendation
  → human_review_gate        straight-through vs escalate (+ reason)
  → rationale_generator      bilingual EN/AR memo (LLM, structured)
  → finalize_case            SLA clock + final audit event
END
```

The state channel carries the whole `CaseState`; nodes mutate-and-return it.
If `langgraph` is not installed, `builder.run_pipeline` falls back to an
identical in-process sequential runner so the app always runs.

## 4. Data flow & persistence

- The API intake endpoint authenticates via mock UAE PASS, auto-fills the
  profile, loads documents, and persists the case (`status=intake`).
- `/run` executes the pipeline and persists the finalised case.
- The SQLite store keeps the full `CaseState` as JSON plus indexed columns
  (`status`, `needs_review`, `confidence`, `arrears_amount`, `redefault_prob`)
  powering the officer queue and proactive list. All access is through
  `db/repository.py`; switching to Postgres is a `database.py` change only.

## 5. Frontend

A React + Vite + TypeScript multipage **workflow** UI (not a chatbot):

- **Beneficiary:** Home (mock UAE PASS login) → New Request (auto-filled profile,
  documents, validation) → My Case (recommendation, plans, confidence, bilingual
  memo, status, audit).
- **Officer:** Review Queue → Case detail (evidence, policy panel, candidate
  plans, confidence, escalation reason, approve/override/reject + notes, audit).
- **Insight:** Proactive Alerts (bonus) and Replay Dashboard.
- Bilingual EN/AR labels with RTL, high-contrast accessibility mode,
  government-style theme.

## 6. Extensibility

- Replace any `services/mocks/*` connector with a real one behind the same
  signature (UAE PASS OIDC, MOEI core banking, AECB).
- Add an interest/profit term inside `solver.py` without touching the graph.
- Version policies so historical cases replay under the rules in force at the time.
- Swap SQLite → Postgres via the repository.
