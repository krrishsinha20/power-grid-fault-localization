import math

from networkx import DiGraph, Graph
from networkx.algorithms.tree.mst import minimum_spanning_edges


class TopologyInference:
    """
    Infers missing pole-to-pole wiring order for the ~60% of
    transformers where `seq_on_line` / `parent_pole_id` was never
    digitized.

    Approach: geometric minimum-spanning-tree, rooted at the
    transformer's REAL surveyed location (from the transformer
    registry, always present per the data contract) -- not an
    approximation.

      1. For each transformer, take every pole under it that has no
         confirmed parent edge (i.e. it's still disconnected from the
         existing topology graph).
      2. Build a complete graph over {transformer_location} + those
         poles, weighted by real-world (haversine) distance.
      3. Compute a minimum spanning tree over that graph. On a radial
         LT network, the MST is a reasonable proxy for the actual
         wiring: adjacent poles on the same physical line are close
         together, and the true line order almost never crosses over
         itself geographically.
      4. Orient the MST edges away from the transformer root (BFS)
         so we get parent -> child edges consistent with the rest of
         the graph.

    This is a real inference, not a guess dressed up as one -- it can
    still be wrong (e.g. two adjacent spurs that happen to be
    geographically close but are actually on different branches), so
    every edge we add is tagged `inferred=True` plus the distance in
    metres, and the confidence engine downgrades any incident whose
    boundary touches an inferred edge. See ARCHITECTURE.md for the
    known failure modes of this approach.
    """

    # Anything wired by an inferred edge longer than this is flagged
    # as low-confidence -- a real LT span between adjacent poles is
    # rarely more than ~80m.
    LONG_EDGE_THRESHOLD_M = 150.0

    def __init__(self, graph: DiGraph):
        self.graph = graph

    def infer(self):
        """
        Mutates self.graph in place, adding inferred parent->child
        edges for every transformer with disconnected poles.

        Returns:
        {
            "added_edges": int,
            "edges": list[tuple],
            "long_edges": list[tuple]  # inferred edges over the
                                        # distance threshold -- these
                                        # are the ones most likely to
                                        # be wrong
        }
        """

        inferred_edges = []
        long_edges = []

        transformers = {}

        for node, data in self.graph.nodes(data=True):

            transformer = data["transformer_id"]

            transformers.setdefault(
                transformer,
                []
            ).append(node)

        existing_connected = set()

        for u, v in self.graph.edges():
            existing_connected.add(u)
            existing_connected.add(v)

        for transformer, poles in transformers.items():

            isolated = [
                pole
                for pole in poles
                if pole not in existing_connected
            ]

            if len(isolated) < 2:
                continue

            transformer_coord = self._transformer_coord(poles)

            if transformer_coord is None:
                # No way to anchor a root -- fall back to picking an
                # arbitrary anchor among the isolated poles
                # themselves, so we still connect them rather than
                # leaving a completely blind DT.
                anchor = isolated[0]
                root_key = ("__pole__", anchor)
            else:
                root_key = ("__root__", transformer)

            mst_edges = self._build_geometric_mst(
                root_key,
                transformer_coord,
                isolated
            )

            oriented_edges = self._orient_from_root(
                root_key,
                mst_edges
            )

            for parent, child, distance_m in oriented_edges:

                if parent == root_key or (
                    isinstance(parent, tuple) and parent[0] == "__root__"
                ):
                    # Root is virtual (the transformer itself, not a
                    # pole) -- the first real pole becomes a top-level
                    # node with no parent pole, same as a normally
                    # digitized line's first pole.
                    continue

                self.graph.add_edge(
                    parent,
                    child,
                    inferred=True,
                    inferred_distance_m=round(distance_m, 1)
                )

                inferred_edges.append((parent, child))

                if distance_m > self.LONG_EDGE_THRESHOLD_M:
                    long_edges.append((parent, child))

        return {

            "added_edges": len(inferred_edges),

            "edges": inferred_edges,

            "long_edges": long_edges

        }

    def _transformer_coord(self, poles):
        """
        Reads the transformer's real surveyed lat/lon straight off
        the graph nodes (GraphBuilder attaches transformer_lat /
        transformer_lon to every pole node). This replaced an earlier
        version that approximated the root as the centroid of the
        poles themselves -- on a spread-out, undigitized DT that
        centroid could land nowhere near the actual transformer,
        producing a wrong-shaped MST (poles splitting off a virtual
        midpoint instead of a single line radiating from the real
        DT). Falls back to a pole-centroid only if, for some reason,
        no pole in this group carries transformer coordinates (e.g.
        an orphaned pole with no transformer row).
        """

        for pole in poles:

            data = self.graph.nodes[pole]

            t_lat = data.get("transformer_lat")
            t_lon = data.get("transformer_lon")

            if t_lat is not None and t_lon is not None:
                return (t_lat, t_lon)

        # Fallback: no transformer coordinates available anywhere in
        # this group -- approximate with the pole centroid so we
        # still produce a connected (if less trustworthy) topology
        # rather than leaving the DT completely unwired.
        lats = []
        lons = []

        for pole in poles:
            data = self.graph.nodes[pole]
            lat = data.get("latitude")
            lon = data.get("longitude")
            if lat is not None and lon is not None:
                lats.append(lat)
                lons.append(lon)

        if not lats:
            return None

        return (sum(lats) / len(lats), sum(lons) / len(lons))

    def _build_geometric_mst(self, root_key, root_coord, isolated):

        helper = Graph()

        helper.add_node(root_key, coord=root_coord)

        for pole in isolated:
            data = self.graph.nodes[pole]
            coord = (data.get("latitude"), data.get("longitude"))
            helper.add_node(pole, coord=coord)

        nodes = list(helper.nodes())

        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):

                n1 = nodes[i]
                n2 = nodes[j]

                c1 = helper.nodes[n1]["coord"]
                c2 = helper.nodes[n2]["coord"]

                if None in c1 or None in c2:
                    weight = float("inf")
                else:
                    weight = self._haversine_m(c1, c2)

                helper.add_edge(n1, n2, weight=weight)

        mst = list(
            minimum_spanning_edges(
                helper,
                weight="weight",
                data=True
            )
        )

        return mst

    def _orient_from_root(self, root_key, mst_edges):
        """
        BFS out from the transformer root over the MST edges,
        producing (parent, child, distance_m) tuples oriented away
        from the root.
        """

        adjacency = {}

        for u, v, data in mst_edges:
            weight = data.get("weight", 0.0)
            adjacency.setdefault(u, []).append((v, weight))
            adjacency.setdefault(v, []).append((u, weight))

        visited = {root_key}
        queue = [root_key]
        oriented = []

        while queue:

            current = queue.pop(0)

            for neighbor, weight in adjacency.get(current, []):

                if neighbor in visited:
                    continue

                visited.add(neighbor)

                oriented.append((current, neighbor, weight))

                queue.append(neighbor)

        return oriented

    @staticmethod
    def _haversine_m(coord1, coord2):

        lat1, lon1 = coord1
        lat2, lon2 = coord2

        R = 6371000.0

        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        d_phi = math.radians(lat2 - lat1)
        d_lambda = math.radians(lon2 - lon1)

        a = (
            math.sin(d_phi / 2) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
        )

        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c