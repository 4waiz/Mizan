import { useEffect, useState } from "react";
import { useI18n } from "../i18n";
import { api } from "../api";
import { Band, Alert, Metric, pct } from "../components/ui";

export default function Replay() {
  const { t } = useI18n();
  const [s, setS] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api.replay().then(setS).catch((e) => setErr(String(e)));
  }, []);

  if (err) return (
    <>
      <Band title={t("replay_dashboard")} subtitle={t("replay_subtitle")} />
      <Alert kind="err">{err}</Alert>
    </>
  );
  if (!s) return <Band title={t("replay_dashboard")} subtitle={t("loading")} />;

  const byOutcome: Record<string, number> = s.by_outcome ?? {};
  const max = Math.max(1, ...Object.values(byOutcome));
  const cols = s.cases?.length ? Object.keys(s.cases[0]) : [];

  return (
    <>
      <Band title={t("replay_dashboard")} subtitle={t("replay_subtitle")} />

      <div className="grid grid-4">
        <Metric k={t("total_cases")} v={s.total_cases} />
        <Metric k={t("straight_through")} v={s.straight_through} delta={pct(s.straight_through_rate)} />
        <Metric k={t("human_review")} v={s.human_review} />
        <Metric k={t("manual_days_saved")} v={s.estimated_manual_working_days_saved} />
      </div>

      <div className="caption" style={{ marginTop: 8 }}>
        {t("avg_processing_pre")} {Math.round(s.avg_processing_ms)} ms · {t("avg_processing_sla")}{" "}
        {s.legacy_sla_working_days} {t("per_case")}
      </div>

      <div className="section-title">{t("outcomes")}</div>
      <div className="card bars">
        {Object.entries(byOutcome).map(([k, v]) => (
          <div key={k} className="bar-row">
            <span className="lbl">{k}</span>
            <div className="bar-track">
              <div className="bar-fill" style={{ width: `${(v / max) * 100}%` }} />
            </div>
            <span className="num">{v}</span>
          </div>
        ))}
      </div>

      <div className="section-title">{t("cases")}</div>
      <div className="table-scroll">
        <table className="tbl">
          <thead>
            <tr>
              {cols.map((c) => (
                <th key={c}>{c}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {s.cases?.map((row: any, i: number) => (
              <tr key={i}>
                {cols.map((c) => (
                  <td key={c}>{String(row[c])}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
