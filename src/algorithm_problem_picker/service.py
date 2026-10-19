"""Complete collection and enrichment before presenting any result."""

from collections.abc import Callable

from .models import Order, Progress, Result, SearchCriteria, SortKey, Stage, now
from .ports import ProblemSource
from .selection import filter_listing, filter_solvers, recommend, sort_problems


class Picker:
    def __init__(self, source: ProblemSource, report: Callable[[Progress], None] = lambda _: None):
        self.source = source
        self.report = report

    def recommend(self, criteria: SearchCriteria, count: int = 1) -> Result:
        return self._run(criteria, count, random_selection=True)

    def list(self, criteria: SearchCriteria, limit: int = 20,
             sort: SortKey = SortKey.ID, order: Order = Order.ASC) -> Result:
        sort, order = SortKey(sort), Order(order)
        if sort == SortKey.RANDOM and order == Order.DESC:
            raise ValueError("random과 --order desc를 함께 지정할 수 없습니다.")
        return self._run(criteria, limit, random_selection=False, sort=sort, order=order)

    def _run(self, criteria: SearchCriteria, requested: int, random_selection: bool,
             sort: SortKey = SortKey.ID, order: Order = Order.ASC) -> Result:
        if type(requested) is not int or requested <= 0:
            raise ValueError("개수는 양의 정수여야 합니다.")
        started_at = now()
        progress = Progress()
        try:
            user = self.source.resolve_user(criteria.user_handle) if criteria.user_handle else None
            if user:
                progress.advance(Stage.USER_RESOLVED)
                self.report(progress)
            progress.advance(Stage.COLLECTING)
            self.report(progress)
            listing = self.source.collect(criteria, user)
            progress.collected = len(listing.candidates)
            progress.advance(Stage.ENRICHING)
            self.report(progress)
            candidates, omitted = filter_listing(listing.candidates, criteria)
            problems = []
            for candidate in candidates:
                problem = self.source.read_details(candidate)
                assert (problem.id, problem.title, problem.url, problem.tier, problem.pass_rate,
                        problem.listed_at) == (candidate.id, candidate.title, candidate.url,
                        candidate.tier, candidate.pass_rate, candidate.listed_at)
                problems.append(problem)
                progress.detailed += 1
                self.report(progress)
            eligible, solver_omitted = filter_solvers(problems, criteria)
            progress.advance(Stage.COMPLETE)
            self.report(progress)
            selected = recommend(eligible, requested) if random_selection else sort_problems(eligible, sort, order)[:requested]
            return Result(criteria=criteria, user=user, problems=tuple(selected),
                          fetched_count=progress.collected, eligible_count=len(eligible),
                          omitted_unknown_count=omitted + solver_omitted, started_at=started_at,
                          finished_at=now(), requested_count=requested,
                          shortage=max(0, requested - len(selected)) if random_selection else 0)
        except KeyboardInterrupt:
            progress.advance(Stage.CANCELLED)
            self.report(progress)
            raise
        except Exception:
            progress.advance(Stage.FAILED)
            self.report(progress)
            raise
