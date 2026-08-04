import uuid


def generate_incident_id():

    return (
        f"INC-{uuid.uuid4().hex[:8].upper()}"
    )


def generate_ticket_id():

    return (
        f"TKT-{uuid.uuid4().hex[:8].upper()}"
    )


def generate_transformer_id(
    number: int
):

    return f"DT{number:04}"


def generate_pole_id(
    number: int
):

    return f"P{number:05}"


def generate_feeder_id(
    number: int
):

    return f"F{number:03}"