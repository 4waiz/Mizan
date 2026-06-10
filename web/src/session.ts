// Tiny localStorage-backed session for the UAE PASS login + active case.
export type Role = "citizen" | "officer";

export interface Session {
  role?: Role;
  // citizen
  fixture?: string;
  beneficiaryId?: string;
  name?: string;
  username?: string;
  activeCaseId?: string;
  lastRunCaseId?: string;
  // officer
  officerId?: string;
  officerName?: string;
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

/** Clear the citizen identity (keeps any officer session). */
export function signOutCitizen() {
  const s = getSession();
  const next: Session = {
    officerId: s.officerId,
    officerName: s.officerName,
    officerCaseId: s.officerCaseId,
  };
  localStorage.setItem(KEY, JSON.stringify(next));
  window.dispatchEvent(new Event("mz_session"));
}

/** Clear the officer identity (keeps any citizen session). */
export function signOutOfficer() {
  const s = getSession();
  const { officerId, officerName, officerCaseId, ...rest } = s;
  localStorage.setItem(KEY, JSON.stringify(rest));
  window.dispatchEvent(new Event("mz_session"));
}

export const isCitizen = (s: Session = getSession()) => !!s.fixture;
export const isOfficer = (s: Session = getSession()) => !!s.officerId;

// ── Credentials ──────────────────────────────────────────────────────────────
// Officer dashboard.
export const OFFICER_CREDENTIALS = {
  username: "OfficerAwaiz",
  password: "Officer123",
  name: "Officer Awaiz",
};

// Citizen portal users. Every password is "123". Each maps to a UAE PASS
// identity (a backend fixture). `dup` flags the duplicate-request account that
// the engine rejects immediately at the fraud/dedupe step.
export interface CitizenUser {
  username: string;
  password: string;
  fixture: string;
  dup?: boolean;
}

export const CITIZEN_USERS: CitizenUser[] = [
  { username: "ahmed", password: "123", fixture: "clean_approval" },
  { username: "fatima", password: "123", fixture: "unemployment_hardship" },
  { username: "mariam", password: "123", fixture: "missing_documents" },
  { username: "saeed", password: "123", fixture: "duplicate_application", dup: true },
];
