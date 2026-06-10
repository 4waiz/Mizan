import { Routes, Route, Navigate, useLocation } from "react-router-dom";
import type { ReactNode } from "react";
import Layout from "./components/Layout";
import Home from "./pages/Home";
import CitizenLogin from "./pages/CitizenLogin";
import OfficerLogin from "./pages/OfficerLogin";
import NewRequest from "./pages/NewRequest";
import MyCase from "./pages/MyCase";
import OfficerQueue from "./pages/OfficerQueue";
import OfficerCase from "./pages/OfficerCase";
import Proactive from "./pages/Proactive";
import Replay from "./pages/Replay";
import Insights from "./pages/Insights";
import Telemetry from "./pages/Telemetry";
import { isCitizen, isOfficer } from "./session";

function RequireCitizen({ children }: { children: ReactNode }) {
  const loc = useLocation();
  if (!isCitizen()) return <Navigate to="/login" replace state={{ from: loc.pathname }} />;
  return <>{children}</>;
}

function RequireOfficer({ children }: { children: ReactNode }) {
  const loc = useLocation();
  if (!isOfficer()) return <Navigate to="/officer/login" replace state={{ from: loc.pathname }} />;
  return <>{children}</>;
}

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Home />} />
        {/* Historical Intelligence — PUBLIC (aggregates only, no auth guard) */}
        <Route path="/insights" element={<Insights />} />
        <Route path="/login" element={<CitizenLogin />} />
        <Route path="/officer/login" element={<OfficerLogin />} />

        {/* Citizen portal — requires a citizen (UAE PASS) session */}
        <Route path="/new-request" element={<RequireCitizen><NewRequest /></RequireCitizen>} />
        <Route path="/my-case" element={<RequireCitizen><MyCase /></RequireCitizen>} />

        {/* Officer dashboard — requires an officer session */}
        <Route path="/officer/queue" element={<RequireOfficer><OfficerQueue /></RequireOfficer>} />
        <Route path="/officer/case" element={<RequireOfficer><OfficerCase /></RequireOfficer>} />
        <Route path="/proactive" element={<RequireOfficer><Proactive /></RequireOfficer>} />
        <Route path="/replay" element={<RequireOfficer><Replay /></RequireOfficer>} />
        <Route path="/telemetry" element={<RequireOfficer><Telemetry /></RequireOfficer>} />

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  );
}
