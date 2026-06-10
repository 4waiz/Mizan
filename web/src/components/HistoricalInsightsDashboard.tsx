import { useEffect, useState } from "react";
import { useI18n } from "../i18n";
import { api } from "../api";
import { Alert, Metric, aed, pct } from "./ui";

// Risk-bucket key → CSS colour var, low→green … critical→red.
const BUCKET_COLOR: Record<string, string> = {
  low: "var(--green)",
  medium: "var(--ink)",
  high: "var(--gold)",
  severe: "#ea580c", // orange
  critical: "var(--danger)",
};

// Proactive-scan risk label → CSS colour var (same gradient).
const RISK_LABEL_COLOR: Record<string, string> = {
  Low: "var(--green)",
  Medium: "var(--ink)",
  High: "var(--gold)",
  Severe: "#ea580c",
  Critical: "var(--danger)",
};

function HBar({
  label,
  count,
  percent,
  color,
  countLabel,
}: {
  label: string;
  count: number;
  percent: number;
  color: string;
  countLabel: string;
}) {
  const w = Math.max(0, Math.min(100, percent));
  return (
    <div className="bar-row" style={{ gridTemplateColumns: "220px 1fr 110px" }}>
      <span className="lbl">{label}</span>
      <div className="bar-track">
        <div className="bar-fill" style={{ width: `${w}%`, background: color }} />
      </div>
      <span className="num" style={{ width: "auto" }}>
        {count} · {Math.round(percent)}%
        <span className="muted caption" style={{ display: "block" }}>
          {countLabel}
        </span>
      </span>
    </div>
  );
}

export default function HistoricalInsightsDashboard() {
  const { t } = useI18n();
  const [insights, setInsights] = useState<any | null>(null);
  const [scan, setScan] = useState<any | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api.organizerInsights().then(setInsights).catch((e) => setErr(String(e)));
    api.proactiveScan().then(setScan).catch(() => {
      /* non-fatal — the page still renders the aggregates it has */
    });
  }, []);

  if (err) return <Alert kind="err">{err}</Alert>;
  if (!insights) return <Alert kind="info">{t("loading")}</Alert>;

  // Graceful "no dataset" state — backend returns { loaded:false, message, … }.
  if (insights.loaded === false) {
    return (
      <Alert kind="info">
        <b>{t("insights_dataset_missing_title")}</b>
        <br />
        {insights.message ?? ""}
        <br />
        <span className="muted">{t("insights_dataset_missing_hint")}</span>
      </Alert>
    );
  }

  const totals = insights.totals ?? {};
  const medians = insights.medians ?? {};
  const split: Record<string, { count: number; percent: number }> =
    insights.request_type_split ?? {};
  const buckets = insights.risk_buckets ?? {};
  const distribution: any[] = buckets.distribution ?? [];
  const edge = insights.deduction_cap_edge_cases ?? {};
  const patterns: any[] = scan?.patterns ?? [];

  return (
    <>
      {/* ── KPI cards ───────────────────────────────────────────────────────── */}
      <div className="section-title">{t("insights_kpis")}</div>
      <div className="grid grid-3">
        <Metric k={t("kpi_total_cases")} v={(totals.raw_records ?? 0).toLocaleString("en-US")} />
        <Metric k={t("kpi_usable_records")} v={(totals.usable_records ?? 0).toLocaleString("en-US")} />
        <Metric k={t("kpi_years_covered")} v={totals.year_span ?? "-"} />
        <Metric k={t("kpi_median_overdue_amt")} v={aed(medians.over_due_amt)} />
        <Metric
          k={t("kpi_median_overdue_months")}
          v={`${medians.over_due_months ?? "-"} ${t("months_suffix")}`}
        />
        <Metric k={t("kpi_median_salary")} v={aed(medians.current_salary)} />
        <Metric k={t("kpi_median_current_emi")} v={aed(medians.current_emi_amt)} />
      </div>

      {/* ── Request-type split ──────────────────────────────────────────────── */}
      <div className="section-title">{t("insights_request_split")}</div>
      <div className="card bars">
        {Object.entries(split).map(([type, v]) => (
          <HBar
            key={type}
            label={type}
            count={v.count}
            percent={v.percent}
            color="var(--ink)"
            countLabel={t("count_label")}
          />
        ))}
      </div>

      {/* ── Overdue-month risk buckets ──────────────────────────────────────── */}
      <div className="section-title">{t("insights_risk_buckets")}</div>
      <div className="card bars">
        {distribution.map((b: any) => (
          <HBar
            key={b.key}
            label={`${b.label} (${b.range})`}
            count={b.count}
            percent={b.percent}
            color={BUCKET_COLOR[b.key] ?? "var(--ink)"}
            countLabel={t("count_label")}
          />
        ))}
      </div>

      {/* ── 20% deduction-cap edge cases ────────────────────────────────────── */}
      <div className="section-title">{t("insights_cap_edge")}</div>
      <div className="grid grid-2">
        <div className="card">
          <div className="eyebrow">{t("insights_cap_current_emi")}</div>
          <div style={{ fontFamily: "var(--mono)", fontSize: 40, marginTop: 8, color: "var(--danger)" }}>
            {pct((edge.current_emi?.over_cap_percent ?? 0) / 100)}
          </div>
          <div className="caption mono">
            {edge.current_emi?.over_cap ?? 0} / {edge.current_emi?.evaluated ?? 0}
          </div>
        </div>
        <div className="card">
          <div className="eyebrow">{t("insights_cap_new_emi")}</div>
          <div style={{ fontFamily: "var(--mono)", fontSize: 40, marginTop: 8, color: "var(--gold)" }}>
            {pct((edge.new_emi?.over_cap_percent ?? 0) / 100)}
          </div>
          <div className="caption mono">
            {edge.new_emi?.over_cap ?? 0} / {edge.new_emi?.evaluated ?? 0}
          </div>
        </div>
      </div>
      <Alert kind="warn">{t("insights_cap_explain")}</Alert>

      {/* ── Proactive scan table (anonymized) ───────────────────────────────── */}
      <div className="section-title">{t("insights_proactive_scan")}</div>
      <div className="caption muted" style={{ marginBottom: 10 }}>
        {t("insights_proactive_note")}
      </div>
      {patterns.length > 0 ? (
        <div className="table-scroll">
          <table className="tbl">
            <thead>
              <tr>
                <th>{t("col_request_type")}</th>
                <th>{t("col_risk")}</th>
                <th>{t("col_cases")}</th>
                <th>{t("col_median_score")}</th>
                <th>{t("col_median_overdue_months")}</th>
                <th>{t("col_salary_band")}</th>
                <th>{t("col_exceeds_cap")}</th>
                <th>{t("col_recommended_intervention")}</th>
              </tr>
            </thead>
            <tbody>
              {patterns.map((p: any, i: number) => (
                <tr key={i}>
                  <td>{p.request_type}</td>
                  <td>
                    <span
                      className="stamp"
                      style={{
                        fontSize: 10,
                        color: RISK_LABEL_COLOR[p.risk_label] ?? "var(--ink)",
                        borderColor: RISK_LABEL_COLOR[p.risk_label] ?? "var(--line)",
                      }}
                    >
                      {p.risk_label}
                    </span>
                  </td>
                  <td>{p.case_count}</td>
                  <td>{p.median_score}</td>
                  <td>{p.median_overdue_months}</td>
                  <td>{p.salary_band}</td>
                  <td>{pct((p.exceeds_cap_share ?? 0))}</td>
                  <td>{p.recommended_intervention}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <Alert kind="info">{t("insights_proactive_note")}</Alert>
      )}

      {/* ── What this proves ────────────────────────────────────────────────── */}
      <div className="section-title">{t("insights_what_proves")}</div>
      <Alert kind="info">{t("insights_what_proves_body")}</Alert>

      {/* ── Privacy note ────────────────────────────────────────────────────── */}
      <div className="caption muted" style={{ marginTop: 16 }}>
        🔒 {t("insights_privacy_note")}
      </div>
    </>
  );
}
