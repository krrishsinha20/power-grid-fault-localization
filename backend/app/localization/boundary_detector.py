from networkx import DiGraph


class BoundaryDetector:
    """
    Finds the live/dark boundary in the topology.

    Two twists on top of the plain "parent live, child dark" rule:

    1. Missing-device poles. A pole with no telemetry device never
       gets a real energized reading — its `energized` field is
       whatever default it was created with, not evidence. So if the
       boundary child itself has no device, we don't trust its own
       state; instead we walk further down the branch until we find a
       pole that actually reports (has a device with a real reading),
       and report the fault as a *range* — "somewhere between the last
       confirmed-live pole and the first confirmed-dark pole" — rather
       than pretending we know the exact span.

    2. Transformer fault detection unchanged in shape, but also
       carries the missing-device caveat: a root pole with no device
       can't tell us it's dark on its own; we only trust it if it (or
       something with real telemetry under it) actually reports dark.
    """

    def __init__(self, graph: DiGraph):
        self.graph = graph

    def detect(self):
        """
        Returns detected fault boundaries. Each boundary dict:

        {
            "parent": <pole_id or None>,
            "child": <pole_id>,          # first node on the dark side
                                          # with *confirmed* telemetry
            "range_poles": [...],        # no-device poles sitting
                                          # between parent and child,
                                          # unknown state, part of the
                                          # ambiguity range
            "boundary_uncertain": bool   # True if we had to skip over
                                          # undeviced poles to get here
        }
        """

        boundaries = []

        # -----------------------------
        # Span Fault Detection
        # -----------------------------
        for parent in self.graph.nodes():

            parent_data = self.graph.nodes[parent]

            if not self._has_device(parent_data):
                # No real reading on the parent either -- we can't
                # anchor a boundary here with confidence. Skip; if
                # this parent's own ancestor is a confirmed-live pole,
                # that ancestor will be considered separately.
                continue

            if not parent_data.get("energized", True):
                # Parent itself is dark -- not a live/dark edge.
                continue

            for child in self.graph.successors(parent):

                resolved = self._resolve_dark_child(child)

                if resolved is None:
                    continue

                boundaries.append(
                    {
                        "parent": parent,
                        "child": resolved["child"],
                        "range_poles": resolved["range_poles"],
                        "boundary_uncertain": resolved["uncertain"]
                    }
                )

        # -----------------------------
        # Transformer Fault Detection
        # -----------------------------
        for node in self.graph.nodes():

            predecessors = list(
                self.graph.predecessors(node)
            )

            if len(predecessors) != 0:
                continue

            resolved = self._resolve_dark_child(node)

            if resolved is None:
                continue

            boundaries.append(
                {
                    "parent": None,
                    "child": resolved["child"],
                    "range_poles": resolved["range_poles"],
                    "boundary_uncertain": resolved["uncertain"]
                }
            )

        return boundaries

    def _has_device(self, node_data: dict) -> bool:
        # graph_builder tags this; default True so we fail open for
        # any graph built before this flag existed rather than
        # silently dropping every boundary.
        return node_data.get("has_device", True)

    def _resolve_dark_child(self, child: str):
        """
        Starting at `child`, decide whether this branch is genuinely
        dark. If `child` has no device, walk down until we find a pole
        that actually reports, collecting the skipped no-device poles
        as an uncertainty range.

        Returns None if this branch is not dark (live, confirmed), or
        a dict describing the confirmed dark child + any ambiguous
        range poles skipped to get there.
        """

        range_poles = []
        current = child
        uncertain = False

        while True:

            node_data = self.graph.nodes[current]

            if self._has_device(node_data):

                if not node_data.get("energized", True):

                    return {
                        "child": current,
                        "range_poles": range_poles,
                        "uncertain": uncertain
                    }

                # Confirmed live -- this branch is not dark.
                return None

            # No device on `current`. We can't trust its state.
            # Look at its children to see if any of them give us
            # real evidence.
            range_poles.append(current)
            uncertain = True

            successors = list(self.graph.successors(current))

            if not successors:
                # Dead end with no telemetry at all on this branch --
                # we genuinely cannot say whether it's faulted.
                return None

            # Radial network: a span has at most one meaningful path
            # forward per branch point, but there can be multiple
            # successors (spurs). Check each; if any resolves dark,
            # report it. If more than one resolves dark independently
            # that's a separate boundary the outer loop will still
            # find when it processes those nodes directly, so taking
            # the first is enough here.
            resolved_any = None

            for successor in successors:
                resolved = self._resolve_dark_child(successor)
                if resolved is not None:
                    resolved_any = resolved
                    break

            if resolved_any is None:
                return None

            return {
                "child": resolved_any["child"],
                "range_poles": range_poles + resolved_any["range_poles"],
                "uncertain": True
            }