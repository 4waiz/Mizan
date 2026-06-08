# Mizan — Slides Outline

A 10-slide deck for the hackathon pitch.

---

### Slide 1 — Title
**Mizan (ميزان) — AI Case Officer for Housing Loan Arrears Rescheduling**
MOEI · Sheikh Zayed Housing Programme. *"The balance between compassion and policy."*

### Slide 2 — The problem
- Arrears rescheduling today: **manual, ~5 working days** per case.
- Slow, inconsistent between officers, hard to audit, doesn't scale.
- Beneficiaries in hardship wait while the queue grows.

### Slide 3 — The idea
- An **autonomous case officer**, not a chatbot.
- Reads the case, applies policy, proposes compliant repayment plans, and
  **decides** — escalating only the exceptional cases.
- Instant · consistent · explainable · auditable.

### Slide 4 — How it decides (trust by design)
- **Deterministic policy engine** makes every decision (20% cap, original-period
  cap, active-request, documents, hardship, obligations, fraud).
- **LLM is advisory only** — extraction, classification, bilingual memo. Structured
  output, and a deterministic MockLLM when offline. *No hallucinated decisions.*

### Slide 5 — Architecture
- LangGraph pipeline over one typed `CaseState`:
  intake → documents → fraud → affordability → risk → **policy solver** →
  human-review gate → rationale → finalize.
- FastAPI + SQLite (Postgres-ready) + Streamlit workflow UI.

### Slide 6 — The candidate-plan solver
- Generates concrete options (update / transfer / maintain / request-info /
  reject / refer), **filters by hard rules**, ranks by **sustainability** and
  **citizen burden**. Picks the humane, compliant option.

### Slide 7 — Escalate only the exceptional
- Confidence score + explicit triggers (fraud, suspicious docs, low confidence,
  high obligations, proactive flags).
- Officer gets a queue, evidence, policy panel, candidate plans, confidence,
  escalation reason, and approve / override / reject with notes.

### Slide 8 — Governance & explainability
- Every step writes an **audit event** with `rule_ids` + `evidence_ids`.
- Bilingual **EN/AR** rationale memo. SLA clock (instant vs 5 days).
- Accessibility: high-contrast mode, RTL Arabic.

### Slide 9 — Impact (replay)
- 8 representative cases · ~62% straight-through · ~25 manual working-days saved.
- Bonus: **proactive risk alerts** catch beneficiaries *before* serious arrears.

### Slide 10 — Roadmap
- Real UAE PASS + MOEI/AECB connectors (same interfaces).
- Postgres + event-sourced audit; officer-feedback retraining of the risk model.
- Policy versioning for faithful historical replay.
