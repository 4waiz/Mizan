import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useI18n } from "../i18n";
import { api } from "../api";
import { getSession, setSession } from "../session";
import { Band, Alert, ProfileCard, DecisionBadge, PolicyTable, Metric } from "../components/ui";

export default function NewRequest() {
  const { t } = useI18n();
  const [caseData, setCaseData] = useState<any>(null);
  const [run, setRun] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const s = getSession();

  useEffect(() => {
    if (!s.fixture) return;
    (async () => {
      try {
        let caseId = s.activeCaseId;
        if (getSession().fixture !== s.fixture || !caseId) {
          const res = await api.intake(s.fixture!, "application");
          caseId = res.case_id;
          setSession({ activeCaseId: caseId });
        }
        setCaseData(await api.getCase(caseId!));
      } catch (e) {
        setErr(String(e));
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [s.fixture]);

  if (!s.fixture)
    return (
      <>
        <Band title={t("new_request")} subtitle={t("subtitle")} />
        <Alert kind="warn">Please sign in on the Home page first.</Alert>
      </>
    );

  const doRun = async () => {
    setBusy(true);
    setErr(null);
    try {
      const r = await api.runCase(getSession().activeCaseId!);
      setRun(r);
      setSession({ lastRunCaseId: getSession().activeCaseId });
    } catch (e) {
      setErr(String(e));
    } finally {
      setBusy(false);
    }
  };

  const docs = caseData?.document_inventory?.documents ?? [];
  const proc = run?.case?.sla?.processing_ms;

  return (
    <>
      <Band title={t("new_request")} subtitle={t("subtitle")} />
      {err && <Alert kind="err">{err}</Alert>}

      <div className="section-title">1 · {t("profile")}</div>
      <div className="caption">Auto-filled from UAE PASS and MOEI records.</div>
      {caseData && <ProfileCard case={caseData} />}

      <div className="section-title">2 · {t("documents")}</div>
      <div className="card">
        {docs.length ? (
          docs.map((d: any) => (
            <div key={d.document_id} className="kv">
              📎 <b>{d.doc_type}</b> · {d.file_name ?? ""} · issued {d.issued_on ?? "-"} ·{" "}
              <code>{d.status}</code>
            </div>
          ))
        ) : (
          <span className="muted">No documents on file.</span>
        )}
      </div>
      <div className="caption">
        In production these are uploaded via the portal; here they are mocked in the
        document store.
      </div>

      <div className="section-title">3 · Submit &amp; assess</div>
      <p className="muted">
        Submitting runs the governed pipeline: document audit → fraud/dedupe →
        affordability → risk → policy solver → human-review gate.
      </p>

      <button className="btn primary" onClick={doRun} disabled={busy || !caseData}>
        {busy ? <span className="spinner" /> : "▶"} {t("run")}
      </button>

      {run && (
        <div style={{ marginTop: 24 }}>
          <Alert kind="ok">Assessment complete.</Alert>
          <div className="grid grid-3">
            <Metric
              k="Processing time"
              v={proc != null ? `${Math.round(proc)} ms` : "-"}
              delta="vs. 5 working days manually"
            />
          </div>
          <div style={{ marginTop: 12 }}>
            <DecisionBadge case={run.case} />
          </div>
          <div className="section-title">{t("validation")}</div>
          <PolicyTable case={run.case} />
          <Link className="btn" to="/my-case">
            ➡ View full result on My Case
          </Link>
        </div>
      )}
    </>
  );
}
