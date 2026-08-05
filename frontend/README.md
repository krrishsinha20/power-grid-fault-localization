# KSPDB Fault Localization — Quick Start

## Folder layout expected at repo root

```
.
├── docker-compose.yml
├── .env.example
├── backend/          <- your existing FastAPI project (Dockerfile, requirements.txt, app/, tests/)
└── frontend/          <- this new React/TypeScript console (see frontend/README.md)
```

If your backend zip currently unpacks as `backend/backend/...`, move
the inner `backend/` contents up one level so `Dockerfile`,
`requirements.txt`, and `app/` sit directly under `./backend` at the
repo root — `docker-compose.yml` expects that path.

## Run everything with one command

```bash
cp .env.example .env
# paste a Groq API key in .env if you want the AI "explain" feature —
# everything else works without one

docker compose up
```

- Backend API + docs: **http://localhost:8000/docs**
- Operator console + simulator: **http://localhost:5173**

First boot seeds the database automatically (see backend logs).

## Run without Docker (two terminals)

**Terminal 1 — backend** (see `backend/` for its own README/DEPLOYMENT
notes):
```bash
cd backend
python -m venv venv
# Linux/macOS: source venv/bin/activate
# Windows PowerShell: .\venv\Scripts\Activate.ps1
# Windows CMD: venv\Scripts\activate.bat
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Terminal 2 — frontend:**
```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```
Opens on **http://localhost:5173**.

## What you'll see

1. **Operator console** — live incident list (worst-impact first),
   map, and a detail panel with AI explain + ticket workflow actions.
2. **Fault simulator** — a form-driven panel that calls every
   `/simulate/*` endpoint: span/transformer/feeder faults, the three
   noise types (dead sensor, duplicate telemetry, out-of-order
   telemetry), and repair. Every action's result appears in a running
   log so you can watch the incident list react in real time.

See `frontend/README.md` for the frontend's own structure and design
notes.
