# Power Grid Fault Localization System

A real-time power grid fault localization system where deterministic graph algorithms identify fault boundaries while an LLM generates human-readable root-cause analysis and recommended actions. The system ingests high-frequency telemetry from grid sensors, builds a dynamic topology tree, accurately localizes physical line and transformer failures to single boundaries, suppresses noise and scheduled outages, auto-generates tickets, and provides AI-powered root-cause explanations on demand.

---

## 🌐 Live Deployment

If you want to explore and test the system immediately without running it locally, use the live deployed links:

- 🖥️ **Live Frontend Operator Console**: [https://hearty-spirit-production-7a5f.up.railway.app/](https://hearty-spirit-production-7a5f.up.railway.app/)
- ⚙️ **Live Backend OpenAPI Docs**: [https://power-grid-fault-localization-production.up.railway.app/docs](https://power-grid-fault-localization-production.up.railway.app/docs)

---

## ⚡ Quick Start (Clone & Run)

Follow these simple commands line-by-line in your terminal:

```bash
# 1. Clone repository & enter the project folder
git clone https://github.com/krrishsinha20/power-grid-fault-localization.git && cd power-grid-fault-localization

# 2. Build and launch all services (PostgreSQL, FastAPI Backend, Vite Frontend)
docker compose up --build
```

Once database initialization and seeding finish, your terminal will output:

```text
================================================================
  FLASH — Power Grid Fault Localization System Ready!
  • Frontend Operator Console : http://localhost:5173
  • Backend OpenAPI Docs      : http://localhost:8000/docs
  • Backend API Base URL      : http://localhost:8000
================================================================
```

### Local Service Endpoints
Click on the URLs printed in your terminal or open them in your browser:
- 🖥️ **Frontend Operator Console**: [http://localhost:5173](http://localhost:5173)
- ⚙️ **Backend OpenAPI Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- 🔌 **Backend Base API**: [http://localhost:8000](http://localhost:8000)

---

## 🔑 LLM API Key Configuration (Optional)

The system includes an AI-powered **Root Cause Analysis & Action Recommendation** module using LLM capabilities (Groq API).

### How to add your API Key:
1. Create or update the `.env` file in the root folder or `backend/` directory:
   ```env
   GROQ_API_KEY=gsk_your_groq_api_key_here
   ```
2. Alternatively, set it directly in your terminal session before launching:
   ```bash
   GROQ_API_KEY="gsk_your_groq_api_key_here" docker compose up --build
   ```

> [!NOTE]
> **Graceful Fallback Mode**: Providing an LLM API key is **optional**. If `GROQ_API_KEY` is omitted, the system seamlessly falls back to local heuristic-based root-cause analysis templates. All core fault localization algorithms, graph topology engines, GIS map visualizations, noise suppression logic, and ticket auto-generation operate at **100% functionality out-of-the-box** without an API key.

---

## 🎥 Demonstration Video

[![System Walkthrough Demo](https://img.youtube.com/vi/DEMO_VIDEO_ID/maxresdefault.jpg)](DEMO_VIDEO_URL)  
*(Watch full feature demonstration video: [DEMO_VIDEO_URL])*

---

## 📚 Documentation Map

- **[ARCHITECTURE.md](file:///c:/Users/KRRISH/Desktop/Propel/ARCHITECTURE.md)**: Deep dive into the data ingestion pipeline, graph-based topology engine, boundary detection algorithm, missing-topology inference, noise suppression, API specifications, UI UX choices, and AI cost/degradation model.
- **[DEPLOYMENT.md](file:///c:/Users/KRRISH/Desktop/Propel/DEPLOYMENT.md)**: Local Docker Compose setup guide, environment configuration, system verification steps, Railway cloud deployment notes, and a detailed troubleshooting matrix for bugs encountered during development.
- **[DECISIONS.md](file:///c:/Users/KRRISH/Desktop/Propel/DECISIONS.md)**: Chronological decision log covering key architectural trade-offs, bug fixes, known issues (such as PIN code defaults), known limitations, fragile components, and roadmap for future iterations.
- **[AI-WORKFLOW.md](file:///c:/Users/KRRISH/Desktop/Propel/AI-WORKFLOW.md)**: Analysis of AI-assisted engineering methodology, breakdown of human vs AI contribution percentages, and 3 concrete case studies of subtle AI-generated bugs discovered and fixed through systematic testing.
