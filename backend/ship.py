from dataclasses import dataclass, field
from typing import Optional
from container import Container


@dataclass
class Bay:
    """
    A Bay is one slot on the ship where a single container can sit.
    Think of it like a numbered parking space, but stacked in 3D:
    row (side to side), tier (up and down), and bay (front to back).
    """
    bay_id: str            # e.g. "B01-T02-R03"
    row: int                # left-right position
    tier: int               # up-down position (tier 1 = bottom)
    bay_number: int         # front-back position
    max_weight: float       # heaviest container this slot can safely hold (kg)
    is_reefer: bool = False # True if this slot has power for refrigerated containers
    occupied_by: Optional[str] = None  # container_id sitting here, or None if empty

    def is_empty(self) -> bool:
        return self.occupied_by is None


@dataclass
class Ship:
    """
    A Ship is just a name plus a list of Bays (empty parking spaces)
    and a list of Containers that need to be placed into those spaces.
    """
    name: str
    bays: list = field(default_factory=list)
    containers_to_place: list = field(default_factory=list)

    def add_bay(self, bay: Bay):
        self.bays.append(bay)

    def add_container(self, container: Container):
        self.containers_to_place.append(container)

    def empty_bays(self):
        """Returns only the bays that don't have a container in them yet."""
        return [bay for bay in self.bays if bay.is_empty()]

    def total_container_weight(self) -> float:
        """Adds up the weight of every container waiting to be placed."""
        return sum(c.weight for c in self.containers_to_place)


# Let's test it: build a tiny ship with 3 bays and 2 containers
if __name__ == "__main__":
    ship = Ship(name="MV Test Voyager")

    # Add 3 empty parking spaces
    ship.add_bay(Bay(bay_id="B01-T01-R01", row=1, tier=1, bay_number=1, max_weight=30000))
    ship.add_bay(Bay(bay_id="B01-T02-R01", row=1, tier=2, bay_number=1, max_weight=25000))
    ship.add_bay(Bay(bay_id="B02-T01-R01", row=2, tier=1, bay_number=1, max_weight=30000, is_reefer=True))

    # Add 2 containers that need homes
    ship.add_container(Container("CONT001", 6.06, 2.44, 2.59, 21600, destination_port="Chennai"))
    ship.add_container(Container("CONT002", 6.06, 2.44, 2.59, 18000, destination_port="Kochi"))

    print("Ship name:", ship.name)
    print("Number of bays:", len(ship.bays))
    print("Number of empty bays:", len(ship.empty_bays()))
    print("Containers waiting to be placed:", len(ship.containers_to_place))
    print("Total weight to place (kg):", ship.total_container_weight())