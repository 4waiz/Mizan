import { useEffect, useState, type ReactNode } from "react";
import { NavLink } from "react-router-dom";
import { useI18n } from "../i18n";
import { api } from "../api";
import { getSession } from "../session";

function HealthBadge() {
  const [h, setH] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    api
      .health()
      .then(setH)
      .catch((e) => setErr(String(e)));
  }, []);
  if (err)
    return (
      <div className="alert err" style={{ fontSize: 12 }}>
        Backend unreachable. Start it with <code>uvicorn</code> on :8000.
      </div>
    );
  if (!h)
    return (
      <div className="caption">Checking backend…</div>
    );
  return (
    <div className="alert ok" style={{ fontSize: 12 }}>
      Backend ✓ · engine: {h.engine} · LLM: {h.llm_provider}
    </div>
  );
}

export default function Layout({ children }: { children: ReactNode }) {
  const { t, lang, setLang, hc, setHc } = useI18n();
  const [, force] = useState(0);
  useEffect(() => {
    const h = () => force((n) => n + 1);
    window.addEventListener("mz_session", h);
    return () => window.removeEventListener("mz_session", h);
  }, []);
  const s = getSession();

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="scale">⚖️</span> Mizan <span className="muted">/ ميزان</span>
        </div>
        <div className="caption">{t("subtitle")}</div>

        <nav className="nav">
          <NavLink to="/" end>
            🏠 {t("home")}
          </NavLink>

          <div className="nav-group-label">👤 {t("beneficiary")}</div>
          <NavLink to="/new-request">📝 {t("new_request")}</NavLink>
          <NavLink to="/my-case">📄 {t("my_case")}</NavLink>

          <div className="nav-group-label">🧑‍⚖️ {t("officer")}</div>
          <NavLink to="/officer/queue">📥 {t("queue")}</NavLink>
          <NavLink to="/officer/case">🗂️ Case Review</NavLink>

          <div className="nav-group-label">📊 {t("insight")}</div>
          <NavLink to="/proactive">📡 {t("proactive")}</NavLink>
          <NavLink to="/replay">📈 {t("replay")}</NavLink>
        </nav>

        <hr className="rule" style={{ margin: "16px 0" }} />

        <label className="field">{t("language")} / اللغة</label>
        <div className="row" style={{ marginBottom: 12 }}>
          <button
            className={`btn ${lang === "en" ? "primary" : ""}`}
            onClick={() => setLang("en")}
            style={{ flex: 1 }}
          >
            English
          </button>
          <button
            className={`btn ${lang === "ar" ? "primary" : ""}`}
            onClick={() => setLang("ar")}
            style={{ flex: 1 }}
          >
            العربية
          </button>
        </div>

        <label className="row" style={{ fontSize: 14, cursor: "pointer" }}>
          <input
            type="checkbox"
            checked={hc}
            onChange={(e) => setHc(e.target.checked)}
            style={{ width: "auto" }}
          />
          {t("high_contrast")}
        </label>

        <hr className="rule" style={{ margin: "16px 0" }} />
        {s.name && (
          <div className="alert info" style={{ fontSize: 12 }}>
            ✅ {t("signed_in_as")} <b>{s.name}</b>
          </div>
        )}
        <HealthBadge />
        <div className="caption" style={{ marginTop: 8 }}>
          Synthetic data only. No real identifiers.
        </div>
      </aside>

      <main className="main">{children}</main>
    </div>
  );
}
