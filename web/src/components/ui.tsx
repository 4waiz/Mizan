import type { ReactNode } from "react";
import { useI18n } from "../i18n";

export const aed = (n: number | null | undefined) =>
  `AED ${Math.round(n ?? 0).toLocaleString("en-US")}`;
export const pct = (v: number | null | undefined) =>
  v == null ? "—" : `${Math.round(v * 100)}%`;

export function Band({ title, subtitle }: { title: ReactNode; subtitle?: string }) {
  return (
    <div className="band">
      <h1>{title}</h1>
      {subtitle && <p>{subtitle}</p>}
    </div>
  );
}

export function Metric({
  k,
  v,
  delta,
}: {
  k: string;
  v: ReactNode;
  delta?: ReactNode;
}) {
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

const STATUS_COLOR: Record<string, string> = {
  auto_approved: "var(--gov-green)",
  officer_approved: "var(--gov-green)",
  pending_human_review: "var(--gov-gold)",
  info_requested: "var(--gov-gold)",
  rejected: "var(--danger)",
  officer_rejected: "var(--danger)",
  officer_overridden: "var(--info)",
  processing: "#555",
  intake: "#555",
};

export function StatusPill({ status }: { status: string }) {
  return (
    <span className="pill" style={{ background: STATUS_COLOR[status] ?? "#555" }}>
      {status.replace(/_/g, " ").toUpperCase()}
    </span>
  );
}

export function ProfileCard({ case: c }: { case: any }) {
  const { t } = useI18n();
  const b = c.beneficiary ?? {};
  const loan = c.loan ?? {};
  const arr = c.arrears ?? {};
  return (
    <div className="card">
      <div className="grid grid-3">
        <div>
          <div style={{ fontWeight: 700 }}>
            {b.full_name_en ?? "—"} · {b.full_name_ar ?? ""}
          </div>
          <div className="caption">
            {b.emirates_id_masked ?? ""} · {b.emirate ?? ""}
          </div>
          <div className="caption">
            {b.employment_status ?? ""} · {b.employer_name ?? "—"}
          </div>
        </div>
        <div className="grid" style={{ gap: 8 }}>
          <Metric k={t("income")} v={aed(b.monthly_income_aed)} />
          <Metric k={t("installment")} v={aed(loan.current_installment_aed)} />
        </div>
        <div className="grid" style={{ gap: 8 }}>
          <Metric k={t("arrears")} v={aed(arr.arrears_amount_aed)} />
          <Metric k="Hardship" v={b.hardship_type ?? "none"} />
        </div>
      </div>
    </div>
  );
}

export function DecisionBadge({ case: c }: { case: any }) {
  const { t, outcome } = useI18n();
  const rec = c.recommendation ?? {};
  const review = c.needs_human_review;
  const color = review ? "var(--gov-gold)" : "var(--gov-green)";
  return (
    <div className="decision" style={{ borderLeftColor: color }}>
      <div className="muted">{t("recommendation")}</div>
      <div className="label" style={{ color }}>
        {outcome(rec.outcome_type)}
      </div>
      <div className="kv" dir="rtl">
        {rec.decision_label_ar ?? ""}
      </div>
      <div className="muted" style={{ marginTop: 6 }}>
        {review ? `⚠ ${c.escalation_reason ?? ""}` : "✓ Straight-through (auto-issued)"}
      </div>
    </div>
  );
}

const RESULT_ICON: Record<string, string> = {
  pass: "✅",
  fail: "❌",
  warn: "⚠️",
  not_applicable: "➖",
};

export function PolicyTable({ case: c }: { case: any }) {
  const rows = c.policy_checks ?? [];
  if (!rows.length) return <Alert kind="info">No policy checks recorded.</Alert>;
  return (
    <div className="card">
      {rows.map((r: any, i: number) => (
        <div key={i} className="kv" style={{ marginBottom: 8 }}>
          {RESULT_ICON[r.result] ?? ""} <b>{r.rule_id}</b> — {r.title}
          <br />
          <span className="muted">{r.detail}</span>
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
        const border = chosen
          ? "var(--gov-green)"
          : valid
            ? "var(--line)"
            : "var(--danger)";
        const tag = chosen ? "★ SELECTED" : valid ? "valid" : "filtered out";
        return (
          <div
            key={i}
            className="card"
            style={{ borderLeft: `6px solid ${border}` }}
          >
            <b>{outcome(p.outcome_type)}</b> <span className="muted">· {tag}</span>
            {p.new_installment_aed != null && p.new_installment_aed > 0 && (
              <div className="kv">
                Installment <b>{aed(p.new_installment_aed)}</b> ·{" "}
                {pct(p.deduction_ratio)} of income · {p.new_term_months ?? "—"} months
              </div>
            )}
            <div className="muted">{p.rationale ?? ""}</div>
            {p.violated_rule_ids?.length > 0 && (
              <div style={{ color: "var(--danger)", fontSize: 13 }}>
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
          <span className="muted">{t("confidence")}</span>
          <span className="muted">{conf.band ?? ""}</span>
        </div>
        <div className="metric" style={{ border: "none", padding: 0 }}>
          <div className="v">{pct(cv)}</div>
        </div>
        <div className="progress">
          <span style={{ width: `${Math.min(Math.max(cv, 0), 1) * 100}%` }} />
        </div>
        <div className="caption">{(conf.reasons ?? []).join(" · ")}</div>
      </div>
      <div className="card">
        <div className="spread">
          <span className="muted">{t("risk")}</span>
          <span className="muted">{risk.band ?? ""}</span>
        </div>
        <div className="metric" style={{ border: "none", padding: 0 }}>
          <div className="v">{pct(risk.redefault_probability)}</div>
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
      <div style={{ marginTop: 8 }}>
        <b>{memo.title_en ?? ""}</b>
        <p>{memo.body_en ?? ""}</p>
        <div dir="rtl">
          <b>{memo.title_ar ?? ""}</b>
          <p>{memo.body_ar ?? ""}</p>
        </div>
      </div>
    </details>
  );
}

export function AuditTimeline({ events }: { events: any[] }) {
  return (
    <div>
      {events.map((e, i) => {
        const rid = (e.rule_ids ?? []).join(", ");
        return (
          <div key={i} className="timeline-row">
            🕒 <span className="muted">{(e.timestamp ?? "").slice(11, 19)}</span> ·{" "}
            <b>{e.node || e.event_type}</b> — {e.message}
            {rid && <span className="muted"> [{rid}]</span>}
          </div>
        );
      })}
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
      <div style={{ marginTop: 8 }}>{children}</div>
    </details>
  );
}
