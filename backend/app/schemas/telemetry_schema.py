from datetime import datetime

from pydantic import BaseModel


class TelemetryCreate(BaseModel):

    pole_id: str

    device_id: str

    event: str

    energized: bool

    sequence_number: int

    timestamp: datetime


class TelemetryResponse(BaseModel):

    id: int

    pole_id: int

    device_id: str

    event: str

    energized: bool

    sequence_number: int

    timestamp: datetime

    class Config:

        from_attributes = True