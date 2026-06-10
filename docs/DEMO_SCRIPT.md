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

## Close · Replay Dashboard

1. Open **Replay Dashboard**.
2. Show: **8 cases**, **~62% straight-through**, **3 escalated**, **~25 manual
   working-days saved**, outcome distribution, and the per-case table.

> "Five days of officer work, reduced to milliseconds — consistent, explainable,
> auditable, and escalating only the cases that genuinely need a human."
