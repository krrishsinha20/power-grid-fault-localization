# Deployment & Operation Guide

This guide covers local Docker Compose setup, environment configuration, system verification, production deployment on Railway, and troubleshooting matrix for known operational issues.

---

## Prerequisites

- **Docker Desktop**: Engine v24.0+
- **Docker Compose**: v2.20+
- **Git**: v2.30+
- **Memory/CPU**: Minimum 4 GB RAM, 2 CPU cores

---

## Local Docker Setup

The entire stack (PostgreSQL database, FastAPI backend engine, and Vite/React frontend UI) runs out of the box from the repository root.

### 1. Clone Repository & Environment File
```bash
git clone https://github.com/krrishsinha20/power-grid-fault-localization.git
cd power-grid-fault-localization

# Copy example environment file to root .env and backend/.env
cp .env.example .env
cp .env.example backend/.env
```

### 2. Configure Environment Variables
Edit `.env` as needed:
```env
# Groq LLM Key for "Explain this fault" AI feature
GROQ_API_KEY=gsk_your_groq_api_key_here

# PostgreSQL connection string for local Docker Compose
DATABASE_URL=postgresql+psycopg2://postgres:hellosql@db:5432/power_grid_db

# SQLAlchemy SQL Query logging
SQL_ECHO=false

# Frontend API Target URL (baked into frontend static bundle at build time)
VITE_API_BASE_URL=http://localhost:8000
```

### 3. Build and Launch
```bash
docker compose up --build
```

On initial startup, `db` container initializes PostgreSQL 16. Once `db` reports `service_healthy`, `backend` starts, auto-runs database table creation and seeds network topology (440 poles across 15 transformers), followed by `frontend` Nginx web server startup.

---

## System Verification Steps

Once containers start, verify system health:

1. **Backend OpenAPI Documentation**:
   - Open [http://localhost:8000/docs](http://localhost:8000/docs)
   - Verify HTTP 200 response and Swagger UI layout displaying `/incidents`, `/tickets`, `/telemetry`, and `/simulate` routes.

2. **Frontend Operator Console**:
   - Open [http://localhost:5173](http://localhost:5173)
   - Verify top stats bar displays total poles (~440), live/dark status ratio, active incidents, and open tickets.
   - Verify interactive GIS Map renders poles and transformer nodes.

3. **Clean State Reset**:
   To drop all local volumes, clear database state, and rebuild fresh:
   ```bash
   docker compose down -v
   docker compose up --build
   ```

---

## Troubleshooting Matrix (Actual Lessons Learned)

The following operational bugs were encountered during development and resolved:

### 1. Frontend Build Context Double-Nesting
- **Symptom**: `docker compose up --build` failed with error: `Dockerfile not found in ./frontend`.
- **Root Cause**: The Vite frontend repository structure was located at `./frontend/frontend/` containing `Dockerfile`, `package.json`, and `src/`. `docker-compose.yml` was originally set to `context: ./frontend`.
- **Fix**: Updated `docker-compose.yml` build context:
  ```yaml
  frontend:
    build:
      context: ./frontend/frontend
  ```

### 2. Database Connection `localhost` vs Service Name (`db`)
- **Symptom**: Backend container crashed on startup with `psycopg2.OperationalError: could not connect to server: Connection refused at localhost:5432`.
- **Root Cause**: `backend/.env` contained `DATABASE_URL=...@localhost:5432/...`. Inside Docker networking, `localhost` refers to the container's isolated loopback interface, not the host machine or host container network.
- **Fix**: Override `DATABASE_URL` in `docker-compose.yml` on the backend service to point to the Compose service hostname (`db`):
  ```yaml
  backend:
    environment:
      DATABASE_URL: postgresql+psycopg2://postgres:hellosql@db:5432/power_grid_db
  ```

### 3. Leaflet CSS CDN Integrity Hash Mismatch
- **Symptom**: GIS map markers rendered as giant broken bullet points across the screen; map tile tiles misaligned.
- **Root Cause**: CDN `<link>` tag in `index.html` contained an invalid `integrity` subresource hash, causing browsers to block `leaflet.css` loading.
- **Fix**: Replaced broken CDN link with standard Leaflet CSS import in the application package bundle or cleaned integrity attributes.

### 4. React `StrictMode` Map Remount / Container Re-initialization Crash
- **Symptom**: Console error `Error: Map container is already initialized` when navigating back to the map or during development hot-reloads.
- **Root Cause**: React 18 `StrictMode` intentionally mounts, unmounts, and remounts components in development to catch side-effects. Leaflet maps attach to DOM nodes synchronously and crash if re-initialized on an existing DOM node without cleanup.
- **Fix**: Added proper cleanup lifecycle hook in `MapView.tsx`:
  ```tsx
  useEffect(() => {
    const map = L.map(mapRef.current);
    return () => {
      map.remove(); // Cleanly detach Leaflet instance on unmount
    };
  }, []);
  ```

### 5. CSS Grid Container "Blowout" & Map Overflow
- **Symptom**: Operator Console map expanded infinitely beyond screen height, pushing incident list table off-screen.
- **Root Cause**: CSS Grid flex items defaults to `min-height: auto`. Leaflet container inside a flex/grid child calculated auto height based on canvas size, creating a layout blowout.
- **Fix**: Added `min-height: 0` and `overflow: hidden` to CSS Grid container elements wrapping `MapView`.

---

## Production Cloud Deployment (Railway)

The live production application is deployed on [Railway](https://railway.app) in low-latency Asia region (Singapore/Mumbai):

1. **Services Architecture**:
   - **`Postgres`**: Managed Railway PostgreSQL database instance.
   - **`backend`**: Deployed from `./backend` context.
     - Environment Variables:
       - `DATABASE_URL`: `${{Postgres.DATABASE_URL}}` (Railway dynamic connection string)
       - `GROQ_API_KEY`: Secrets managed via Railway Env Variables.
       - `PORT`: `8000`
   - **`frontend`**: Deployed from `./frontend/frontend` context.
     - Environment Variables:
       - `VITE_API_BASE_URL`: Railway Backend Service URL (`https://power-grid-fault-localization-production.up.railway.app`)

2. **Network Routing**:
   - Public domains are generated for `frontend` and `backend`.
   - CORS middleware in FastAPI backend permits requests from Railway frontend origin.
