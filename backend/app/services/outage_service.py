from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.scheduled_outage import ScheduledOutage


# Real-world caveat from the data contract: scheduled shutdowns start
# late and overrun by 20-40 minutes routinely. We pad both ends of the
# published window generously so a real outage isn't mistaken for
# planned maintenance just because the crew was late switching off,
# and so it isn't mistaken for a fault just because they were late
# switching back on either.
START_GRACE = timedelta(minutes=15)
END_GRACE = timedelta(minutes=40)


class OutageService:
    """
    NOTE on the "1 in 10 cancelled without the feed being updated"
    caveat from the data contract: there is no way to detect a
    cancelled-but-unupdated scheduled outage from this feed alone --
    if the feed says ACTIVE, we have no signal to contradict it. This
    is a known, documented failure mode (see ARCHITECTURE.md): a
    cancelled outage will suppress a real fault for the duration of
    its window. Mitigation is operator-facing, not algorithmic --
    the operator console shows *which* incidents were suppressed by a
    scheduled outage and lets a human override, rather than silently
    dropping them with no trace.
    """

    def __init__(self, db: Session):
        self.db = db
        self._active_outages_cache = None

    def is_within_scheduled_outage(
        self,
        feeder_id: str | None,
        transformer_id: str | None,
        at: datetime | None = None
    ) -> ScheduledOutage | None:

        # BUG FIX: every other timestamp in this system (Pole.last_seen_at,
        # Telemetry.timestamp/received_at, ScheduledOutage.start_time/
        # end_time via seed) is stored and compared in UTC. datetime.now()
        # returns local server time, which silently breaks this
        # comparison on any host not running in UTC -- a real fault could
        # get suppressed as "within" a scheduled outage window that has
        # already ended, or a genuinely suppressed outage could leak
        # through as a fault. Must be utcnow() to match everything else.
        at = at or datetime.utcnow()

        outages = self._get_active_outages()

        for outage in outages:

            start = outage.start_time - START_GRACE
            end = outage.end_time + END_GRACE

            # Skip if current time is outside outage window
            if not (start <= at <= end):
                continue

            # Transformer-specific planned outage
            if (
                outage.transformer_id is not None
                and outage.transformer_id == transformer_id
            ):
                return outage

            # Feeder-wide planned outage
            if (
                outage.transformer_id is None
                and outage.feeder_id == feeder_id
            ):
                return outage

        return None

    def _get_active_outages(self):
        """
        Cached per OutageService instance. LocalizationService creates
        one OutageService per `process()` call and checks every
        boundary against it in the same request -- without this cache
        we'd re-run the same "status == ACTIVE" query once per
        boundary, which adds up during a storm with dozens of
        simultaneous faults.
        """

        if self._active_outages_cache is None:

            self._active_outages_cache = (
                self.db.query(ScheduledOutage)
                .filter(
                    ScheduledOutage.status == "ACTIVE"
                )
                .all()
            )

        return self._active_outages_cache