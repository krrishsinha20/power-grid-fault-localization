import networkx as nx

from sqlalchemy.orm import Session

from app.models.pole import Pole
from app.models.transformer import Transformer


class GraphBuilder:
    """
    Builds the in-memory topology graph used by localization. Each
    node carries `has_device` (derived from `last_device_id` being
    set) so BoundaryDetector and the confidence engine can tell a
    pole with a real telemetry reading apart from one whose
    `energized` value is just a default/last-known-nothing, per the
    ~9% no-device coverage gap in the data contract.

    Also carries `pole_active` (the Pole.active flag -- distinct from
    whether it *reports*; a pole can be active but simply have no
    device) and `db_id`, useful for callers that need to go back to
    the ORM row without a second query.

    Each node also carries `transformer_lat` / `transformer_lon` --
    the REAL surveyed location of the transformer this pole belongs
    to (from the transformer registry, always present per the data
    contract), not a computed approximation. TopologyInference uses
    this as the true root anchor for its geometric inference instead
    of guessing at a centroid of the poles themselves.
    """

    def __init__(self, db: Session):

        self.db = db
        self.graph = nx.DiGraph()

    def build(self):

        poles = self.db.query(Pole).all()

        transformers = self.db.query(Transformer).all()

        pole_map = {
            pole.id: pole
            for pole in poles
        }

        transformer_map = {
            transformer.id: transformer
            for transformer in transformers
        }

        for pole in poles:

            transformer = transformer_map.get(
                pole.transformer_id
            )

            feeder_id = None
            transformer_business_id = None
            transformer_lat = None
            transformer_lon = None

            if transformer:

                feeder_id = transformer.feeder_id

                transformer_business_id = (
                    transformer.transformer_id
                )

                transformer_lat = transformer.latitude
                transformer_lon = transformer.longitude

            has_device = pole.last_device_id is not None

            self.graph.add_node(

                pole.pole_id,

                db_id=pole.id,

                energized=pole.energized,

                active=pole.active,

                has_device=has_device,

                latitude=pole.latitude,

                longitude=pole.longitude,

                transformer_id=transformer_business_id,

                transformer_lat=transformer_lat,

                transformer_lon=transformer_lon,

                feeder_id=feeder_id,

                pincode=pole.pincode,

                last_seen_at=pole.last_seen_at

            )

        for pole in poles:

            if pole.parent_pole_id is None:
                continue

            parent = pole_map.get(
                pole.parent_pole_id
            )

            if parent is None:
                continue

            self.graph.add_edge(

                parent.pole_id,

                pole.pole_id,

                inferred=False

            )

        return self.graph

    def get_graph(self):

        return self.graph

    def node_count(self):

        return self.graph.number_of_nodes()

    def edge_count(self):

        return self.graph.number_of_edges()

    def successors(
        self,
        pole_id: str
    ):

        return list(
            self.graph.successors(pole_id)
        )

    def predecessors(
        self,
        pole_id: str
    ):

        return list(
            self.graph.predecessors(pole_id)
        )