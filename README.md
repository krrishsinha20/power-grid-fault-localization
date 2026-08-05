# Power Grid Fault Localization System

A real-time power grid fault localization system where deterministic graph algorithms identify fault boundaries while an LLM generates human-readable root-cause analysis and recommended actions. The system ingests high-frequency telemetry from grid sensors, builds a dynamic topology tree, accurately localizes physical line and transformer failures to single boundaries, suppresses noise and scheduled outages, auto-generates tickets, and provides AI-powered root-cause explanations on demand.

## Quick Start (Clone & Run)

To clone directly into your current working directory in VS Code and launch:

```bash
# 1. Clone all files directly into the current open folder
git clone https://github.com/krrishsinha20/power-grid-fault-localization.git .

# 2. Launch the entire stack (PostgreSQL, FastAPI Backend, React Frontend)
docker compose up --build
```

Once initialization finishes and database seeding completes, your terminal will display:

```text
================================================================
  FLASH — Power Grid Fault Localization System Ready!
  • Frontend Operator Console : http://localhost:5173
  • Backend OpenAPI Docs      : http://localhost:8000/docs
  • Backend API Base URL      : http://localhost:8000
================================================================
```

- **Frontend Console**: [http://localhost:5173](http://localhost:5173)
- **Backend API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

## Live Deployment

- **Live Frontend Application**: https://hearty-spirit-production-7a5f.up.railway.app/
- **Live Backend OpenAPI Docs**: https://power-grid-fault-localization-production.up.railway.app/docs

## Demonstration Video

[![System Walkthrough Demo](https://img.youtube.com/vi/DEMO_VIDEO_ID/maxresdefault.jpg)](DEMO_VIDEO_URL)  
*(Watch full feature demonstration video: [DEMO_VIDEO_URL])*

## Documentation Map

- **[ARCHITECTURE.md](file:///c:/Users/KRRISH/Desktop/Propel/ARCHITECTURE.md)**: Deep dive into the data ingestion pipeline, graph-based topology engine, boundary detection algorithm, missing-topology inference, noise suppression, API specifications, UI UX choices, and AI cost/degradation model.
- **[DEPLOYMENT.md](file:///c:/Users/KRRISH/Desktop/Propel/DEPLOYMENT.md)**: Local Docker Compose setup guide, environment configuration, system verification steps, Railway cloud deployment notes, and a detailed troubleshooting matrix for bugs encountered during development.
- **[DECISIONS.md](file:///c:/Users/KRRISH/Desktop/Propel/DECISIONS.md)**: Chronological decision log covering key architectural trade-offs, bug fixes, known issues (such as PIN code defaults), known limitations, fragile components, and roadmap for future iterations.
- **[AI-WORKFLOW.md](file:///c:/Users/KRRISH/Desktop/Propel/AI-WORKFLOW.md)**: Analysis of AI-assisted engineering methodology, breakdown of human vs AI contribution percentages, and 3 concrete case studies of subtle AI-generated bugs discovered and fixed through systematic testing.
