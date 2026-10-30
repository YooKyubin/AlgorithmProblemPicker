"""Platform-neutral unique sampling after complete collection and filtering."""

from collections.abc import Hashable, Sequence
import random

from .models import ProblemRecord


def recommend[P: ProblemRecord](problems: Sequence[P], count: int) -> list[P]:
    unique: dict[Hashable, P] = {}
    for problem in problems:
        unique.setdefault(problem.id, problem)
    population = list(unique.values())
    return random.sample(population, k=min(count, len(population)))
