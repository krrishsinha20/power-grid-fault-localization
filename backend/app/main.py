import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database.database import SessionLocal
from app.database.init_db import create_tables
from app.database.seed import seed_database

from app.services.scheduler_service import heartbeat_loop

from app.api.telemetry import router as telemetry_router
from app.api.simulator import router as simulator_router
from app.api.incident import router as incident_router
from app.api.tickets import router as ticket_router
from app.api.dashboard import router as dashboard_router
from app.api.poles import router as poles_router
from app.api.scheduled_outage import router as scheduled_outage_router

app = FastAPI(title="AI Power Grid Fault Localization", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    create_tables()
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()
    asyncio.create_task(heartbeat_loop())

app.include_router(telemetry_router)
app.include_router(simulator_router)
app.include_router(incident_router)
app.include_router(ticket_router)
app.include_router(dashboard_router)
app.include_router(poles_router)
app.include_router(scheduled_outage_router)

@app.get("/")
def root():
    return {"message": "AI Power Grid Fault Localization API", "status": "Running"}