"""Pure filtering; external state never participates in selection."""

from collections.abc import Sequence
import random

from .models import Known, Order, Problem, Rated, SearchCriteria, SortKey, Unavailable


def _within(value, lower, upper) -> bool:
    return (lower is None or value >= lower) and (upper is None or value <= upper)


def filter_listing(problems: Sequence[Problem], criteria: SearchCriteria) -> tuple[list[Problem], int]:
    selected: list[Problem] = []
    omitted = 0
    seen: set[int] = set()
    tier_filter = criteria.min_tier is not None or criteria.max_tier is not None
    rate_filter = criteria.min_rate is not None or criteria.max_rate is not None
    accepted_filter = criteria.min_accepted is not None or criteria.max_accepted is not None
    for problem in problems:
        if problem.id in seen:
            continue
        seen.add(problem.id)
        if tier_filter:
            if isinstance(problem.tier, Unavailable):
                omitted += 1
                continue
            if not isinstance(problem.tier, Rated) or not _within(
                problem.tier.value, criteria.min_tier, criteria.max_tier
            ):
                continue
        if rate_filter:
            if isinstance(problem.pass_rate, Unavailable):
                omitted += 1
                continue
            if not _within(problem.pass_rate.value, criteria.min_rate, criteria.max_rate):
                continue
        if accepted_filter:
            if isinstance(problem.accepted_count, Unavailable):
                omitted += 1
                continue
            if not _within(problem.accepted_count.value, criteria.min_accepted, criteria.max_accepted):
                continue
        selected.append(problem)
    return selected, omitted


def sort_problems(problems: Sequence[Problem], sort: SortKey = SortKey.ID,
                  order: Order = Order.ASC) -> list[Problem]:
    if sort == SortKey.RANDOM:
        shuffled = list(problems)
        random.shuffle(shuffled)
        return shuffled
    if sort == SortKey.ID:
        return sorted(problems, key=lambda problem: problem.id, reverse=order == Order.DESC)
    attribute = {SortKey.DIFFICULTY: 'tier', SortKey.RATE: 'pass_rate', SortKey.ACCEPTED: 'accepted_count'}[sort]
    direction = -1 if order == Order.DESC else 1

    def key(problem: Problem):
        metric = getattr(problem, attribute)
        known = isinstance(metric, (Known, Rated))
        return (not known, direction * metric.value if known else 0, problem.id)

    return sorted(problems, key=key)


def recommend(problems: Sequence[Problem], count: int) -> list[Problem]:
    unique: dict[int, Problem] = {}
    for problem in problems:
        unique.setdefault(problem.id, problem)
    population = list(unique.values())
    return random.sample(population, k=min(count, len(population)))
