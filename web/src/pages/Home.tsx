import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useI18n } from "../i18n";
import { api } from "../api";
import { getSession, setSession } from "../session";
import { Band, Alert } from "../components/ui";

export default function Home() {
  const { t } = useI18n();
  const nav = useNavigate();
  const [fixtures, setFixtures] = useState<any[]>([]);
  const [choice, setChoice] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [signed, setSigned] = useState<string | null>(getSession().name ?? null);

  useEffect(() => {
    api
      .fixtures()
      .then((f) => {
        const apps = f.filter((x) => x.trigger_type === "application");
        setFixtures(f);
        setChoice(apps[0]?.fixture_id ?? f[0]?.fixture_id ?? "");
      })
      .catch((e) => setErr(String(e)));
  }, []);

  const applicants = fixtures.filter((f) => f.trigger_type === "application");
  const selected = fixtures.find((f) => f.fixture_id === choice);

  const signIn = () => {
    if (!selected) return;
    setSession({
      fixture: selected.fixture_id,
      beneficiaryId: selected.beneficiary_id,
      name: selected.name_en,
    });
    setSigned(selected.name_en);
  };

  return (
    <>
      <Band title={t("app_title")} subtitle={t("subtitle")} />

      <p style={{ fontSize: 18, lineHeight: 1.6, maxWidth: 820 }}>
        An autonomous case officer that turns the manual <b>5-working-day</b> arrears
        rescheduling review into an <b>instant, explainable, auditable</b> decision —
        and escalates only the exceptional cases to a human.
      </p>

      {err && (
        <Alert kind="err">
          Cannot reach the backend. Start it with{" "}
          <code>uvicorn app.main:app --port 8000</code> from <code>backend/</code>.
          <br />
          {err}
        </Alert>
      )}

      <div className="card" style={{ marginTop: 24 }}>
        <h3 style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <img src="/uaepass.png" alt="UAE PASS" style={{ height: 34 }} />
          <span>{t("login")}</span>
        </h3>

        <div
          className="grid"
          style={{ gridTemplateColumns: "1fr auto", alignItems: "end", marginTop: 16 }}
        >
          <div>
            <label className="field">
              Select a citizen identity to sign in as (synthetic UAE PASS):
            </label>
            <select value={choice} onChange={(e) => setChoice(e.target.value)}>
              {applicants.map((f) => (
                <option key={f.fixture_id} value={f.fixture_id}>
                  {f.name_en} · {f.beneficiary_id} ({f.fixture_id})
                </option>
              ))}
            </select>
            {selected?.note && <div className="caption">{selected.note}</div>}
          </div>
          <button className="btn btn-uaepass" onClick={signIn}>
            <img src="/uaepass.png" alt="" />
            {t("login")}
          </button>
        </div>
      </div>

      {signed && (
        <Alert kind="info">
          ✅ {t("signed_in_as")} <b>{signed}</b>.{" "}
          <a
            href="/new-request"
            onClick={(e) => {
              e.preventDefault();
              nav("/new-request");
            }}
          >
            Open New Request →
          </a>
        </Alert>
      )}

      <hr className="rule" />

      <div className="grid grid-3">
        <div className="card">
          <h4>👤 {t("beneficiary")}</h4>
          <ul>
            <li>New Request</li>
            <li>My Case (status + result)</li>
          </ul>
        </div>
        <div className="card">
          <h4>🧑‍⚖️ {t("officer")}</h4>
          <ul>
            <li>Review Queue</li>
            <li>Case detail + actions</li>
          </ul>
        </div>
        <div className="card">
          <h4>📊 {t("insight")}</h4>
          <ul>
            <li>Proactive Alerts</li>
            <li>Replay Dashboard</li>
          </ul>
        </div>
      </div>
    </>
  );
}
