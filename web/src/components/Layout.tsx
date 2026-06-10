import { useEffect, useState, type ReactNode } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { useI18n } from "../i18n";
import { api } from "../api";
import { getSession, isCitizen, isOfficer, signOutCitizen, signOutOfficer } from "../session";

function useHealth() {
  const [err, setErr] = useState(false);
  useEffect(() => {
    api.health().catch(() => setErr(true));
  }, []);
  return { err };
}

const NAV_HOME = { to: "/", end: true, num: "00", key: "home" } as const;
// Always-visible top-level nav (like Home) — public Historical Intelligence.
const NAV_INSIGHTS = { to: "/insights", num: "07", key: "insights" } as const;
const NAV_CITIZEN = [
  { to: "/new-request", num: "01", key: "new_request" },
  { to: "/my-case", num: "02", key: "my_case" },
] as const;
const NAV_OFFICER = [
  { to: "/officer/queue", num: "03", key: "queue" },
  { to: "/officer/case", num: "04", key: "nav_case_review" },
  { to: "/proactive", num: "05", key: "proactive" },
  { to: "/replay", num: "06", key: "replay" },
  { to: "/telemetry", num: "08", key: "telemetry" },
] as const;

const FOOTER_GROUPS = [
  {
    head: "beneficiary",
    links: [
      { to: "/new-request", key: "new_request" },
      { to: "/my-case", key: "my_case" },
    ],
  },
  {
    head: "officer",
    links: [
      { to: "/officer/queue", key: "queue" },
      { to: "/officer/case", key: "nav_case_review" },
    ],
  },
  {
    head: "insight",
    links: [
      { to: "/insights", key: "insights" },
      { to: "/proactive", key: "proactive" },
      { to: "/replay", key: "replay" },
    ],
  },
] as const;

function Brand({ footer, onClick }: { footer?: boolean; onClick?: () => void }) {
  return (
    <div
      className={`brand${footer ? " f-brand" : ""}`}
      onClick={onClick}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={onClick ? (e) => (e.key === "Enter" || e.key === " ") && onClick() : undefined}
      style={onClick ? { cursor: "pointer" } : undefined}
      title={onClick ? "Go to home" : undefined}
    >
      <img className="seal" src={footer ? "/light.png" : "/logo.png"} alt="Mizan ميزان" />
    </div>
  );
}

export default function Layout({ children }: { children: ReactNode }) {
  const { t, lang, setLang, hc, setHc } = useI18n();
  const nav = useNavigate();
  const [, force] = useState(0);
  const [scrolled, setScrolled] = useState(false);
  const { err } = useHealth();

  useEffect(() => {
    const onSession = () => force((n) => n + 1);
    const onScroll = () => setScrolled(window.scrollY > 8);
    window.addEventListener("mz_session", onSession);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => {
      window.removeEventListener("mz_session", onSession);
      window.removeEventListener("scroll", onScroll);
    };
  }, []);

  const s = getSession();
  const citizen = isCitizen(s);
  const officer = isOfficer(s);

  const navItems = [
    NAV_HOME,
    NAV_INSIGHTS,
    ...(citizen ? NAV_CITIZEN : []),
    ...(officer ? NAV_OFFICER : []),
  ];

  return (
    <div className="shell">
      <header className={`topbar${scrolled ? " scrolled" : ""}`}>
        <Brand onClick={() => nav("/")} />

        <nav className="topnav">
          {navItems.map((item) => (
            <NavLink key={item.to} to={item.to} end={(item as any).end}>
              <span className="num">{item.num}</span>
              {(item as any).label ?? t((item as any).key)}
            </NavLink>
          ))}
        </nav>

        <div className="topbar-actions">
          <span className="statuschip" title={err ? t("service_unavailable") : t("all_systems_operational")}>
            <span
              className="dot"
              style={err ? { background: "var(--danger)", boxShadow: "0 0 0 3px rgba(220,38,38,.16)" } : undefined}
            />
            {err ? t("offline") : t("system_online")}
          </span>

          {/* Session: user identity pill + sign out */}
          {citizen || officer ? (
            <div className="usermenu" title={citizen ? t("citizen_session") : t("officer_session")}>
              <span className="avatar">{(citizen ? s.name : s.officerName)?.[0]?.toUpperCase() ?? "U"}</span>
              <span className="who">
                <span className="who-name">{citizen ? s.name : s.officerName}</span>
                <span className="who-role">{citizen ? t("beneficiary") : t("officer")}</span>
              </span>
              <button
                className="signout"
                onClick={() => {
                  if (citizen) {
                    signOutCitizen();
                    nav("/login");
                  } else {
                    signOutOfficer();
                    nav("/officer/login");
                  }
                }}
              >
                {t("sign_out")}
              </button>
            </div>
          ) : (
            <button className="btn ghost" style={{ padding: "8px 14px" }} onClick={() => nav("/login")}>
              {t("sign_in")}
            </button>
          )}

          <div className="seg" role="group" aria-label="Language">
            <button className={lang === "en" ? "on" : ""} onClick={() => setLang("en")}>
              EN
            </button>
            <button className={lang === "ar" ? "on" : ""} onClick={() => setLang("ar")}>
              ع
            </button>
          </div>
        </div>
      </header>

      <main className="main">{children}</main>

      <footer className="footer">
        <div className="footer-inner">
          <div>
            <Brand footer />
            <div className="f-tag">
              {t("brand_sub") !== "brand_sub"
                ? t("brand_sub")
                : "Sheikh Zayed Housing Programme · MOEI. An autonomous case officer for arrears rescheduling."}
            </div>
            {s.name && (
              <div className="f-tag" style={{ marginTop: 12 }}>
                {t("footer_signed_in")} <b style={{ color: "#fff" }}>{s.name}</b>
              </div>
            )}
          </div>

          {FOOTER_GROUPS.map((g) => (
            <div key={g.head}>
              <h5>{t(g.head)}</h5>
              <ul>
                {g.links.map((l) => (
                  <li key={l.to}>
                    <NavLink to={l.to}>{(l as any).label ?? t((l as any).key)}</NavLink>
                  </li>
                ))}
              </ul>
            </div>
          ))}

          <div>
            <h5>{t("language")}</h5>
            <ul>
              <li>
                <button className="flink" onClick={() => setLang("en")}>
                  English
                </button>
              </li>
              <li>
                <button className="flink" onClick={() => setLang("ar")}>
                  العربية
                </button>
              </li>
            </ul>
          </div>
        </div>

        <div className="f-base">
          <span className="f-copy">© Copyright Team AAU Mizan</span>
          <div className="f-logos">
            <img src="/moei.png" alt="Ministry of Energy and Infrastructure" />
            <img src="/42abudhabi.png" alt="42 Abu Dhabi" />
          </div>
          <label className="hc-toggle">
            <input type="checkbox" checked={hc} onChange={(e) => setHc(e.target.checked)} />
            {t("high_contrast")}
          </label>
        </div>
      </footer>
    </div>
  );
}
