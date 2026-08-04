import random
import math

from sqlalchemy.orm import Session

from app.models.transformer import Transformer
from app.models.pole import Pole


class NetworkGenerator:
    """
    Builds a synthetic network shaped like the real thing described in
    01-problem-context.md / 02-data-and-systems.md:

      - Each transformer feeds a radial LT line: a main trunk of poles
        walking outward from the DT, plus 1-5 branch spurs peeling off
        the trunk at random points (never rejoining -- radial, no
        loops).
      - Poles are placed along that line geometrically (small lat/lon
        steps in a consistent walking direction per branch), not at
        random coordinates, so `TopologyInference`'s geometric MST has
        something realistic to work with and so faults look like a
        real geographic cluster on a map.
      - ~91% of poles get a device (device_id set); ~9% have none
        (device_id NULL), per the coverage gap in the data contract.
      - For ~60% of transformers, we deliberately do NOT persist
        `parent_pole_id` / `seq_on_line` -- this is the undigitized
        majority the assignment centers on. The other ~40% keep their
        real generated order, standing in for transformers that were
        digitized.
    """

    UNDIGITIZED_TRANSFORMER_RATIO = 0.60
    DEVICE_COVERAGE_RATIO = 0.91

    # Roughly metres-to-degrees at these latitudes, used to keep pole
    # spacing along a line realistic (LT spans are usually 30-80m).
    METRES_PER_DEGREE_LAT = 111_320.0

    def __init__(
        self,
        db: Session,
        feeders: int = 3,
        transformers_per_feeder: int = 5,
        min_poles: int = 20,
        max_poles: int = 40,
        base_lat: float = 12.9716,
        base_lon: float = 77.5946,
    ):

        self.db = db

        self.feeders = feeders
        self.transformers_per_feeder = transformers_per_feeder

        self.min_poles = min_poles
        self.max_poles = max_poles

        self.base_lat = base_lat
        self.base_lon = base_lon

        self.graph = {}

    def generate(self):

        pole_number = 1
        transformer_number = 1

        for feeder in range(1, self.feeders + 1):

            feeder_id = f"F{feeder:03}"

            for _ in range(self.transformers_per_feeder):

                dt_lat = self.base_lat + random.uniform(-0.02, 0.02)
                dt_lon = self.base_lon + random.uniform(-0.02, 0.02)

                transformer = Transformer(

                    transformer_id=f"DT{transformer_number:04}",

                    feeder_id=feeder_id,

                    name=f"Transformer {transformer_number}",

                    latitude=dt_lat,

                    longitude=dt_lon,

                    pincode="411001",

                )

                self.db.add(transformer)
                self.db.flush()

                total_poles = random.randint(
                    self.min_poles,
                    self.max_poles
                )

                is_digitized = (
                    random.random() > self.UNDIGITIZED_TRANSFORMER_RATIO
                )

                pole_number = self._generate_line(
                    transformer=transformer,
                    dt_lat=dt_lat,
                    dt_lon=dt_lon,
                    total_poles=total_poles,
                    pole_number=pole_number,
                    persist_topology=is_digitized
                )

                transformer_number += 1

        self.db.commit()

        return self.graph

    def _generate_line(
        self,
        transformer: Transformer,
        dt_lat: float,
        dt_lon: float,
        total_poles: int,
        pole_number: int,
        persist_topology: bool
    ):
        """
        Walks a main trunk outward from the transformer, peeling off
        1-5 branch spurs at random trunk poles. Returns the next free
        pole_number for the caller.
        """

        num_branches = random.randint(1, min(5, max(1, total_poles // 8)))

        # Reserve poles for the trunk vs branches roughly 60/40.
        trunk_count = max(3, int(total_poles * 0.6))
        remaining = total_poles - trunk_count

        heading = random.uniform(0, 2 * math.pi)

        trunk_poles = self._walk_line(
            transformer=transformer,
            start_lat=dt_lat,
            start_lon=dt_lon,
            heading=heading,
            count=trunk_count,
            pole_number=pole_number,
            parent_id=None,
            persist_topology=persist_topology
        )

        pole_number += trunk_count

        # Distribute remaining poles across branches, spurring off
        # random points on the trunk (never the DT itself, never the
        # very last trunk pole so there's somewhere for the branch to
        # visually diverge from).
        if remaining > 0 and len(trunk_poles) > 1:

            per_branch = max(1, remaining // num_branches)

            for _ in range(num_branches):

                if remaining <= 0:
                    break

                branch_len = min(remaining, per_branch)

                spur_point = random.choice(trunk_poles[:-1])

                branch_heading = heading + random.uniform(
                    -math.pi / 2, math.pi / 2
                )

                self._walk_line(
                    transformer=transformer,
                    start_lat=spur_point["lat"],
                    start_lon=spur_point["lon"],
                    heading=branch_heading,
                    count=branch_len,
                    pole_number=pole_number,
                    parent_id=spur_point["db_id"],
                    persist_topology=persist_topology
                )

                pole_number += branch_len
                remaining -= branch_len

        return pole_number

    def _walk_line(
        self,
        transformer: Transformer,
        start_lat: float,
        start_lon: float,
        heading: float,
        count: int,
        pole_number: int,
        parent_id: int | None,
        persist_topology: bool
    ):
        """
        Places `count` poles in a line starting near (start_lat,
        start_lon), each ~40-70m from the previous one in a consistent
        direction, chaining parent -> child. Returns a list of dicts
        describing each pole placed (used so branches can spur off an
        arbitrary point on this line).
        """

        placed = []

        lat = start_lat
        lon = start_lon

        current_parent_id = parent_id

        for i in range(count):

            step_m = random.uniform(35, 70)

            d_lat = (
                step_m * math.cos(heading)
                / self.METRES_PER_DEGREE_LAT
            )

            metres_per_degree_lon = (
                self.METRES_PER_DEGREE_LAT
                * math.cos(math.radians(lat))
            )

            d_lon = (
                step_m * math.sin(heading)
                / max(metres_per_degree_lon, 1.0)
            )

            lat += d_lat
            lon += d_lon

            has_device = (
                random.random() < self.DEVICE_COVERAGE_RATIO
            )

            pole_id_str = f"P{pole_number + i:05}"

            pole = Pole(

                pole_id=pole_id_str,

                transformer_id=transformer.id,

                parent_pole_id=(
                    current_parent_id if persist_topology else None
                ),

                latitude=lat,

                longitude=lon,

                pincode="411001",

                energized=True,

                active=True,

                last_device_id=(
                    f"DEV-{pole_id_str}" if has_device else None
                ),

            )

            self.db.add(pole)
            self.db.flush()

            self.graph[pole.pole_id] = []

            if current_parent_id is not None:

                parent_pole = self.db.get(Pole, current_parent_id)

                if parent_pole is not None:
                    self.graph.setdefault(
                        parent_pole.pole_id, []
                    ).append(pole.pole_id)

            placed.append({
                "db_id": pole.id,
                "pole_id": pole.pole_id,
                "lat": lat,
                "lon": lon,
            })

            current_parent_id = pole.id

        return placed