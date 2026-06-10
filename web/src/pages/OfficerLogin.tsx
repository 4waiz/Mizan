import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { setSession, OFFICER_CREDENTIALS } from "../session";
import { Band, Alert } from "../components/ui";

export default function OfficerLogin() {
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
      setErr("Invalid officer credentials.");
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
      <Band title="Officer Dashboard" subtitle="Sheikh Zayed Housing Programme · MOEI" fileRef="OFFICER · لوحة الموظف" />

      <p className="lead">
        Restricted access. Sign in to review escalated cases, approve, override or
        reject determinations.
      </p>

      <div className="card tab" style={{ marginTop: 24, maxWidth: 480 }}>
        <div className="eyebrow" style={{ marginBottom: 16 }}>Officer authentication</div>
        {err && <Alert kind="err">{err}</Alert>}
        <form onSubmit={signIn}>
          <label className="field">Username</label>
          <input
            value={username}
            autoFocus
            autoComplete="username"
            onChange={(e) => setUsername(e.target.value)}
            placeholder="OfficerAwaiz"
          />
          <div style={{ height: 14 }} />
          <label className="field">Password</label>
          <input
            type="password"
            value={password}
            autoComplete="current-password"
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
          />
          <button className="btn primary block" type="submit" style={{ marginTop: 18 }}>
            Sign in to dashboard
          </button>
        </form>
        <div className="caption" style={{ marginTop: 16 }}>
          Demo officer · <code>OfficerAwaiz</code> / <code>Officer123</code>
        </div>
      </div>

      <div className="caption" style={{ marginTop: 18 }}>
        Not an officer?{" "}
        <a
          href="/login"
          onClick={(e) => {
            e.preventDefault();
            nav("/login");
          }}
        >
          ← Citizen portal sign-in
        </a>
      </div>
    </>
  );
}
