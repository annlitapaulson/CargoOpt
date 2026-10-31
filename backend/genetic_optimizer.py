import random
from container import Container
from ship import Ship, Bay

# Voyage order: first port = unloaded first. Use UPPERCASE names.
PORT_ORDER = ["COLOMBO", "SINGAPORE", "DUBAI"]


class GeneticOptimizer:
    """
    This class finds a good way to place containers into bays,
    by evolving random guesses into better ones over many generations.
    """

    def __init__(self, ship: Ship, population_size: int = 50, generations: int = 100):
        self.ship = ship
        self.population_size = population_size
        self.generations = generations
        self.containers = ship.containers_to_place
        self.bays = ship.bays

    # ---- STEP 1: make one random guess ----
    def create_random_arrangement(self):
        """
        An 'arrangement' here is just a list. Each position in the list
        corresponds to one container, and the value is which bay index
        that container is placed in. We shuffle bay positions randomly.
        """
        bay_indexes = list(range(len(self.bays)))
        random.shuffle(bay_indexes)
        # only take as many bay slots as we have containers
        return bay_indexes[:len(self.containers)]

    # ---- STEP 2: score how good an arrangement is ----
    def port_rank(self, port):
        name = (port or "").strip().upper()
        return PORT_ORDER.index(name) if name in PORT_ORDER else None



    def hazard_gap_broken(self, arrangement, i, j):
        """True if hazardous container i and fragile container j are too close:
        same or adjacent section, or any container sits in a section between them."""
        si = self.bays[arrangement[i]].bay_number
        sj = self.bays[arrangement[j]].bay_number
        if abs(si - sj) < 2:
            return True
        low, high = min(si, sj), max(si, sj)
        for k in arrangement:
            if low < self.bays[k].bay_number < high:
                return True
        return False

    def buried_under(self, placed, container, bay):
        """Containers lower in the same stack that unload earlier than this one."""
        found = []
        ra = self.port_rank(container.destination_port)
        if ra is None:
            return found
        for t in range(1, bay.tier):
            lower = placed.get((bay.bay_number, bay.row, t))
            if lower is None:
                continue
            rb = self.port_rank(lower.destination_port)
            if rb is not None and rb < ra:
                found.append(lower)
        return found
    def fitness(self, arrangement):
        """Higher score = better arrangement."""
        score = 0

        placed = {}
        for container_index, bay_index in enumerate(arrangement):
            bay = self.bays[bay_index]
            placed[(bay.bay_number, bay.row, bay.tier)] = self.containers[container_index]

        for container_index, bay_index in enumerate(arrangement):
            container = self.containers[container_index]
            bay = self.bays[bay_index]

            if container.weight > bay.max_weight:
                score -= 1000

            score += (10 - bay.tier) * (container.weight / 1000)

            if bay.tier > 1:
                below = placed.get((bay.bay_number, bay.row, bay.tier - 1))

                if below is None:
                    score -= 500
                else:
                    if container.weight > below.weight:
                        score -= 300
                    if container.length > below.length or container.width > below.width:
                        score -= 300
                    if below.is_fragile:
                        score -= 300

                # Port rule (extended): every container below that unloads earlier
                score -= 200 * len(self.buried_under(placed, container, bay))

        for i in range(len(arrangement)):
            for j in range(len(arrangement)):
                if i != j and self.containers[i].is_hazardous and self.containers[j].is_fragile:
                    if self.hazard_gap_broken(arrangement, i, j):
                        score -= 400

        left_weight = 0
        right_weight = 0
        for container_index, bay_index in enumerate(arrangement):
            bay = self.bays[bay_index]
            weight = self.containers[container_index].weight
            if bay.row % 2 == 1:
                left_weight += weight
            else:
                right_weight += weight

        total_weight = left_weight + right_weight
        if total_weight > 0:
            imbalance = abs(left_weight - right_weight) / total_weight * 100
            score -= imbalance * 10
            if imbalance > 10:
                score -= (imbalance - 10) * 20
        return score

    # ---- STEP 3: pick two decent parents to "breed" ----
    def find_violations(self, arrangement):
        """Return a list of plain-English messages for every rule the arrangement breaks."""
        violations = []

        placed = {}
        for container_index, bay_index in enumerate(arrangement):
            bay = self.bays[bay_index]
            placed[(bay.bay_number, bay.row, bay.tier)] = self.containers[container_index]

        for container_index, bay_index in enumerate(arrangement):
            container = self.containers[container_index]
            bay = self.bays[bay_index]
            cid = container.container_id

            if container.weight > bay.max_weight:
                violations.append(f"{cid} is heavier than the limit of bay {bay.bay_id} ({bay.max_weight:.0f} kg)")

            if bay.tier > 1:
                below = placed.get((bay.bay_number, bay.row, bay.tier - 1))
                if below is None:
                    violations.append(f"{cid} is floating in {bay.bay_id} with nothing below it")
                else:
                    if container.weight > below.weight:
                        violations.append(f"{cid} is heavier than {below.container_id} below it")
                    if container.length > below.length or container.width > below.width:
                        violations.append(f"{cid} overhangs {below.container_id} below it")
                    if below.is_fragile:
                        violations.append(f"{cid} sits on fragile {below.container_id}")

                for lower in self.buried_under(placed, container, bay):
                    violations.append(
                        f"{lower.container_id} (for {lower.destination_port}) is buried under "
                        f"{cid} (for {container.destination_port}), which unloads later"
                    )

        left_weight = 0
        right_weight = 0
        for container_index, bay_index in enumerate(arrangement):
            bay = self.bays[bay_index]
            weight = self.containers[container_index].weight
            if bay.row % 2 == 1:
                left_weight += weight
            else:
                right_weight += weight

        total_weight = left_weight + right_weight
        if total_weight > 0:
            imbalance = abs(left_weight - right_weight) / total_weight * 100
            if imbalance >= 10:
                violations.append(f"Port/starboard imbalance is {imbalance:.2f}% (limit 10%)")

        for i in range(len(arrangement)):
            for j in range(len(arrangement)):
                if i != j and self.containers[i].is_hazardous and self.containers[j].is_fragile:
                    if self.hazard_gap_broken(arrangement, i, j):
                        violations.append(
                            f"Hazardous {self.containers[i].container_id} is too close to fragile "
                            f"{self.containers[j].container_id} (needs an empty section between them)"
                        )

        return violations
    def select_parent(self, population_with_scores):
        """
        Tournament selection: grab 3 random arrangements, return the best of the 3.
        This gives good arrangements a better chance of being chosen,
        without ALWAYS picking only the single best (which would stop exploring).
        """
        competitors = random.sample(population_with_scores, 3)
        competitors.sort(key=lambda pair: pair[1], reverse=True)
        return competitors[0][0]  # the arrangement (not the score) of the winner

    # ---- STEP 4: combine two parents into a child ----
    def crossover(self, parent1, parent2):
        """
        Takes the first half of parent1 and the second half of parent2,
        then fixes any bay that got used twice (a container can't share a bay!).
        """
        if len(parent1) < 2:
            return parent1[:]

        cut = len(parent1) // 2
        child = parent1[:cut] + parent2[cut:]

        used = set()
        available_bays = [b for b in range(len(self.bays)) if b not in child]
        for i in range(len(child)):
            if child[i] in used:
                child[i] = available_bays.pop()
            used.add(child[i])
        return child

    # ---- STEP 5: randomly tweak a child sometimes ----
    def mutate(self, arrangement, mutation_rate=0.3):
        """
        Two kinds of tweaks:
        1. swap two containers' bays
        2. move one container into a bay nobody is using
        """
        arrangement = arrangement[:]
        if random.random() < mutation_rate and len(arrangement) >= 2:
            i, j = random.sample(range(len(arrangement)), 2)
            arrangement[i], arrangement[j] = arrangement[j], arrangement[i]
        if random.random() < mutation_rate:
            unused = [b for b in range(len(self.bays)) if b not in arrangement]
            if unused:
                k = random.randrange(len(arrangement))
                arrangement[k] = random.choice(unused)
        return arrangement

    # ---- PUTTING IT ALL TOGETHER ----
    def run(self):
        # Generation 0: start with random guesses
        population = [self.create_random_arrangement() for _ in range(self.population_size)]

        best_arrangement = None
        best_score = float("-inf")

        for generation in range(self.generations):
            scored_population = [(arr, self.fitness(arr)) for arr in population]

            # Track the best one we've ever seen
            for arrangement, score in scored_population:
                if score > best_score:
                    best_score = score
                    best_arrangement = arrangement

            # Build the next generation
            next_population = [best_arrangement[:]]
            while len(next_population) < self.population_size:
                parent1 = self.select_parent(scored_population)
                parent2 = self.select_parent(scored_population)
                child = self.crossover(parent1, parent2)
                child = self.mutate(child)
                next_population.append(child)

            population = next_population

        return best_arrangement, best_score


# Let's test it on our tiny ship
if __name__ == "__main__":
    ship = Ship(name="MV Test Voyager")
    ship.add_bay(Bay(bay_id="B01-T01-R01", row=1, tier=1, bay_number=1, max_weight=30000))
    ship.add_bay(Bay(bay_id="B01-T02-R01", row=1, tier=2, bay_number=1, max_weight=25000))
    ship.add_bay(Bay(bay_id="B02-T01-R01", row=2, tier=1, bay_number=1, max_weight=30000))

    ship.add_container(Container("CONT001", 6.06, 2.44, 2.59, 21600, destination_port="Chennai"))
    ship.add_container(Container("CONT002", 6.06, 2.44, 2.59, 18000, destination_port="Kochi"))

    optimizer = GeneticOptimizer(ship, population_size=50, generations=100)
    best_arrangement, best_score = optimizer.run()

    print("Best score found:", best_score)
    for container_index, bay_index in enumerate(best_arrangement):
        container = ship.containers_to_place[container_index]
        bay = ship.bays[bay_index]
        print(f"{container.container_id} (weight {container.weight}kg) -> {bay.bay_id} (tier {bay.tier})")