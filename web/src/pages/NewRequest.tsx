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

// Show ms under a second, otherwise seconds (e.g. "8.4 s").
function formatProcessing(ms: number): string {
  if (ms < 1000) return `${Math.round(ms)} ms`;
  return `${(ms / 1000).toFixed(1)} s`;
}

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

  // citizen document upload
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [reqDocs, setReqDocs] = useState<{
    required: string[];
    present: string[];
    missing: string[];
  } | null>(null);

  const s = getSession();

  const refreshRequired = async (caseId: string) => {
    try {
      setReqDocs(await api.requiredDocuments(caseId));
    } catch {
      /* non-fatal */
    }
  };

  // Create a fresh, empty application (clears any prior case + uploads).
  const startNew = async () => {
    if (!s.fixture) return;
    setErr(null);
    setRun(null);
    setFailure(null);
    setUploadMsg(null);
    setSteps([]);
    setCaseData(null);
    setReqDocs(null);
    try {
      const res = await api.intake(s.fixture, "application");
      setSession({ activeCaseId: res.case_id, lastRunCaseId: undefined });
      setCaseData(await api.getCase(res.case_id));
      await refreshRequired(res.case_id);
    } catch (e) {
      setErr(String(e));
    }
  };

  useEffect(() => {
    if (!s.fixture) return;
    (async () => {
      try {
        let caseId = s.activeCaseId;
        // Start a fresh empty application when none is active, the beneficiary
        // changed, or the active case has already been assessed.
        const stale = getSession().fixture !== s.fixture || !caseId || !!s.lastRunCaseId;
        if (stale) {
          const res = await api.intake(s.fixture!, "application");
          caseId = res.case_id;
          setSession({ activeCaseId: caseId, lastRunCaseId: undefined });
        }
        setCaseData(await api.getCase(caseId!));
        await refreshRequired(caseId!);
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
          {t("please_signin_citizen_pre")}{" "}
          <Link to="/login">{t("please_signin_citizen_link")}</Link> {t("please_signin_citizen_post")}
        </Alert>
      </>
    );

  const doRun = async () => {
    // The assessment always runs. If documents are still missing, the governed
    // pipeline detects it at the document-audit step and stops there with an
    // "additional information required" result — no verdict on an incomplete
    // file, but the citizen still sees the pipeline work through that far.
    const caseId = getSession().activeCaseId!;
    try {
      setReqDocs(await api.requiredDocuments(caseId));
    } catch {
      /* the pipeline is the source of truth; the banner is just a heads-up */
    }

    setBusy(true);
    setErr(null);
    setRun(null);
    setFailure(null);
    setActiveLabel("");
    setSteps([]);

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

  // Human-readable labels for the known document types (translated via i18n).
  const DOC_LABELS: Record<string, string> = {
    emirates_id: t("doc_emirates_id"),
    salary_certificate: t("doc_salary_certificate"),
    bank_statement: t("doc_bank_statement"),
    liability_letter: t("doc_liability_letter"),
    termination_letter: t("doc_termination_letter"),
    medical_report: t("doc_medical_report"),
    hardship_letter: t("doc_hardship_letter"),
    unknown: t("doc_unknown"),
  };

  const onUploadFiles = async (files: FileList | File[] | null | undefined) => {
    const list = files ? Array.from(files) : [];
    if (!list.length) return;
    const caseId = getSession().activeCaseId;
    if (!caseId) return;
    setUploading(true);
    setUploadMsg(null);
    setErr(null);
    try {
      // Send the real file bytes; the backend reads the text + figures off them.
      const updated = await api.uploadFiles(caseId, list);
      setCaseData(updated);
      await refreshRequired(caseId);
      setUploadMsg(
        `Uploaded ${list.length} document${list.length > 1 ? "s" : ""}: ` +
          list.map((f) => f.name).join(", "),
      );
    } catch (e) {
      setErr(String(e));
    } finally {
      setUploading(false);
    }
  };

  const docs = caseData?.document_inventory?.documents ?? [];
  const proc = run?.case?.sla?.processing_ms;
  const missing = reqDocs?.missing ?? [];
  const hasMissing = missing.length > 0;

  return (
    <>
      <Band title={t("new_request")} subtitle={t("subtitle")} />
      {err && <Alert kind="err">{err}</Alert>}

      <div className="section-title">1 · {t("profile")}</div>
      <div className="caption">{t("identity_autofill_note")}</div>
      {caseData && (
        <ProfileCard
          case={caseData}
          revealFinancials={reqDocs != null && reqDocs.missing.length === 0 && docs.length > 0}
        />
      )}

      <div className="section-title section-title--action">
        <span>2 · {t("documents")}</span>
        <button
          className="btn ghost"
          onClick={startNew}
          disabled={uploading || busy}
          title={t("start_new_application_title")}
        >
          {t("start_new_application")}
        </button>
      </div>

      {/* Required-documents checklist */}
      {reqDocs && (
        <div className="card" style={{ marginBottom: 12 }}>
          <div className="eyebrow" style={{ marginBottom: 8 }}>
            {t("required_documents")}
          </div>
          {reqDocs.required.map((rt) => {
            const have = reqDocs.present.includes(rt);
            return (
              <div key={rt} className="kv" style={{ color: have ? "var(--ok, #1e7d43)" : "#9aa0a6" }}>
                {have ? "✓" : "○"} <b>{DOC_LABELS[rt] ?? rt}</b>
                {have ? "" : t("not_uploaded")}
              </div>
            );
          })}
        </div>
      )}

      {/* Drag-and-drop upload zone */}
      <label
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          onUploadFiles(e.dataTransfer.files);
        }}
        style={{
          display: "block",
          border: `2px dashed ${dragOver ? "var(--accent, #0e8a8a)" : "#cdd3da"}`,
          background: dragOver ? "rgba(14,138,138,0.06)" : "var(--card, #fff)",
          borderRadius: 12,
          padding: "26px 18px",
          textAlign: "center",
          cursor: uploading ? "default" : "pointer",
        }}
      >
        <input
          type="file"
          multiple
          accept=".pdf,.png,.jpg,.jpeg"
          style={{ display: "none" }}
          disabled={uploading}
          onChange={(e) => {
            onUploadFiles(e.target.files);
            e.currentTarget.value = "";
          }}
        />
        <div style={{ marginBottom: 6 }}>
          {uploading ? (
            <span style={{ fontSize: 26 }}>⏳</span>
          ) : (
            <img
              src="/upload-icon.png"
              alt="Upload"
              style={{ height: 40, width: "auto", display: "inline-block" }}
            />
          )}
        </div>
        <div style={{ fontWeight: 600 }}>
          {uploading ? t("uploading") : t("dragdrop_documents")}
        </div>
        <div className="caption" style={{ marginTop: 4 }}>
          {t("dragdrop_hint")}
        </div>
      </label>

      {/* Uploaded files */}
      <div className="card" style={{ marginTop: 12 }}>
        {docs.length ? (
          docs.map((d: any) => (
            <div key={d.document_id} className="kv">
              📎 <b>{DOC_LABELS[d.doc_type] ?? d.doc_type}</b> · {d.file_name ?? ""} ·{" "}
              <code>{d.status}</code>
            </div>
          ))
        ) : (
          <span className="muted">{t("no_documents_yet")}</span>
        )}
        {uploadMsg && (
          <div className="caption" style={{ marginTop: 8, color: "var(--ok, #1e7d43)" }}>
            ✓ {uploadMsg}
          </div>
        )}
      </div>

      <div className="section-title">3 · {t("submit_and_assess")}</div>
      <p className="muted">{t("pipeline_explainer")}</p>

      {/* Heads-up only — the assessment still runs and stops at the document
          audit step if anything below is still missing. */}
      {hasMissing && (
        <Alert kind="warn">
          <b>{t("some_documents_missing")}</b>
          <ul style={{ margin: "8px 0 0 18px" }}>
            {missing.map((m) => (
              <li key={m}>{DOC_LABELS[m] ?? m}</li>
            ))}
          </ul>
        </Alert>
      )}

      <button
        className="btn primary"
        onClick={doRun}
        disabled={busy || !caseData || uploading}
      >
        {busy ? <span className="spinner" /> : "▶"} {t("run")}
      </button>

      {/* Live progress load bar */}
      {steps.length > 0 && (
        <PipelineProgress steps={steps} caption={activeLabel} failed={!!failure} />
      )}

      {/* Early exit — either an incomplete file (stopped at document audit) or a
          duplicate/active-application conflict (stopped at fraud/dedupe). */}
      {failure &&
        (/incomplete|document|SZHP-R4/i.test(failure) ? (
          <Alert kind="warn">
            <b>{t("additional_info_required")}</b>
            <br />
            {failure}
            <br />
            <span className="muted">{t("skipped_incomplete_note")}</span>
          </Alert>
        ) : (
          <Alert kind="err">
            <b>{t("assessment_failed_rejected")}</b>
            <br />
            {failure}
            <br />
            <span className="muted">{t("skipped_duplicate_note")}</span>
          </Alert>
        ))}

      {run && !failure && (
        <div style={{ marginTop: 24 }}>
          <Alert kind="ok">{t("assessment_complete")}</Alert>
          <div className="grid grid-3">
            <Metric
              k={t("processing_time")}
              v={proc != null ? formatProcessing(proc) : "-"}
            />
          </div>
          <div style={{ marginTop: 12 }}>
            <DecisionBadge case={run.case} />
          </div>
          <div className="section-title">{t("validation")}</div>
          <PolicyTable case={run.case} />
          <Link className="btn" to="/my-case">
            {t("view_full_result")}
          </Link>
        </div>
      )}

      {/* Even on rejection, show the decision + link to the record */}
      {run && failure && (
        <div style={{ marginTop: 16 }}>
          <DecisionBadge case={run.case} />
          <Link className="btn" to="/my-case" style={{ marginTop: 12 }}>
            {t("view_full_result")}
          </Link>
        </div>
      )}
    </>
  );
}
