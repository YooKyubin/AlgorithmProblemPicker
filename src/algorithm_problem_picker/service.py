"""Complete listing collection before filtering and selecting results."""

from collections.abc import Callable

from .models import Order, ProblemRecord, Progress, Result, Stage, now
from .ports import PlatformPolicy, ProblemSource
from .selection import recommend


class Picker[P: ProblemRecord, C, U]:
    def __init__(self, policy: PlatformPolicy[P, C, U], source: ProblemSource[P, C, U],
                 report: Callable[[Progress], None] = lambda _: None):
        self.policy = policy
        self.source = source
        self.report = report

    def recommend(self, criteria: C, count: int = 1) -> Result[P, C, U]:
        return self._run(criteria, count, random_selection=True)

    def list(self, criteria: C, limit: int = 20,
             sort: str = 'id', order: Order = Order.ASC) -> Result[P, C, U]:
        order = Order(order)
        sort = self.policy.validate_list_options(sort, order)
        return self._run(criteria, limit, random_selection=False, sort=sort, order=order)

    def _run(self, criteria: C, requested: int, random_selection: bool,
             sort: str = 'id', order: Order = Order.ASC) -> Result[P, C, U]:
        if type(requested) is not int or requested <= 0:
            raise ValueError("개수는 양의 정수여야 합니다.")
        started_at = now()
        progress = Progress()
        try:
            user = self.source.prepare_user(criteria)
            if user is not None:
                progress.advance(Stage.USER_RESOLVED)
                self.report(progress)
            progress.advance(Stage.COLLECTING)
            self.report(progress)
            listing = self.source.collect(criteria, user)
            progress.collected = len(listing.candidates)
            progress.advance(Stage.PROCESSING)
            self.report(progress)
            eligible, omitted = self.policy.filter_listing(listing.candidates, criteria)
            selected = recommend(eligible, requested) if random_selection else self.policy.sort_problems(
                eligible, sort, order)[:requested]
            result = Result(criteria=criteria, user=user, problems=tuple(selected),
                          fetched_count=progress.collected, eligible_count=len(eligible),
                          omitted_unknown_count=omitted, started_at=started_at,
                          finished_at=now(), requested_count=requested,
                          shortage=max(0, requested - len(selected)) if random_selection else 0)
            progress.advance(Stage.COMPLETE)
            self.report(progress)
            return result
        except KeyboardInterrupt:
            progress.advance(Stage.CANCELLED)
            self.report(progress)
            raise
        except Exception:
            progress.advance(Stage.FAILED)
            self.report(progress)
            raise
