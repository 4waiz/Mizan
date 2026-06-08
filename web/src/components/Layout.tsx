import { useEffect, useState, type ReactNode } from "react";
import { NavLink } from "react-router-dom";
import { useI18n } from "../i18n";
import { api } from "../api";
import { getSession } from "../session";

function HealthBadge() {
  const [h, setH] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    api.health().then(setH).catch((e) => setErr(String(e)));
  }, []);
  if (err)
    return (
      <div className="alert err" style={{ fontSize: 12 }}>
        Backend offline — start <code>uvicorn</code> on :8000.
      </div>
    );
  if (!h) return <div className="caption">Checking backend…</div>;
  return (
    <div className="row" style={{ gap: 8, fontSize: 12 }}>
      <span className="stamp green" style={{ fontSize: 9, padding: "2px 7px" }}>
        Online
      </span>
      <span className="muted mono" style={{ fontSize: 11 }}>
        {h.engine} · {h.llm_provider}
      </span>
    </div>
  );
}

const NAV = [
  { to: "/", end: true, num: "00", key: "home" },
  { group: "beneficiary" },
  { to: "/new-request", num: "01", key: "new_request" },
  { to: "/my-case", num: "02", key: "my_case" },
  { group: "officer" },
  { to: "/officer/queue", num: "03", key: "queue" },
  { to: "/officer/case", num: "04", label: "Case Review" },
  { group: "insight" },
  { to: "/proactive", num: "05", key: "proactive" },
  { to: "/replay", num: "06", key: "replay" },
] as const;

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
          <span className="seal">⚖</span>
          <span>
            <span className="word">
              Mizan <small>ميزان</small>
            </span>
          </span>
        </div>
        <div className="brand-sub">
          Sheikh Zayed Housing Programme
          <br />
          MOEI · Arrears Rescheduling
        </div>

        <nav className="nav">
          {NAV.map((item, i) =>
            "group" in item ? (
              <div key={i} className="nav-group eyebrow">
                {t(item.group)}
              </div>
            ) : (
              <NavLink key={item.to} to={item.to} end={(item as any).end}>
                <span className="num">{item.num}</span>
                {(item as any).label ?? t((item as any).key)}
              </NavLink>
            ),
          )}
        </nav>

        <hr className="rule" style={{ margin: "20px 0" }} />

        <div className="eyebrow" style={{ marginBottom: 8 }}>
          {t("language")} · اللغة
        </div>
        <div className="row" style={{ marginBottom: 16, flexWrap: "nowrap" }}>
          <button
            className={`btn ${lang === "en" ? "primary" : "ghost"}`}
            onClick={() => setLang("en")}
            style={{ flex: 1 }}
          >
            EN
          </button>
          <button
            className={`btn ${lang === "ar" ? "primary" : "ghost"}`}
            onClick={() => setLang("ar")}
            style={{ flex: 1 }}
          >
            ع
          </button>
        </div>

        <label className="row" style={{ fontSize: 13, cursor: "pointer" }}>
          <input
            type="checkbox"
            checked={hc}
            onChange={(e) => setHc(e.target.checked)}
            style={{ width: "auto" }}
          />
          {t("high_contrast")}
        </label>

        <hr className="rule" style={{ margin: "20px 0" }} />
        {s.name && (
          <div className="alert info" style={{ fontSize: 12, marginTop: 0 }}>
            Signed in · <b>{s.name}</b>
          </div>
        )}
        <HealthBadge />
        <div className="caption" style={{ marginTop: 12, fontSize: 11 }}>
          Synthetic data only. No real identifiers.
        </div>
      </aside>

      <main className="main">{children}</main>
    </div>
  );
}
