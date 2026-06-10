import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { I18nProvider } from "./i18n";
import App from "./App";
import ErrorBoundary from "./components/ErrorBoundary";
import "./styles.css";

// Demo: start signed OUT on every fresh page load so the login flow is always
// explicit (portal chooser → citizen/officer sign-in). A full page reload re-runs
// this module and wipes the session; in-app SPA navigation does NOT re-run it, so
// the session set right after login survives while you move between pages.
localStorage.removeItem("mz_session");

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
