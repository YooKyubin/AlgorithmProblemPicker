import pytest
from typer.testing import CliRunner

from algorithm_problem_picker import cli
from algorithm_problem_picker.models import CompletedListing
from algorithm_problem_picker.ports import SourceAccessError, SourceSchemaError, SourceCompletenessError, UserResolutionError

runner = CliRunner()


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

        def collect(self, criteria, user):
            calls.append(criteria)
            return CompletedListing(())

    monkeypatch.setattr(cli, 'JungolSource', Source)
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
    from algorithm_problem_picker.models import UserReference, now
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
    for args in (['--help'], ['--version'], ['list','--help'], ['recommend','--help']):
        assert runner.invoke(cli.app, args).exit_code == 0
    assert calls == []


@pytest.mark.parametrize('command', ['list','recommend'])
def test_tier_help_explains_site_search(source_factory, command):
    _, calls = source_factory
    result = runner.invoke(cli.app,[command,'--help'],terminal_width=180)
    assert result.exit_code == 0 and not calls
    message = ' '.join(result.stdout.replace('│','').split())
    assert '사이트 검색 조건' in message
    assert '표시 티어' in message and '범위 밖' in message
    assert '미제공' in message and '실제 0' in message and '미확인' in message
    assert '버튼이 없으면 현재 목록' in message and '지연 반영' in message


@pytest.mark.parametrize('command', ['list','recommend'])
@pytest.mark.parametrize('bounds', [['--min-tier','9','--max-tier','13'],['--min-tier','9'],['--max-tier','7']])
def test_site_tier_bounds_and_observed_tier_output(source_factory, monkeypatch, problem, command, bounds):
    from rich.console import Console
    from algorithm_problem_picker.models import Rated
    source, calls = source_factory
    monkeypatch.setattr(source,'collect',lambda *args:CompletedListing((problem(tier=Rated(8)),)))
    monkeypatch.setattr(cli,'out',Console(width=180,highlight=False,markup=False))
    result = runner.invoke(cli.app,[command,*bounds])
    assert result.exit_code == 0, result.exception
    assert '조회 1' in result.stdout and '적격 1' in result.stdout
    row = next(line for line in result.stdout.splitlines() if line.lstrip().startswith('1000 '))
    assert row.split()[:4] == ['1000','문제','1000','8']
    for option, value in zip(bounds[::2],bounds[1::2]):
        assert option[2:].replace('-','_')+'='+value in result.stdout
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
@pytest.mark.parametrize('option', ['--min-rate','--max-rate','--min-accepted','--max-accepted'])
def test_missing_statistic_filter_outputs_normal_empty_result(source_factory, monkeypatch, problem, command, option):
    from algorithm_problem_picker.models import Unavailable
    source, calls = source_factory
    items = (problem(rate=Unavailable(),accepted=Unavailable()),
             problem(1001,rate=Unavailable(),accepted=Unavailable()))
    monkeypatch.setattr(source,'collect',lambda *args:CompletedListing(items+items[:1]))
    result = runner.invoke(cli.app,[command,option,'0']+(['--count','3'] if command == 'recommend' else []))
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


def test_recommend_default_and_shortage(source_factory):
    result = runner.invoke(cli.app, ['recommend'])
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


@pytest.mark.parametrize('args', [[],['0'],['-1'],['1.5']])
def test_open_invalid_before_source(source_factory, args):
    _, calls = source_factory
    assert runner.invoke(cli.app, ['open', *args]).exit_code == 2
    assert not calls


@pytest.mark.parametrize('fail_ids', [set(), {1001}, {1000,1001}])
def test_open_unique_order_and_failure_links(source_factory, monkeypatch, fail_ids):
    _, source_calls = source_factory
    opened = []
    def open_url(url):
        opened.append(url)
        return int(url.rsplit('/',1)[1]) not in fail_ids
    monkeypatch.setattr(cli.webbrowser, 'open', open_url)
    result = runner.invoke(cli.app, ['open','1000','1000','1001'])
    assert result.exit_code == (1 if fail_ids else 0)
    assert opened == ['https://jungol.co.kr/problem/1000','https://jungol.co.kr/problem/1001']
    assert all(url in result.stdout for url in opened)
    assert all(str(id) in result.stderr for id in fail_ids)
    assert not source_calls
