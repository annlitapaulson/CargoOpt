from ship import Ship


class StabilityChecker:
    """
    Looks at a finished container arrangement and reports whether
    the ship is balanced side-to-side, and how high its center of
    gravity sits (lower is safer).
    """

    def __init__(self, ship: Ship, arrangement):
        self.ship = ship
        self.arrangement = arrangement  # same format as the GA: list of bay indexes, one per container

    def check_port_starboard_balance(self):
        """
        'Port' = left side of the ship, 'Starboard' = right side.
        We treat row numbers as a stand-in for left/right position.
        We add up weight on each side and compare them.
        A big difference means the ship could list (lean) to one side.
        """
        left_weight = 0.0   # rows 1 and 2 = left side, in our simple test ship
        right_weight = 0.0  # rows 3 and 4 = right side

        for container_index, bay_index in enumerate(self.arrangement):
            container = self.ship.containers_to_place[container_index]
            bay = self.ship.bays[bay_index]

            if bay.row % 2 == 1:      # odd row number = left side
                left_weight += container.weight
            else:                      # even row number = right side
                right_weight += container.weight

        total = left_weight + right_weight
        if total == 0:
            imbalance_percent = 0
        else:
            imbalance_percent = abs(left_weight - right_weight) / total * 100

        return {
            "left_weight_kg": left_weight,
            "right_weight_kg": right_weight,
            "imbalance_percent": round(imbalance_percent, 2),
            "is_balanced": imbalance_percent < 10  # under 10% difference = acceptable
        }

    def calculate_center_of_gravity_height(self):
        """
        A weighted average of tier heights, using each container's weight
        as the 'weight' in the average. Higher result = more top-heavy = less safe.
        We assume each tier is roughly 2.6 meters tall (a standard container height).
        """
        tier_height_m = 2.6
        total_weight = 0.0
        weighted_height_sum = 0.0

        for container_index, bay_index in enumerate(self.arrangement):
            container = self.ship.containers_to_place[container_index]
            bay = self.ship.bays[bay_index]

            height_of_this_bay = bay.tier * tier_height_m
            weighted_height_sum += container.weight * height_of_this_bay
            total_weight += container.weight

        if total_weight == 0:
            return 0.0

        return round(weighted_height_sum / total_weight, 2)

    def full_report(self):
        balance = self.check_port_starboard_balance()
        cog_height = self.calculate_center_of_gravity_height()

        print("--- Stability Report ---")
        print(f"Left side weight:  {balance['left_weight_kg']} kg")
        print(f"Right side weight: {balance['right_weight_kg']} kg")
        print(f"Imbalance: {balance['imbalance_percent']}%  ", end="")
        print("(OK)" if balance["is_balanced"] else "(WARNING: too lopsided)")
        print(f"Center of gravity height: {cog_height} meters ", end="")
        print("(lower is safer)")


# Test it using the same tiny ship and the best arrangement idea from Stage 2
if __name__ == "__main__":
    from container import Container
    from ship import Bay

    ship = Ship(name="MV Test Voyager")
    ship.add_bay(Bay(bay_id="B01-T01-R01", row=1, tier=1, bay_number=1, max_weight=30000))
    ship.add_bay(Bay(bay_id="B01-T02-R01", row=1, tier=2, bay_number=1, max_weight=25000))
    ship.add_bay(Bay(bay_id="B02-T01-R01", row=2, tier=1, bay_number=1, max_weight=30000))

    ship.add_container(Container("CONT001", 6.06, 2.44, 2.59, 21600, destination_port="Chennai"))
    ship.add_container(Container("CONT002", 6.06, 2.44, 2.59, 18000, destination_port="Kochi"))

    # Manually use the arrangement your run found: CONT001 -> bay 0, CONT002 -> bay 2
    example_arrangement = [0, 2]

    checker = StabilityChecker(ship, example_arrangement)
    checker.full_report()