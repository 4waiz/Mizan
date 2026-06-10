import { useNavigate } from "react-router-dom";
import { useI18n } from "../i18n";
import { getSession, isCitizen, isOfficer } from "../session";
import { Band, Alert } from "../components/ui";

export default function Home() {
  const { t } = useI18n();
  const nav = useNavigate();
  const s = getSession();
  const citizen = isCitizen(s);
  const officer = isOfficer(s);

  return (
    <>
      <Band title="An autonomous case officer" subtitle="Sheikh Zayed Housing Programme · MOEI" />

      <p className="lead">
        Mizan turns the manual <b>five-working-day</b> arrears rescheduling review into an{" "}
        <b>instant, explainable, auditable</b> decision - escalating only the exceptional
        cases to a human.
      </p>

      {(citizen || officer) && (
        <Alert kind="info">
          Signed in as <b>{citizen ? s.name : s.officerName}</b> ({citizen ? "Citizen" : "Officer"}).{" "}
          <a
            href={citizen ? "/new-request" : "/officer/queue"}
            onClick={(e) => {
              e.preventDefault();
              nav(citizen ? "/new-request" : "/officer/queue");
            }}
          >
            Go to your {citizen ? "portal" : "dashboard"} →
          </a>
        </Alert>
      )}

      <div className="section-title">Choose your portal</div>
      <div className="grid grid-2">
        {/* Citizen */}
        <div className="card">
          <span className="chip">👤</span>
          <h4 style={{ fontSize: 22, marginTop: 16 }}>Citizen Portal</h4>
          <ul className="ticks">
            <li>Sign in with a demo account or UAE PASS</li>
            <li>Submit a rescheduling request</li>
            <li>Watch the assessment run, step by step</li>
            <li>Track the decision on My Case</li>
          </ul>
          <button className="btn primary" style={{ marginTop: 16 }} onClick={() => nav("/login")}>
            {citizen ? "Open Citizen Portal →" : "Citizen sign-in →"}
          </button>
        </div>

        {/* Officer */}
        <div className="card">
          <span className="chip">⚖</span>
          <h4 style={{ fontSize: 22, marginTop: 16 }}>Officer Dashboard</h4>
          <ul className="ticks">
            <li>Review the escalation queue</li>
            <li>Approve, override or reject determinations</li>
            <li>Proactive risk alerts</li>
            <li>Replay & audit dashboard</li>
          </ul>
          <button className="btn" style={{ marginTop: 16 }} onClick={() => nav("/officer/login")}>
            {officer ? "Open Officer Dashboard →" : "Officer sign-in →"}
          </button>
        </div>
      </div>

      <div className="section-title">How it works</div>
      <div className="grid grid-3">
        {[
          { icon: "✍", h: t("beneficiary"), items: ["New Request", "My Case · status + result"] },
          { icon: "⚖", h: t("officer"), items: ["Review Queue", "Case detail + actions"] },
          { icon: "📊", h: t("insight"), items: ["Proactive Alerts", "Replay Dashboard"] },
        ].map((c) => (
          <div key={c.h} className="card">
            <span className="chip">{c.icon}</span>
            <h4 style={{ fontSize: 20, marginTop: 16 }}>{c.h}</h4>
            <ul className="ticks">
              {c.items.map((i) => (
                <li key={i}>{i}</li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </>
  );
}
