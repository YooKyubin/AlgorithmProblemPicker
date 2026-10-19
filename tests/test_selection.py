from decimal import Decimal

import pytest

from algorithm_problem_picker.models import Known, Rated, SearchCriteria, Unavailable, Unrated
from algorithm_problem_picker import selection


def test_inclusive_decimal_filters_and_unknowns(problem):
    problems = [problem(), problem(1001, rate=Known(Decimal("47.449"))),
                problem(1002, rate=Unavailable()), problem(1003, tier=Unrated()),
                problem(1004, tier=Unavailable()), problem(1005, solvers=Known(0))]
    criteria = SearchCriteria(min_tier=1, max_tier=1, min_rate=Decimal("47.45"),
                              max_rate=Decimal("47.45"), min_solvers=10, max_solvers=10)
    cheap, omitted = selection.filter_listing(problems, criteria)
    result, solver_omitted = selection.filter_solvers(cheap, criteria)
    assert [p.id for p in result] == [1000]
    assert omitted == 2  # missing rate and missing tier, not the explicit Unrated
    assert solver_omitted == 0
    assert len(selection.filter_listing(problems, SearchCriteria())[0]) == 6
    assert selection.filter_solvers([problems[-1]], SearchCriteria(max_solvers=0))[0]
    assert selection.filter_solvers([problem(solvers=Unavailable())],
                                    SearchCriteria(min_solvers=0))[1] == 1


def test_default_id_order_and_one_sided_bounds(problem):
    items = [problem(1002), problem(1000), problem(1001)]
    assert [p.id for p in selection.sort_problems(items)] == [1000, 1001, 1002]
    assert selection.filter_listing(items, SearchCriteria(max_rate=Decimal("47.44")))[0] == []
    assert selection.filter_listing(items, SearchCriteria(min_tier=2))[0] == []


@pytest.mark.parametrize('kwargs', [dict(min_tier=0), dict(max_tier=31),
    dict(min_rate=Decimal('NaN')), dict(max_rate=Decimal('Infinity')),
    dict(min_rate=Decimal('-1')), dict(min_solvers=-1), dict(min_tier=3, max_tier=2),
    dict(min_solvers=3, max_solvers=2), dict(status='solved'), dict(user_handle='someone')])
def test_invalid_criteria(kwargs):
    with pytest.raises(ValueError):
        SearchCriteria(**kwargs)


@pytest.mark.parametrize('requested,size', [(5,12),(20,12),(3,0)])
def test_recommend_entire_unique_population(problem, monkeypatch, requested, size):
    population = [problem(1000+i) for i in range(size)]
    received = []
    def sample(items, k):
        received.append(([p.id for p in items], k))
        return list(reversed(items))[:k]
    monkeypatch.setattr('random.sample', sample)
    result = selection.recommend(population + population[:1], requested)
    assert received == [([p.id for p in population], min(requested,size))]
    assert len(result) == min(requested,size)
    assert len({p.id for p in result}) == len(result)


@pytest.mark.parametrize('sort', ['difficulty','rate','solvers'])
@pytest.mark.parametrize('order,expected', [('asc',[1000,1001,1002,1003,1004]),
                                          ('desc',[1002,1000,1001,1003,1004])])
def test_metric_order_ties_and_missing_last(problem, sort, order, expected):
    low = [problem(1001), problem(1000)]
    high = problem(1002, tier=Rated(5), rate=Known(Decimal('90')), solvers=Known(30))
    missing = [problem(1004, tier=Unavailable(), rate=Unavailable(), solvers=Unavailable()),
               problem(1003, tier=Unrated(), rate=Unavailable(), solvers=Unavailable())]
    assert [p.id for p in selection.sort_problems(low + [high] + missing, sort, order)] == expected


def test_id_desc_and_shuffle_entire_population(problem, monkeypatch):
    items = [problem(1000+i) for i in range(25)]
    assert selection.sort_problems(items, 'id','desc')[0].id == 1024
    def shuffle(population):
        assert len(population) == 25
        population.reverse()
    monkeypatch.setattr('random.shuffle', shuffle)
    shuffled = selection.sort_problems(items, 'random')
    assert shuffled[0].id == 1024 and {p.id for p in shuffled} == {p.id for p in items}
