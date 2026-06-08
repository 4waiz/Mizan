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
      <Band title={`📡 ${t("proactive")}`} subtitle={t("subtitle")} />
      <p className="muted">
        Cases flagged <b>before</b> they fall into serious arrears, ranked by re-default
        risk — enabling early officer outreach.
      </p>
      {err && <Alert kind="err">{err}</Alert>}
      {alerts?.length === 0 && <Alert kind="ok">No proactive alerts at present.</Alert>}

      {alerts?.map((a) => {
        const rp = a.redefault_probability;
        const color =
          rp >= 0.6 ? "var(--danger)" : rp >= 0.35 ? "var(--gov-gold)" : "var(--gov-green)";
        return (
          <div key={a.case_id} className="card" style={{ borderLeft: `6px solid ${color}` }}>
            <b>{a.beneficiary_name_en}</b> · <code>{a.case_id}</code>
            <div className="kv">
              {t("risk")}: <b style={{ color }}>{pct(rp)}</b>
            </div>
            <div className="muted">Drivers: {(a.drivers ?? []).join(", ")}</div>
            <div className="kv">
              Suggested action: <b>{a.suggested_action}</b>
            </div>
            <button
              className="btn"
              style={{ marginTop: 8 }}
              onClick={() => open(a.case_id)}
            >
              Open case {a.case_id}
            </button>
          </div>
        );
      })}
    </>
  );
}
