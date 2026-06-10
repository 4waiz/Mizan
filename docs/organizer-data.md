# Mizan — Organizer Historical Data

How Mizan uses the **organizer-provided historical arrears Excel** as a
"Historical Intelligence" layer — for aggregated insights, risk calibration,
demo realism, and policy edge-case analysis — while keeping raw personal data
out of the UI and keeping every final decision in the **deterministic policy
engine**.

---

## 1. Dataset purpose

The organizer supplied a real historical dataset of housing-loan arrears
rescheduling cases (2023–2025). Mizan ingests it to:

- **Describe reality** — produce aggregated insights (medians, counts,
  percentages) about how arrears cases actually behave.
- **Calibrate risk** — use the historical overdue-month distribution to
  calibrate the risk-score thresholds and the risk buckets.
- **Make the demo realistic** — keep synthetic demo documents fully synthetic
  but **data-informed**, mapping their figures onto real organizer patterns.
- **Validate policy edge cases** — quantify how often, e.g., current
  installments already exceed the **20% deduction cap**, so we know where
  automation matters most.

The historical layer **calibrates and explains; it never decides.** Final
outcomes are produced by the deterministic policy rules (see
[DECISION_LOGIC.md](DECISION_LOGIC.md)), not by historical averages or an LLM.

## 2. File location

- Path: [`data/RescheduleArrears.xlsx`](../data/RescheduleArrears.xlsx)
- Structure: **3 worksheets**, one per year — **2023**, **2024**, **2025**.
- The year for each row is **derived from the worksheet it came from**.

Place the file at exactly this path. If it is absent, the insights endpoints
return `{ "loaded": false }` and the rest of the app runs unchanged.

## 3. Columns used

The ingestion layer (`backend/app/data/organizer_dataset.py`) keeps only the
analytical columns below (fuzzy-matched across sheets — see §4):

| Column | Use |
|--------|-----|
| `CURRENT_SALARY` | Monthly income; affordability and deduction-ratio analysis. |
| `OVER_DUE_AMT` | Overdue (arrears) amount. |
| `OVER_DUE_MONTHS` | Months in arrears; drives the risk buckets. |
| `CURRENT_EMI_AMT` | Current monthly installment; 20%-cap edge-case analysis. |
| `NEW_EMI_AMT` | Proposed/approved installment after rescheduling. |
| `REQUEST_TYPE` / `APPROVED_REQUEST_TYPE` | Treatment path (update installment vs transfer arrears). |
| `DEDUCT_FROM_SALARY` | Whether the installment is deducted at source. |
| `UNTIL_LOAN_END` | Whether arrears are deferred to original loan maturity. |
| `CREATED_DATE` | Request creation date (approval-duration calc). |
| `APPROVED_DATE` | Approval date (approval-duration calc). |
| `JUSTIFICATIONS` | Stated hardship/justification text (aggregated only). |
| `REMARKS` | Officer remarks (aggregated only). |
| `START_YEAR` | Loan/program start year context. |

### Dropped at load (privacy)

The following **identifier columns are dropped at ingestion**, before any
aggregation, and never leave the backend:

`APPLICANT` · `APPLICATION_ID` · `AGREEMENT_ID` · `EDB_LOAN_ID` ·
`EDB_CUSTOMER_ID` · `AUTH_SIGNATORY` · `CREATED_BY`

## 4. Cleaning steps

1. **Fuzzy column mapping across sheets** — the three yearly worksheets do not
   have perfectly identical headers, so columns are matched by normalized/fuzzy
   name to a canonical schema.
2. **Numeric coercion** — salary, overdue amount, EMI, and overdue-month fields
   are coerced to numbers; unparseable values become null.
3. **Date parsing** — `CREATED_DATE` / `APPROVED_DATE` are parsed to dates so
   approval duration can be computed.
4. **Plausibility filters** — rows outside sane ranges are dropped:
   - salary in **AED 1,000–400,000**,
   - overdue months in **0–360**,
   - EMI **≤ 200,000**.
5. **Year derivation** — the case year is taken from the worksheet name
   (2023 / 2024 / 2025).

After cleaning: **2,158 raw records → 1,933 usable** (225 dropped) across
2023–2025.

## 5. Privacy / anonymization approach

- **PII dropped at ingestion.** Identifier columns (§3) are removed at load
  before any aggregation runs.
- **Only aggregates leave the backend.** The API exposes **medians, counts,
  percentages, risk buckets, and banded anonymized patterns** — never raw rows.
- **No raw personal data in the UI.** The `/insights` dashboard renders only
  aggregated/banded values; individual citizens are never identifiable.
- **Synthetic stays synthetic.** Demo documents remain fully synthetic; the
  organizer data only informs their *shape* (typical figures and request mix).

## 6. Aggregated metrics generated

Generated into `data/processed/` (`organizer_insights.json`,
`risk_buckets.json`, `proactive_scan.json`). Verified figures from the real
`data/RescheduleArrears.xlsx`:

- **Volume:** 2,158 raw records · **1,933 usable** · 225 dropped · 2023–2025
  (3 sheets).
- **Medians:**
  - salary **AED 26,205**
  - overdue amount **AED 43,119**
  - overdue **11 months**
  - current EMI **AED 3,751**
  - new EMI **AED 1,004**
  - current EMI / salary ratio **15%**
  - approval duration **11 days** (vs ~5 working-day manual baseline)
- **Request-type split:** `UPDATE_INSTALLMENT` **86.7% (1,676)** ·
  `TRANSFER_ARREARS` **13.3% (257)**.
- **Overdue-month risk buckets:** Low(0–2) **13.1%** · Medium(3–6) **21.4%** ·
  High(7–12) **18.7%** · Severe(13–24) **22.2%** · Critical(25+) **24.6%**.
- **20% deduction-cap edge cases:** **13.0%** of current EMIs exceed the cap
  (252 of 1,933) · **3.0%** of new EMIs exceed it (57 of 1,873).
- **Proactive scan:** **406 high-risk rows**; band distribution
  Critical **45** / Severe **361** / High **463** / Medium **641** / Low **423**.

## 7. Risk bucket definitions

Buckets are defined on **overdue months**:

| Bucket | Overdue months |
|--------|----------------|
| **Low** | 0–2 |
| **Medium** | 3–6 |
| **High** | 7–12 |
| **Severe** | 13–24 |
| **Critical** | 25+ |

These bands calibrate the risk-score thresholds used by the engine. Note that
**46.8%** of historical cases fall into Severe or Critical (13+ overdue months)
— arrears tend to accumulate for months before any action is taken.

## 8. How it supports the pitch deck

The organizer data turns the pitch from "a generic AI demo" into a
**data-informed** story:

- It proves arrears rescheduling is a **recurring operational workflow**
  (1,933 usable cases over three years), not a rare edge case.
- It quantifies the **time problem** (median 11 overdue months; median 11-day
  approval) and the **policy problem** (13% of current installments already
  breach the 20% cap).
- It shows the **two dominant treatment paths** (update installment 86.7%,
  transfer arrears 13.3%) the solver must handle well.
- It reframes the impact: Mizan shifts the service from **late arrears
  treatment** to **early financial intervention** (proactive scan surfaces 406
  high-risk cases).

See [SLIDES_OUTLINE.md](SLIDES_OUTLINE.md) → "What the organizer data revealed".

## 9. How it supports the rubric

**Agentic Decision Intelligence.** The historical layer gives the agent a
grounded prior on how real cases behave — overdue-month distributions, EMI
changes, and request-type mix — so its risk forecasting and plan ranking reflect
production reality rather than hand-picked assumptions, while the agent still
reaches each outcome through transparent, reproducible steps.

**Policy Compliance & Governance.** The data is used to *validate* policy edge
cases (13% of current EMIs exceed the 20% cap; 3% of new EMIs would) and to
*calibrate* risk thresholds — but it is explicitly **walled off from
decisioning**. The 20% deduction cap, original-repayment-period cap,
active-request validation, and document-completeness checks remain deterministic
rules; historical averages never make the final call.

**Technical Excellence & Data Integration.** A real, messy, multi-sheet Excel is
ingested through fuzzy column mapping, numeric coercion, date parsing, and
plausibility filtering, with PII dropped at load. The pipeline
(`scripts/analyze_organizer_excel.py` → `data/processed/*.json` →
`historical_insights_service.py`/`risk_forecaster.py` → API) is reproducible and
degrades gracefully (`loaded: false`) when the file is absent.

**Impact on Service Transformation.** The numbers make the transformation
concrete: a median 11-month arrears age and 11-day approval baseline become an
argument for instant, consistent processing, and a 406-case proactive scan turns
a reactive, late-stage process into **early financial intervention**.

**Demo/Explainability & User Experience.** The `/insights` dashboard makes the
historical intelligence visible and explainable — aggregates, risk buckets, and
banded patterns only — so reviewers can see exactly what informs the system
without ever seeing a real citizen's data, and the demo cases visibly map to
real organizer patterns.

---

*The organizer dataset is used for aggregated insights, risk calibration, demo
realism, and policy edge-case analysis only. Raw personal data is never exposed
in the UI. Synthetic demo documents remain synthetic but are data-informed.
Final decisions are governed by deterministic policy rules.*
