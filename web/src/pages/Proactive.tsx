import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useI18n } from "../i18n";
import { api } from "../api";
import { setSession } from "../session";
import { Band, Alert, pct } from "../components/ui";

export default function Proactive() {
  const { t } = useI18n();
  const nav = useNavigate();
  const [alerts, setAlerts] = useState<any[] | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api.alerts().then(setAlerts).catch((e) => setErr(String(e)));
  }, []);

  const open = (id: string) => {
    setSession({ officerCaseId: id });
    nav("/officer/case");
  };

  return (
    <>
      <Band title={t("proactive")} subtitle="Insight · early-warning watchlist" />
      <p className="lead" style={{ fontSize: 20 }}>
        Cases flagged <b>before</b> they fall into serious arrears, ranked by re-default
        risk — enabling early officer outreach.
      </p>
      {err && <Alert kind="err">{err}</Alert>}
      {alerts?.length === 0 && <Alert kind="ok">No proactive alerts at present.</Alert>}

      {alerts?.map((a) => {
        const rp = a.redefault_probability;
        const tone = rp >= 0.6 ? "red" : rp >= 0.35 ? "gold" : "green";
        const color =
          rp >= 0.6 ? "var(--danger)" : rp >= 0.35 ? "var(--gold)" : "var(--green)";
        return (
          <div key={a.case_id} className="card" style={{ borderLeft: `4px solid ${color}` }}>
            <div className="spread" style={{ alignItems: "flex-start" }}>
              <div>
                <div style={{ fontFamily: "var(--serif)", fontSize: 20, fontWeight: 600 }}>
                  {a.beneficiary_name_en}
                </div>
                <div className="caption mono">{a.case_id}</div>
              </div>
              <span className={`stamp rotate ${tone}`}>
                {t("risk")} {pct(rp)}
              </span>
            </div>
            <div className="muted" style={{ marginTop: 8 }}>
              Drivers: {(a.drivers ?? []).join(", ")}
            </div>
            <div className="kv" style={{ marginTop: 4 }}>
              Suggested action: <b>{a.suggested_action}</b>
            </div>
            <button className="btn ghost" style={{ marginTop: 12 }} onClick={() => open(a.case_id)}>
              Open case →
            </button>
          </div>
        );
      })}
    </>
  );
}
