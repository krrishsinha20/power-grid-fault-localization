from networkx import DiGraph


class DownstreamCounter:
    """
    Walks the topology downstream from a fault boundary and counts the
    poles that are *actually* dark.

    Important: this does NOT just walk the tree structure. A real line
    fault de-energizes everything below it, so as long as we are inside
    a genuine outage every descendant we visit should also report
    energized=False. The moment we hit a descendant that is still LIVE,
    that branch cannot be part of this outage — either:

      - the node above it is a lone dead/misreporting sensor whose
        actual children are fine (the "single pole's own lamp circuit"
        case from the brief), or
      - there is a second, independent fault further down that will be
        detected as its own boundary separately.

    So a live node stops the walk on that branch instead of being
    blindly counted as affected.
    """

    def __init__(self, graph: DiGraph):
        self.graph = graph

    def count(self, start_pole: str):
        """
        Returns:
        {
            "count": int,               # confirmed-dark poles downstream
            "poles": list[str],         # confirmed-dark pole ids
            "reconnect_poles": list[str]  # live poles hit while walking
                                           # down (signals a sensor
                                           # anomaly / a separate fault
                                           # below this boundary)
        }
        """

        visited = set()
        affected = []
        reconnects = []

        self._dfs(start_pole, visited, affected, reconnects)

        return {
            "count": len(affected),
            "poles": affected,
            "reconnect_poles": reconnects
        }

    def _dfs(
        self,
        current: str,
        visited: set,
        affected: list,
        reconnects: list
    ):

        if current in visited:
            return

        visited.add(current)

        node_data = self.graph.nodes[current]

        is_energized = node_data.get("energized", True)

        if is_energized:
            # This node is live. It cannot be part of the dark
            # downstream region — record it and do not descend
            # further on this branch, since everything below a live
            # pole is, by the radial-network rule, also live (or is
            # a separate fault we'll catch as its own boundary).
            if current != affected[0] if affected else True:
                reconnects.append(current)
            return

        affected.append(current)

        for child in self.graph.successors(current):

            self._dfs(
                child,
                visited,
                affected,
                reconnects
            )