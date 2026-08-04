from datetime import datetime

from pydantic import BaseModel


class ScheduledOutageCreate(BaseModel):

    outage_id: str

    feeder_id: str

    transformer_id: str | None = None

    start_time: datetime

    end_time: datetime

    reason: str

    status: str = "ACTIVE"


class ScheduledOutageUpdate(BaseModel):

    feeder_id: str | None = None

    transformer_id: str | None = None

    start_time: datetime | None = None

    end_time: datetime | None = None

    reason: str | None = None

    status: str | None = None


class ScheduledOutageResponse(ScheduledOutageCreate):

    id: int

    created_at: datetime

    updated_at: datetime

    class Config:

        from_attributes = True