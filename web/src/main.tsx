import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { I18nProvider } from "./i18n";
import App from "./App";
import ErrorBoundary from "./components/ErrorBoundary";
import "./styles.css";

// Demo: start signed OUT on every fresh page load so the login flow is always
// explicit (portal chooser → citizen/officer sign-in). A full reload runs this
// once; in-app navigation keeps the session set during this load. We clear only
// if it wasn't set this same load (guarded by a per-load sessionStorage flag).
if (!sessionStorage.getItem("mz_loaded")) {
  localStorage.removeItem("mz_session");
  sessionStorage.setItem("mz_loaded", "1");
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <I18nProvider>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </I18nProvider>
    </ErrorBoundary>
  </React.StrictMode>,
);
