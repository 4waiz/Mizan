# Mizan — Demo Script (~7 minutes)

> Goal: show that a manual **5-working-day** arrears review becomes an **instant,
> explainable, auditable** decision — with humans involved only on the
> exceptional cases.

## 0 · Setup (before the demo)

```bash
# Terminal 1
make backend        # http://localhost:8000  (auto-seeds 8 demo cases on first run)
# Terminal 2
cd web && npm run dev   # http://localhost:5173
```

Open the UI. In the left sidebar you can switch **language (EN/AR)** and toggle
**high-contrast** mode at any time — do this once to show accessibility.

> **Note — data-informed synthetic cases.** The demo scenarios below are
> **synthetic, but data-informed**: each is mapped to a real pattern found in
> the organizer-provided historical Excel (`data/RescheduleArrears.xlsx`,
> 2023–2025). The mapping:
> - **Clean approval** → common **update-installment** under the 20% cap (86.7% of history).
> - **Missing documents** → document-validation / completeness path.
> - **High obligations** → pressure case (income vs obligations).
> - **Medical hardship** → **transfer arrears** / temporary-circumstance path.
> - **Unemployment hardship** → maintain installment / **transfer arrears**.
> - **Active request conflict** → governance rule (active application blocks a new decision).
> - **Suspicious document** → fraud / inconsistency governance.
>
> The documents stay fully synthetic; only their figures and request mix are
> informed by the real organizer patterns. No real citizen identities appear.

Opening line:
> "Mizan is not a chatbot. It's an autonomous case officer. Watch it process five
> very different arrears cases the way a government officer would — and decide,
> by itself, which ones a human still needs to see."

---

## 1 · Clean approval (straight-through) — `Ahmed Al Mansoori`

1. **Home →** sign in with UAE PASS as *Ahmed Al Mansoori (clean_approval)*.
2. **New Request →** show the **auto-filled profile** and **documents on file**
   (Emirates ID, salary certificate, bank statement).
3. Click **Run assessment**.
4. Point at the **processing time (a few milliseconds)** vs. *5 working days*.
5. Result: **Update installment**, straight-through, **confidence ~92%**.
6. **My Case →** show candidate plans (UPDATE selected, others ranked), the
   policy checks all green, the **bilingual EN/AR memo**, and the **audit trail**.

> "All green. The system updated the installment to clear the arrears inside the
> original term, stayed under the 20% cap, and issued the decision itself."

## 2 · Missing documents (blocked, auto) — `Fatima Al Suwaidi`

1. Sign in as *Fatima (missing_documents)* → New Request → Run.
2. Result: **Request more information** — SZHP-R4 fails (salary + bank missing).
3. Show that straight-through processing is **blocked** but still automated — no
   officer time wasted.

## 3 · Unemployment hardship (compassionate auto) — `Khalid Al Hosani`

1. Sign in as *Khalid (unemployment_hardship)* → Run.
2. Result: **Transfer arrears to end**.
3. In **My Case**, show the candidate panel: **UPDATE is filtered out** because
   it would breach the 20% cap; **TRANSFER** keeps the monthly burden low by
   deferring arrears to maturity.

> "The rules don't just say no. The solver found the *humane* compliant option —
> defer the arrears, keep the family's monthly payment affordable."

## 4 · Suspicious document (human review) — `Omar Al Balushi`

1. **Officer Queue** (switch hats to the officer).
2. Open *Omar Al Balushi* — escalation reason: income mismatch + altered document.
3. Show the **evidence panel** (the `[ALTERED]` salary certificate, declared
   AED 25,000 vs verified AED 12,000), the **fraud flags**, low **confidence**.
4. Outcome is **Refer to officer** — **never auto-rejected** (SZHP-R7).
5. Use the **Override** drawer: set a conservative plan, add **decision notes**,
   apply. Show it appended to the **audit trail**.

> "On suspicion we never auto-reject. We hand the officer the evidence, the
> policy view, and a safe default — and we record exactly what they decided."

## 5 · Proactive alert (bonus) — `Hessa Al Marri`

1. **Proactive Alerts** page.
2. Show *Hessa Al Marri* flagged at **~54% re-default risk** — recently
   unemployed, high obligations, weak recent payments — **before** serious
   arrears.
3. Suggested action + one-click into the case for **early outreach**.

## 6 · Historical Intelligence (organizer data) — `/insights`

1. Open the **`/insights`** Historical Intelligence dashboard.
2. Narrate the **organizer-data story**: "Before building anything, we ingested
   the organizer's real historical arrears Excel — **2,158 raw / 1,933 usable**
   cases across **2023–2025**."
3. Point at the aggregated insights: **median 11 overdue months**, **46.8%
   Severe/Critical** at 13+ months, **median 11-day approval**, and the
   treatment split — **update installment 86.7%** vs **transfer arrears 13.3%**.
4. Show the **policy edge cases**: **13%** of current installments already exceed
   the **20% deduction cap** — exactly the kind of check Mizan automates.
5. Show the **proactive scan**: **406 high-risk** historical rows — the basis for
   shifting from late arrears treatment to **early financial intervention**.

> "This is real historical intelligence, fully anonymized — only aggregates,
> risk buckets, and banded patterns. No raw personal data, no real identities.
> It calibrates our risk scoring and demo realism, but it never makes a policy
> decision — the deterministic rules do that."

## Close · Replay Dashboard

1. Open **Replay Dashboard**.
2. Show: **8 cases**, **~62% straight-through**, **3 escalated**, **~25 manual
   working-days saved**, outcome distribution, and the per-case table.

> "Five days of officer work, reduced to milliseconds — consistent, explainable,
> auditable, and escalating only the cases that genuinely need a human."
