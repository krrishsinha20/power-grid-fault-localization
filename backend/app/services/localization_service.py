from sqlalchemy.orm import Session

from app.localization.graph_builder import GraphBuilder
from app.localization.boundary_detector import BoundaryDetector
from app.localization.downstream_counter import DownstreamCounter
from app.localization.confidence import ConfidenceEngine
from app.localization.topology_inference import TopologyInference

from app.models.incident import Incident

from app.services.outage_service import OutageService


class LocalizationService:
    """
    Orchestrates the full detect -> localize pipeline:

      1. Build the topology graph from the pole registry.
      2. Run TopologyInference to geometrically wire up the ~60% of
         transformers with no recorded pole ordering.
      3. Detect live/dark boundaries (span, transformer, or a
         range when the boundary itself sits behind no-device poles).
      4. Skip boundaries inside an active scheduled outage window.
      5. Count genuinely-dark downstream poles per boundary.
      6. Score confidence, factoring in inferred topology and
         boundary uncertainty.
      7. Merge feeder-wide blackouts: if every transformer under a
         feeder is fully dark, a fault upstream of the feeder (the 11kV
         side) is the real cause -- reporting it as N separate
         transformer-fault tickets is exactly the "one alert per dark
         pole" failure mode the brief warns about, just one level up
         the tree. Those boundaries are collapsed into a single
         FEEDER_FAULT incident before they're returned.
    """

    def __init__(self, db: Session):

        self.db = db

    def process(self):

        graph = GraphBuilder(
            self.db
        ).build()

        inference_result = TopologyInference(graph).infer()

        long_inferred_edges = set(inference_result["long_edges"])

        boundaries = BoundaryDetector(
            graph
        ).detect()

        if len(boundaries) == 0:

            return []

        already_tracked = {

            row.end_pole
            for row in (
                self.db.query(Incident)
                .filter(Incident.status.notin_(["VERIFIED", "CLOSED"]))
                .all()
            )

        }

        counter = DownstreamCounter(graph)

        confidence_engine = ConfidenceEngine(graph)

        outage_service = OutageService(self.db)

        incidents = []
        self.suppressed_count = 0
        self.suppressed_outages = []

        for boundary in boundaries:

            # Don't recreate already active incidents
            if boundary["child"] in already_tracked:
                continue

            child_node = graph.nodes[boundary["child"]]

            active_outage = outage_service.is_within_scheduled_outage(
                feeder_id=child_node["feeder_id"],
                transformer_id=child_node["transformer_id"]
            )

            # Planned outage -> Ignore
            if active_outage is not None:
                self.suppressed_count += 1
                self.suppressed_outages.append(active_outage)
                continue

            downstream = counter.count(
                boundary["child"]
            )

            edge_data = {}
            if boundary["parent"] is not None:
                edge_data = graph.get_edge_data(
                    boundary["parent"], boundary["child"]
                ) or {}

            is_inferred_edge = edge_data.get("inferred", False)
            inferred_distance_m = edge_data.get("inferred_distance_m")

            edge_key = (boundary["parent"], boundary["child"])

            if edge_key in long_inferred_edges:
                inferred_distance_m = inferred_distance_m or (
                    ConfidenceEngine.LONG_INFERRED_EDGE_THRESHOLD_M + 1
                )

            confidence = confidence_engine.calculate(
                affected_poles=downstream["count"],
                missing_topology=is_inferred_edge,
                boundary_uncertain=boundary["boundary_uncertain"],
                range_pole_count=len(boundary["range_poles"]),
                inferred_edge_distance_m=(
                    inferred_distance_m if is_inferred_edge else None
                ),
            )

            fault_type = None

            if (
                downstream["count"] == 1
                and boundary["parent"] is not None
                and not downstream["reconnect_poles"]
            ):
                fault_type = "SENSOR_FAILURE"
            elif downstream["reconnect_poles"]:
                fault_type = "SENSOR_FAILURE"

            incidents.append(

                {

                    "start_pole": boundary["parent"],

                    "end_pole": boundary["child"],

                    "affected_poles": downstream["count"],

                    "affected_pole_ids": downstream["poles"],

                    "confidence": confidence["confidence"],

                    "penalties": confidence["penalties"],

                    "fault_type": fault_type,

                    "boundary_uncertain": boundary["boundary_uncertain"],

                    "range_poles": boundary["range_poles"],

                    "latitude": child_node["latitude"],

                    "longitude": child_node["longitude"],

                    "feeder_id": child_node["feeder_id"] or "UNKNOWN",

                    "transformer_id": child_node["transformer_id"] or "UNKNOWN",

                    "pincode": child_node["pincode"] or "UNKNOWN"

                }

            )

        return self._merge_feeder_wide_faults(graph, incidents)

    def _merge_feeder_wide_faults(self, graph, incidents):
        """
        Groups this batch's non-sensor-failure incidents by feeder_id.
        For any feeder where EVERY pole under it is currently dark
        (i.e. the outage isn't confined to one or two transformers --
        the whole feeder is down, meaning the real fault is upstream
        on the 11kV side), collapse all of that feeder's boundary
        incidents into one FEEDER_FAULT incident covering every
        affected pole, instead of leaving one ticket per transformer.
        """

        by_feeder = {}

        for incident in incidents:

            if incident["fault_type"] == "SENSOR_FAILURE":
                continue

            feeder_id = incident["feeder_id"]

            if feeder_id in (None, "UNKNOWN"):
                continue

            by_feeder.setdefault(feeder_id, []).append(incident)

        merged_feeder_ids = set()
        feeder_fault_incidents = []

        for feeder_id, feeder_incidents in by_feeder.items():

            if not self._feeder_fully_dark(graph, feeder_id):
                continue

            merged_feeder_ids.add(feeder_id)

            all_pole_ids = []
            seen = set()

            for incident in feeder_incidents:
                for pole_id in incident["affected_pole_ids"]:
                    if pole_id not in seen:
                        seen.add(pole_id)
                        all_pole_ids.append(pole_id)

            worst_confidence = min(
                incident["confidence"] for incident in feeder_incidents
            )

            merged_penalties = [
                f"Merged {len(feeder_incidents)} transformer-level "
                f"boundaries under feeder {feeder_id} into one "
                f"feeder-wide incident (every pole on this feeder "
                f"is dark)."
            ]

            representative = feeder_incidents[0]

            feeder_fault_incidents.append({
                "start_pole": None,
                "end_pole": representative["end_pole"],
                "affected_poles": len(all_pole_ids),
                "affected_pole_ids": all_pole_ids,
                "confidence": worst_confidence,
                "penalties": merged_penalties,
                "fault_type": "FEEDER_FAULT",
                "boundary_uncertain": any(
                    incident["boundary_uncertain"]
                    for incident in feeder_incidents
                ),
                "range_poles": [],
                "latitude": representative["latitude"],
                "longitude": representative["longitude"],
                "feeder_id": feeder_id,
                "transformer_id": "MULTIPLE",
                "pincode": representative["pincode"],
            })

        if not merged_feeder_ids:
            return incidents

        remaining = [
            incident for incident in incidents
            if incident["feeder_id"] not in merged_feeder_ids
        ]

        return remaining + feeder_fault_incidents

    def _feeder_fully_dark(self, graph, feeder_id):

        total = 0
        dark = 0

        for _, data in graph.nodes(data=True):

            if data.get("feeder_id") != feeder_id:
                continue

            total += 1

            if not data.get("energized", True):
                dark += 1

        return total > 0 and dark == total