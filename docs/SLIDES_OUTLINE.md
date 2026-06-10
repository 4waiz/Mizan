# Mizan — Slides Outline

A 12-slide deck for the hackathon pitch, built around a live **demo video**.

> **Demo video:** [`intro.mp4`](../intro.mp4) (project root). Embed it on Slide 9
> and keep it queued as a fallback in case the live environment misbehaves.

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
- FastAPI + SQLite (Postgres-ready) + React + Vite workflow UI.

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

### Slide 9 — Demo video 🎬
> **Play [`intro.mp4`](../intro.mp4) here (~7 min).** Live walkthrough of the
> agent processing real, very different arrears cases end-to-end.

What the video shows, in order:
1. **Ahmed Al Mansoori** — clean approval, straight-through, **~92% confidence**,
   instant decision (vs. 5 days).
2. **Fatima Al Suwaidi** — missing documents → *Request more information*,
   blocked but fully automated (SZHP-R4).
3. **Khalid Al Hosani** — unemployment hardship → solver filters out UPDATE
   (breaks 20% cap), picks **Transfer arrears to end** — the humane option.
4. **Omar Al Balushi** — suspicious document → human review, evidence panel,
   fraud flags, **never auto-rejected** (SZHP-R7); officer override + notes.
5. **Hessa Al Marri** — proactive alert at **~54% re-default risk**, caught
   *before* serious arrears.

> Each beneficiary's synthetic document pack (Emirates ID, salary certificate,
> bank statement, MOEI loan statement, memo) is uploaded live from
> [`demo_documents/`](../demo_documents/) — **70 PDFs across 7 cases**.

### Slide 10 — Impact (replay dashboard)
- **8 representative cases · ~62% straight-through · 3 escalated · ~25 manual
  working-days saved.**
- Outcome distribution + per-case table, all reproducible (deterministic seed).
- Bonus: **proactive risk alerts** catch beneficiaries *before* serious arrears.

### Slide 11 — Why it's safe to trust
- Decisions are **deterministic and reproducible** — same inputs, same outcome.
- **On suspicion, never auto-reject** — hand the officer evidence + a safe default.
- Synthetic, watermarked demo data — **no real persons, banks, or government
  records**; only neutral placeholders.

### Slide 12 — Roadmap
- Real UAE PASS + MOEI/AECB connectors (same interfaces).
- Postgres + event-sourced audit; officer-feedback retraining of the risk model.
- Policy versioning for faithful historical replay.

---

### Closing line
> "Five days of officer work, reduced to milliseconds — consistent, explainable,
> auditable, and escalating only the cases that genuinely need a human."
