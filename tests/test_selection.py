from decimal import Decimal
from datetime import datetime

import pytest

from algorithm_problem_picker.models import Known, Rated, SearchCriteria, Unavailable, Unrated
from algorithm_problem_picker import selection


def test_inclusive_decimal_filters_and_unknowns(problem):
    problems = [problem(), problem(1001, rate=Known(Decimal("47.449"))),
                problem(1002, rate=Unavailable()), problem(1003, tier=Unrated()),
                problem(1004, tier=Unavailable()), problem(1005, accepted=Known(0))]
    criteria = SearchCriteria(min_tier=1, max_tier=1, min_rate=Decimal("47.45"),
                              max_rate=Decimal("47.45"), min_accepted=10, max_accepted=10)
    result, omitted = selection.filter_listing(problems, criteria)
    assert [p.id for p in result] == [1000]
    assert omitted == 2  # missing rate and missing tier, not the explicit Unrated
    assert len(selection.filter_listing(problems, SearchCriteria())[0]) == 6
    assert selection.filter_listing([problems[-1]], SearchCriteria(max_accepted=0))[0]
    assert selection.filter_listing([problem(accepted=Unavailable())],
                                    SearchCriteria(min_accepted=0))[1] == 1


def test_default_id_order_and_one_sided_bounds(problem):
    items = [problem(1002), problem(1000), problem(1001)]
    assert [p.id for p in selection.sort_problems(items)] == [1000, 1001, 1002]
    assert selection.filter_listing(items, SearchCriteria(max_rate=Decimal("47.44")))[0] == []
    assert selection.filter_listing(items, SearchCriteria(min_tier=2))[0] == items


@pytest.mark.parametrize('bounds', [dict(min_tier=9,max_tier=13),dict(min_tier=9),dict(max_tier=9)])
@pytest.mark.parametrize('filters,expected', [({},[1000,1001,1002]),
    (dict(min_rate=Decimal('40')),[1000,1001]), (dict(min_accepted=20),[1001,1002])])
def test_rated_site_bounds_preserve_values_and_numeric_filters(problem, bounds, filters, expected):
    items = [problem(tier=Rated(8)),problem(1001,tier=Rated(10),rate=Known(Decimal('80')),accepted=Known(20)),
             problem(1002,tier=Rated(13),rate=Known(Decimal('10')),accepted=Known(30))]
    eligible, omitted = selection.filter_listing(items,SearchCriteria(**bounds,**filters))
    assert [item.id for item in eligible] == expected
    assert omitted == 0
    assert all(item is items[item.id-1000] for item in eligible)
    assert [item.id for item in selection.sort_problems(eligible,'difficulty','asc')] == expected
    assert [item.id for item in selection.sort_problems(eligible,'difficulty','desc')] == expected[::-1]


@pytest.mark.parametrize('kwargs', [dict(min_tier=0), dict(max_tier=31),
    dict(min_rate=Decimal('NaN')), dict(max_rate=Decimal('Infinity')),
    dict(min_rate=Decimal('-1')), dict(min_accepted=-1), dict(min_tier=3, max_tier=2),
    dict(min_accepted=3, max_accepted=2), dict(status='solved'), dict(user_handle='someone')])
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


@pytest.mark.parametrize('sort', ['difficulty','rate','accepted'])
@pytest.mark.parametrize('order,expected', [('asc',[1000,1001,1002,1003,1004]),
                                          ('desc',[1002,1000,1001,1003,1004])])
def test_metric_order_ties_and_missing_last(problem, sort, order, expected):
    low = [problem(1001), problem(1000)]
    high = problem(1002, tier=Rated(5), rate=Known(Decimal('90')), accepted=Known(30))
    missing = [problem(1004, tier=Unavailable(), rate=Unavailable(), accepted=Unavailable()),
               problem(1003, tier=Unrated(), rate=Unavailable(), accepted=Unavailable())]
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


@pytest.mark.parametrize('bounds', [{}, dict(min_tier=9), dict(max_tier=14), dict(min_tier=9,max_tier=14)])
def test_three_tier_states_and_unique_unknown_count(problem, bounds):
    items = [problem(tier=Rated(9)), problem(1001,tier=Unrated()),
             problem(1002,tier=Unavailable(),rate=Unavailable())]
    eligible, omitted = selection.filter_listing(items, SearchCriteria(**bounds))
    assert [p.id for p in eligible] == ([1000] if bounds else [1000,1001,1002])
    assert omitted == (1 if bounds else 0)
    assert selection.filter_listing(items[1:],SearchCriteria(min_tier=9)) == ([],1)


@pytest.mark.parametrize('bounds,expected', [(dict(min_accepted=10,max_accepted=20),[10,20]),
    (dict(min_accepted=10),[10,20,21]),(dict(max_accepted=10),[0,9,10]),
    (dict(min_accepted=0,max_accepted=0),[0]),({},[0,9,10,20,21,None])])
def test_accepted_bounds(problem, bounds, expected):
    values = [0,9,10,20,21,None]
    items = [problem(1000+i,accepted=Unavailable() if value is None else Known(value)) for i,value in enumerate(values)]
    selected, omitted = selection.filter_listing(items,SearchCriteria(**bounds))
    assert [None if isinstance(p.accepted_count,Unavailable) else p.accepted_count.value for p in selected] == expected
    assert omitted == bool(bounds)


@pytest.mark.parametrize('metric', ['rate','accepted'])
@pytest.mark.parametrize('bounds,expected', [({},[1000,1001,1002]),({'min':1},[1001]),
    ({'max':0},[1000]),({'min':0,'max':0},[1000])])
def test_missing_statistics_are_not_zero(problem, metric, bounds, expected):
    items = [problem(rate=Known(Decimal('0.00')),accepted=Known(0)),
             problem(1001,rate=Known(Decimal('20')),accepted=Known(20)),
             problem(1002,rate=Unavailable(),accepted=Unavailable())]
    options = {boundary+'_'+metric:Decimal(value) if metric == 'rate' else value for boundary,value in bounds.items()}
    eligible, omitted = selection.filter_listing(items+items[2:],SearchCriteria(**options))
    assert [item.id for item in eligible] == expected
    assert omitted == (1 if bounds else 0)


def test_numeric_rejection_does_not_count_later_missing_statistic(problem):
    items = [problem(rate=Known(Decimal('0')),accepted=Unavailable()),
             problem(1001,rate=Unavailable(),accepted=Unavailable())]
    assert selection.filter_listing(items+items,SearchCriteria(min_rate=Decimal('1'),min_accepted=0)) == ([],1)


def test_unknown_count_stops_at_first_active_filter(problem):
    items = [problem(tier=Rated(1),rate=Unavailable(),accepted=Unavailable()),
             problem(1001,tier=Unavailable(),rate=Unavailable(),accepted=Unavailable()),
             problem(1002,tier=Unrated(),rate=Unavailable(),accepted=Unavailable()),
             problem(1003,tier=Rated(9),rate=Unavailable(),accepted=Unavailable())]
    assert selection.filter_listing(items+items[:1],SearchCriteria(min_tier=9,min_rate=Decimal('0'),min_accepted=0)) == ([],3)


@pytest.mark.parametrize('value', [-1,1.5,True])
@pytest.mark.parametrize('field', ['min_accepted','max_accepted'])
def test_invalid_accepted_boundary(field, value):
    with pytest.raises(ValueError):
        SearchCriteria(**{field:value})


@pytest.mark.parametrize('changes', [dict(id=True),dict(id=0),dict(title='  '),dict(url='https://jungol.co.kr/problem/99'),
    dict(tier=Known(9)),dict(pass_rate=Known(Decimal('NaN'))),dict(pass_rate=Known(Decimal('101'))),
    dict(accepted_count=Known(True)),dict(accepted_count=Known(-1)),dict(accepted_count=Known(1.5)),
    dict(listed_at=datetime(2026,10,21))])
def test_problem_validation_preserves_domain_invariants(problem, changes):
    from dataclasses import replace
    with pytest.raises(ValueError):
        replace(problem(),**changes)


@pytest.mark.parametrize('value',[True,0,31,1.5])
def test_rated_requires_integer_1_to_30(value):
    with pytest.raises(ValueError):
        Rated(value)
