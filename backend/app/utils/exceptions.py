class PoleNotFoundException(Exception):

    def __init__(self, pole_id: str):

        super().__init__(
            f"Pole '{pole_id}' not found."
        )


class TransformerNotFoundException(Exception):

    def __init__(self, transformer_id: str):

        super().__init__(
            f"Transformer '{transformer_id}' not found."
        )


class IncidentNotFoundException(Exception):

    def __init__(self, incident_id: str):

        super().__init__(
            f"Incident '{incident_id}' not found."
        )


class TicketNotFoundException(Exception):

    def __init__(self, ticket_id: str):

        super().__init__(
            f"Ticket '{ticket_id}' not found."
        )


class InvalidTelemetryException(Exception):

    def __init__(self):

        super().__init__(
            "Invalid telemetry payload."
        )