import pytest
from typer.testing import CliRunner

from algorithm_problem_picker import cli
from algorithm_problem_picker.models import CompletedListing
from algorithm_problem_picker.ports import SourceAccessError, UserResolutionError

runner = CliRunner()


@pytest.fixture
def source_factory(monkeypatch):
    calls = []

    class Source:
        def __init__(self, report):
            pass

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
    ['--min-solvers','-1'], ['--status','unsolved'], ['--user','Name'],
    ['--limit','1.2'], ['--min-solvers','20','--max-solvers','10'], ['--user','@']])
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
        '--min-solvers','0','--max-solvers','100'])
    assert result.exit_code == 0, result.exception
    criteria = calls[1]
    assert criteria.min_rate == Decimal('47.45') and criteria.max_rate == Decimal('50')
    assert criteria.min_tier == 1 and criteria.max_tier == 30
    assert criteria.min_solvers == 0 and criteria.max_solvers == 100
    assert criteria.status == 'solved' and criteria.user_handle == 'Case'
    assert '@Case' in result.stdout


@pytest.mark.parametrize('error,code', [(SourceAccessError('access failed'),1),
    (UserResolutionError('unknown user'),1), (KeyboardInterrupt(),130)])
def test_list_failure_no_partial_output(error, code, source_factory, monkeypatch):
    source, _ = source_factory
    def fail(*args):
        raise error
    monkeypatch.setattr(source, 'collect', fail)
    result = runner.invoke(cli.app, ['list'])
    assert result.exit_code == code
    assert '적격' not in result.stdout
    assert result.stderr


def test_help_and_version_do_not_start_source(source_factory):
    _, calls = source_factory
    for args in (['--help'], ['--version'], ['list','--help']):
        assert runner.invoke(cli.app, args).exit_code == 0
    assert calls == []


def test_recommend_default_and_shortage(source_factory):
    result = runner.invoke(cli.app, ['recommend'])
    assert result.exit_code == 0, result.exception
    assert '요청 1' in result.stdout and '반환 0' in result.stdout and '부족 1' in result.stdout


@pytest.mark.parametrize('count', ['0','-1','1.5'])
def test_recommend_count_validation(source_factory, count):
    _, calls = source_factory
    assert runner.invoke(cli.app, ['recommend','--count',count]).exit_code == 2
    assert not calls


@pytest.mark.parametrize('error,code', [(SourceAccessError('failed'),1),(KeyboardInterrupt(),130)])
def test_recommend_failure(error, code, source_factory, monkeypatch):
    source, _ = source_factory
    def fail(*args):
        raise error
    monkeypatch.setattr(source, 'collect', fail)
    result = runner.invoke(cli.app, ['recommend'])
    assert result.exit_code == code and '부족' not in result.stdout


def test_random_desc_invalid_before_source(source_factory):
    _, calls = source_factory
    result = runner.invoke(cli.app, ['list','--sort','random','--order','desc'])
    assert result.exit_code == 2 and not calls


@pytest.mark.parametrize('sort', ['id','difficulty','rate','solvers','random'])
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
