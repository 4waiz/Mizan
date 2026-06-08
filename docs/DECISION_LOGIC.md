# Mizan — Decision Logic

All decisions are **deterministic**. This document is the single source of truth
for how an outcome is reached, so a reviewer can reproduce any recommendation by
hand.

## 1. Hard rules (`policies/rules.py`)

| Rule ID | Statement | Effect |
|---------|-----------|--------|
| **SZHP-R1** | Monthly deduction must not exceed **20%** of beneficiary income | Filters out any candidate plan whose installment/income > 20% |
| **SZHP-R2** | Proposed schedule must not exceed the **original approved period** | Filters out any plan whose term > original term |
| **SZHP-R3** | An existing **active application** blocks a new straight-through decision | Forces `REJECT_ACTIVE_REQUEST` |
| **SZHP-R4** | All **required documents** must be present and current | Missing → `REQUEST_MORE_INFO`; stale → WARN |
| **SZHP-R5** | Arrears transfer / postponement needs a **valid hardship justification** | FAIL if hardship claimed without evidence |
| **SZHP-R6** | **High external obligations** (≥50% income) reduce aggressiveness | WARN → escalate repayment-change plans |
| **SZHP-R7** | **Suspicious documents** are referred to a human, never auto-rejected | Forces `REFER_TO_OFFICER`, never `REJECT` |

Required documents (situational): Emirates ID always; salary certificate + bank
statement if employed/self-employed; termination letter if unemployment hardship;
medical report if medical hardship.

## 2. Candidate plans (`policies/solver.py`)

Loan math is **profit-free** (simple principal arithmetic). Let
`outstanding` = outstanding principal, `arrears` = overdue amount,
`remaining` = original_term − months_elapsed, `income` = monthly income.

| Outcome | Construction | Validity |
|---------|--------------|----------|
| `UPDATE_INSTALLMENT` | installment = (outstanding + arrears) / remaining; end date unchanged | R1 (≤20%) and R2 |
| `TRANSFER_ARREARS` | keep current installment; defer arrears as a balloon at **original maturity** (end date unchanged → R2 always holds) | R1 on current installment |
| `MAINTAIN_INSTALLMENT` | no change; only generated when arrears ≈ 0 | R1 on current installment |
| `REQUEST_MORE_INFO` | generated when R4 fails | always valid (terminal) |
| `REJECT_ACTIVE_REQUEST` | generated when R3 fails | always valid (terminal) |
| `REFER_TO_OFFICER` | always added as a safe fallback | always valid (lowest rank) |

### Scoring each financial plan

- `deduction_ratio = installment / income`
- `burden_relief = clamp(1 − deduction_ratio / 0.20)` — lighter monthly burden scores higher.
- `resolution` = 1.0 for UPDATE/MAINTAIN-when-clean, 0.6 for TRANSFER (arrears deferred, not cleared).
- `sustainability = clamp(0.5·resolution + 0.5·(1 − redefault_probability))`
- **Composite**:
  - hardship case → `0.6·burden_relief + 0.4·sustainability` (+0.05 nudge to TRANSFER)
  - otherwise → `0.6·sustainability + 0.4·burden_relief`
- Invalid plans get composite 0.

### Ranking & selection precedence (`graph/nodes/policy_solver.py`)

1. active application open → `REJECT_ACTIVE_REQUEST` (R3)
2. suspicious doc / income fraud (untrusted inputs) → `REFER_TO_OFFICER` (R7)
3. required documents missing → `REQUEST_MORE_INFO` (R4)
4. otherwise the **best valid financial plan** by composite score
5. nothing valid → `REFER_TO_OFFICER`

## 3. Scoring

### Affordability (`scoring/affordability.py`)
`max_affordable = 0.20 · income`; disposable = income − external obligations;
`data_completeness` rewards verified income + salary/bank docs + good extraction.

### Risk (`scoring/risk.py`)
Features: obligations ratio, current deduction ratio, months in arrears,
on-time ratio, unemployment flag, normalised dependents. A seeded
`LogisticRegression` (deterministic) scores them; if scikit-learn is absent the
same weights are applied by a transparent hand-coded logistic. Bands:
`high ≥ 0.60`, `medium ≥ 0.35`, else `low`.

### Confidence (`scoring/confidence.py`)
Weighted blend of: data completeness (0.20), extraction confidence (0.15),
fraud-clean (0.25), policy clarity (0.20), solver decisiveness (0.20).
Bands: `high ≥ 0.75`, `medium ≥ 0.50`, else `low`.

## 4. Human-review gate (`graph/nodes/human_review_gate.py`)

A case **escalates** if any of:
- recommended outcome is `REFER_TO_OFFICER`,
- trigger is a proactive flag (officer outreach),
- a high-severity fraud flag or suspicious document,
- confidence < `auto_approve_confidence` (default 0.75),
- high obligations (R6 WARN) alongside a repayment-change plan.

Otherwise it is **straight-through**. `REJECT_ACTIVE_REQUEST` and
`REQUEST_MORE_INFO` are deterministic automated outcomes (auto-issued) unless a
suspicious document / high-severity fraud demands a human.

## 5. Worked examples (the 8 fixtures)

| Fixture | Outcome | Route | Why |
|---------|---------|-------|-----|
| clean_approval | UPDATE_INSTALLMENT | auto | affordable update clears arrears in-period; high confidence |
| missing_documents | REQUEST_MORE_INFO | auto | salary + bank statements missing (R4) |
| unemployment_hardship | TRANSFER_ARREARS | auto | update would breach R1 → defer arrears; affordable & supported |
| medical_hardship | TRANSFER_ARREARS | auto | near maturity, update breaches R1 → defer to maturity |
| high_obligations | UPDATE_INSTALLMENT | **review** | obligations ≥50% income (R6) with a repayment change |
| active_request_conflict | REJECT_ACTIVE_REQUEST | auto | active application open (R3) |
| suspicious_document | REFER_TO_OFFICER | **review** | income mismatch + altered doc (R7) — never auto-rejected |
| proactive_alert | MAINTAIN_INSTALLMENT | **review** | not yet in arrears but high re-default risk → officer outreach |
