import time
from app import build_demo_ship
from genetic_optimizer import GeneticOptimizer
from rl_optimizer import RLOptimizer

ship = build_demo_ship()
print(f"{len(ship.containers_to_place)} containers, {len(ship.bays)} bays")

t = time.time()
best_ga = float("-inf")
ga_arr = None
for _ in range(5):
    arr, score = GeneticOptimizer(ship, population_size=100, generations=200).run()
    if score > best_ga:
        best_ga, ga_arr = score, arr
print(f"GA: score {best_ga:.2f}, {time.time() - t:.1f}s")

t = time.time()
rl_arr, rl_score = RLOptimizer(ship, episodes=20000).run()
print(f"RL: score {rl_score:.2f}, {time.time() - t:.1f}s")

scorer = GeneticOptimizer(ship)
print("GA violations:", scorer.find_violations(ga_arr) or "none")
print("RL violations:", scorer.find_violations(rl_arr) or "none")