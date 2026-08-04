from datetime import datetime

from pydantic import BaseModel


class IncidentCreate(BaseModel):

    incident_id: str

    fault_type: str

    feeder_id: str

    transformer_id: str

    # Span Fault -> value
    # Transformer Fault -> None
    # Feeder Fault -> None
    start_pole: str | None = None

    end_pole: str | None = None

    affected_pole_count: int

    affected_pole_ids: list[str]

    confidence: float


class IncidentResponse(IncidentCreate):

    id: int

    status: str

    root_cause: str | None = None

    ai_summary: str | None = None

    recommended_action: str | None = None

    created_at: datetime

    updated_at: datetime

    class Config:
        from_attributes = True