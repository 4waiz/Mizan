import { Component, type ReactNode } from "react";

interface State {
  error: Error | null;
}

// The boundary can render outside the I18nProvider tree (it wraps the app), so
// it reads the persisted language directly rather than using the hook.
const EB_STRINGS: Record<string, { en: string; ar: string }> = {
  ui_error_title: { en: "The UI hit an error", ar: "واجهت الواجهة خطأً" },
  clear_session_reload: { en: "Clear session & reload", ar: "مسح الجلسة وإعادة التحميل" },
};
function ebt(key: string): string {
  const lang = (typeof localStorage !== "undefined" && localStorage.getItem("mz_lang")) === "ar" ? "ar" : "en";
  return EB_STRINGS[key]?.[lang] ?? key;
}

/**
 * Catches render-time errors anywhere in the tree and shows the message on
 * screen instead of a blank white page — so failures are debuggable in the UI.
 */
export default class ErrorBoundary extends Component<{ children: ReactNode }, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: unknown) {
    // eslint-disable-next-line no-console
    console.error("Mizan UI crashed:", error, info);
  }

  render() {
    if (this.state.error) {
      return (
        <div style={{ padding: 32, fontFamily: "monospace", maxWidth: 900, margin: "0 auto" }}>
          <h2 style={{ color: "#dc2626" }}>{ebt("ui_error_title")}</h2>
          <p style={{ whiteSpace: "pre-wrap" }}>{this.state.error.message}</p>
          <pre style={{ background: "#f5f5f5", padding: 16, overflow: "auto", fontSize: 12 }}>
            {this.state.error.stack}
          </pre>
          <button
            onClick={() => {
              localStorage.removeItem("mz_session");
              window.location.href = "/";
            }}
            style={{ padding: "10px 16px", cursor: "pointer" }}
          >
            {ebt("clear_session_reload")}
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
