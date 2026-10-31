from ship import Ship


class EmissionsCalculator:
    """
    Estimates fuel burned and CO2 emitted for a voyage, based on how
    much weight the ship is carrying. This is a simplified version of
    the real IMO CII (Carbon Intensity Indicator) formula.
    """

    # Real ships burn roughly this much fuel (kg) per nautical mile,
    # per 1000 kg of cargo carried. This is a simplified estimate,
    # not the exact IMO formula, but the same idea.
    FUEL_PER_TON_PER_MILE = 0.0025   # kg of fuel, per ton of cargo, per nautical mile
    CO2_PER_KG_FUEL = 3.114          # burning 1kg of standard marine fuel produces this much CO2 (kg)

    def __init__(self, ship: Ship, voyage_distance_nm: float):
        self.ship = ship
        self.voyage_distance_nm = voyage_distance_nm  # nautical miles for this trip

    def total_cargo_tons(self) -> float:
        total_kg = sum(c.weight for c in self.ship.containers_to_place)
        return total_kg / 1000  # convert kg to metric tons

    def estimate_fuel_kg(self) -> float:
        cargo_tons = self.total_cargo_tons()
        fuel = cargo_tons * self.voyage_distance_nm * self.FUEL_PER_TON_PER_MILE
        return round(fuel, 2)

    def estimate_co2_kg(self) -> float:
        fuel = self.estimate_fuel_kg()
        return round(fuel * self.CO2_PER_KG_FUEL, 2)

    def cii_grade(self) -> str:
        """
        Simplified CII-style grade: CO2 emitted per ton of cargo, per mile.
        Real IMO grading is more complex, but the concept is the same -
        the more efficiently you use the ship's capacity, the better the grade.
        """
        cargo_tons = self.total_cargo_tons()
        if cargo_tons == 0 or self.voyage_distance_nm == 0:
            return "N/A"

        co2 = self.estimate_co2_kg()
        intensity = co2 / (cargo_tons * self.voyage_distance_nm)

        # These thresholds are simplified for teaching purposes
        if intensity < 0.006:
            return "A (Excellent)"
        elif intensity < 0.008:
            return "B (Good)"
        elif intensity < 0.010:
            return "C (Moderate)"
        elif intensity < 0.012:
            return "D (Poor)"
        else:
            return "E (Very Poor - needs improvement)"

    def full_report(self):
        print("--- Emissions Report ---")
        print(f"Voyage distance: {self.voyage_distance_nm} nautical miles")
        print(f"Total cargo: {self.total_cargo_tons()} tons")
        print(f"Estimated fuel burned: {self.estimate_fuel_kg()} kg")
        print(f"Estimated CO2 emitted: {self.estimate_co2_kg()} kg")
        print(f"CII Grade: {self.cii_grade()}")


# Test it on our familiar tiny ship, sailing Chennai to Kochi (~330 nautical miles)
if __name__ == "__main__":
    from container import Container

    ship = Ship(name="MV Test Voyager")
    ship.add_container(Container("CONT001", 6.06, 2.44, 2.59, 21600, destination_port="Chennai"))
    ship.add_container(Container("CONT002", 6.06, 2.44, 2.59, 18000, destination_port="Kochi"))

    calculator = EmissionsCalculator(ship, voyage_distance_nm=330)
    calculator.full_report()