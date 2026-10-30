import re
from dataclasses import replace
from decimal import Decimal

import pytest
from typer.testing import CliRunner

from algorithm_problem_picker import cli, platforms
from algorithm_problem_picker.models import CompletedListing, Known, now
from algorithm_problem_picker.jungol_models import Rated, SearchCriteria, UserReference
from algorithm_problem_picker.ports import SourceAccessError, SourceSchemaError, SourceCompletenessError, UserResolutionError

runner = CliRunner()

TIER_NAMES = (
    'B5', 'B4', 'B3', 'B2', 'B1', 'S5', 'S4', 'S3', 'S2', 'S1',
    'G5', 'G4', 'G3', 'G2', 'G1', 'P5', 'P4', 'P3', 'P2', 'P1',
    'D5', 'D4', 'D3', 'D2', 'D1', 'R5', 'R4', 'R3', 'R2', 'R1',
)


def _problem_ids(output):
    return [int(value) for value in re.findall(r'^\s*(\d+)\s+문제 ', output, re.MULTILINE)]


def _result_summary(output):
    return [line for line in output.splitlines() if line.startswith(('조건:', '조회 ', '부족 '))
            and not line.startswith('조회 시각:')]


@pytest.fixture
def source_factory(monkeypatch):
    calls = []

    class Source:
        def __init__(self, report):
            calls.append('constructed')

        def __enter__(self):
            calls.append('started')
            return self

        def __exit__(self, *args):
            calls.append('closed')

        def prepare_user(self, criteria):
            return self.resolve_user(criteria.user_handle) if criteria.user_handle else None

        def collect(self, criteria, user):
            calls.append(criteria)
            return CompletedListing(())

    binding = platforms.REGISTRY[platforms.DEFAULT_PLATFORM]
    monkeypatch.setitem(platforms.REGISTRY, platforms.DEFAULT_PLATFORM,
                        replace(binding, source_factory=lambda report: Source(report)))
    monkeypatch.setattr(cli.webbrowser, 'open', lambda *a, **k: pytest.fail('unexpected browser'))
    return Source, calls


@pytest.mark.parametrize('args', [
    ['--limit','0'], ['--min-rate','NaN'], ['--max-rate','Infinity'],
    ['--min-rate','80','--max-rate','20'], ['--min-tier','31'],
    ['--min-accepted','-1'], ['--status','unsolved'], ['--user','Name'],
    ['--limit','1.2'], ['--min-accepted','20','--max-accepted','10'], ['--user','@']])
def test_invalid_list_before_browser(args, source_factory):
    _, calls = source_factory
    assert runner.invoke(cli.app, ['list', *args]).exit_code == 2
    assert calls == []


def test_list_empty_and_default_output_channels(source_factory):
    _, calls = source_factory
    result = runner.invoke(cli.app, ['list'])
    assert result.exit_code == 0, result.exception
    assert '적격 0' in result.stdout and '표시 0' in result.stdout
    assert '요청 20' in result.stdout
    assert 'Ctrl+C' in result.stderr and 'Ctrl+C' not in result.stdout
    assert calls[-1] == 'closed'


def test_common_filters_and_exact_user_reach_service(source_factory, monkeypatch):
    from decimal import Decimal
    from algorithm_problem_picker.models import now
    from algorithm_problem_picker.jungol_models import UserReference
    source, calls = source_factory
    def resolve(self, handle):
        assert handle == 'Case'
        return UserReference(handle, 42, now())
    monkeypatch.setattr(source, 'resolve_user', resolve, raising=False)
    result = runner.invoke(cli.app, ['list','--status','solved','--user','@Case',
        '--min-tier','1','--max-tier','30','--min-rate','47.45','--max-rate','50',
        '--min-accepted','0','--max-accepted','100'])
    assert result.exit_code == 0, result.exception
    criteria = calls[2]
    assert criteria.min_rate == Decimal('47.45') and criteria.max_rate == Decimal('50')
    assert criteria.min_tier == 1 and criteria.max_tier == 30
    assert criteria.min_accepted == 0 and criteria.max_accepted == 100
    assert criteria.status == 'solved' and criteria.user_handle == 'Case'
    assert '@Case' in result.stdout


@pytest.mark.parametrize('command', ['list', 'recommend'])
@pytest.mark.parametrize('number,name', tuple(enumerate(TIER_NAMES, start=1)))
def test_tier_abbreviations_match_numeric_criteria(source_factory, command, number, name):
    _, calls = source_factory
    for arguments in (['--tier', f'{name}..{name.lower()}'],
                      ['--min-tier', name.lower(), '--max-tier', str(number)]):
        calls.clear()
        result = runner.invoke(cli.app, [command, *arguments], terminal_width=180)
        assert result.exit_code == 0, result.output
        criteria = next(call for call in calls if isinstance(call, SearchCriteria))
        assert criteria == SearchCriteria(min_tier=number, max_tier=number)
        assert f'min_tier={name}' in result.stdout and f'max_tier={name}' in result.stdout


@pytest.mark.parametrize('command', ['list', 'recommend'])
@pytest.mark.parametrize('value,lower,upper', [
    ('S5..G1', 6, 15), ('g5..', 11, None), ('..s1', None, 10),
    ('S5..15', 6, 15), ('6..g1', 6, 15),
])
def test_tier_abbreviation_ranges(source_factory, command, value, lower, upper):
    _, calls = source_factory
    result = runner.invoke(cli.app, [command, '--tier', value])
    assert result.exit_code == 0, result.output
    assert next(call for call in calls if isinstance(call, SearchCriteria)) == SearchCriteria(lower, upper)


@pytest.mark.parametrize('command', ['list', 'recommend'])
@pytest.mark.parametrize('arguments,option', [
    (['--tier', 'B0..S1'], '--tier'), (['--tier', 'B6..S1'], '--tier'),
    (['--tier', 'X5..S1'], '--tier'), (['--tier', 'B05..S1'], '--tier'),
    (['--tier', 'G1..S5'], '--tier'), (['--tier', 'B1..B5'], '--tier'),
    (['--min-tier', ' B5'], '--min-tier'), (['--max-tier', 'R2 '], '--max-tier'),
    (['--min-tier', 'Silver1'], '--min-tier'), (['--max-tier', 'S１'], '--max-tier'),
    (['--tier', 'S5..G1', '--min-tier', 'S5'], '--tier'),
    (['--tier', 'B5..B1', '--tier', 'S5..S1'], '--tier'),
])
def test_invalid_tier_abbreviations_before_source(source_factory, command, arguments, option):
    _, calls = source_factory
    result = runner.invoke(cli.app, [command, *arguments], terminal_width=180)
    assert result.exit_code == 2 and not calls and not result.stdout
    assert option in result.stderr and '조회 시작' not in result.stderr


@pytest.mark.parametrize('command', ['list', 'recommend'])
def test_all_tier_names_and_unrated_output(source_factory, monkeypatch, problem, command):
    from rich.console import Console
    from algorithm_problem_picker.models import Unavailable
    from algorithm_problem_picker.jungol_models import Unrated
    source, _ = source_factory
    items = tuple(problem(1000+i, tier=Rated(i+1)) for i in range(30)) + (
        problem(1030, tier=Unrated()), problem(1031, tier=Unavailable()))
    monkeypatch.setattr(source, 'collect', lambda *args: CompletedListing(items))
    monkeypatch.setattr(cli, 'out', Console(width=180, highlight=False, markup=False))
    extra = ['--limit', '32'] if command == 'list' else ['--count', '32']
    result = runner.invoke(cli.app, [command, *extra])
    assert result.exit_code == 0, result.output
    rows = {int(parts[0]): parts[3] for line in result.stdout.splitlines()
            if re.match(r'^\s*10[0-3][0-9]\s+문제 ', line) and (parts := line.split())}
    assert [rows[1000+i] for i in range(32)] == [*TIER_NAMES, '미정', '미확인']


@pytest.mark.parametrize('command', ['list', 'recommend'])
@pytest.mark.parametrize('metric,value,expected', [
    ('tier', '9..13', [1000, 1001, 1002, 1003, 1004]),
    ('rate', '40.5..80', [1001, 1002, 1003]),
    ('accepted', '500..1000', [1001, 1002, 1003]),
    ('tier', '9..', [1000, 1001, 1002, 1003, 1004]),
    ('tier', '..13', [1000, 1001, 1002, 1003, 1004]),
    ('rate', '40.5..', [1001, 1002, 1003, 1004]),
    ('rate', '..80', [1000, 1001, 1002, 1003]),
    ('accepted', '500..', [1001, 1002, 1003, 1004]),
    ('accepted', '..1000', [1000, 1001, 1002, 1003]),
    ('tier', '1..1', [1000, 1001, 1002, 1003, 1004]),
    ('tier', '30..30', [1000, 1001, 1002, 1003, 1004]),
])
def test_ranges_match_legacy(source_factory, monkeypatch, problem, command, metric, value, expected):
    source, calls = source_factory
    items = tuple(problem(1000+i, tier=Rated(8), rate=Known(Decimal(rate)), accepted=Known(accepted))
                  for i, (rate, accepted) in enumerate(zip(
                      ['40.49', '40.5', '60.25', '80', '80.01'], [499, 500, 750, 1000, 1001])))
    def collect(self, criteria, user):
        calls.append(criteria)
        return CompletedListing(items)
    monkeypatch.setattr(source, 'collect', collect)
    lower, upper = value.split('..')
    extra = ['--limit', '10', '--sort', 'accepted', '--order', 'desc'] if command == 'list' else ['--count', '10']
    results = []
    criteria = []
    legacy = ([f'--min-{metric}', lower] if lower else []) + ([f'--max-{metric}', upper] if upper else [])
    for bounds in ([f'--{metric}', value], legacy):
        calls.clear()
        result = runner.invoke(cli.app, [command, *bounds, *extra], terminal_width=180)
        assert result.exit_code == 0, result.output
        criteria.append(next(call for call in calls if isinstance(call, SearchCriteria)))
        ids = _problem_ids(result.stdout)
        assert sorted(ids) == expected and len(ids) == len(set(ids))
        if command == 'list':
            assert ids == list(reversed(expected))
        else:
            assert f'부족 {10-len(expected)}개' in result.stdout
        results.append(_result_summary(result.stdout))
    assert criteria[0] == criteria[1]
    assert results[0] == results[1]


@pytest.mark.parametrize('command', ['list', 'recommend'])
@pytest.mark.parametrize('metric', ['rate', 'accepted'])
def test_zero_range_separates_zero_and_missing(source_factory, monkeypatch, problem, command, metric):
    from algorithm_problem_picker.models import Unavailable
    source, calls = source_factory
    missing = problem(1001, rate=Unavailable(), accepted=Unavailable())
    items = (problem(rate=Known(Decimal('0')), accepted=Known(0)), missing,
             problem(1002, rate=Known(Decimal('1')), accepted=Known(1)), missing)
    monkeypatch.setattr(source, 'collect', lambda *args: CompletedListing(items))
    extra = ['--count', '3'] if command == 'recommend' else []
    result = runner.invoke(cli.app, [command, f'--{metric}', '0..0', *extra], terminal_width=180)
    assert result.exit_code == 0, result.output
    assert _problem_ids(result.stdout) == [1000]
    assert '조회 3' in result.stdout and '적격 1' in result.stdout
    assert '미제공으로 1개 제외' in result.stderr and calls[-1] == 'closed'
    if command == 'recommend':
        assert '부족 2개' in result.stdout


@pytest.mark.parametrize('command', ['list', 'recommend'])
def test_equal_rate_preserves_decimal(source_factory, monkeypatch, problem, command):
    source, _ = source_factory
    monkeypatch.setattr(source, 'collect', lambda *args: CompletedListing((
        problem(rate=Known(Decimal('47.45'))),
        problem(1001, rate=Known(Decimal('47.450000000000000001'))))))
    result = runner.invoke(cli.app, [command, '--rate', '47.45..47.45'], terminal_width=180)
    assert result.exit_code == 0, result.output
    assert _problem_ids(result.stdout) == [1000]
    assert 'min_rate=47.45' in result.stdout and 'max_rate=47.45' in result.stdout


@pytest.mark.parametrize('command', ['list', 'recommend'])
def test_mixed_and_omitted_ranges_preserve_criteria(source_factory, command):
    _, calls = source_factory
    arguments = ['--tier', '9..13', '--min-rate', '4.05e1', '--max-rate', '80', '--accepted=00500..']
    result = runner.invoke(cli.app, [command, *arguments], terminal_width=180)
    assert result.exit_code == 0, result.output
    criteria = next(call for call in calls if isinstance(call, SearchCriteria))
    assert criteria == SearchCriteria(9, 13, Decimal('40.5'), Decimal('80'), 500, None)
    assert 'max_accepted=' not in result.stdout and '경고' not in result.stderr
    calls.clear()
    result = runner.invoke(cli.app, [command, '--accepted', '00500..', '--max-rate', '80',
                                   '--min-rate', '4.05e1', '--tier=9..13'], terminal_width=180)
    assert result.exit_code == 0, result.output
    assert next(call for call in calls if isinstance(call, SearchCriteria)) == criteria
    calls.clear()
    result = runner.invoke(cli.app, [command], terminal_width=180)
    assert result.exit_code == 0, result.output
    assert next(call for call in calls if isinstance(call, SearchCriteria)) == SearchCriteria()
    assert 'min_' not in result.stdout and 'max_' not in result.stdout


@pytest.mark.parametrize('command', ['list', 'recommend'])
@pytest.mark.parametrize('metric', ['tier', 'rate', 'accepted'])
@pytest.mark.parametrize('value', [
    '', '..', '5', '1...5', '1..3..5', '1..x', '5..1', '-1..5', '+1..5', '1,000..',
    '1%..5', ' 1..5', '1 ..5', '1..5 ', '1..\t5', '1e0..5', 'NaN..5', '0..Infinity',
    '１..５', '١..٥', 'Bronze..Ruby',
])
def test_invalid_ranges_before_source(source_factory, command, metric, value):
    _, calls = source_factory
    result = runner.invoke(cli.app, [command, f'--{metric}={value}'], terminal_width=180)
    assert result.exit_code == 2 and not calls and not result.stdout
    message = ' '.join(result.stderr.replace('│', '').split())
    assert f'--{metric}' in message and '조회 시작' not in message
    assert '경계' in message or '하한' in message or '예:' in message
    if value != '5..1':
        assert '예:' in message


@pytest.mark.parametrize('command', ['list', 'recommend'])
@pytest.mark.parametrize('metric,value', [
    ('tier', '0..5'), ('tier', '1..31'), ('tier', '1.0..5'),
    ('accepted', '0..1.5'), ('rate', '0..100.1'), ('rate', '.5..1'), ('rate', '1..5.'),
])
def test_range_metric_limits_before_source(source_factory, command, metric, value):
    _, calls = source_factory
    result = runner.invoke(cli.app, [command, f'--{metric}', value], terminal_width=180)
    assert result.exit_code == 2 and not calls and not result.stdout
    assert f'--{metric}' in result.stderr and '조회 시작' not in result.stderr


@pytest.mark.parametrize('command', ['list', 'recommend'])
@pytest.mark.parametrize('metric', ['tier', 'rate', 'accepted'])
@pytest.mark.parametrize('boundary', ['min', 'max'])
@pytest.mark.parametrize('reverse', [False, True])
@pytest.mark.parametrize('value,old_value', [('1..5', '1'), ('1..', '5'), ('0..5', '0')])
def test_range_conflicts_before_source(source_factory, command, metric, boundary, reverse, value, old_value):
    if metric == 'tier' and old_value == '0':
        value, old_value = '1..5', '1'
    _, calls = source_factory
    new = [f'--{metric}', value]
    old = [f'--{boundary}-{metric}', old_value]
    arguments = old + new if reverse else new + old
    result = runner.invoke(cli.app, [command, *arguments], terminal_width=180)
    assert result.exit_code == 2 and not calls and not result.stdout
    message = ' '.join(result.stderr.replace('│', '').split())
    assert f'--{metric}' in message and old[0] in message and '한 가지 표기' in message
    assert '조회 시작' not in message


@pytest.mark.parametrize('command', ['list', 'recommend'])
@pytest.mark.parametrize('metric', ['tier', 'rate', 'accepted'])
@pytest.mark.parametrize('second', ['1..5', '2..6'])
def test_repeated_ranges_before_source(source_factory, command, metric, second):
    _, calls = source_factory
    result = runner.invoke(cli.app, [command, f'--{metric}', '1..5', f'--{metric}={second}'],
                           terminal_width=180)
    assert result.exit_code == 2 and not calls and not result.stdout
    assert f'--{metric}' in result.stderr and '한 번만' in result.stderr
    assert '조회 시작' not in result.stderr


@pytest.mark.parametrize('command', ['list', 'recommend'])
@pytest.mark.parametrize('metric', ['tier', 'rate', 'accepted'])
def test_missing_range_value_before_source(source_factory, command, metric):
    _, calls = source_factory
    result = runner.invoke(cli.app, [command, f'--{metric}'], terminal_width=180)
    assert result.exit_code == 2 and not calls and not result.stdout
    assert f'--{metric}' in result.stderr and 'requires an argument' in result.stderr


@pytest.mark.parametrize('command', ['list', 'recommend'])
def test_range_help_preserves_legacy_options(source_factory, command):
    _, calls = source_factory
    result = runner.invoke(cli.app, [command, '--help'], terminal_width=220)
    assert result.exit_code == 0 and not calls
    message = ' '.join(result.stdout.replace('│', '').split())
    for metric in ('tier', 'rate', 'accepted'):
        assert f'--{metric}' in message and f'--min-{metric}' in message and f'--max-{metric}' in message
    for explanation in ('MIN..MAX', 'MIN..', '..MAX', '양 끝 포함', '한 번만', '혼용', '기존', '1~30', '0~100'):
        assert explanation in message
    assert '사이트 검색 조건' in message and '범위 밖' in message and 'solvers' not in message


@pytest.mark.parametrize('command', ['list', 'recommend'])
def test_combined_ranges_preserve_user_and_limit(source_factory, monkeypatch, problem, command):
    source, calls = source_factory
    user = UserReference('Case', 42, now())
    monkeypatch.setattr(source, 'resolve_user', lambda self, handle: user, raising=False)
    def collect(self, criteria, resolved):
        assert resolved == user
        calls.append(criteria)
        return CompletedListing(tuple(problem(1000+i, tier=Rated(8), rate=Known(Decimal('50')),
                                              accepted=Known(500+i*100)) for i in range(4)))
    monkeypatch.setattr(source, 'collect', collect)
    results, criteria = [], []
    bounds = [
        ['--tier', '9..13', '--rate', '40.5..80', '--accepted', '500..1000'],
        ['--min-tier', '9', '--max-tier', '13', '--min-rate', '40.5', '--max-rate', '80',
         '--min-accepted', '500', '--max-accepted', '1000'],
    ]
    extra = ['--limit', '2', '--sort', 'accepted', '--order', 'desc'] if command == 'list' else ['--count', '2']
    for arguments in bounds:
        calls.clear()
        result = runner.invoke(cli.app, [command, *arguments, '--status', 'solved', '--user', '@Case', *extra],
                               terminal_width=180)
        assert result.exit_code == 0, result.output
        criteria.append(next(call for call in calls if isinstance(call, SearchCriteria)))
        ids = _problem_ids(result.stdout)
        assert len(ids) == 2 and len(set(ids)) == 2 and set(ids) <= {1000, 1001, 1002, 1003}
        if command == 'list':
            assert ids == [1003, 1002]
        assert '@Case' in result.stdout and '적격 4' in result.stdout
        results.append(_result_summary(result.stdout))
    assert criteria[0] == criteria[1] and results[0] == results[1]


@pytest.mark.parametrize('error,code', [(SourceAccessError('access failed'),1),
    (SourceSchemaError('schema failed'),1), (SourceCompletenessError('progress failed'),1),
    (UserResolutionError('unknown user'),1), (KeyboardInterrupt(),130)])
def test_list_failure_no_partial_output(error, code, source_factory, monkeypatch):
    source, calls = source_factory
    def fail(*args):
        raise error
    monkeypatch.setattr(source, 'collect', fail)
    result = runner.invoke(cli.app, ['list'])
    assert result.exit_code == code
    assert result.stdout == ''
    assert result.stderr and calls[-1] == 'closed'


def test_help_and_version_do_not_start_source(source_factory):
    _, calls = source_factory
    for prefix in ([], ['--platform', 'jungol']):
        for args in (['--help'], ['--version'], ['list','--help'], ['recommend','--help'], ['open','--help']):
            result = runner.invoke(cli.app, [*prefix, *args], terminal_width=180)
            assert result.exit_code == 0, result.output
            if args[-1] == '--help':
                assert 'algo-pick' in result.stdout
    root = runner.invoke(cli.app, ['--help'], terminal_width=180).stdout
    root = ' '.join(root.split())
    assert '--platform' in root and 'jungol' in root
    assert '명령 앞' in root and '기본' in root and '선택 가능' in root
    assert calls == []


@pytest.mark.parametrize('command', ['list','recommend'])
def test_tier_help_explains_site_search(source_factory, command):
    _, calls = source_factory
    result = runner.invoke(cli.app,[command,'--help'],terminal_width=180)
    assert result.exit_code == 0 and not calls
    message = ' '.join(result.stdout.replace('│','').split())
    assert '사이트 검색 조건' in message
    assert 'B5~R1' in message and '대소문자 무관' in message and 'S5..G1' in message
    assert '표시 티어' in message and '범위 밖' in message
    assert '미제공' in message and '실제 0' in message and '미확인' in message
    assert '버튼이 없으면 현재 목록' in message and '지연 반영' in message


@pytest.mark.parametrize('command', ['list','recommend'])
@pytest.mark.parametrize('bounds', [['--min-tier','9','--max-tier','13'],['--min-tier','9'],['--max-tier','7']])
def test_site_tier_bounds_and_observed_tier_output(source_factory, monkeypatch, problem, command, bounds):
    from rich.console import Console
    from algorithm_problem_picker.jungol_models import Rated
    source, calls = source_factory
    monkeypatch.setattr(source,'collect',lambda *args:CompletedListing((problem(tier=Rated(8)),)))
    monkeypatch.setattr(cli,'out',Console(width=180,highlight=False,markup=False))
    result = runner.invoke(cli.app,[command,*bounds])
    assert result.exit_code == 0, result.exception
    assert '조회 1' in result.stdout and '적격 1' in result.stdout
    row = next(line for line in result.stdout.splitlines() if line.lstrip().startswith('1000 '))
    assert row.split()[:4] == ['1000','문제','1000','S3']
    for option, value in zip(bounds[::2],bounds[1::2]):
        assert option[2:].replace('-','_')+'='+TIER_NAMES[int(value)-1] in result.stdout
    assert '티어' not in result.stderr and '경고' not in result.stderr
    assert calls[-1] == 'closed'


def test_accepted_output_and_processing(source_factory, monkeypatch, problem):
    from algorithm_problem_picker.models import Known, Unavailable
    source, _ = source_factory
    monkeypatch.setattr(source,'collect',lambda *args:CompletedListing((problem(accepted=Known(0)),problem(1001,accepted=Unavailable()))))
    result = runner.invoke(cli.app,['list','--sort','accepted'])
    assert result.exit_code == 0, result.exception
    assert '정답 제출 수' in result.stdout and '미확인' in result.stdout
    assert '중복 정답 제출' in result.stdout and '목록 관측' in result.stdout
    assert 'Processing' in result.stderr and '수집 2' in result.stderr
    assert '상세' not in result.stderr
    filtered = runner.invoke(cli.app,['recommend','--min-accepted','0','--max-accepted','0'])
    assert filtered.exit_code == 0 and '적격 1' in filtered.stdout
    assert 'min_accepted=0' in filtered.stdout and '정답 제출 수' in filtered.stdout


@pytest.mark.parametrize('command', ['list','recommend'])
def test_zero_and_missing_statistics_output(source_factory, monkeypatch, problem, command):
    from decimal import Decimal
    from rich.console import Console
    from algorithm_problem_picker.models import Known, Unavailable
    source, _ = source_factory
    items = (problem(rate=Known(Decimal('0.00')),accepted=Known(0)),
             problem(1001,rate=Unavailable(),accepted=Unavailable()))
    monkeypatch.setattr(source,'collect',lambda *args:CompletedListing(items))
    monkeypatch.setattr(cli,'out',Console(width=180,highlight=False,markup=False))
    result = runner.invoke(cli.app,[command]+(['--count','2'] if command == 'recommend' else []))
    assert result.exit_code == 0, result.exception
    rows = [line.split() for line in result.stdout.splitlines() if line.lstrip().startswith(('1000 ','1001 '))]
    assert next(row for row in rows if row[0] == '1000')[4:6] == ['0.00%','0']
    assert next(row for row in rows if row[0] == '1001')[4:6] == ['미확인','미확인']
    assert '적격 2' in result.stdout and '미제공으로' not in result.stderr


@pytest.mark.parametrize('command', ['list','recommend'])
@pytest.mark.parametrize('option', ['--min-rate','--max-rate','--min-accepted','--max-accepted', '--rate', '--accepted'])
def test_missing_statistic_filter_outputs_normal_empty_result(source_factory, monkeypatch, problem, command, option):
    from algorithm_problem_picker.models import Unavailable
    source, calls = source_factory
    items = (problem(rate=Unavailable(),accepted=Unavailable()),
             problem(1001,rate=Unavailable(),accepted=Unavailable()))
    monkeypatch.setattr(source,'collect',lambda *args:CompletedListing(items+items[:1]))
    value = '0..0' if option in ('--rate', '--accepted') else '0'
    result = runner.invoke(cli.app,[command,option,value]+(['--count','3'] if command == 'recommend' else []))
    assert result.exit_code == 0, result.exception
    assert '조건에 맞는 문제가 없습니다.' in result.stdout and '적격 0' in result.stdout
    assert '조회 2' in result.stdout and ('반환 0' if command == 'recommend' else '표시 0') in result.stdout
    assert '미제공으로 2개 제외' in result.stderr and '미제공으로' not in result.stdout
    if command == 'recommend':
        assert '요청 3' in result.stdout and '부족 3개' in result.stdout
    assert calls[-1] == 'closed'


@pytest.mark.parametrize('command', ['list','recommend'])
@pytest.mark.parametrize('legacy,replacement', [('--min-solvers','--min-accepted'),('--max-solvers','--max-accepted')])
@pytest.mark.parametrize('mixed', [False,True])
def test_legacy_range_rejected_before_source(source_factory, command, legacy, replacement, mixed):
    _, calls = source_factory
    arguments = [command,legacy,'not-a-number']
    if mixed:
        arguments += ['--min-accepted','0']
    result = runner.invoke(cli.app,arguments,terminal_width=180)
    assert result.exit_code == 2 and not calls and not result.stdout
    message = ' '.join(result.stderr.replace('│','').split())
    assert replacement in message
    assert '맞힌 사람 수' in message and '정답 제출 수' in message
    assert '중복' in message and '달라질 수' in message
    assert '조회 시작' not in result.stderr


def test_legacy_sort_rejected_before_source(source_factory):
    _, calls = source_factory
    result = runner.invoke(cli.app,['list','--sort','solvers'],terminal_width=180)
    assert result.exit_code == 2 and not calls and not result.stdout
    message = ' '.join(result.stderr.replace('│','').split())
    assert '--sort accepted' in message
    assert '맞힌 사람 수' in message and '정답 제출 수' in message


@pytest.mark.parametrize('command', ['list','recommend'])
def test_help_only_exposes_accepted(source_factory, command):
    _, calls = source_factory
    result = runner.invoke(cli.app,[command,'--help'],terminal_width=180)
    assert result.exit_code == 0 and not calls
    assert '--min-accepted' in result.stdout and '--max-accepted' in result.stdout
    assert '중복 정답 제출' in result.stdout
    assert 'solvers' not in result.stdout


@pytest.mark.parametrize('platform_args', [[], ['--platform', 'jungol']])
def test_recommend_default_and_shortage(source_factory, platform_args):
    result = runner.invoke(cli.app, [*platform_args, 'recommend'])
    assert result.exit_code == 0, result.exception
    assert '요청 1' in result.stdout and '반환 0' in result.stdout and '부족 1' in result.stdout


@pytest.mark.parametrize('count', ['0','-1','1.5'])
def test_recommend_count_validation(source_factory, count):
    _, calls = source_factory
    assert runner.invoke(cli.app, ['recommend','--count',count]).exit_code == 2
    assert not calls


@pytest.mark.parametrize('error,code', [(SourceAccessError('failed'),1),(SourceSchemaError('schema failed'),1),
    (SourceCompletenessError('progress failed'),1),(KeyboardInterrupt(),130)])
def test_recommend_failure(error, code, source_factory, monkeypatch):
    source, calls = source_factory
    def fail(*args):
        raise error
    monkeypatch.setattr(source, 'collect', fail)
    result = runner.invoke(cli.app, ['recommend'])
    assert result.exit_code == code and result.stdout == ''
    assert result.stderr and calls[-1] == 'closed'


def test_random_desc_invalid_before_source(source_factory):
    _, calls = source_factory
    result = runner.invoke(cli.app, ['list','--sort','random','--order','desc'])
    assert result.exit_code == 2 and not calls


@pytest.mark.parametrize('sort', ['id','difficulty','rate','accepted','random'])
def test_list_sort_options(source_factory, sort):
    result = runner.invoke(cli.app, ['list','--sort',sort,'--order','asc'])
    assert result.exit_code == 0, result.exception


@pytest.mark.parametrize('args', [[],['0'],['-1'],['1.5'],['1000','0','1001'],['1000','invalid','1001']])
def test_open_invalid_before_source(source_factory, args):
    _, calls = source_factory
    assert runner.invoke(cli.app, ['open', *args]).exit_code == 2
    assert not calls


@pytest.mark.parametrize('fail_ids', [set(), {1001}, {1000,1001}])
@pytest.mark.parametrize('platform_args', [[], ['--platform', 'jungol']])
def test_open_unique_order_and_failure_links(source_factory, monkeypatch, fail_ids, platform_args):
    _, source_calls = source_factory
    opened = []
    def open_url(url):
        opened.append(url)
        return int(url.rsplit('/',1)[1]) not in fail_ids
    monkeypatch.setattr(cli.webbrowser, 'open', open_url)
    result = runner.invoke(cli.app, [*platform_args, 'open','1000','1000','1001'])
    assert result.exit_code == (1 if fail_ids else 0)
    assert opened == ['https://jungol.co.kr/problem/1000','https://jungol.co.kr/problem/1001']
    assert all(url in result.stdout for url in opened)
    assert all(str(id) in result.stderr for id in fail_ids)
    assert not source_calls


@pytest.mark.parametrize('command', ['list', 'recommend'])
def test_default_and_explicit_jungol_share_complete_candidates(source_factory, monkeypatch, problem, command):
    source, calls = source_factory
    items = tuple(problem(1000 + i, rate=Known(Decimal('10') if i == 0 else Decimal('47.45')))
                  for i in range(25))
    user = UserReference('Case', 42, now())
    prepared = []

    def resolve(self, handle):
        prepared.append(handle)
        return user

    def collect(self, criteria, reference):
        assert reference is user
        calls.append(criteria)
        return CompletedListing(items)

    populations = []

    def sample(population, k):
        populations.append(([item.id for item in population], k))
        return list(reversed(population))[:k]

    monkeypatch.setattr(source, 'resolve_user', resolve, raising=False)
    monkeypatch.setattr(source, 'collect', collect)
    monkeypatch.setattr('random.sample', sample)
    results = []
    criteria = []
    for prefix in ([], ['--platform', 'jungol']):
        calls.clear()
        options = ['--count', '30'] if command == 'recommend' else []
        result = runner.invoke(cli.app, [*prefix, command, '--min-rate', '40', '--status', 'solved',
                                        '--user', '@Case', *options], terminal_width=180)
        assert result.exit_code == 0, result.output
        assert '조회 25' in result.stdout and '적격 24' in result.stdout and '@Case' in result.stdout
        assert 'Ctrl+C' in result.stderr and 'Ctrl+C' not in result.stdout
        ids = _problem_ids(result.stdout)
        assert len(set(ids)) == len(ids)
        if command == 'list':
            assert ids == list(range(1001, 1021)) and '요청 20' in result.stdout
        else:
            assert set(ids) == set(range(1001, 1025)) and '부족 6' in result.stdout
        assert calls[0:2] == ['constructed', 'started'] and calls[-1] == 'closed'
        criteria.append(next(value for value in calls if isinstance(value, SearchCriteria)))
        results.append(_result_summary(result.stdout))
    assert criteria[0] == criteria[1] and results[0] == results[1]
    assert prepared == ['Case', 'Case']
    assert populations == ([(list(range(1001, 1025)), 24)] * 2 if command == 'recommend' else [])
