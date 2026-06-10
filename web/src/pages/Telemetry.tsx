/**
 * AI Telemetry — live proof-of-work panel (officer side).
 *
 * Consumes the telemetry the FastAPI backend persists on the CaseState and
 * streams over the existing SSE `/run/stream` feed. It renders:
 *   • the active LLM provider + exact model name,
 *   • live-updating cumulative token counters (prompt / completion / total),
 *   • a scrolling terminal-style feed of each per-node inference call.
 *
 * It is defensive by design: every field is optional and defaults sensibly, so
 * a run with missing metadata (or the deterministic mock) renders cleanly
 * instead of crashing. When the backend is live on Groq, every uploaded case
 * visibly burns tokens here.
 */
import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "../api";
import { Band, Alert } from "../components/ui";
import { useI18n } from "../i18n";

// ── Telemetry shapes (mirror the backend Pydantic models) ────────────────────
interface TokenUsage {
  prompt_tokens?: number;
  completion_tokens?: number;
  total_tokens?: number;
}
interface ComputationLogEntry {
  seq: number;
  node: string;
  task: string;
  provider: string;
  model: string;
  usage?: TokenUsage;
  finish_reason?: string | null;
  live?: boolean;
  duration_ms?: number | null;
  timestamp: string;
}
interface TelemetrySnapshot {
  provider: string;
  model: string;
  live: boolean;
  total_calls: number;
  cumulative_usage: TokenUsage;
  computation_log: ComputationLogEntry[];
}

const EMPTY: TelemetrySnapshot = {
  provider: "—",
  model: "—",
  live: false,
  total_calls: 0,
  cumulative_usage: { prompt_tokens: 0, completion_tokens: 0, total_tokens: 0 },
  computation_log: [],
};

const num = (n: number | null | undefined) => (n ?? 0).toLocaleString("en-US");

// A line in the terminal feed: either a system note or a recorded LLM call.
type FeedLine =
  | { kind: "sys"; text: string }
  | { kind: "call"; entry: ComputationLogEntry };

export default function Telemetry() {
  const { t } = useI18n();
  const [cases, setCases] = useState<any[] | null>(null);
  const [caseId, setCaseId] = useState<string>("");
  const [snap, setSnap] = useState<TelemetrySnapshot>(EMPTY);
  const [feed, setFeed] = useState<FeedLine[]>([]);
  const [running, setRunning] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const termRef = useRef<HTMLDivElement>(null);

  // Smoothly animated counters so the total visibly "ticks up".
  const displayTotal = useCountUp(snap.cumulative_usage.total_tokens ?? 0);

  // Load the case list once for the picker.
  useEffect(() => {
    api
      .listCases()
      .then((rows) => {
        setCases(rows);
        if (rows?.length && !caseId) setCaseId(rows[0].case_id);
      })
      .catch((e) => setErr(String(e)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Auto-scroll the terminal as new lines arrive.
  useEffect(() => {
    const el = termRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [feed]);

  const pushLine = (line: FeedLine) => setFeed((prev) => [...prev, line]);

  // When picking a case that already ran, hydrate its persisted telemetry.
  const loadPersisted = async (id: string) => {
    setErr(null);
    try {
      const c = await api.getCase(id);
      const telem: TelemetrySnapshot = { ...EMPTY, ...(c?.telemetry ?? {}) };
      setSnap(telem);
      setFeed([
        { kind: "sys", text: `// loaded persisted telemetry for ${id}` },
        ...telem.computation_log.map(
          (entry) => ({ kind: "call", entry }) as FeedLine,
        ),
        {
          kind: "sys",
          text: telem.live
            ? `// ${telem.total_calls} live call(s) · ${num(
                telem.cumulative_usage.total_tokens,
              )} tokens burned via ${telem.provider}/${telem.model}`
            : `// no live inference recorded (mock / not yet run)`,
        },
      ]);
    } catch (e) {
      setErr(String(e));
    }
  };

  useEffect(() => {
    if (caseId) loadPersisted(caseId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [caseId]);

  // Run the pipeline live and stream telemetry into the terminal feed.
  const runLive = async () => {
    if (!caseId || running) return;
    setRunning(true);
    setErr(null);
    setSnap(EMPTY);
    setFeed([{ kind: "sys", text: `$ mizan run --live ${caseId}` }]);

    try {
      await api.runCaseStream(caseId, (ev: any) => {
        switch (ev?.type) {
          case "start":
            pushLine({ kind: "sys", text: `// pipeline started · ${ev.total} nodes` });
            break;
          case "step":
            pushLine({ kind: "sys", text: `▸ ${ev.active ?? ev.label ?? ev.key}…` });
            break;
          case "telemetry": {
            // Live token usage for one or more node inference calls.
            setSnap((prev) => ({
              ...prev,
              provider: ev.provider ?? prev.provider,
              model: ev.model ?? prev.model,
              live: ev.live ?? prev.live,
              total_calls: ev.total_calls ?? prev.total_calls,
              cumulative_usage: ev.cumulative_usage ?? prev.cumulative_usage,
              computation_log: [
                ...prev.computation_log,
                ...(ev.new_entries ?? []),
              ],
            }));
            for (const entry of ev.new_entries ?? []) {
              pushLine({ kind: "call", entry });
            }
            break;
          }
          case "skipped":
            pushLine({ kind: "sys", text: `⤼ skipped ${ev.label ?? ev.key} (${ev.reason ?? ""})` });
            break;
          case "failed":
            pushLine({ kind: "sys", text: `✕ ${ev.reason ?? "stopped"}` });
            break;
          case "complete": {
            const telem: TelemetrySnapshot = {
              ...EMPTY,
              ...(ev.case?.telemetry ?? {}),
            };
            setSnap(telem);
            pushLine({
              kind: "sys",
              text: telem.live
                ? `✓ complete · ${telem.total_calls} live call(s) · ${num(
                    telem.cumulative_usage.total_tokens,
                  )} tokens burned`
                : `✓ complete · mock run (0 tokens)`,
            });
            break;
          }
        }
      });
    } catch (e) {
      setErr(String(e));
      pushLine({ kind: "sys", text: `✕ error: ${String(e)}` });
    } finally {
      setRunning(false);
    }
  };

  const cu = snap.cumulative_usage ?? EMPTY.cumulative_usage;

  return (
    <>
      <Band
        title={t("telemetry")}
        subtitle="Live AI Computation · Proof-of-Work"
        fileRef="TELEMETRY · القياس"
      />

      {err && <Alert kind="err">{err}</Alert>}

      {/* Provider / model status strip */}
      <div className="telem-strip">
        <div className="telem-pill">
          <span className="telem-k">PROVIDER</span>
          <span className="telem-v">{(snap.provider ?? "—").toUpperCase()}</span>
        </div>
        <div className="telem-pill">
          <span className="telem-k">MODEL</span>
          <span className="telem-v mono">{snap.model ?? "—"}</span>
        </div>
        <div className="telem-pill">
          <span className="telem-k">STATUS</span>
          <span className={`telem-v ${snap.live ? "live" : "idle"}`}>
            <span className={`telem-dot ${snap.live ? "on" : ""}`} />
            {snap.live ? "LIVE · BURNING TOKENS" : "IDLE / MOCK"}
          </span>
        </div>
        <div className="telem-pill">
          <span className="telem-k">INFERENCE CALLS</span>
          <span className="telem-v mono">{num(snap.total_calls)}</span>
        </div>
      </div>

      {/* Big live token counters */}
      <div className="telem-counters">
        <Counter label="TOTAL TOKENS" value={displayTotal} big />
        <Counter label="PROMPT" value={cu.prompt_tokens ?? 0} />
        <Counter label="COMPLETION" value={cu.completion_tokens ?? 0} />
      </div>

      {/* Controls */}
      <div className="telem-controls card">
        <label className="caption" htmlFor="telem-case">
          Case
        </label>
        <select
          id="telem-case"
          className="telem-select mono"
          value={caseId}
          disabled={running}
          onChange={(e) => setCaseId(e.target.value)}
        >
          {(cases ?? []).map((c) => (
            <option key={c.case_id} value={c.case_id}>
              {c.case_id} · {c.beneficiary?.full_name_en ?? c.status ?? ""}
            </option>
          ))}
        </select>
        <button className="btn primary" onClick={runLive} disabled={running || !caseId}>
          {running ? "Running…" : "▶ Run live inference"}
        </button>
      </div>

      {/* Terminal-style scrolling computation feed */}
      <div className="telem-term" ref={termRef}>
        <div className="telem-term-head">
          <span className="dot r" />
          <span className="dot y" />
          <span className="dot g" />
          <span className="telem-term-title mono">
            mizan@groq — computation log
          </span>
        </div>
        <div className="telem-term-body mono">
          {feed.length === 0 && (
            <div className="telem-row sys">// no computations yet — run a case to burn tokens</div>
          )}
          {feed.map((line, i) =>
            line.kind === "sys" ? (
              <div key={i} className="telem-row sys">
                {line.text}
              </div>
            ) : (
              <CallRow key={i} entry={line.entry} />
            ),
          )}
          {running && <div className="telem-row cursor">▋</div>}
        </div>
      </div>
    </>
  );
}

// ── One inference call rendered as a terminal line ───────────────────────────
function CallRow({ entry }: { entry: ComputationLogEntry }) {
  const u = entry.usage ?? {};
  const ms = entry.duration_ms != null ? `${Math.round(entry.duration_ms)}ms` : "—";
  return (
    <div className={`telem-row call ${entry.live ? "live" : "mock"}`}>
      <span className="telem-seq">[{String(entry.seq).padStart(2, "0")}]</span>{" "}
      <span className="telem-node">{entry.node}</span>
      <span className="telem-task"> · {entry.task}</span>{" "}
      <span className="telem-model">{entry.provider}/{entry.model}</span>{" "}
      <span className="telem-tokens">
        prompt=<b>{num(u.prompt_tokens)}</b> completion=<b>{num(u.completion_tokens)}</b>{" "}
        total=<b>{num(u.total_tokens)}</b>
      </span>{" "}
      <span className="telem-meta">
        ({entry.finish_reason ?? "—"} · {ms} · {entry.live ? "LIVE" : "mock"})
      </span>
    </div>
  );
}

function Counter({ label, value, big }: { label: string; value: number; big?: boolean }) {
  return (
    <div className={`telem-counter ${big ? "big" : ""}`}>
      <div className="telem-counter-v mono">{num(value)}</div>
      <div className="telem-counter-k">{label}</div>
    </div>
  );
}

// Animate a number toward its target so counters visibly ramp up.
function useCountUp(target: number): number {
  const [val, setVal] = useState(0);
  const raf = useRef<number | null>(null);
  const from = useRef(0);
  const start = useRef(0);

  useEffect(() => {
    from.current = val;
    start.current = 0;
    const dur = 600;
    const tick = (ts: number) => {
      if (!start.current) start.current = ts;
      const p = Math.min(1, (ts - start.current) / dur);
      const eased = 1 - Math.pow(1 - p, 3);
      setVal(Math.round(from.current + (target - from.current) * eased));
      if (p < 1) raf.current = requestAnimationFrame(tick);
    };
    raf.current = requestAnimationFrame(tick);
    return () => {
      if (raf.current) cancelAnimationFrame(raf.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [target]);

  return val;
}
