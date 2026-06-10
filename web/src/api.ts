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

/**
 * POST + consume a Server-Sent Events stream, invoking `onEvent` for each
 * `data:` line (parsed JSON). Resolves once the stream closes. Used for the live
 * "auditing documents → checking fraud → …" run progress.
 */
async function streamSSE(path: string, onEvent: (e: any) => void): Promise<void> {
  const resp = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { Accept: "text/event-stream" },
  });
  if (!resp.ok || !resp.body) {
    await handle(resp); // throws with a useful message
    return;
  }
  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    // SSE events are separated by a blank line.
    let sep: number;
    while ((sep = buffer.indexOf("\n\n")) !== -1) {
      const chunk = buffer.slice(0, sep);
      buffer = buffer.slice(sep + 2);
      for (const line of chunk.split("\n")) {
        const trimmed = line.trimStart();
        if (trimmed.startsWith("data:")) {
          const payload = trimmed.slice(5).trim();
          if (payload) {
            try {
              onEvent(JSON.parse(payload));
            } catch {
              /* ignore malformed frame */
            }
          }
        }
      }
    }
  }
}

export const api = {
  health: () => get<any>("/api/health"),
  fixtures: () => get<any[]>("/api/fixtures"),
  intake: (fixture_id: string, trigger_type = "application") =>
    post<{ case_id: string; status: string }>("/api/cases/intake", {
      fixture_id,
      trigger_type,
    }),
  getCase: (id: string) => get<any>(`/api/cases/${id}`),
  uploadDocuments: (id: string, documents: any[]) =>
    post<any>(`/api/cases/${id}/documents`, { documents }),
  uploadDocumentTypes: (id: string, doc_types: string[], file_names: string[]) =>
    post<any>(`/api/cases/${id}/documents/by-type`, { doc_types, file_names }),
  // Send the actual file bytes; the backend extracts text + figures from them.
  uploadFiles: (id: string, files: File[]) => {
    const form = new FormData();
    for (const f of files) form.append("files", f, f.name);
    return fetch(`${BASE}/api/cases/${id}/documents/upload`, {
      method: "POST",
      body: form, // browser sets multipart/form-data boundary
    }).then((r) => handle<any>(r));
  },
  requiredDocuments: (id: string) =>
    get<{ required: string[]; present: string[]; missing: string[] }>(
      `/api/cases/${id}/documents/required`,
    ),
  listCases: () => get<any[]>("/api/cases"),
  runCase: (id: string) => post<any>(`/api/cases/${id}/run`),
  runCaseStream: (id: string, onEvent: (e: any) => void) =>
    streamSSE(`/api/cases/${id}/run/stream`, onEvent),
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
