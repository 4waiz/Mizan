import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useI18n } from "../i18n";
import { api } from "../api";
import { getSession, setSession } from "../session";
import {
  Band,
  Alert,
  ProfileCard,
  DecisionBadge,
  PolicyTable,
  Metric,
  PipelineProgress,
  type ProgressStep,
} from "../components/ui";

export default function NewRequest() {
  const { t } = useI18n();
  const [caseData, setCaseData] = useState<any>(null);
  const [run, setRun] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  // live pipeline progress
  const [steps, setSteps] = useState<ProgressStep[]>([]);
  const [activeLabel, setActiveLabel] = useState<string>("");
  const [failure, setFailure] = useState<string | null>(null);

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
        <Alert kind="warn">
          Please <Link to="/login">sign in to the Citizen Portal</Link> first.
        </Alert>
      </>
    );

  const doRun = async () => {
    setBusy(true);
    setErr(null);
    setRun(null);
    setFailure(null);
    setActiveLabel("");
    setSteps([]);

    const caseId = getSession().activeCaseId!;
    try {
      await api.runCaseStream(caseId, (ev) => {
        switch (ev.type) {
          case "start":
            setSteps(
              ev.steps.map((st: any) => ({ key: st.key, label: st.label, state: "pending" as const })),
            );
            break;
          case "step":
            setActiveLabel(ev.active);
            setSteps((prev) =>
              prev.map((p) =>
                p.key === ev.key ? { ...p, state: "active" } : p,
              ),
            );
            break;
          case "done":
            setSteps((prev) =>
              prev.map((p) =>
                p.key === ev.key
                  ? { ...p, state: ev.status === "conflict" ? "failed" : "done" }
                  : p,
              ),
            );
            break;
          case "skipped":
            setSteps((prev) =>
              prev.map((p) => (p.key === ev.key ? { ...p, state: "skipped" } : p)),
            );
            break;
          case "failed":
            setFailure(ev.reason);
            break;
          case "complete":
            setRun({ case: ev.case });
            setSession({ lastRunCaseId: caseId });
            break;
        }
      });
    } catch (e) {
      setErr(String(e));
    } finally {
      setBusy(false);
      setActiveLabel("");
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
        affordability → risk → policy solver → human-review gate. A duplicate or
        active application is rejected immediately at the fraud/dedupe step.
      </p>

      <button className="btn primary" onClick={doRun} disabled={busy || !caseData}>
        {busy ? <span className="spinner" /> : "▶"} {t("run")}
      </button>

      {/* Live progress load bar */}
      {steps.length > 0 && (
        <PipelineProgress steps={steps} caption={activeLabel} failed={!!failure} />
      )}

      {/* Hard rejection (early exit on conflict) */}
      {failure && (
        <Alert kind="err">
          <b>Assessment failed — request rejected.</b>
          <br />
          {failure}
          <br />
          <span className="muted">
            Affordability and risk analysis were skipped: there is no point assessing a
            duplicate request.
          </span>
        </Alert>
      )}

      {run && !failure && (
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

      {/* Even on rejection, show the decision + link to the record */}
      {run && failure && (
        <div style={{ marginTop: 16 }}>
          <DecisionBadge case={run.case} />
          <Link className="btn" to="/my-case" style={{ marginTop: 12 }}>
            ➡ View full result on My Case
          </Link>
        </div>
      )}
    </>
  );
}
