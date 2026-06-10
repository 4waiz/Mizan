import { useEffect, useState } from "react";
import { useI18n } from "../i18n";
import { api } from "../api";
import { getSession } from "../session";
import {
  Band,
  Alert,
  ProfileCard,
  DecisionBadge,
  PlanCards,
  PolicyTable,
  ConfidenceBlock,
  AuditTimeline,
  Expander,
  DocumentPreview,
} from "../components/ui";

const OUTCOMES = [
  "UPDATE_INSTALLMENT",
  "TRANSFER_ARREARS",
  "MAINTAIN_INSTALLMENT",
  "REQUEST_MORE_INFO",
  "REJECT_ACTIVE_REQUEST",
];

export default function OfficerCase() {
  const { t, outcome } = useI18n();
  const urlCase = new URLSearchParams(window.location.search).get("case");
  const [caseId, setCaseId] = useState(urlCase ?? getSession().officerCaseId ?? "");
  const [caseData, setCaseData] = useState<any>(null);
  const [audit, setAudit] = useState<any>(null);
  const [officerId, setOfficerId] = useState(getSession().officerId ?? "officer-001");
  const [notes, setNotes] = useState("");
  const [msg, setMsg] = useState<{ kind: "ok" | "err" | "info"; text: string } | null>(null);
  const [err, setErr] = useState<string | null>(null);

  // override form
  const [oc, setOc] = useState(OUTCOMES[0]);
  const [inst, setInst] = useState(0);
  const [term, setTerm] = useState(0);

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

  const after = (text: string, kind: "ok" | "err" | "info" = "ok") => {
    setMsg({ kind, text });
    load(caseId);
  };

  const approve = async () => {
    try {
      await api.approve(caseId, officerId, notes || null);
      after(t("approved_logged"));
    } catch (e) {
      after(String(e), "err");
    }
  };
  const reject = async () => {
    try {
      await api.reject(caseId, officerId, notes || null);
      after(t("rejected_logged"), "info");
    } catch (e) {
      after(String(e), "err");
    }
  };
  const doOverride = async () => {
    try {
      await api.override(caseId, officerId, oc, inst || null, term || null, notes || null);
      after(t("override_applied"));
    } catch (e) {
      after(String(e), "err");
    }
  };

  const docs = caseData?.document_inventory?.documents ?? [];
  const ef = caseData?.extracted_fields ?? {};
  const flags = caseData?.fraud_flags?.flags ?? [];
  const od = caseData?.officer_decision;

  return (
    <>
      <Band title={t("case_review")} subtitle={t("case_review_subtitle")} />

      <div className="grid form-toolbar" style={{ gridTemplateColumns: "1fr auto auto", alignItems: "end" }}>
        <div>
          <label className="field">{t("case_id")}</label>
          <input value={caseId} onChange={(e) => setCaseId(e.target.value)} />
        </div>
        <div>
          <label className="field">{t("officer_id")}</label>
          <input value={officerId} onChange={(e) => setOfficerId(e.target.value)} />
        </div>
        <button className="btn" onClick={() => load(caseId)}>
          {t("load")}
        </button>
      </div>

      {!caseId && <Alert kind="info">{t("open_from_queue")}</Alert>}
      {err && <Alert kind="err">{err}</Alert>}
      {msg && <Alert kind={msg.kind}>{msg.text}</Alert>}

      {caseData && (
        <div className="grid split-3-2" style={{ gridTemplateColumns: "3fr 2fr", marginTop: 16 }}>
          {/* LEFT */}
          <div>
            <ProfileCard case={caseData} />
            <DecisionBadge case={caseData} />
            {caseData.escalation_reason && (
              <Alert kind="warn">
                <b>{t("escalation")}:</b> {caseData.escalation_reason}
              </Alert>
            )}

            <div className="section-title">{t("candidate_plans")}</div>
            <PlanCards case={caseData} />

            <div className="section-title">{t("policy_checks")}</div>
            <PolicyTable case={caseData} />

            <div className="section-title">{t("evidence")}</div>
            {docs.map((d: any) => (
              <Expander key={d.document_id} summary={`📎 ${d.doc_type} · ${d.file_name ?? ""}`}>
                <pre className="raw">{d.raw_text || t("no_extracted_text")}</pre>
                <DocumentPreview
                  beneficiaryId={caseData.beneficiary?.beneficiary_id}
                  docType={d.doc_type}
                />
              </Expander>
            ))}
            <div className="caption">
              {t("extracted_prefix")} income={ef.declared_monthly_income_aed} · employer=
              {ef.employer_name} · confidence={ef.extraction_confidence}
            </div>
            {flags.length > 0 && (
              <Alert kind="err">
                {t("fraud_flags_prefix")}{" "}
                {flags.map((f: any) => `${f.code} (${f.severity})`).join(", ")}
              </Alert>
            )}
          </div>

          {/* RIGHT */}
          <div>
            <ConfidenceBlock case={caseData} />
            <div className="card">
              <div className="section-title" style={{ marginTop: 0 }}>
                {t("decision")}
              </div>
              <label className="field">{t("notes")}</label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder={t("rationale_placeholder")}
              />

              <button
                className="btn primary block"
                style={{ marginTop: 12 }}
                onClick={approve}
              >
                ✅ {t("approve")}
              </button>

              <Expander summary={`✏️ ${t("override")}`}>
                <label className="field">{t("new_outcome")}</label>
                <select value={oc} onChange={(e) => setOc(e.target.value)}>
                  {OUTCOMES.map((o) => (
                    <option key={o} value={o}>
                      {outcome(o)}
                    </option>
                  ))}
                </select>
                <div className="grid grid-2" style={{ marginTop: 8 }}>
                  <div>
                    <label className="field">{t("new_installment_aed")}</label>
                    <input
                      type="number"
                      value={inst}
                      onChange={(e) => setInst(Number(e.target.value))}
                    />
                  </div>
                  <div>
                    <label className="field">{t("new_term_months")}</label>
                    <input
                      type="number"
                      value={term}
                      onChange={(e) => setTerm(Number(e.target.value))}
                    />
                  </div>
                </div>
                <button className="btn block" style={{ marginTop: 10 }} onClick={doOverride}>
                  {t("apply_override")}
                </button>
              </Expander>

              <button className="btn danger block" style={{ marginTop: 10 }} onClick={reject}>
                ❌ {t("reject")}
              </button>

              {od && (
                <Alert kind="info">
                  {t("last_action")} <b>{od.action}</b> · {od.officer_id} · {od.notes ?? ""}
                </Alert>
              )}
            </div>
          </div>
        </div>
      )}

      {caseData && (
        <Expander summary={`🧾 ${t("audit")}`}>
          {audit && <AuditTimeline events={audit.events} />}
        </Expander>
      )}
    </>
  );
}
