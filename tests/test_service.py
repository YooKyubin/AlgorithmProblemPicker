from dataclasses import replace
from decimal import Decimal

import pytest

from algorithm_problem_picker.models import CompletedListing, Known, SearchCriteria, UserReference, now
from algorithm_problem_picker.ports import SourceAccessError, SourceCompletenessError
from algorithm_problem_picker.service import Picker


class FixedSource:
    def __init__(self, problems):
        self.problems = problems
        self.details = []
        self.fail_id = None

    def resolve_user(self, handle):
        return UserReference(handle, 42, now())

    def collect(self, criteria, user):
        # The second page repeats the first ID with a changed record.
        items = self.problems + [replace(self.problems[0], title='later record')]
        if criteria.status == 'solved':
            items = [p for p in items if p.id == 1000]
        elif criteria.status == 'unsolved':
            items = [p for p in items if p.id != 1000]  # 1001 only has wrong submissions
        return CompletedListing(tuple(items))

    def read_details(self, candidate):
        self.details.append(candidate.id)
        if candidate.id == self.fail_id:
            raise SourceAccessError('detail failed')
        return candidate


def test_complete_dedup_cheap_filter_and_limit(problem):
    source = FixedSource([problem(), problem(1001, rate=Known(Decimal('10'))), problem(1002)])
    result = Picker(source).list(SearchCriteria(min_rate=Decimal('40')), limit=1)
    assert result.fetched_count == 3
    assert result.eligible_count == 2
    assert result.problems[0].title == '문제 1000'
    assert source.details == [1000, 1002]
    assert result.problems[0].pass_rate == Known(Decimal('47.45'))


def test_user_partition_and_normalized_exact_handle(problem):
    source = FixedSource([problem(), problem(1001), problem(1002)])
    picker = Picker(source)
    all_ids = {p.id for p in picker.list(SearchCriteria()).problems}
    solved = picker.list(SearchCriteria(status='solved', user_handle='@Case'))
    unsolved = picker.list(SearchCriteria(status='unsolved', user_handle='@Case'))
    assert solved.user.handle == 'Case'
    solved_ids, unsolved_ids = {p.id for p in solved.problems}, {p.id for p in unsolved.problems}
    assert not solved_ids & unsolved_ids
    assert solved_ids | unsolved_ids == all_ids
    assert 1001 in unsolved_ids


def test_detail_failure_never_returns_result(problem):
    source = FixedSource([problem(), problem(1001)])
    source.fail_id = 1001
    with pytest.raises(SourceAccessError):
        Picker(source).list(SearchCriteria(), limit=1)


@pytest.mark.parametrize('operation', ['list', 'recommend'])
def test_incomplete_collection_never_enriches_sorts_or_samples(problem, monkeypatch, operation):
    source = FixedSource([problem()])
    def incomplete(*args):
        raise SourceCompletenessError('additional load never completed')
    def premature(*args, **kwargs):
        pytest.fail('selection before complete collection')
    monkeypatch.setattr(source, 'collect', incomplete)
    monkeypatch.setattr('algorithm_problem_picker.service.sort_problems', premature)
    monkeypatch.setattr('algorithm_problem_picker.service.recommend', premature)
    stages = []
    with pytest.raises(SourceCompletenessError):
        getattr(Picker(source, report=lambda progress: stages.append(progress.stage)), operation)(SearchCriteria())
    assert not source.details
    assert 'Complete' not in stages and stages[-1] == 'Failed'


def test_recommend_enriches_all_candidates_before_sample(problem, monkeypatch):
    source = FixedSource([problem(1000+i) for i in range(12)])
    def sample(items, k):
        assert source.details == [1000+i for i in range(12)]
        assert len(items) == 12 and k == 5
        return items[-5:]
    monkeypatch.setattr('random.sample', sample)
    result = Picker(source).recommend(SearchCriteria(), count=5)
    assert [p.id for p in result.problems] == [1007,1008,1009,1010,1011]
    assert result.requested_count == result.returned_count == 5 and result.shortage == 0


def test_recommend_failure_does_not_sample(problem, monkeypatch):
    source = FixedSource([problem(), problem(1001)])
    source.fail_id = 1001
    monkeypatch.setattr('random.sample', lambda *args: pytest.fail('sample before complete'))
    with pytest.raises(SourceAccessError):
        Picker(source).recommend(SearchCriteria())


def test_recommend_shortage_and_shared_filter(problem):
    source = FixedSource([problem(), problem(1001, rate=Known(Decimal('10')))])
    criteria = SearchCriteria(min_rate=Decimal('40'))
    listed = Picker(source).list(criteria)
    result = Picker(source).recommend(criteria, count=5)
    assert result.problems == listed.problems
    assert result.shortage == 4 and result.returned_count == 1


def test_sort_full_candidates_before_limit_keeps_unrated(problem):
    from algorithm_problem_picker.models import Unrated
    source = FixedSource([problem(1000, tier=Unrated()), problem(1001),
                          problem(1002, rate=Known(Decimal('99')))])
    result = Picker(source).list(SearchCriteria(), sort='rate', order='desc', limit=1)
    assert result.problems[0].id == 1002 and result.eligible_count == 3
    assert len(source.details) == 3


def test_solver_filter_uses_enriched_counts_and_retains_listing_values(problem, monkeypatch):
    source = FixedSource([problem(1000, solvers=Known(0)), problem(1001, solvers=Known(6000))])
    def details(candidate):
        return replace(candidate, solver_count=Known(5171 if candidate.id == 1000 else 0))
    monkeypatch.setattr(source, 'read_details', details)
    result = Picker(source).list(SearchCriteria(min_solvers=5000))
    assert [p.id for p in result.problems] == [1000]
    assert result.problems[0].solver_count == Known(5171)
    assert result.problems[0].pass_rate == source.problems[0].pass_rate
    assert result.problems[0].tier == source.problems[0].tier
