import { useEffect, useState } from "react";
import { useI18n } from "../i18n";
import { api } from "../api";
import { getSession } from "../session";
import {
  Band,
  Alert,
  ProfileCard,
  StatusPill,
  DecisionBadge,
  ConfidenceBlock,
  PlanCards,
  PolicyTable,
  MemoBlock,
  AuditTimeline,
  Expander,
  DocumentPreview,
} from "../components/ui";

export default function MyCase() {
  const { t } = useI18n();
  const s = getSession();
  const urlCase = new URLSearchParams(window.location.search).get("case");
  const [caseId, setCaseId] = useState(urlCase ?? s.lastRunCaseId ?? s.activeCaseId ?? "");
  const [caseData, setCaseData] = useState<any>(null);
  const [audit, setAudit] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);

  const load = async (id: string) => {
    if (!id) return;
    setErr(null);
    try {
      setCaseData(await api.getCase(id));
      setAudit(await api.audit(id));
    } catch (e) {
      setErr(String(e));
      setCaseData(null);
    }
  };

  useEffect(() => {
    load(caseId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const sla = caseData?.sla ?? {};

  return (
    <>
      <Band title={t("status")} subtitle={t("subtitle")} />

      <div className="grid form-toolbar" style={{ gridTemplateColumns: "1fr auto", alignItems: "end" }}>
        <div>
          <label className="field">Case ID</label>
          <input value={caseId} onChange={(e) => setCaseId(e.target.value)} />
        </div>
        <button className="btn" onClick={() => load(caseId)}>
          Load
        </button>
      </div>

      {!caseId && <Alert kind="info">Submit a request first, or paste a case ID.</Alert>}
      {err && <Alert kind="err">{err}</Alert>}

      {caseData && (
        <>
          <div
            className="grid split-2-1"
            style={{ gridTemplateColumns: "2fr 1fr", marginTop: 16 }}
          >
            <ProfileCard case={caseData} />
            <div className="card">
              <div className="muted">{t("status")}</div>
              <div style={{ margin: "8px 0" }}>
                <StatusPill status={caseData.status} />
              </div>
              {sla.processing_ms != null && (
                <div className="caption">
                  Decided in {Math.round(sla.processing_ms)} ms (legacy SLA:{" "}
                  {sla.legacy_sla_working_days ?? 5} working days).
                </div>
              )}
            </div>
          </div>

          <hr className="rule" />
          <DecisionBadge case={caseData} />
          <div style={{ marginTop: 12 }}>
            <ConfidenceBlock case={caseData} />
          </div>

          <div className="section-title">{t("candidate_plans")}</div>
          <PlanCards case={caseData} />

          <div className="section-title">{t("validation")}</div>
          <PolicyTable case={caseData} />

          <MemoBlock case={caseData} />

          {(caseData.document_inventory?.documents ?? []).length > 0 && (
            <>
              <div className="section-title">{t("evidence")}</div>
              {(caseData.document_inventory?.documents ?? []).map((d: any) => (
                <Expander
                  key={d.document_id}
                  summary={`📎 ${d.doc_type} · ${d.file_name ?? ""}`}
                >
                  {d.raw_text && <pre className="raw">{d.raw_text}</pre>}
                  <DocumentPreview
                    beneficiaryId={caseData.beneficiary?.beneficiary_id}
                    docType={d.doc_type}
                  />
                </Expander>
              ))}
            </>
          )}

          <Expander summary={`🧾 ${t("audit")}`}>
            {audit && <AuditTimeline events={audit.events} />}
          </Expander>
        </>
      )}
    </>
  );
}
