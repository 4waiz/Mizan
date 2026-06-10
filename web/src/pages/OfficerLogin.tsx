import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useI18n } from "../i18n";
import { setSession, OFFICER_CREDENTIALS } from "../session";
import { Band, Alert } from "../components/ui";

export default function OfficerLogin() {
  const { t } = useI18n();
  const nav = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState<string | null>(null);

  const signIn = (e: React.FormEvent) => {
    e.preventDefault();
    setErr(null);
    if (
      username.trim() !== OFFICER_CREDENTIALS.username ||
      password !== OFFICER_CREDENTIALS.password
    ) {
      setErr(t("invalid_officer_credentials"));
      return;
    }
    setSession({
      role: "officer",
      officerId: OFFICER_CREDENTIALS.username,
      officerName: OFFICER_CREDENTIALS.name,
    });
    nav("/officer/queue");
  };

  return (
    <>
      <Band title={t("officer_dashboard")} subtitle={t("subtitle")} fileRef="OFFICER · لوحة الموظف" />

      <p className="lead">{t("officer_login_lead")}</p>

      <div className="card tab" style={{ marginTop: 24, maxWidth: 480 }}>
        <div className="eyebrow" style={{ marginBottom: 16 }}>{t("officer_authentication")}</div>
        {err && <Alert kind="err">{err}</Alert>}
        <form onSubmit={signIn}>
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
            {t("sign_in_dashboard")}
          </button>
        </form>
      </div>

      <div className="caption" style={{ marginTop: 18 }}>
        {t("not_an_officer")}{" "}
        <a
          href="/login"
          onClick={(e) => {
            e.preventDefault();
            nav("/login");
          }}
        >
          ← {t("citizen_portal_signin")}
        </a>
      </div>
    </>
  );
}
