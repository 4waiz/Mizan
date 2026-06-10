# Mizan — React Frontend

The Mizan workflow UI — React + Vite + TypeScript, built on the
**Paper** design system (see `../SKILL.md`). It talks to the FastAPI backend
and covers every screen: Home (mock UAE PASS login), New Request, My Case,
Officer Queue, Officer Case Review, Proactive Alerts, and the Replay Dashboard.

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
