"""algo-pick commands and dependency composition."""

from importlib.metadata import version
import webbrowser
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from . import platforms
from .models import FILTER_OPTION_NAMES, RANGE_FILTER_OPTIONS, Order, Progress, RawFilterInput, Result
from .ports import FilterInputError, PlatformPolicy, SourceError
from .service import Picker

app = typer.Typer(name='algo-pick', invoke_without_command=True, no_args_is_help=True,
                  help="문제 검색·추천. --platform은 명령 앞에 지정합니다.")
out = Console(highlight=False, markup=False)
err = Console(stderr=True, highlight=False, markup=False)

TierOption = Annotated[str | None, typer.Option(help="난이도 경계. 허용 값과 의미는 선택 플랫폼의 지원 정보 참고")]
RateOption = Annotated[str | None, typer.Option(help="정답률 경계. 선택 플랫폼의 단위·허용 값 참고")]
AcceptedOption = Annotated[str | None, typer.Option(help="정답 제출 수 경계. 선택 플랫폼의 지원 정보 참고")]
StatusOption = Annotated[str, typer.Option(help="사용자 풀이 조건. 선택 플랫폼의 지원 정보 참고")]
UserOption = Annotated[str, typer.Option("--user", help="사용자 식별자. 선택 플랫폼의 지원 정보 참고")]


TierRangeOption = Annotated[list[str], typer.Option(metavar="MIN..MAX",
    help="난이도 범위. 표기와 허용 값은 선택 플랫폼의 지원 정보 참고")]
RateRangeOption = Annotated[list[str], typer.Option(metavar="MIN..MAX",
    help="정답률 범위. 표기와 허용 값은 선택 플랫폼의 지원 정보 참고")]
AcceptedRangeOption = Annotated[list[str], typer.Option(metavar="MIN..MAX",
    help="정답 제출 수 범위. 표기와 허용 값은 선택 플랫폼의 지원 정보 참고")]


def _selected(ctx: typer.Context) -> platforms.PlatformBinding:
    assert isinstance(ctx.obj, platforms.PlatformBinding)
    return ctx.obj


def _input_error(binding: platforms.PlatformBinding, error: FilterInputError) -> typer.BadParameter:
    return typer.BadParameter(f'{binding.info.display_name}({binding.info.key}): {error}',
                              param_hint=error.option or None)


def _show_help(ctx: typer.Context, value: bool) -> None:
    if not value or ctx.resilient_parsing:
        return
    typer.echo(ctx.get_help())
    if ctx.parent is None:
        typer.echo(f'기본 플랫폼: {platforms.DEFAULT_PLATFORM}. 선택 가능한 플랫폼: '
                  + ', '.join(platforms.REGISTRY) + '.')
    else:
        binding = _selected(ctx)
        typer.echo(f'플랫폼: {binding.info.display_name}({binding.info.key})')
        if ctx.command.name in {'list', 'recommend'}:
            supported: set[str] = set()
            typer.echo('지원 필터:')
            for capability in binding.info.filters:
                if ctx.command.name not in capability.commands:
                    continue
                supported.update(capability.option_names)
                unit = f' (단위: {capability.unit})' if capability.unit else ''
                typer.echo(', '.join(capability.option_names) + ': ' + capability.meaning + unit)
                typer.echo('  허용 값: ' + capability.value_help)
                typer.echo('  조합: ' + capability.combination_help)
            visible = {option for parameter in ctx.command.params if not parameter.hidden
                       for option in parameter.opts if option in FILTER_OPTION_NAMES}
            unsupported = visible - supported
            if unsupported:
                typer.echo('지원하지 않는 필터: ' + ', '.join(sorted(unsupported)))
            typer.echo('정렬: ' + binding.info.sort_help)
            for note in binding.info.help_notes:
                typer.echo(note)
    raise typer.Exit()


HelpOption = Annotated[bool, typer.Option('--help', callback=_show_help, is_eager=True, expose_value=False,
                                        help='선택 플랫폼의 지원 정보와 도움말 표시')]


def _parse_filters(ctx: typer.Context, raw: RawFilterInput):
    binding = _selected(ctx)
    supported = {option for capability in binding.info.filters if ctx.command.name in capability.commands
                 for option in capability.option_names}
    retired = {entry.option_name for entry in binding.info.retired_options}
    unsupported = raw.supplied_options - supported - retired
    if unsupported:
        err.print(f'{binding.info.display_name}({binding.info.key}): 지원하지 않는 필터: '
                  + ', '.join(sorted(unsupported)))
        raise typer.Exit(2)
    try:
        return binding.policy.parse_filters(raw)
    except FilterInputError as error:
        raise _input_error(binding, error) from error


@app.callback()
def main(
    ctx: typer.Context,
    platform: str = typer.Option(platforms.DEFAULT_PLATFORM, '--platform', help='명령 앞에 지정하는 플랫폼'),
    show_version: bool = typer.Option(False, "--version", is_eager=True),
    show_help: HelpOption = False,
) -> None:
    if show_version:
        typer.echo(version("algorithm-problem-picker"))
        raise typer.Exit()
    try:
        binding = platforms.REGISTRY.get(platform)
    except platforms.PlatformConfigurationError as error:
        err.print(str(error))
        raise typer.Exit(1) from error
    if binding is None:
        raise typer.BadParameter(f'{platform!r}: 선택 가능한 플랫폼: ' + ', '.join(platforms.REGISTRY),
                                 param_hint='--platform')
    ctx.obj = binding


def _criteria(ctx: typer.Context):
    values: dict[str, str | tuple[str, ...]] = {}
    supplied: set[str] = set()
    for option in FILTER_OPTION_NAMES:
        parameter = option[2:].replace('-', '_')
        source = ctx.get_parameter_source(parameter)
        assert source is not None
        value = ctx.params[parameter]
        if option in RANGE_FILTER_OPTIONS:
            assert isinstance(value, tuple)
            values[option] = tuple(value)
        elif value is not None:
            assert isinstance(value, str)
            values[option] = value
        if source.name == 'COMMANDLINE':
            supplied.add(option)
    return _parse_filters(ctx, RawFilterInput(values, frozenset(supplied)))


def _progress(progress: Progress) -> None:
    err.print(f"{progress.stage} · 수집 {progress.collected} · Ctrl+C 취소")


def _present(result: Result, policy: PlatformPolicy, recommend: bool = False) -> None:
    table = Table(*policy.columns, box=None, min_width=115)
    table.columns[-1].no_wrap = True
    table.columns[-1].overflow = 'ignore'
    table.columns[1].overflow = 'fold'
    for problem in result.problems:
        row = policy.format_row(problem)
        assert len(row) == len(policy.columns)
        table.add_row(*row)
    if result.problems:
        out.print(table, soft_wrap=True)
    else:
        out.print("조건에 맞는 문제가 없습니다.")
    out.print("조건: " + policy.format_conditions(result.criteria, result.user))
    out.print(f"조회 {result.fetched_count} · 적격 {result.eligible_count} · 요청 {result.requested_count} · "
              f"{'반환' if recommend else '표시'} {result.returned_count}")
    if recommend:
        out.print(f"부족 {result.shortage}개")
    out.print(f"조회 시각: {result.started_at.astimezone().isoformat()} ~ {result.finished_at.astimezone().isoformat()}")
    for note in policy.observation_notes:
        out.print(note)
    if result.omitted_unknown_count:
        err.print(f"필터 지표 미제공으로 {result.omitted_unknown_count}개 제외")


def _run(binding: platforms.PlatformBinding, criteria, requested: int, recommend: bool = False,
         sort: str = 'id', order: Order = Order.ASC) -> None:
    try:
        err.print("조회 시작 · Ctrl+C 취소")
        with binding.source_factory(err.print) as source:
            picker = Picker(binding.policy, source, report=_progress)
            result = picker.recommend(criteria, count=requested) if recommend else picker.list(
                criteria, limit=requested, sort=sort, order=order)
        _present(result, binding.policy, recommend=recommend)
    except KeyboardInterrupt:
        err.print("취소했습니다. 조회용 브라우저를 정리했습니다.")
        raise typer.Exit(130)
    except SourceError as error:
        err.print(f"조회 실패: {error}\n입력 핸들·접속 상태와 {binding.info.display_name} 공개 화면을 확인하세요.")
        raise typer.Exit(1)


@app.command("list", help="전체 후보를 조회합니다.")
def list_command(
    ctx: typer.Context,
    tier: TierRangeOption = [], rate: RateRangeOption = [], accepted: AcceptedRangeOption = [],
    min_tier: TierOption = None, max_tier: TierOption = None,
    min_rate: RateOption = None, max_rate: RateOption = None,
    min_accepted: AcceptedOption = None, max_accepted: AcceptedOption = None,
    min_solvers: Annotated[str | None, typer.Option(hidden=True)] = None,
    max_solvers: Annotated[str | None, typer.Option(hidden=True)] = None,
    status: StatusOption = 'all', user: UserOption = "",
    sort: Annotated[str, typer.Option(help="전체 적격 후보 정렬. 선택 플랫폼의 지원 정보 참고")] = 'id',
    order: Annotated[Order, typer.Option(help="정렬 방향. 동점 처리는 선택 플랫폼의 규칙 적용")] = Order.ASC,
    limit: Annotated[int, typer.Option(min=1, help="전체 필터 후 표시 개수")] = 20,
    show_help: HelpOption = False,
) -> None:
    criteria = _criteria(ctx)
    try:
        sort_key = _selected(ctx).policy.validate_list_options(sort, order)
    except FilterInputError as error:
        raise _input_error(_selected(ctx), error) from error
    _run(_selected(ctx), criteria, limit, sort=sort_key, order=order)


@app.command(help="전체 적격 후보에서 중복 없이 추천합니다.")
def recommend(
    ctx: typer.Context,
    tier: TierRangeOption = [], rate: RateRangeOption = [], accepted: AcceptedRangeOption = [],
    min_tier: TierOption = None, max_tier: TierOption = None,
    min_rate: RateOption = None, max_rate: RateOption = None,
    min_accepted: AcceptedOption = None, max_accepted: AcceptedOption = None,
    min_solvers: Annotated[str | None, typer.Option(hidden=True)] = None,
    max_solvers: Annotated[str | None, typer.Option(hidden=True)] = None,
    status: StatusOption = 'all', user: UserOption = "",
    count: Annotated[int, typer.Option(min=1, help="추천 개수")] = 1,
    show_help: HelpOption = False,
) -> None:
    criteria = _criteria(ctx)
    _run(_selected(ctx), criteria, count, recommend=True)


@app.command("open", help="명시한 문제 번호만 기본 브라우저로 엽니다.")
def open_command(ctx: typer.Context,
                 ids: Annotated[list[str], typer.Argument(metavar='ID', help="문제 번호 (한 개 이상)")],
                 show_help: HelpOption = False) -> None:
    failed: list[str] = []
    try:
        links = _selected(ctx).policy.problem_links(ids)
    except FilterInputError as error:
        raise _input_error(_selected(ctx), error) from error
    for link in links:
        url = link.url
        out.print(url, soft_wrap=True)
        try:
            opened = webbrowser.open(url)
        except (webbrowser.Error, OSError):
            opened = False
        if not opened:
            failed.append(link.label)
    if failed:
        err.print("기본 브라우저 전달 실패: " + ", ".join(map(str, failed)) + ". 출력된 링크를 직접 열어주세요.")
        raise typer.Exit(1)
