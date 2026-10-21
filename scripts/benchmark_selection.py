"""Measure local work only; candidate construction and browsing are excluded."""

from decimal import Decimal
import platform
from time import perf_counter

from algorithm_problem_picker.models import Known, Problem, Rated, SearchCriteria, now
from algorithm_problem_picker.selection import filter_listing, recommend, sort_problems


def main() -> None:
    items = [Problem(id=i+1, title=f"problem {i+1}", url=f"https://jungol.co.kr/problem/{i+1}",
                     tier=Rated(i % 30 + 1), pass_rate=Known(Decimal(i % 101)), accepted_count=Known(i),
                     listed_at=now()) for i in range(10_000)]
    criteria = SearchCriteria(min_tier=5, max_tier=25, min_rate=Decimal("30"),
                              max_rate=Decimal("90"), min_accepted=10)
    start = perf_counter()
    eligible, _ = filter_listing(items, criteria)
    ordered = sort_problems(eligible, "rate", "desc")
    selected = recommend(eligible, 5)
    elapsed = perf_counter() - start
    assert len(ordered) == len(eligible) and len(selected) == 5
    print(platform.platform(), platform.python_version())
    print(f"prepared=10000 eligible={len(eligible)} selected=5 seconds={elapsed:.6f}")


if __name__ == "__main__":
    main()
