# KSPDB Fault Console — Frontend

Operator console + fault simulator UI for the backend in `../backend`.
React + TypeScript, built with Vite.

## Why this stack

Built in TypeScript/React specifically to match Propel's production
stack (chat interface, onboarding flows, theming system all run on
TypeScript/Node/React/Postgres), rather than defaulting to whatever
was fastest to prototype. The backend is Python/FastAPI — chosen
purely because it was the fastest path to prototype the graph-based
localization logic; that choice doesn't reflect a stack preference,
since the brief explicitly scores architecture and reasoning, not
language.

## Run it locally (no Docker)

```bash
cp .env.example .env
# edit .env if your backend isn't on http://localhost:8000

npm install
npm run dev
```

Opens on http://localhost:5173. Requires the backend (see
`../backend/README.md`) already running.

## Run it via Docker

From the repo root:

```bash
docker compose up
```

This builds and serves the frontend on **http://localhost:5173**
(mapped from the container's nginx on port 80) alongside the backend
and database. See the root `docker-compose.yml` and `DEPLOYMENT.md`.

## What's in here

- `src/api/client.ts` — typed wrapper around every backend endpoint.
- `src/types.ts` — TypeScript types mirroring the backend's Pydantic
  schemas exactly (`app/schemas/*.py`).
- `src/hooks/usePolling.ts` — generic polling hook. The console
  refreshes incidents/tickets/dashboard every `VITE_POLL_INTERVAL_MS`
  (default 5s) — see `ARCHITECTURE.md` in the repo root for why
  polling was chosen over WebSockets here.
- `src/hooks/usePoleLookup.ts` — works around a backend schema gap:
  `IncidentResponse` doesn't currently return lat/lon/pincode (even
  though the `Incident` DB model has those columns — see
  `DECISIONS.md`). This hook fetches the pole registry once and
  resolves each incident's `end_pole` to coordinates, so the map and
  detail panel work today and will also pick up real coordinates
  automatically if the backend is updated to return them directly.
- `src/components/MapView.tsx` — Leaflet + free OpenStreetMap tiles
  (no API key required, per the assignment's constraint that the
  deployed URL must work without a reviewer's own key).
- `src/components/IncidentDetail.tsx` — ticket workflow actions. The
  "force-close without verification" action is deliberately separated
  and labeled as an admin override, never the primary resolve path —
  see the note in `DECISIONS.md` about `POST /tickets/{id}/close`
  bypassing telemetry verification.
- `src/components/SimulatorPanel.tsx` — drives every `/simulate/*`
  endpoint from the UI, per the brief's requirement that the
  simulator be "drivable from the UI or a single documented command."

## UI reasoning (short version — full version in root ARCHITECTURE.md)

- The stats bar's live/dark ratio strip is the first thing on screen,
  before any list or map — the brief asks that "the most important
  thing dominate the screen," and for a control room that's "how much
  of the grid is dark right now," not a count of tickets.
- Resolved incidents sort to the bottom of the list, visually dimmed,
  rather than disappearing — an operator should never lose an audit
  trail, but also never have to scroll past closed tickets to find
  what's still open.
- Confidence is shown as a meter plus a plain-language explanation
  (not just a number), because a bare "67%" tells a non-engineer
  nothing about whether to trust it or why.
- Map markers are one per incident (not one per pole), colored by
  fault type, so a storm with a dozen simultaneous faults is still
  scannable at a glance instead of a wall of pole-level dots.
