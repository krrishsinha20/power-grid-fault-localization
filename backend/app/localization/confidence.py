from networkx import DiGraph


class ConfidenceEngine:
    """
    Produces a 0-100 confidence score plus a human-readable list of
    penalties, so the operator console can show *why* a ticket is
    less than 100% sure, not just a bare number.

    Two new inputs beyond the original telemetry/topology penalties:

      - `boundary_uncertain` / `range_pole_count`: set when
        BoundaryDetector had to walk past one or more no-device poles
        to find the fault boundary (see boundary_detector.py). The
        reported span is a range, not a single confirmed span, so
        confidence takes an extra hit proportional to how many poles
        are in that blind spot.

      - `inferred_edge_distance_m`: set when the boundary sits on an
        edge that TopologyInference had to infer geometrically rather
        than read from the registry. A short inferred edge (adjacent
        poles, plausible real span) costs less confidence than a long
        one (the MST guessed across a gap it probably shouldn't have).
    """

    LONG_INFERRED_EDGE_THRESHOLD_M = 150.0

    def __init__(self, graph: DiGraph):
        self.graph = graph

    def calculate(
        self,
        affected_poles: int,
        missing_telemetry: int = 0,
        missing_topology: bool = False,
        duplicate_events: int = 0,
        inactive_devices: int = 0,
        boundary_uncertain: bool = False,
        range_pole_count: int = 0,
        inferred_edge_distance_m: float | None = None,
    ):

        score = 100.0

        penalties = []

        # Missing telemetry
        if missing_telemetry > 0:
            deduction = min(20, missing_telemetry * 2)
            score -= deduction
            penalties.append(
                f"{deduction}% deducted due to missing telemetry"
            )

        # Missing topology (coarse DT-level fallback used instead of
        # a real span-level answer)
        if missing_topology:
            score -= 20
            penalties.append(
                "20% deducted due to inferred topology"
            )

        # Boundary had to be walked past no-device poles -- the exact
        # span is a range, not a confirmed point.
        if boundary_uncertain:
            deduction = min(15, 5 + range_pole_count * 3)
            score -= deduction
            penalties.append(
                f"{deduction}% deducted: boundary falls in a "
                f"{range_pole_count}-pole range with no telemetry "
                f"device to pinpoint it exactly"
            )

        # The boundary edge itself was geometrically inferred rather
        # than read from the registry.
        if inferred_edge_distance_m is not None:

            if inferred_edge_distance_m > self.LONG_INFERRED_EDGE_THRESHOLD_M:
                deduction = 20
                penalties.append(
                    f"20% deducted: inferred wiring edge is "
                    f"{inferred_edge_distance_m:.0f}m, longer than a "
                    f"typical LT span -- this guess is less reliable"
                )
            else:
                deduction = 8
                penalties.append(
                    f"8% deducted: fault boundary sits on a "
                    f"geometrically inferred edge "
                    f"({inferred_edge_distance_m:.0f}m), not a "
                    f"digitized one"
                )

            score -= deduction

        # Duplicate events
        if duplicate_events > 0:
            deduction = min(10, duplicate_events)
            score -= deduction
            penalties.append(
                f"{deduction}% deducted due to duplicate telemetry"
            )

        # Offline devices
        if inactive_devices > 0:
            deduction = min(10, inactive_devices * 2)
            score -= deduction
            penalties.append(
                f"{deduction}% deducted due to inactive devices"
            )

        # Very small fault region
        if affected_poles <= 1:
            score -= 5
            penalties.append(
                "5% deducted due to limited evidence"
            )

        score = max(score, 0)

        return {
            "confidence": round(score, 2),
            "penalties": penalties
        }