from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.pole import Pole
from app.models.telemetry import Telemetry
from app.schemas.telemetry_schema import TelemetryCreate


# A power_lost message can legitimately arrive up to ~6 hours late
# (device retrying from a queue after being offline). Anything older
# than this relative to our own clock is treated as noise rather than
# a live state change -- we still store it for the audit trail, but
# we never let it flip the pole's current state.
MAX_ACCEPTABLE_STALENESS = timedelta(hours=6)

# Device clocks can disagree by up to ~90s per the spec. We allow a
# little slack before calling something "out of order" so ordinary
# jitter doesn't get rejected.
CLOCK_SKEW_TOLERANCE = timedelta(seconds=90)


class TelemetryService:

    def __init__(self, db: Session):
        self.db = db

    def ingest(self, payload: TelemetryCreate) -> Telemetry:
        """
        Receive telemetry from simulator / IoT device.

        Always stores the raw event (audit trail is unconditional --
        we never lose data), but only lets it update the pole's
        "current" state when it is the most recent evidence we have
        for that device, per the `seq` field (resets to 0 on `boot`).

        Handles, per the data contract in 02-data-and-systems.md:
          - at-least-once delivery / exact duplicates (same device_id
            + seq already applied)
          - out-of-order arrival (lower seq arriving after a higher
            one from the same device)
          - stale retries (a `power_lost` from hours ago arriving
            late, after the device already came back and reported
            `power_restored`)
          - device swap on a pole (a new device_id shows up for a
            pole we already know -- pole_id is the trusted key for
            location per the data contract, so we just start tracking
            the new device_id's sequence from scratch)
          - firmware 1.2.x devices that never send `power_lost` --
            these are handled upstream by DeadSensorService via
            heartbeat timeout, not here.
        """

        pole = (
            self.db.query(Pole)
            .filter(Pole.pole_id == payload.pole_id)
            .first()
        )

        if pole is None:
            raise ValueError(
                f"Pole '{payload.pole_id}' not found."
            )

        if payload.sequence_number < 0:
            raise ValueError(
                "Invalid sequence number."
            )

        if not payload.event.strip():
            raise ValueError(
                "Event cannot be empty."
            )

        is_duplicate = self._is_exact_duplicate(pole, payload)

        should_apply = (
            not is_duplicate
            and self._should_update_state(pole, payload)
        )

        telemetry = Telemetry(

            pole_id=pole.id,

            device_id=payload.device_id,

            event=payload.event,

            energized=payload.energized,

            sequence_number=payload.sequence_number,

            timestamp=payload.timestamp

        )

        self.db.add(telemetry)

        if should_apply:

            pole.energized = payload.energized
            pole.last_seen_at = datetime.utcnow()
            pole.last_device_id = payload.device_id
            pole.last_applied_seq = payload.sequence_number

        elif not is_duplicate:
            # We still heard from the device even if this particular
            # packet is stale/out-of-order -- update last_seen_at so
            # DeadSensorService doesn't wrongly flag it as silent, but
            # don't touch energized/last_applied_seq.
            pole.last_seen_at = datetime.utcnow()

        self.db.flush()

        self.db.refresh(telemetry)

        return telemetry

    def _is_exact_duplicate(
        self,
        pole: Pole,
        payload: TelemetryCreate
    ) -> bool:

        if pole.last_device_id != payload.device_id:
            return False

        if pole.last_applied_seq is None:
            return False

        return payload.sequence_number == pole.last_applied_seq

    def _should_update_state(
        self,
        pole: Pole,
        payload: TelemetryCreate
    ) -> bool:

        # New or swapped device on this pole -- start fresh. pole_id
        # is the trusted identity per the data contract, device_id is
        # not, so a change here is expected behaviour, not an anomaly.
        if pole.last_device_id != payload.device_id:
            return True

        if pole.last_applied_seq is None:
            return True

        # `boot` resets the device's own seq counter to 0. If we see
        # a boot (or a seq that has wrapped back down right after a
        # boot event) from the *same* device_id, trust it as a fresh
        # start rather than rejecting it as "out of order".
        if payload.event == "boot":
            return True

        if payload.sequence_number <= pole.last_applied_seq:
            # Lower or equal seq than what we've already applied for
            # this device -- this is either a duplicate retry or an
            # out-of-order/late arrival. Don't let it override newer
            # state.
            return False

        # Sequence looks newer. Still guard against a very stale
        # message (e.g. a `power_lost` retried for hours) landing
        # after we've already moved on -- if the payload's own
        # timestamp is implausibly old relative to now, treat it as
        # stale rather than current, even though its seq is higher
        # than anything we've seen (can happen after a long queue
        # flush on reconnect).
        now = datetime.utcnow()
        payload_ts = payload.timestamp

        if payload_ts is not None:
            age = now - payload_ts.replace(tzinfo=None)
            if age > MAX_ACCEPTABLE_STALENESS:
                return False

        return True

    def latest_state(
        self,
        pole_id: str
    ) -> Pole | None:

        return (
            self.db.query(Pole)
            .filter(Pole.pole_id == pole_id)
            .first()
        )

    def latest_events(
        self,
        limit: int = 100,
        include_heartbeat: bool = False
    ):

        query = (
            self.db.query(Telemetry)
            .order_by(
                Telemetry.timestamp.desc()
            )
        )

        if not include_heartbeat:

            query = query.filter(
                Telemetry.event != "heartbeat"
            )

        return query.limit(limit).all()