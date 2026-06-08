// Thin HTTP client for the Mizan FastAPI backend. In dev, Vite proxies /api -> :8000.
const BASE = import.meta.env.VITE_API_BASE ?? "";

async function handle<T>(resp: Response): Promise<T> {
  if (!resp.ok) {
    let detail = resp.statusText;
    try {
      const j = await resp.json();
      detail = j.detail ?? JSON.stringify(j);
    } catch {
      /* ignore */
    }
    throw new Error(`${resp.status}: ${detail}`);
  }
  return resp.json() as Promise<T>;
}

const get = <T>(path: string) => fetch(`${BASE}${path}`).then((r) => handle<T>(r));
const post = <T>(path: string, body?: unknown) =>
  fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  }).then((r) => handle<T>(r));

export const api = {
  health: () => get<any>("/"),
  fixtures: () => get<any[]>("/api/fixtures"),
  intake: (fixture_id: string, trigger_type = "application") =>
    post<{ case_id: string; status: string }>("/api/cases/intake", {
      fixture_id,
      trigger_type,
    }),
  getCase: (id: string) => get<any>(`/api/cases/${id}`),
  listCases: () => get<any[]>("/api/cases"),
  runCase: (id: string) => post<any>(`/api/cases/${id}/run`),
  audit: (id: string) => get<any>(`/api/cases/${id}/audit`),
  officerQueue: () => get<any[]>("/api/officer/queue"),
  approve: (id: string, officer_id: string, notes: string | null) =>
    post<any>(`/api/officer/${id}/approve`, { officer_id, notes }),
  reject: (id: string, officer_id: string, notes: string | null) =>
    post<any>(`/api/officer/${id}/reject`, { officer_id, notes }),
  override: (
    id: string,
    officer_id: string,
    outcome_type: string,
    new_installment_aed: number | null,
    new_term_months: number | null,
    notes: string | null,
  ) =>
    post<any>(`/api/officer/${id}/override`, {
      officer_id,
      outcome_type,
      new_installment_aed,
      new_term_months,
      notes,
    }),
  replay: () => get<any>("/api/replay/summary"),
  alerts: () => get<any[]>("/api/proactive/alerts"),
};
