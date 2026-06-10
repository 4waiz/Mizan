import type { ReactNode } from "react";
import { useI18n } from "../i18n";

export const aed = (n: number | null | undefined) =>
  `AED ${Math.round(n ?? 0).toLocaleString("en-US")}`;
export const pct = (v: number | null | undefined) =>
  v == null ? "-" : `${Math.round(v * 100)}%`;

/* Letterhead masthead - eyebrow (org) · serif title · double rule · file ref. */
export function Band({
  title,
  subtitle,
  fileRef,
}: {
  title: ReactNode;
  subtitle?: string;
  fileRef?: string;
}) {
  return (
    <header className="masthead">
      <div className="top">
        <div>
          <div className="eyebrow">{subtitle ?? "Sheikh Zayed Housing Programme · MOEI"}</div>
          <h1>{title}</h1>
        </div>
        <div className="ref">
          {fileRef ?? "FILE · القضية"}
          <br />
          MIZAN / ميزان
        </div>
      </div>
      <div className="rules" />
    </header>
  );
}

export function Metric({ k, v, delta }: { k: string; v: ReactNode; delta?: ReactNode }) {
  return (
    <div className="metric">
      <div className="k">{k}</div>
      <div className="v">{v}</div>
      {delta != null && <div className="delta">{delta}</div>}
    </div>
  );
}

export function Alert({
  kind = "info",
  children,
}: {
  kind?: "ok" | "warn" | "err" | "info";
  children: ReactNode;
}) {
  return <div className={`alert ${kind}`}>{children}</div>;
}

const STATUS_TONE: Record<string, string> = {
  auto_approved: "green",
  officer_approved: "green",
  pending_human_review: "gold",
  info_requested: "gold",
  rejected: "red",
  officer_rejected: "red",
  officer_overridden: "blue",
  processing: "ink",
  intake: "ink",
};

export function StatusPill({ status, lg }: { status: string; lg?: boolean }) {
  const tone = STATUS_TONE[status] ?? "ink";
  return (
    <span className={`stamp ${tone}${lg ? " lg" : ""}`}>
      {status.replace(/_/g, " ")}
    </span>
  );
}

export function ProfileCard({
  case: c,
  revealFinancials = true,
}: {
  case: any;
  revealFinancials?: boolean;
}) {
  const { t } = useI18n();
  const b = c.beneficiary ?? {};
  const loan = c.loan ?? {};
  const arr = c.arrears ?? {};
  const hidden = (
    <span style={{ fontSize: 13, fontWeight: 500, color: "var(--ink-soft, #9aa0a6)" }}>
      🔒 Pending documents
    </span>
  );
  return (
    <div className="card tab">
      <div className="spread" style={{ alignItems: "flex-start", marginBottom: 16 }}>
        <div>
          <div className="eyebrow">{t("profile")}</div>
          <div style={{ fontFamily: "var(--serif)", fontSize: 22, fontWeight: 600, marginTop: 2 }}>
            {b.full_name_en ?? "-"}
          </div>
          <div style={{ fontFamily: "var(--serif)", color: "var(--ink-soft)" }} dir="rtl">
            {b.full_name_ar ?? ""}
          </div>
          <div className="caption mono">
            {b.emirates_id_masked ?? ""} · {b.emirate ?? ""}
          </div>
          <div className="caption">
            {b.employment_status ?? ""} · {b.employer_name ?? "-"}
          </div>
        </div>
        <span className="stamp ink" style={{ fontSize: 10 }}>
          {b.hardship_type && b.hardship_type !== "none"
            ? `Hardship · ${b.hardship_type}`
            : "No hardship"}
        </span>
      </div>
      <div className="grid grid-3">
        <Metric k={t("income")} v={revealFinancials ? aed(b.monthly_income_aed) : hidden} />
        <Metric
          k={t("installment")}
          v={revealFinancials ? aed(loan.current_installment_aed) : hidden}
        />
        <Metric k={t("arrears")} v={revealFinancials ? aed(arr.arrears_amount_aed) : hidden} />
      </div>
    </div>
  );
}

const DECISION_STAMP: Record<string, { label: string; tone: string }> = {
  auto_approved: { label: "Auto · Approved", tone: "green" },
  officer_approved: { label: "Approved", tone: "green" },
  officer_overridden: { label: "Overridden", tone: "blue" },
  officer_rejected: { label: "Rejected", tone: "red" },
  rejected: { label: "Rejected", tone: "red" },
  pending_human_review: { label: "Refer to Officer", tone: "gold" },
  info_requested: { label: "Info Requested", tone: "gold" },
};

export function DecisionBadge({ case: c }: { case: any }) {
  const { t, outcome } = useI18n();
  const rec = c.recommendation ?? {};
  const review = c.needs_human_review;
  const stamp =
    DECISION_STAMP[c.status] ?? (review
      ? { label: "Refer to Officer", tone: "gold" }
      : { label: "Determined", tone: "green" });
  return (
    <div className="determination">
      <div className="stamp-slot">
        <span className={`stamp rotate lg ${stamp.tone}`}>{stamp.label}</span>
      </div>
      <div className="eyebrow">{t("recommendation")} · التوصية</div>
      <div className="verdict">{outcome(rec.outcome_type)}</div>
      {rec.decision_label_ar && (
        <div className="verdict-ar" dir="rtl">
          {rec.decision_label_ar}
        </div>
      )}
      <hr className="perf" />
      <div className="muted">
        {review ? `⚠ ${c.escalation_reason ?? ""}` : "Straight-through - issued without manual review."}
      </div>
    </div>
  );
}

const RESULT_ICON: Record<string, string> = {
  pass: "✓",
  fail: "✕",
  warn: "!",
  not_applicable: "–",
};
const RESULT_TONE: Record<string, string> = {
  pass: "var(--green)",
  fail: "var(--danger)",
  warn: "var(--gold)",
  not_applicable: "var(--muted)",
};

export function PolicyTable({ case: c }: { case: any }) {
  const rows = c.policy_checks ?? [];
  if (!rows.length) return <Alert kind="info">No policy checks recorded.</Alert>;
  return (
    <div className="card">
      {rows.map((r: any, i: number) => (
        <div
          key={i}
          className="kv"
          style={{
            display: "grid",
            gridTemplateColumns: "22px 1fr",
            gap: 10,
            padding: "8px 0",
            borderBottom: i < rows.length - 1 ? "1px solid var(--line)" : "none",
          }}
        >
          <span
            style={{
              fontFamily: "var(--mono)",
              fontWeight: 700,
              color: RESULT_TONE[r.result],
              textAlign: "center",
            }}
          >
            {RESULT_ICON[r.result] ?? "·"}
          </span>
          <span>
            <b>{r.rule_id}</b> - {r.title}
            <br />
            <span className="muted">{r.detail}</span>
          </span>
        </div>
      ))}
    </div>
  );
}

export function PlanCards({ case: c }: { case: any }) {
  const { outcome } = useI18n();
  const plans = c.candidate_plans ?? [];
  const selected = c.recommendation?.selected_plan?.outcome_type;
  return (
    <>
      {plans.map((p: any, i: number) => {
        const valid = p.is_valid;
        const chosen = p.outcome_type === selected;
        const border = chosen ? "var(--green)" : valid ? "var(--line-2)" : "var(--danger)";
        return (
          <div
            key={i}
            className="card"
            style={{ borderLeft: `4px solid ${border}`, marginBottom: 10 }}
          >
            <div className="spread">
              <b style={{ fontFamily: "var(--serif)", fontSize: 18 }}>
                {outcome(p.outcome_type)}
              </b>
              <span className={`stamp ${chosen ? "green" : valid ? "ink" : "red"}`} style={{ fontSize: 10 }}>
                {chosen ? "★ Selected" : valid ? "Valid" : "Filtered out"}
              </span>
            </div>
            {p.new_installment_aed != null && p.new_installment_aed > 0 && (
              <div className="kv mono" style={{ marginTop: 6 }}>
                {aed(p.new_installment_aed)} · {pct(p.deduction_ratio)} of income ·{" "}
                {p.new_term_months ?? "-"} months
              </div>
            )}
            <div className="muted" style={{ marginTop: 4 }}>
              {p.rationale ?? ""}
            </div>
            {p.violated_rule_ids?.length > 0 && (
              <div style={{ color: "var(--danger)", fontSize: 13, marginTop: 4 }}>
                Violated: {p.violated_rule_ids.join(", ")}
              </div>
            )}
          </div>
        );
      })}
    </>
  );
}

export function ConfidenceBlock({ case: c }: { case: any }) {
  const { t } = useI18n();
  const conf = c.confidence ?? {};
  const risk = c.risk ?? {};
  const cv = conf.value ?? 0;
  return (
    <div className="grid grid-2">
      <div className="card">
        <div className="spread">
          <span className="eyebrow">{t("confidence")}</span>
          <span className="stamp ink" style={{ fontSize: 10 }}>
            {conf.band ?? "-"}
          </span>
        </div>
        <div style={{ fontFamily: "var(--mono)", fontSize: 32, marginTop: 6 }}>{pct(cv)}</div>
        <div className="progress">
          <span style={{ width: `${Math.min(Math.max(cv, 0), 1) * 100}%` }} />
        </div>
        <div className="caption">{(conf.reasons ?? []).join(" · ")}</div>
      </div>
      <div className="card">
        <div className="spread">
          <span className="eyebrow">{t("risk")}</span>
          <span className="stamp gold" style={{ fontSize: 10 }}>
            {risk.band ?? "-"}
          </span>
        </div>
        <div style={{ fontFamily: "var(--mono)", fontSize: 32, marginTop: 6 }}>
          {pct(risk.redefault_probability)}
        </div>
        <div className="caption">Drivers: {(risk.drivers ?? []).join(", ")}</div>
      </div>
    </div>
  );
}

export function MemoBlock({ case: c }: { case: any }) {
  const { t } = useI18n();
  const memo = c.rationale_memo;
  if (!memo) return null;
  return (
    <details className="expander" open>
      <summary>📄 {t("recommendation")} memo (EN / AR)</summary>
      <div style={{ marginTop: 10 }}>
        <b style={{ fontFamily: "var(--serif)", fontSize: 18 }}>{memo.title_en ?? ""}</b>
        <p>{memo.body_en ?? ""}</p>
        <div dir="rtl" style={{ borderTop: "1px solid var(--line)", paddingTop: 10 }}>
          <b style={{ fontFamily: "var(--serif)", fontSize: 18 }}>{memo.title_ar ?? ""}</b>
          <p>{memo.body_ar ?? ""}</p>
        </div>
      </div>
    </details>
  );
}

export function AuditTimeline({ events }: { events: any[] }) {
  return (
    <div className="timeline">
      {events.map((e, i) => {
        const rid = (e.rule_ids ?? []).join(", ");
        return (
          <div key={i} className="timeline-row">
            <span className="ts">{(e.timestamp ?? "").slice(11, 19)}</span> ·{" "}
            <b>{e.node || e.event_type}</b> - {e.message}
            {rid && <span className="muted"> [{rid}]</span>}
          </div>
        );
      })}
    </div>
  );
}

/* ── Live pipeline progress (load bar) ─────────────────────────────────────── */
export type StepState = "pending" | "active" | "done" | "skipped" | "failed";

export interface ProgressStep {
  key: string;
  label: string;
  state: StepState;
}

const STEP_GLYPH: Record<StepState, string> = {
  pending: "○",
  active: "◐",
  done: "✓",
  skipped: "⤼",
  failed: "✕",
};

export function PipelineProgress({
  steps,
  caption,
  failed,
}: {
  steps: ProgressStep[];
  caption?: string;
  failed?: boolean;
}) {
  const total = steps.length || 1;
  const settled = steps.filter((s) => s.state === "done" || s.state === "skipped" || s.state === "failed").length;
  const pctDone = Math.round((settled / total) * 100);
  const active = steps.find((s) => s.state === "active");

  return (
    <div className="card" style={{ marginTop: 16 }}>
      <div className="spread" style={{ alignItems: "baseline" }}>
        <span className="eyebrow">{failed ? "Stopped — request rejected" : active ? caption ?? active.label : "Assessment"}</span>
        <span className="mono caption">{pctDone}%</span>
      </div>
      <div className="progress" style={{ marginTop: 10 }}>
        <span
          style={{
            width: `${pctDone}%`,
            background: failed ? "var(--danger)" : undefined,
            transition: "width .35s ease",
          }}
        />
      </div>
      <div style={{ marginTop: 14, display: "grid", gap: 8 }}>
        {steps.map((s) => {
          const tone =
            s.state === "done"
              ? "var(--green)"
              : s.state === "failed"
                ? "var(--danger)"
                : s.state === "skipped"
                  ? "var(--muted)"
                  : s.state === "active"
                    ? "var(--ink)"
                    : "var(--line-2)";
          return (
            <div
              key={s.key}
              className="kv"
              style={{
                display: "grid",
                gridTemplateColumns: "22px 1fr",
                gap: 10,
                alignItems: "center",
                opacity: s.state === "pending" ? 0.5 : 1,
              }}
            >
              <span
                className={s.state === "active" ? "spinner" : ""}
                style={
                  s.state === "active"
                    ? undefined
                    : { color: tone, fontFamily: "var(--mono)", fontWeight: 700, textAlign: "center" }
                }
              >
                {s.state === "active" ? "" : STEP_GLYPH[s.state]}
              </span>
              <span style={{ color: tone, fontWeight: s.state === "active" ? 700 : 400 }}>
                {s.label}
                {s.state === "skipped" && <span className="muted"> · skipped</span>}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function Expander({
  summary,
  children,
  open,
}: {
  summary: ReactNode;
  children: ReactNode;
  open?: boolean;
}) {
  return (
    <details className="expander" open={open}>
      <summary>{summary}</summary>
      <div style={{ marginTop: 10 }}>{children}</div>
    </details>
  );
}
