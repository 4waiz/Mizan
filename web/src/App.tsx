import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import Home from "./pages/Home";
import NewRequest from "./pages/NewRequest";
import MyCase from "./pages/MyCase";
import OfficerQueue from "./pages/OfficerQueue";
import OfficerCase from "./pages/OfficerCase";
import Proactive from "./pages/Proactive";
import Replay from "./pages/Replay";

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/new-request" element={<NewRequest />} />
        <Route path="/my-case" element={<MyCase />} />
        <Route path="/officer/queue" element={<OfficerQueue />} />
        <Route path="/officer/case" element={<OfficerCase />} />
        <Route path="/proactive" element={<Proactive />} />
        <Route path="/replay" element={<Replay />} />
      </Routes>
    </Layout>
  );
}
