from enum import Enum


class FaultType(str, Enum):

    SPAN_FAULT = "SPAN_FAULT"

    TRANSFORMER_FAULT = "TRANSFORMER_FAULT"

    FEEDER_FAULT = "FEEDER_FAULT"

    SENSOR_FAILURE = "SENSOR_FAILURE"

    UNKNOWN = "UNKNOWN"


class IncidentStatus(str, Enum):

    DETECTED = "DETECTED"

    VERIFIED = "VERIFIED"

    RESOLVED = "RESOLVED"

    CLOSED = "CLOSED"


class TicketStatus(str, Enum):

    OPEN = "OPEN"

    ASSIGNED = "ASSIGNED"

    IN_PROGRESS = "IN_PROGRESS"

    CLOSED = "CLOSED"


class TicketPriority(str, Enum):

    LOW = "LOW"

    MEDIUM = "MEDIUM"

    HIGH = "HIGH"

    CRITICAL = "CRITICAL"


class TelemetryEvent(str, Enum):

    HEARTBEAT = "heartbeat"

    POWER_LOST = "power_lost"

    POWER_RESTORED = "power_restored"


class PoleState(str, Enum):

    ENERGIZED = "ENERGIZED"

    DE_ENERGIZED = "DE_ENERGIZED"