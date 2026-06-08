// Tiny localStorage-backed session for the mock UAE PASS login + active case.
export interface Session {
  fixture?: string;
  beneficiaryId?: string;
  name?: string;
  activeCaseId?: string;
  lastRunCaseId?: string;
  officerCaseId?: string;
}

const KEY = "mz_session";

export function getSession(): Session {
  try {
    return JSON.parse(localStorage.getItem(KEY) || "{}");
  } catch {
    return {};
  }
}

export function setSession(patch: Partial<Session>) {
  const next = { ...getSession(), ...patch };
  localStorage.setItem(KEY, JSON.stringify(next));
  window.dispatchEvent(new Event("mz_session"));
  return next;
}
