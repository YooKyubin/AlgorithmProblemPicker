from dataclasses import replace
from decimal import Decimal

import pytest

from algorithm_problem_picker.models import CompletedListing, Known, Rated, SearchCriteria, Unavailable, UserReference, now
from algorithm_problem_picker.ports import SourceAccessError, SourceCompletenessError
from algorithm_problem_picker.service import Picker


class FixedSource:
    def __init__(self, problems):
        self.problems = problems
        self.collected = False
        self.failure = None

    def resolve_user(self, handle):
        return UserReference(handle, 42, now())

    def collect(self, criteria, user):
        if self.failure is not None:
            raise self.failure
        self.collected = True
        # The second page repeats the first ID with a changed record.
        items = self.problems + ([replace(self.problems[0], title='later record')] if self.problems else [])
        if criteria.status == 'solved':
            items = [p for p in items if p.id == 1000]
        elif criteria.status == 'unsolved':
            items = [p for p in items if p.id != 1000]  # 1001 only has wrong submissions
        return CompletedListing(tuple(items))

def test_complete_dedup_cheap_filter_and_limit(problem):
    source = FixedSource([problem(), problem(1001, rate=Known(Decimal('10'))), problem(1002)])
    result = Picker(source).list(SearchCriteria(min_rate=Decimal('40')), limit=1)
    assert result.fetched_count == 3
    assert result.eligible_count == 2
    assert result.problems[0].title == '문제 1000'
    assert source.collected
    assert result.problems[0].pass_rate == Known(Decimal('47.45'))
    assert result.requested_count == result.returned_count == 1 and result.shortage == 0
    assert result.started_at.tzinfo is not None and result.finished_at >= result.started_at


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


def test_collection_failure_never_returns_result(problem):
    source = FixedSource([problem(), problem(1001)])
    source.failure = SourceAccessError('collection failed')
    with pytest.raises(SourceAccessError):
        Picker(source).list(SearchCriteria(), limit=1)


@pytest.mark.parametrize('operation', ['list', 'recommend'])
def test_incomplete_collection_never_filters_sorts_or_samples(problem, monkeypatch, operation):
    source = FixedSource([problem()])
    def incomplete(*args):
        raise SourceCompletenessError('additional load never completed')
    def premature(*args, **kwargs):
        pytest.fail('selection before complete collection')
    monkeypatch.setattr(source, 'collect', incomplete)
    monkeypatch.setattr('algorithm_problem_picker.service.filter_listing', premature)
    monkeypatch.setattr('algorithm_problem_picker.service.sort_problems', premature)
    monkeypatch.setattr('algorithm_problem_picker.service.recommend', premature)
    stages = []
    with pytest.raises(SourceCompletenessError):
        getattr(Picker(source, report=lambda progress: stages.append(progress.stage)), operation)(SearchCriteria())
    assert not source.collected
    assert stages == ['Collecting','Failed']


def test_recommend_collects_all_candidates_before_sample(problem, monkeypatch):
    source = FixedSource([problem(1000+i) for i in range(12)])
    def sample(items, k):
        assert source.collected
        assert len(items) == 12 and k == 5
        return items[-5:]
    monkeypatch.setattr('random.sample', sample)
    result = Picker(source).recommend(SearchCriteria(), count=5)
    assert [p.id for p in result.problems] == [1007,1008,1009,1010,1011]
    assert result.requested_count == result.returned_count == 5 and result.shortage == 0
    assert result.fetched_count == result.eligible_count == 12
    assert result.finished_at.tzinfo is not None and result.finished_at >= result.started_at


def test_recommend_failure_does_not_sample(problem, monkeypatch):
    source = FixedSource([problem(), problem(1001)])
    source.failure = SourceAccessError('collection failed')
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


@pytest.mark.parametrize('operation', ['list','recommend'])
def test_all_unknown_tiers_are_normal_empty_result(problem, operation):
    from algorithm_problem_picker.models import Unavailable, Unrated
    source = FixedSource([problem(tier=Unrated()),problem(1001,tier=Unavailable())])
    result = getattr(Picker(source),operation)(SearchCriteria(min_tier=9,max_tier=14))
    assert result.fetched_count == 2 and result.eligible_count == result.returned_count == 0
    assert result.omitted_unknown_count == 1


@pytest.mark.parametrize('operation', ['list','recommend'])
@pytest.mark.parametrize('bounds,tiers', [(dict(min_tier=9,max_tier=13),(8,14)),
    (dict(min_tier=9),(1,8)), (dict(max_tier=13),(14,30))])
def test_all_rated_outside_site_bounds_remain_eligible(problem, monkeypatch, operation, bounds, tiers):
    source = FixedSource([problem(tier=Rated(tiers[0])),problem(1001,tier=Rated(tiers[1]),accepted=Known(20))])
    populations = []
    def sample(items, k):
        assert source.collected and k == 1
        populations.append(items)
        return items[-1:]
    monkeypatch.setattr('random.sample',sample)
    criteria = SearchCriteria(**bounds,min_rate=Decimal('40'),max_accepted=20)
    options = dict(limit=1,sort='difficulty',order='desc') if operation == 'list' else dict(count=1)
    result = getattr(Picker(source),operation)(criteria,**options)
    assert result.fetched_count == result.eligible_count == 2
    assert result.returned_count == 1 and result.shortage == result.omitted_unknown_count == 0
    assert result.criteria == criteria and result.problems[0] is source.problems[1]
    assert result.problems[0].tier == Rated(tiers[1])
    assert populations == ([source.problems] if operation == 'recommend' else [])


def test_sort_full_candidates_before_limit_keeps_unrated(problem):
    from algorithm_problem_picker.models import Unrated
    source = FixedSource([problem(1000, tier=Unrated()), problem(1001),
                          problem(1002, rate=Known(Decimal('99')))])
    result = Picker(source).list(SearchCriteria(), sort='rate', order='desc', limit=1)
    assert result.problems[0].id == 1002 and result.eligible_count == 3
    assert source.collected


def test_accepted_filter_retains_listing_values(problem):
    source = FixedSource([problem(accepted=Known(6510)),problem(1001,accepted=Known(0))])
    result = Picker(source).list(SearchCriteria(min_accepted=5000))
    assert [p.id for p in result.problems] == [1000]
    assert result.problems[0] is source.problems[0]


@pytest.mark.parametrize('operation', ['list','recommend'])
@pytest.mark.parametrize('filters', [{},dict(min_rate=Decimal('0')),dict(max_rate=Decimal('100')),
    dict(min_accepted=0),dict(max_accepted=0),dict(min_rate=Decimal('0'),max_accepted=0)])
def test_missing_statistics_can_be_normal_empty_result(problem, operation, filters):
    source = FixedSource([problem(rate=Unavailable(),accepted=Unavailable()),
                          problem(1001,rate=Unavailable(),accepted=Unavailable())])
    options = dict(limit=3) if operation == 'list' else dict(count=3)
    result = getattr(Picker(source),operation)(SearchCriteria(**filters),**options)
    assert result.fetched_count == 2
    assert result.eligible_count == result.returned_count == (0 if filters else 2)
    assert result.omitted_unknown_count == (2 if filters else 0)
    assert result.shortage == (3-result.returned_count if operation == 'recommend' else 0)
    if not filters:
        assert set(result.problems) == set(source.problems)
        assert all(item is source.problems[item.id-1000] for item in result.problems)


@pytest.mark.parametrize('operation', ['list','recommend'])
def test_zero_candidates_and_processing_stages(problem, operation):
    stages = []
    counts = []
    def report(progress):
        stages.append(progress.stage)
        counts.append(progress.collected)
    result = getattr(Picker(FixedSource([]),report),operation)(SearchCriteria())
    assert result.fetched_count == result.eligible_count == result.returned_count == 0
    assert stages == ['Collecting','Processing','Complete'] and counts == [0,0,0]
    assert result.shortage == (1 if operation == 'recommend' else 0)


@pytest.mark.parametrize('operation', ['list','recommend'])
def test_cancel_never_processes_partial_result(problem, operation, monkeypatch):
    source = FixedSource([problem()])
    source.failure = KeyboardInterrupt()
    monkeypatch.setattr('algorithm_problem_picker.service.filter_listing',lambda *args:pytest.fail('filter before completion'))
    stages = []
    with pytest.raises(KeyboardInterrupt):
        getattr(Picker(source,lambda progress:stages.append(progress.stage)),operation)(SearchCriteria())
    assert stages == ['Collecting','Cancelled']
