import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useI18n } from "../i18n";
import { api } from "../api";
import { setSession } from "../session";
import { Band, Alert, Metric, aed, pct } from "../components/ui";

export default function OfficerQueue() {
  const { t } = useI18n();
  const nav = useNavigate();
  const [queue, setQueue] = useState<any[] | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api.officerQueue().then(setQueue).catch((e) => setErr(String(e)));
  }, []);

  const open = (id: string) => {
    setSession({ officerCaseId: id });
    nav("/officer/case");
  };

  return (
    <>
      <Band title={t("queue")} subtitle="Officer · cases escalated for human review" />
      {err && <Alert kind="err">{err}</Alert>}
      {queue && (
        <div className="eyebrow" style={{ marginBottom: 16 }}>
          {queue.length} case(s) escalated · awaiting determination
        </div>
      )}

      {queue?.length === 0 && (
        <Alert kind="ok">
          Queue is empty - all recent cases were handled straight-through.
        </Alert>
      )}

      {queue?.map((item) => (
        <div key={item.case_id} className="card" style={{ borderLeft: "4px solid var(--gold)" }}>
          <div
            className="grid"
            style={{ gridTemplateColumns: "1.6fr 1fr 1fr auto", alignItems: "center", gap: 18 }}
          >
            <div>
              <div style={{ fontFamily: "var(--serif)", fontSize: 20, fontWeight: 600 }}>
                {item.beneficiary_name_en}
              </div>
              <div className="caption mono">{item.case_id}</div>
            </div>
            <Metric k={t("arrears")} v={aed(item.arrears_amount_aed)} />
            <Metric k={t("confidence")} v={pct(item.confidence)} />
            <button className="btn primary" onClick={() => open(item.case_id)}>
              Open →
            </button>
          </div>
          <div className="caption" style={{ marginTop: 12, paddingTop: 12, borderTop: "1px solid var(--line)" }}>
            ⚠ {item.escalation_reason ?? ""}
          </div>
        </div>
      ))}
    </>
  );
}
