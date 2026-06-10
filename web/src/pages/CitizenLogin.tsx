import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useI18n } from "../i18n";
import { api } from "../api";
import { setSession, CITIZEN_USERS } from "../session";
import { Band, Alert } from "../components/ui";

type Mode = "password" | "uaepass";

export default function CitizenLogin() {
  const { t } = useI18n();
  const nav = useNavigate();
  const [mode, setMode] = useState<Mode>("password");

  const [fixtures, setFixtures] = useState<any[]>([]);
  const [choice, setChoice] = useState("");
  const [loadErr, setLoadErr] = useState<string | null>(null);

  // password form
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api
      .fixtures()
      .then((f) => {
        const apps = f.filter((x) => x.trigger_type === "application");
        setFixtures(f);
        setChoice(apps[0]?.fixture_id ?? f[0]?.fixture_id ?? "");
      })
      .catch((e) => setLoadErr(String(e)));
  }, []);

  const applicants = fixtures.filter((f) => f.trigger_type === "application");
  const selected = fixtures.find((f) => f.fixture_id === choice);

  const completeLogin = (fixtureId: string, uname?: string) => {
    const fx = fixtures.find((f) => f.fixture_id === fixtureId);
    if (!fx) {
      setErr(t("identity_unavailable"));
      return;
    }
    setSession({
      role: "citizen",
      fixture: fx.fixture_id,
      beneficiaryId: fx.beneficiary_id,
      name: fx.name_en,
      username: uname ?? fx.name_en,
      activeCaseId: undefined,
    });
    nav("/new-request");
  };

  const signInPassword = (e: React.FormEvent) => {
    e.preventDefault();
    setErr(null);
    const u = username.trim().toLowerCase();
    const match = CITIZEN_USERS.find((c) => c.username === u);
    if (!match || match.password !== password) {
      setErr(t("invalid_credentials"));
      return;
    }
    completeLogin(match.fixture, match.username);
  };

  const signInUaePass = () => {
    setErr(null);
    if (!selected) return;
    completeLogin(selected.fixture_id);
  };

  return (
    <>
      <Band title={t("citizen_portal")} subtitle={t("subtitle")} fileRef="CITIZEN · بوابة المستفيد" />

      <p className="lead">{t("citizen_login_lead")}</p>

      {loadErr && (
        <Alert kind="err">
          {t("backend_unreachable")}
          <br />
          {loadErr}
        </Alert>
      )}

      <div className="card tab" style={{ marginTop: 24, maxWidth: 560 }}>
        <div className="seg" role="group" aria-label="Login method" style={{ marginBottom: 20 }}>
          <button className={mode === "password" ? "on" : ""} onClick={() => setMode("password")}>
            {t("account")}
          </button>
          <button className={mode === "uaepass" ? "on" : ""} onClick={() => setMode("uaepass")}>
            UAE PASS
          </button>
        </div>

        {err && <Alert kind="err">{err}</Alert>}

        {mode === "password" ? (
          <form onSubmit={signInPassword}>
            <label className="field">{t("username")}</label>
            <input
              value={username}
              autoFocus
              autoComplete="username"
              onChange={(e) => setUsername(e.target.value)}
            />
            <div style={{ height: 14 }} />
            <label className="field">{t("password")}</label>
            <input
              type="password"
              value={password}
              autoComplete="current-password"
              onChange={(e) => setPassword(e.target.value)}
            />
            <button className="btn primary block" type="submit" style={{ marginTop: 18 }}>
              {t("sign_in")}
            </button>
          </form>
        ) : (
          <div>
            <div className="spread" style={{ alignItems: "center", marginBottom: 16 }}>
              <div className="eyebrow">{t("authentication")}</div>
              <img src="/uaepass.png" alt="UAE PASS" style={{ height: 34 }} />
            </div>
            <label className="field">{t("citizen_identity_uaepass")}</label>
            <select value={choice} onChange={(e) => setChoice(e.target.value)}>
              {applicants.map((f) => (
                <option key={f.fixture_id} value={f.fixture_id}>
                  {f.name_en} · {f.beneficiary_id} ({f.fixture_id})
                </option>
              ))}
            </select>
            {selected?.note && <div className="caption" style={{ marginTop: 8 }}>{selected.note}</div>}
            <button className="btn btn-uaepass block" onClick={signInUaePass} style={{ marginTop: 18 }}>
              {t("login")}
            </button>
          </div>
        )}
      </div>

      <div className="caption" style={{ marginTop: 18 }}>
        {t("are_you_officer")}{" "}
        <a
          href="/officer/login"
          onClick={(e) => {
            e.preventDefault();
            nav("/officer/login");
          }}
        >
          {t("officer_dashboard_signin")} →
        </a>
      </div>
    </>
  );
}
