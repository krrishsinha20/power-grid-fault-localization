from datetime import datetime

from pydantic import BaseModel


class TicketCreate(BaseModel):

    ticket_id: str

    incident_id: int

    priority: str


class TicketResponse(TicketCreate):

    id: int

    assigned_to: str | None = None

    assigned_team: str | None = None

    status: str

    remarks: str | None = None

    created_at: datetime

    updated_at: datetime

    class Config:

        from_attributes = True