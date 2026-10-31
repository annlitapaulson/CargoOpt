import random
import numpy as np
from genetic_optimizer import GeneticOptimizer


class RLOptimizer:
    """Tabular Q-learning. The agent places containers one at a time.
    State = the bays chosen so far (in order). Action = the bay for the next container.
    Reward = 0 until the last container is placed, then the GeneticOptimizer fitness() score."""

    def __init__(self, ship, episodes=20000, alpha=0.1, epsilon_start=1.0, epsilon_end=0.05):
        self.scorer = GeneticOptimizer(ship)   # reused only for its fitness() and find_violations()
        self.n_bays = len(ship.bays)
        self.n_containers = len(ship.containers_to_place)
        self.episodes = episodes
        self.alpha = alpha
        self.epsilon_start = epsilon_start
        self.epsilon_end = epsilon_end
        self.q = {}

    def q_row(self, state):
        if state not in self.q:
            self.q[state] = np.zeros(self.n_bays)
        return self.q[state]

    def choose(self, state, epsilon):
        free = np.array([b for b in range(self.n_bays) if b not in state])
        if random.random() < epsilon:
            return int(random.choice(free))
        row = self.q_row(state)
        return int(free[np.argmax(row[free])])

    def run(self):
        best_arrangement = None
        best_score = float("-inf")
        decay_episodes = self.episodes * 0.8

        for ep in range(self.episodes):
            epsilon = max(
                self.epsilon_end,
                self.epsilon_start - (self.epsilon_start - self.epsilon_end) * ep / decay_episodes,
            )
            arrangement = []
            for k in range(self.n_containers):
                state = tuple(arrangement)
                action = self.choose(state, epsilon)
                arrangement.append(action)
                row = self.q_row(state)

                if k == self.n_containers - 1:
                    score = self.scorer.fitness(arrangement)
                    target = score
                    if score > best_score:
                        best_score = score
                        best_arrangement = arrangement[:]
                else:
                    next_state = tuple(arrangement)
                    free_next = np.array([b for b in range(self.n_bays) if b not in next_state])
                    target = self.q_row(next_state)[free_next].max()

                row[action] += self.alpha * (target - row[action])

        return self.polish(best_arrangement)

    def polish(self, arrangement):
        """Hill climbing: move one container to a free bay, or swap two, until nothing improves."""
        best = arrangement[:]
        best_score = self.scorer.fitness(best)
        improved = True
        while improved:
            improved = False
            for i in range(self.n_containers):
                for b in range(self.n_bays):
                    if b in best:
                        continue
                    trial = best[:]
                    trial[i] = b
                    s = self.scorer.fitness(trial)
                    if s > best_score:
                        best, best_score, improved = trial, s, True
            for i in range(self.n_containers):
                for j in range(i + 1, self.n_containers):
                    trial = best[:]
                    trial[i], trial[j] = trial[j], trial[i]
                    s = self.scorer.fitness(trial)
                    if s > best_score:
                        best, best_score, improved = trial, s, True
        return best, best_score