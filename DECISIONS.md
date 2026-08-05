# Architecture Decision Records (ADR) & Development Log

This document logs significant architectural choices, bug resolutions, technical trade-offs, known limitations, fragile components, and future engineering roadmap items in reverse chronological order (newest first).

---

## Technical Decision & Bug Fix Log

### [2026-08-05] ADR-008: Real-Time Updates via Polling (Not WebSockets)
- **Status**: Accepted & Implemented
- **Decision**: The frontend operator console uses HTTP polling (every 5 seconds) to fetch updated incident, ticket, and dashboard data — not WebSockets or Server-Sent Events.
- **Rationale**: WebSockets require a persistent connection upgrade that is frequently broken by reverse proxies and PaaS platforms (Railway, Render, Heroku) without explicit configuration. A WebSocket that works locally but silently drops on the deployed URL is worse than polling. Polling at a 5-second interval is sufficient for the control room use case — a fault localized 5 seconds after detection is still orders of magnitude faster than the current 2-hour baseline. The tradeoff (slightly higher server request rate, no sub-second push) is acceptable for this problem.

### [2026-08-05] ADR-007: Third-Party Libraries & Tools Used
- **Status**: Accepted & Implemented
- **Backend**:
  - `FastAPI` — async Python web framework for API layer
  - `SQLAlchemy` (ORM) + `PostgreSQL` — relational persistence
  - `NetworkX` — in-memory directed graph for topology and localization traversal
  - `LangChain` + `langchain-groq` — LLM integration for AI root-cause explanation
  - `psycopg2` — PostgreSQL adapter
  - `pytest` — unit test runner for localization, classifier, and ticket flow tests
- **Frontend**:
  - `React` + `Vite` — UI framework and build tool
  - `Leaflet` (via `react-leaflet`) — GIS map rendering for pole and incident visualization
  - `Axios` — HTTP client for API requests
- **Infrastructure**:
  - `Docker` + `Docker Compose` — containerized local development and deployment
  - `Railway` — cloud PaaS for production deployment

### [2026-08-04] ADR-006: PIN Code & Coordinates Alignment (Bangalore 560001)
- **Status**: Resolved & Verified
- **Context**: Previously `backend/app/utils/constants.py` set `DEFAULT_PINCODE = "411001"` (Pune), while grid coordinates were centered around `12.9716, 77.5946` (Bangalore).
- **Decision**: Updated `DEFAULT_PINCODE` to Bangalore's `560001` and `CITY_NAME` to `Bengaluru` across `constants.py`, synthetic network generators, and backend unit test fixtures to maintain 100% regional metadata consistency.

### [2026-08-04] ADR-005: Local Postgres for Docker vs. Railway Postgres for Live Deploy Split
- **Status**: Accepted & Implemented
- **Context**: Running `docker compose up` locally requires an isolated local database, while live cloud deployment on Railway requires connecting to Railway's managed PostgreSQL instance.
- **Decision**:
  - `docker-compose.yml` sets `DATABASE_URL: postgresql+psycopg2://postgres:hellosql@db:5432/power_grid_db` for local containerized development.
  - `backend/.env` holds `localhost:5432` for running Uvicorn directly on the host machine without Docker.
  - Production Railway deployment references Railway's environment variable `${{Postgres.DATABASE_URL}}`.
  - This separation ensures clean developer experience locally without corrupting cloud production data.

### [2026-08-03] ADR-004: Dark Poles Counter Stats Refresh Fix
- **Status**: Resolved & Verified
- **Symptom**: During repeated simulator fault injections, the "Dark Poles" counter in the top stats bar failed to update dynamically without a hard browser refresh.
- **Root Cause**: The React state management hook in `DashboardStats.tsx` cached initial total counts and only polled `/dashboard` on explicit page navigation.
- **Fix**: Added dynamic polling and event triggers on simulator action completions so the top stats bar immediately reflects newly dark poles and active incidents.

### [2026-08-02] ADR-003: Transformer Fault Simulator Button Rewiring
- **Status**: Resolved & Verified
- **Symptom**: Clicking "Inject Transformer Fault" in the simulator created a feeder-wide blackout covering all transformers instead of isolating to a single transformer.
- **Root Cause**: The frontend simulator component misrouted the request to `/simulate/feeder` instead of `/simulate/transformer`.
- **Fix**: Re-wired the button handler to call `POST /simulate/transformer?transformer_id=...`, generating single-transformer incidents as intended.

### [2026-08-01] ADR-002: Unified Incident Grouping Engine (Per-Pole Ticket Bug Fix)
- **Status**: Resolved & Verified
- **Symptom**: Injecting a conductor fault on a span affecting 10 downstream poles generated 10 individual incident records and 10 separate work order tickets.
- **Root Cause**: Telemetry ingestion evaluated state changes on a per-node basis and spawned incidents independently across 3 separate code paths (`span`, `dead-sensor`, `feeder`).
- **Fix**: Refactored `LocalizationService` to route all telemetry boundary events through a single shared grouping pipeline:
  - Finds the highest single $(U, V)$ live-dark boundary span.
  - Groups all downstream dark nodes into **exactly 1 Incident** and **1 Ticket**.
  - Merges feeder-wide outages into `FEEDER_FAULT` incidents (`transformer_id: MULTIPLE`).

### [2026-07-30] ADR-001: Geolocation Selection (Bangalore Coordinates)
- **Status**: Accepted & Implemented
- **Context**: Needed realistic GIS coordinates for distribution network map rendering.
- **Decision**: Adopted Bangalore central coordinates (`12.9716, 77.5946`) matching the project assignment specification example location.

---

## Known Limitations

1. **Missing-Device Boundary UI Verification**:
   - The graph-based localization logic handles missing telemetry devices (poles with no physical sensor) by marking boundary uncertainty and range poles in backend unit tests. However, UI map rendering for range pole highlight indicators has not been specifically re-verified under complex UI manual testing.

2. **Load Testing & Sustained Throughput Targets**:
   - Performance targets specified in design objectives (e.g. 39 msg/s sustained, 5000-msg burst, <120s detection latency) have not undergone formal load-testing using benchmark tools like Locust or k6. We state this explicitly rather than asserting unverified metrics.

---

## Fragile System Components

1. **In-Memory NetworkX Graph Synchronization**:
   - The localization engine builds an in-memory NetworkX directed graph on startup. If pole data is mutated directly in PostgreSQL without calling `GraphBuilder.build()`, in-memory graph state will drift from SQL storage until backend restart.

2. **Single-Worker Uvicorn Deployment**:
   - The backend runs on a single Uvicorn process. Under high telemetry throughput without a message queue (e.g. Redis/RabbitMQ), HTTP telemetry requests block on database transaction commits.

---

## What I'd Do With 2 More Weeks

1. **Load Testing & Telemetry Streaming Buffer**:
   - Implement an asynchronous message buffer (Apache Kafka or Redis Streams) in front of `POST /telemetry` to handle 5000+ msg/s telemetry bursts without HTTP request blocking.
   - Run formal benchmark suites using Locust to measure detection latency under load.

2. **Granular Operator Workflow & Role-Based Access (RBAC)**:
   - Add field crew assignment features to work tickets, allowing dispatchers to assign specific crew IDs, track repair ETA, and log field notes.

3. **Complete UI Range-Pole Boundary Visualizer**:
   - Enhance the Leaflet map component to render dashed boundary bounding boxes around candidate poles when confidence is penalized due to missing sensors.
