from pydantic import BaseModel, Field


class SpanFaultRequest(BaseModel):

    pole_ids: list[str] = Field(
        ...,
        examples=[["P00023", "P00024", "P00025"]]
    )


class TransformerFaultRequest(BaseModel):

    transformer_id: str = Field(
        ...,
        examples=["DT0001"]
    )


class FeederFaultRequest(BaseModel):

    feeder_id: str = Field(
        ...,
        examples=["F001"]
    )


class SensorFaultRequest(BaseModel):

    pole_id: str = Field(
        ...,
        examples=["P00045"]
    )


class DuplicateTelemetryRequest(BaseModel):

    pole_id: str = Field(
        ...,
        examples=["P00045"]
    )

    repeat_count: int = Field(
        default=3,
        ge=2,
        le=20,
        description=(
            "How many times to resend the exact same "
            "(device_id, seq) packet, simulating at-least-once "
            "delivery retries."
        )
    )


class OutOfOrderTelemetryRequest(BaseModel):

    pole_id: str = Field(
        ...,
        examples=["P00045"]
    )


class RepairRequest(BaseModel):

    pole_ids: list[str] = Field(
        ...,
        examples=[["P00023", "P00024", "P00025"]]
    )


class SimulationResponse(BaseModel):

    success: bool

    message: str