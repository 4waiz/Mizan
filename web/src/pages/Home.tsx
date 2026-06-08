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
      <Band title="An autonomous case officer" subtitle="Sheikh Zayed Housing Programme · MOEI" />

      <p className="lead">
        Mizan turns the manual <b>five-working-day</b> arrears rescheduling review into an{" "}
        <b>instant, explainable, auditable</b> decision — escalating only the exceptional
        cases to a human.
      </p>

      {err && (
        <Alert kind="err">
          Cannot reach the backend. Start it with{" "}
          <code>uvicorn app.main:app --port 8000</code> from <code>backend/</code>.
          <br />
          {err}
        </Alert>
      )}

      {/* Sign-in slip */}
      <div className="card tab" style={{ marginTop: 28, maxWidth: 820 }}>
        <div className="spread" style={{ alignItems: "center", marginBottom: 18 }}>
          <div>
            <div className="eyebrow">Authentication</div>
            <h3 style={{ fontSize: 24, marginTop: 2 }}>{t("login")}</h3>
          </div>
          <img src="/uaepass.png" alt="UAE PASS" style={{ height: 40 }} />
        </div>

        <div
          className="grid"
          style={{ gridTemplateColumns: "1fr auto", alignItems: "end", gap: 16 }}
        >
          <div>
            <label className="field">Citizen identity · synthetic UAE PASS</label>
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
          Signed in as <b>{signed}</b>.{" "}
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

      <div className="section-title">Index</div>
      <div className="grid grid-3">
        {[
          { n: "A", h: t("beneficiary"), items: ["New Request", "My Case · status + result"] },
          { n: "B", h: t("officer"), items: ["Review Queue", "Case detail + actions"] },
          { n: "C", h: t("insight"), items: ["Proactive Alerts", "Replay Dashboard"] },
        ].map((c) => (
          <div key={c.n} className="card">
            <div className="row" style={{ gap: 10 }}>
              <span className="stamp ink" style={{ fontSize: 12 }}>
                {c.n}
              </span>
              <h4 style={{ fontSize: 18 }}>{c.h}</h4>
            </div>
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
