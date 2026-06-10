import { useState } from "react";
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
  const [showIntro, setShowIntro] = useState(() => !sessionStorage.getItem("introSeen"));
  const [introFading, setIntroFading] = useState(false);
  // Phones get the portrait, watermark-free clip; tablets and laptops get the landscape intro.
  const [introSrc] = useState(() =>
    typeof window !== "undefined" && window.matchMedia("(max-width: 767px)").matches
      ? "/mobile-intro.mp4"
      : "/intro.mp4"
  );

  const dismissIntro = () => {
    if (introFading) return; // already fading out
    sessionStorage.setItem("introSeen", "1");
    // Trigger the fade-out, then unmount once the transition finishes.
    setIntroFading(true);
    setTimeout(() => setShowIntro(false), 800);
  };

  return (
    <>
      {showIntro && (
        <div
          onClick={dismissIntro}
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 1000,
            background: "#000",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            opacity: introFading ? 0 : 1,
            transition: "opacity 0.8s ease",
            pointerEvents: introFading ? "none" : "auto",
          }}
        >
          <video
            src={introSrc}
            autoPlay
            muted
            playsInline
            onEnded={dismissIntro}
            style={{ width: "100%", height: "100%", objectFit: "cover" }}
          />
          <button
            onClick={dismissIntro}
            className="btn intro-skip"
            style={{ position: "absolute", bottom: 20, right: 16, zIndex: 1001 }}
          >
            {t("skip_intro")}
          </button>
        </div>
      )}

      <Band title={t("home_band_title")} subtitle={t("subtitle")} />

      <p className="lead">
        {t("home_lead_pre")} <b>{t("home_lead_days")}</b> {t("home_lead_mid")}{" "}
        <b>{t("home_lead_attrs")}</b> {t("home_lead_post")}
      </p>

      {(citizen || officer) && (
        <Alert kind="info">
          {t("signed_in_as")} <b>{citizen ? s.name : s.officerName}</b> (
          {citizen ? t("signed_in_role_citizen") : t("signed_in_role_officer")}).{" "}
          <a
            href={citizen ? "/new-request" : "/officer/queue"}
            onClick={(e) => {
              e.preventDefault();
              nav(citizen ? "/new-request" : "/officer/queue");
            }}
          >
            {citizen ? t("go_to_portal") : t("go_to_dashboard")}
          </a>
        </Alert>
      )}

      {!(citizen || officer) && (
        <>
          <div className="section-title">{t("choose_your_portal")}</div>
          <div className="grid grid-2">
            {/* Citizen */}
            <div className="card">
              <span className="chip">👤</span>
              <h4 style={{ fontSize: 22, marginTop: 16 }}>{t("citizen_portal")}</h4>
              <ul className="ticks">
                <li>{t("citizen_portal_card_t1")}</li>
                <li>{t("citizen_portal_card_t2")}</li>
                <li>{t("citizen_portal_card_t3")}</li>
                <li>{t("citizen_portal_card_t4")}</li>
              </ul>
              <button className="btn primary" style={{ marginTop: 16 }} onClick={() => nav("/login")}>
                {t("citizen_signin_btn")}
              </button>
            </div>

            {/* Officer */}
            <div className="card">
              <span className="chip">⚖</span>
              <h4 style={{ fontSize: 22, marginTop: 16 }}>{t("officer_dashboard")}</h4>
              <ul className="ticks">
                <li>{t("officer_dashboard_card_t1")}</li>
                <li>{t("officer_dashboard_card_t2")}</li>
                <li>{t("officer_dashboard_card_t3")}</li>
                <li>{t("officer_dashboard_card_t4")}</li>
              </ul>
              <button className="btn" style={{ marginTop: 16 }} onClick={() => nav("/officer/login")}>
                {t("officer_signin_btn")}
              </button>
            </div>
          </div>
        </>
      )}

      <div className="section-title">{t("how_it_works")}</div>
      <div className="grid grid-3">
        {[
          { icon: "✍", h: t("beneficiary"), items: [t("hiw_citizen_i1"), t("hiw_citizen_i2")] },
          { icon: "⚖", h: t("officer"), items: [t("hiw_officer_i1"), t("hiw_officer_i2")] },
          { icon: "📊", h: t("insight"), items: [t("hiw_insight_i1"), t("hiw_insight_i2")] },
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
