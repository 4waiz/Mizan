# Mizan — React Frontend

The Mizan workflow UI — React + Vite + TypeScript, built on the
**Paper** design system (see `../SKILL.md`). It talks to the FastAPI backend
and covers every screen: Home (mock UAE PASS login), New Request, My Case,
Officer Queue, Officer Case Review, Proactive Alerts, the Replay Dashboard, and
the **Historical Intelligence dashboard** (`/insights`).

> **Historical Intelligence (`/insights`).** `src/pages/Insights.tsx` renders the
> organizer-data dashboard from the `/api/organizer-insights*` and
> `/api/proactive-scan` endpoints. It is built on the organizer-provided
> historical Excel (`../data/RescheduleArrears.xlsx`, 2023–2025), used for
> aggregated insights, risk calibration, and demo realism. It shows **aggregates,
> risk buckets, and anonymized/banded patterns only** — **no raw personal data is
> exposed**, and final decisions are still governed by the deterministic policy
> rules. See [`../docs/organizer-data.md`](../docs/organizer-data.md).

## Run

1. Start the backend (from `../backend`):
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
2. Start the frontend:
   ```bash
   cd web
   npm install
   npm run dev
   ```
   Open http://localhost:5173 — Vite proxies `/api` and `/` to the backend on :8000.

## Build

```bash
npm run build      # outputs to web/dist
npm run preview
```

Set `VITE_API_BASE` to point at a non-proxied backend (e.g. for a production build).

## Design

- **Paper aesthetic**: paper-textured off-white surfaces, Montserrat (display) /
  Roboto (body) / PT Mono, minimal color with the Sheikh Zayed Housing Programme
  green as the only brand accent.
- **Accessibility**: WCAG AA targets, visible `:focus-visible` outlines,
  keyboard-first controls, and a high-contrast toggle.
- **Bilingual**: English / Arabic with full RTL flip.
- The real **UAE PASS** logo (`public/uaepass.png`) is used on the login screen
  and the sign-in button.
