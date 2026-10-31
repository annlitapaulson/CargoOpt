from dataclasses import dataclass

@dataclass
class Container:
    """
    This is like an index card for one shipping container.
    Every container in our system will be described using these facts.
    """
    container_id: str      # e.g. "MSCU1234567" - its unique name tag
    length: float           # in meters
    width: float            # in meters
    height: float           # in meters
    weight: float           # in kilograms (how heavy it is)
    is_fragile: bool = False        # True if it needs gentle handling
    is_hazardous: bool = False      # True if it holds dangerous goods
    destination_port: str = ""      # where this container needs to go

    def volume(self) -> float:
        """How much space this container takes up, in cubic meters."""
        return self.length * self.width * self.height


# Let's test it: create one container and print its facts
if __name__ == "__main__":
    test_container = Container(
        container_id="TEST0000001",
        length=6.06,
        width=2.44,
        height=2.59,
        weight=21600,
        is_fragile=False,
        is_hazardous=False,
        destination_port="Chennai"
    )
    print("Container ID:", test_container.container_id)
    print("Volume (cubic meters):", test_container.volume())
    print("Weight (kg):", test_container.weight)