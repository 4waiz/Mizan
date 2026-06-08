import { useEffect, useState } from "react";
import { api } from "../api";
import { Band, Alert, Metric, pct } from "../components/ui";

export default function Replay() {
  const [s, setS] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api.replay().then(setS).catch((e) => setErr(String(e)));
  }, []);

  if (err) return (
    <>
      <Band title="Replay Dashboard" subtitle="Consistency & impact across all synthetic cases" />
      <Alert kind="err">{err}</Alert>
    </>
  );
  if (!s) return <Band title="Replay Dashboard" subtitle="Loading…" />;

  const byOutcome: Record<string, number> = s.by_outcome ?? {};
  const max = Math.max(1, ...Object.values(byOutcome));
  const cols = s.cases?.length ? Object.keys(s.cases[0]) : [];

  return (
    <>
      <Band title="Replay Dashboard" subtitle="Consistency & impact across all synthetic cases" />

      <div className="grid grid-4">
        <Metric k="Total cases" v={s.total_cases} />
        <Metric k="Straight-through" v={s.straight_through} delta={pct(s.straight_through_rate)} />
        <Metric k="Human review" v={s.human_review} />
        <Metric k="Manual days saved" v={s.estimated_manual_working_days_saved} />
      </div>

      <div className="caption" style={{ marginTop: 8 }}>
        Average automated processing time: {Math.round(s.avg_processing_ms)} ms · legacy SLA:{" "}
        {s.legacy_sla_working_days} working days per case.
      </div>

      <div className="section-title">Outcomes</div>
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

      <div className="section-title">Cases</div>
      <div style={{ overflowX: "auto" }}>
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
