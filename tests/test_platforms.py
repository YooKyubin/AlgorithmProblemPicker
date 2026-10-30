from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import datetime

import pytest
from typer.testing import CliRunner

from algorithm_problem_picker import cli, platforms
from algorithm_problem_picker.models import CompletedListing, FilterCapability, PlatformInfo, ProblemLink, now
from algorithm_problem_picker.ports import FilterInputError

runner = CliRunner()


@dataclass(frozen=True)
class SyntheticProblem:
    id: int
    title: str
    url: str
    listed_at: datetime
    difficulty: int


@dataclass(frozen=True)
class SyntheticCriteria:
    lower: int = 100
    upper: int = 200


class SyntheticPolicy:
    info = PlatformInfo(
        key='test-platform', display_name='합성 플랫폼',
        filters=(FilterCapability('difficulty', ('--tier', '--min-tier', '--max-tier'),
                                  '합성 난도', '점수', '100~200', '양 끝 포함'),),
        retired_options=(), columns=('번호', '제목', '합성 난도', '링크'),
        observation_notes=('합성 난도는 100~200 점수입니다.',), sort_help='id, difficulty',
    )

    def __init__(self, calls):
        self.calls = calls

    @property
    def columns(self):
        return self.info.columns

    @property
    def observation_notes(self):
        return self.info.observation_notes

    def parse_filters(self, raw):
        self.calls.append(('parse', raw))
        lower = raw.values.get('--min-tier', '100')
        upper = raw.values.get('--max-tier', '200')
        ranges = raw.values.get('--tier', ())
        if ranges:
            if len(ranges) != 1:
                raise FilterInputError('합성 난도 범위는 한 번만 지정하세요.', '--tier')
        try:
            if ranges:
                lower, upper = ranges[0].split('..')
            lower, upper = int(lower), int(upper)
        except ValueError as error:
            raise FilterInputError('합성 난도는 100~200 정수입니다.', '--tier') from error
        if not 100 <= lower <= upper <= 200:
            raise FilterInputError('합성 난도는 100~200 정수입니다.', '--tier')
        return SyntheticCriteria(lower, upper)

    def validate_list_options(self, sort, order):
        if sort not in {'id', 'difficulty'}:
            raise FilterInputError('합성 정렬은 id, difficulty입니다.', '--sort')
        return sort

    def filter_listing(self, problems, criteria):
        return [problem for problem in problems if criteria.lower <= problem.difficulty <= criteria.upper], 0

    def sort_problems(self, problems, sort, order):
        attribute = 'id' if sort == 'id' else 'difficulty'
        return sorted(problems, key=lambda problem: getattr(problem, attribute), reverse=order == 'desc')

    def format_row(self, problem):
        return str(problem.id), problem.title, str(problem.difficulty), problem.url

    def format_conditions(self, criteria, user):
        return f'합성 난도 {criteria.lower}..{criteria.upper} 점수'

    def problem_links(self, raw_ids):
        ids = [int(value) for value in raw_ids]
        if any(value <= 0 for value in ids):
            raise FilterInputError('합성 ID는 양수입니다.', 'ID')
        return tuple(ProblemLink(str(value), f'https://example.test/problems/{value}')
                     for value in dict.fromkeys(ids))


@pytest.fixture
def synthetic_platform(monkeypatch):
    calls = []
    policy = SyntheticPolicy(calls)
    problems = (SyntheticProblem(1000, '합성 문제', 'https://example.test/problems/1000', now(), 150),)

    @contextmanager
    def source_context():
        calls.append('entered')

        class Source:
            def prepare_user(self, criteria):
                calls.append('prepared')
                return None

            def collect(self, criteria, user):
                calls.append('collected')
                return CompletedListing(problems)

        try:
            yield Source()
        finally:
            calls.append('closed')

    def source_factory(report):
        calls.append('factory')
        return source_context()

    def unexpected(*args, **kwargs):
        pytest.fail('unexpected JUNGOL or browser operation')

    original_registry = platforms.REGISTRY
    original = original_registry[platforms.DEFAULT_PLATFORM]
    jungol = replace(original, source_factory=unexpected)
    binding = platforms.PlatformBinding(policy.info, policy, source_factory)
    monkeypatch.setattr(platforms, 'REGISTRY', platforms.PlatformRegistry((jungol, binding)))
    monkeypatch.setattr(platforms, 'JungolSource', unexpected)
    monkeypatch.setattr(cli.webbrowser, 'open', unexpected)
    yield binding, calls
    assert set(original_registry) == {'jungol'}


@pytest.mark.parametrize('command', ['list', 'recommend'])
@pytest.mark.parametrize('arguments,names', [
    (['--accepted', '0..0'], ['--accepted']),
    (['--min-accepted', '0'], ['--min-accepted']),
    (['--max-accepted', '100'], ['--max-accepted']),
    (['--status', 'all'], ['--status']),
    (['--user', ''], ['--user']),
    (['--status', 'solved', '--user', 'someone'], ['--status', '--user']),
    (['--accepted', 'invalid', '--accepted', '0..0'], ['--accepted']),
    (['--min-accepted', 'invalid', '--status', 'invalid'], ['--min-accepted', '--status']),
    (['--tier', 'invalid', '--rate', 'invalid', '--accepted', '0..0'], ['--rate', '--accepted']),
    (['--min-solvers', 'invalid', '--accepted', '0..0'], ['--min-solvers', '--accepted']),
])
def test_unsupported_filters_precede_value_parsing(synthetic_platform, command, arguments, names):
    _, calls = synthetic_platform
    result = runner.invoke(cli.app, ['--platform', 'test-platform', command, *arguments], terminal_width=240)
    assert result.exit_code == 2, result.output
    assert 'test-platform' in result.stderr and '지원하지 않는 필터' in result.stderr
    assert all(name in result.stderr for name in names)
    assert result.stdout == '' and calls == []


@pytest.mark.parametrize('command', ['list', 'recommend'])
def test_all_unsupported_names_are_reported_without_duplicates(synthetic_platform, monkeypatch, command):
    binding, calls = synthetic_platform
    info = replace(binding.info, filters=())
    binding.policy.info = info
    monkeypatch.setattr(platforms, 'REGISTRY', platforms.PlatformRegistry((
        platforms.REGISTRY['jungol'], replace(binding, info=info))))
    result = runner.invoke(cli.app, ['--platform', 'test-platform', command,
                                   '--tier', 'invalid', '--tier', 'invalid', '--min-rate', 'NaN'], terminal_width=240)
    assert result.exit_code == 2 and result.stdout == ''
    assert result.stderr.count('--tier') == 1 and result.stderr.count('--min-rate') == 1
    assert calls == []


@pytest.mark.parametrize('command', ['list', 'recommend'])
def test_known_retired_diagnostic_waits_for_all_unsupported_filters(synthetic_platform, monkeypatch, command):
    _, calls = synthetic_platform
    jungol = platforms.REGISTRY['jungol']
    info = replace(jungol.info, filters=tuple(capability for capability in jungol.info.filters
                                             if capability.key != 'accepted'))
    policy = type(jungol.policy)()
    policy.info = info
    monkeypatch.setattr(platforms, 'REGISTRY', platforms.PlatformRegistry((
        replace(jungol, info=info, policy=policy),)))
    result = runner.invoke(cli.app, [command, '--min-solvers', 'invalid', '--accepted', 'invalid'])
    assert result.exit_code == 2 and result.stdout == ''
    assert '지원하지 않는 필터' in result.stderr and '--accepted' in result.stderr
    assert '맞힌 사람 수' not in result.stderr
    assert calls == []


@pytest.mark.parametrize('command', ['list', 'recommend'])
def test_raw_sources_preserve_commandline_and_legacy_last_value(synthetic_platform, command):
    _, calls = synthetic_platform
    result = runner.invoke(cli.app, ['--platform', 'test-platform', command,
                                   '--min-tier', '100', '--min-tier', '120'])
    assert result.exit_code == 0, result.output
    raw = calls[0][1]
    assert raw.values['--min-tier'] == '120'
    assert raw.supplied_options == frozenset({'--min-tier'})


@pytest.mark.parametrize('command', ['list', 'recommend'])
def test_omitted_unsupported_defaults_are_not_requests(synthetic_platform, monkeypatch, command):
    from rich.console import Console
    _, calls = synthetic_platform
    monkeypatch.setattr(cli, 'out', Console(width=180, highlight=False, markup=False))
    result = runner.invoke(cli.app, ['--platform', 'test-platform', command])
    assert result.exit_code == 0, result.output
    message = ' '.join(result.stdout.split())
    assert '번호 제목 합성 난도 링크' in message
    row = next(line.split() for line in result.stdout.splitlines() if line.lstrip().startswith('1000 '))
    assert row == ['1000', '합성', '문제', '150', 'https://example.test/problems/1000']
    requested = 1 if command == 'recommend' else 20
    assert f'조회 1 · 적격 1 · 요청 {requested}' in message
    assert ('반환 1' if command == 'recommend' else '표시 1') in message
    assert '합성 난도 100..200 점수' in message
    assert all(note in result.stdout for note in SyntheticPolicy.info.observation_notes)
    assert all(text not in result.stdout for text in
               ('정답률', '정답 제출 수', '미확인', 'status=', '티어', '목록 관측'))
    assert '미제공으로' not in result.stderr
    raw = calls[0][1]
    assert raw.supplied_options == frozenset()
    assert calls[1:] == ['factory', 'entered', 'prepared', 'collected', 'closed']


@pytest.mark.parametrize('platform', ['unknown', '', 'programmers', 'JUNGOL'])
@pytest.mark.parametrize('command', ['list', 'recommend', 'open'])
def test_unknown_platform_stops_all_operations(synthetic_platform, platform, command):
    _, calls = synthetic_platform
    result = runner.invoke(cli.app, ['--platform', platform, command, *(['1000'] if command == 'open' else [])])
    assert result.exit_code == 2 and result.stdout == ''
    assert repr(platform) in result.stderr and 'jungol' in result.stderr
    assert calls == []


@pytest.mark.parametrize('problem', ['duplicate-key', 'duplicate-option', 'undefined-option', 'output', 'missing-default'])
def test_invalid_configuration_warns_then_fails_on_use(synthetic_platform, monkeypatch, problem):
    binding, calls = synthetic_platform
    jungol = platforms.REGISTRY['jungol']
    bindings = [jungol, binding]
    selected = 'test-platform'
    if problem == 'duplicate-key':
        bindings.append(binding)
    elif problem == 'duplicate-option':
        capability = replace(binding.info.filters[0], key='duplicate')
        binding.policy.info = replace(binding.info, filters=(*binding.info.filters, capability))
        bindings[-1] = replace(binding, info=binding.policy.info)
    elif problem == 'undefined-option':
        capability = replace(binding.info.filters[0], option_names=('--undefined',))
        binding.policy.info = replace(binding.info, filters=(capability,))
        bindings[-1] = replace(binding, info=binding.policy.info)
    elif problem == 'output':
        bindings[-1] = replace(binding, info=replace(binding.info, columns=('incorrect',)))
    else:
        bindings = [binding]
        selected = 'jungol'
    with pytest.warns(RuntimeWarning, match='플랫폼 구성'):
        registry = platforms.PlatformRegistry(bindings)
    monkeypatch.setattr(platforms, 'REGISTRY', registry)
    result = runner.invoke(cli.app, ['--platform', selected, 'list'])
    assert result.exit_code == 1, result.output
    assert '플랫폼 구성' in result.stderr and selected in result.stderr
    assert result.stdout == '' and calls == []
    if problem == 'missing-default':
        result = runner.invoke(cli.app, ['list'])
        assert result.exit_code == 1 and result.stdout == '' and calls == []
    unaffected = 'test-platform' if problem == 'missing-default' else 'jungol'
    result = runner.invoke(cli.app, ['--platform', unaffected, 'list', '--help'])
    assert result.exit_code == 0 and calls == []


@pytest.mark.parametrize('command', ['list', 'recommend'])
@pytest.mark.parametrize('value,valid', [('150..160', True), ('99..150', False), ('150..201', False),
                                       ('not-a-score', False)])
def test_selected_platform_uses_its_own_difficulty_rules(synthetic_platform, command, value, valid):
    _, calls = synthetic_platform
    result = runner.invoke(cli.app, ['--platform', 'test-platform', command, '--tier', value],
                           terminal_width=240)
    if valid:
        assert result.exit_code == 0, result.output
        assert '합성 난도 150..160 점수' in result.stdout
        assert 'factory' in calls and 'collected' in calls
    else:
        assert result.exit_code == 2 and result.stdout == ''
        assert '--tier' in result.stderr and 'test-platform' in result.stderr and '100~200' in result.stderr
        assert len(calls) == 1 and calls[0][0] == 'parse'


def test_selected_platform_sort_error_names_platform(synthetic_platform):
    _, calls = synthetic_platform
    result = runner.invoke(cli.app, ['--platform', 'test-platform', 'list', '--sort', 'accepted'], terminal_width=240)
    assert result.exit_code == 2 and result.stdout == ''
    assert '--sort' in result.stderr and 'test-platform' in result.stderr
    message = ' '.join(result.stderr.replace('│', '').split())
    assert 'id, difficulty' in message and len(calls) == 1 and calls[0][0] == 'parse'


@pytest.mark.parametrize('command', ['list', 'recommend'])
def test_help_uses_selected_rules_without_global_mutation(synthetic_platform, command):
    _, calls = synthetic_platform
    synthetic = runner.invoke(cli.app, ['--platform', 'test-platform', command, '--help'], terminal_width=240)
    jungol = runner.invoke(cli.app, ['--platform', 'jungol', command, '--help'], terminal_width=240)
    repeated = runner.invoke(cli.app, ['--platform', 'test-platform', command, '--help'], terminal_width=240)
    assert synthetic.exit_code == jungol.exit_code == repeated.exit_code == 0
    message = ' '.join(synthetic.stdout.split())
    assert 'test-platform' in message and '합성 난도' in message and '점수' in message and '100~200' in message
    assert '지원하지 않는 필터' in message and '--accepted' in message and '--status' in message
    assert 'B5~R1' not in message and '1~30' not in message and '사이트 검색 조건' not in message
    assert '중복 정답 제출' not in message and '더 불러오기' not in message
    assert synthetic.stdout == repeated.stdout and '100~200' not in jungol.stdout
    assert 'jungol' in jungol.stdout and 'B5~R1' in jungol.stdout
    root = runner.invoke(cli.app, ['--help'], terminal_width=240)
    version = runner.invoke(cli.app, ['--platform', 'test-platform', '--version'])
    assert root.exit_code == version.exit_code == 0
    assert 'test-platform' in root.stdout and 'jungol' in root.stdout
    assert calls == []
