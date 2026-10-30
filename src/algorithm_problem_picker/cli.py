"""jpick commands and dependency composition."""

from importlib.metadata import version
import webbrowser
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from . import platforms
from .jungol_models import SearchCriteria, Status
from .models import Order, Progress, RawFilterInput, Result
from .ports import FilterInputError, PlatformPolicy, SourceError
from .service import Picker

app = typer.Typer(invoke_without_command=True, no_args_is_help=True,
                  help="JUNGOL 문제 검색·추천. 티어 B5=Bronze V ~ R1=Ruby I (기존 1~30도 지원).")
out = Console(highlight=False, markup=False)
err = Console(stderr=True, highlight=False, markup=False)

TierOption = Annotated[str | None, typer.Option(
    help="사이트 검색 조건인 티어 경계 B5~R1, 대소문자 무관 (기존 1~30도 지원, 포함). 표시 티어는 범위 밖일 수 있습니다.")]
RateOption = Annotated[str | None, typer.Option(help="정답률 0~100 소수, % 없이 (포함)")]
AcceptedOption = Annotated[int | None, typer.Option(min=0, help="정답 제출 수, 동일 사용자의 중복 정답 제출 포함 (경계 포함)")]
StatusOption = Annotated[Status, typer.Option(help="공개 기준 사용자 풀이 여부")]
UserOption = Annotated[str, typer.Option("--user", help="정확한 공개 핸들. @ 접두사 허용")]


def _single_range(value: list[str]) -> list[str]:
    if len(value) > 1:
        raise typer.BadParameter("범위 옵션은 한 번만 지정하세요.")
    return value


TierRangeOption = Annotated[list[str], typer.Option(callback=_single_range, metavar="MIN..MAX",
    help="사이트 검색 조건 B5~R1, 대소문자 무관 (기존 1~30도 지원). 예: S5..G1, G5.., ..S1. 표시 티어는 범위 밖일 수 있습니다.")]
RateRangeOption = Annotated[list[str], typer.Option(callback=_single_range, metavar="MIN..MAX",
    help="정답률 0~100 소수, % 없이")]
AcceptedRangeOption = Annotated[list[str], typer.Option(callback=_single_range, metavar="MIN..MAX",
    help="정답 제출 수 0 이상 정수, 동일 사용자의 중복 정답 제출 포함")]


_LISTING_HELP = (
    "범위 옵션은 MIN..MAX, MIN.., ..MAX 형태로 양 끝 포함이며 한 번만 지정합니다. "
    "기존 --min-*/--max-* 옵션은 유지하며 같은 지표의 범위 옵션과 혼용할 수 없습니다. "
    "명시적인 빈 통계는 미제공이며 실제 0과 다릅니다. 해당 지표 필터가 있으면 제외하고 없으면 미확인으로 표시합니다. "
    "더 불러오기 버튼이 없으면 현재 목록으로 완료하며 이후 지연 반영은 보장하지 않습니다."
)


def _parse_filters(raw: RawFilterInput) -> SearchCriteria:
    try:
        return platforms.REGISTRY[platforms.DEFAULT_PLATFORM].policy.parse_filters(raw)
    except FilterInputError as error:
        raise typer.BadParameter(str(error), param_hint=error.option or None) from error


def _reject_min_solvers(value: str | None) -> None:
    if value is not None:
        _parse_filters(RawFilterInput({'--min-solvers': value}))


def _reject_max_solvers(value: str | None) -> None:
    if value is not None:
        _parse_filters(RawFilterInput({'--max-solvers': value}))


@app.callback()
def main(show_version: bool = typer.Option(False, "--version", is_eager=True)) -> None:
    if show_version:
        typer.echo(version("algorithm-problem-picker"))
        raise typer.Exit()


def _criteria(min_tier, max_tier, min_rate, max_rate, min_accepted, max_accepted, status, user,
              *, tier: list[str], rate: list[str], accepted: list[str]) -> SearchCriteria:
    boundaries = {
        '--min-tier': min_tier, '--max-tier': max_tier,
        '--min-rate': min_rate, '--max-rate': max_rate,
        '--min-accepted': min_accepted, '--max-accepted': max_accepted,
        '--status': status, '--user': user,
    }
    values = {option: str(value) for option, value in boundaries.items() if value is not None}
    values.update({'--tier': tuple(tier), '--rate': tuple(rate), '--accepted': tuple(accepted)})
    return _parse_filters(RawFilterInput(values))


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


def _run(criteria: SearchCriteria, requested: int, recommend: bool = False,
         sort: str = 'id', order: Order = Order.ASC) -> None:
    binding = platforms.REGISTRY[platforms.DEFAULT_PLATFORM]
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
        err.print(f"조회 실패: {error}\n입력 핸들·접속 상태와 정올 공개 화면을 확인하세요.")
        raise typer.Exit(1)


@app.command("list", help="전체 후보를 조회합니다. 티어는 사이트 검색 조건이며 표시 티어는 요청 범위 밖일 수 있습니다.",
             epilog=_LISTING_HELP)
def list_command(
    tier: TierRangeOption = [], rate: RateRangeOption = [], accepted: AcceptedRangeOption = [],
    min_tier: TierOption = None, max_tier: TierOption = None,
    min_rate: RateOption = None, max_rate: RateOption = None,
    min_accepted: AcceptedOption = None, max_accepted: AcceptedOption = None,
    min_solvers: Annotated[str | None, typer.Option(hidden=True, is_eager=True, callback=_reject_min_solvers)] = None,
    max_solvers: Annotated[str | None, typer.Option(hidden=True, is_eager=True, callback=_reject_max_solvers)] = None,
    status: StatusOption = Status.ALL, user: UserOption = "",
    sort: Annotated[str, typer.Option(help="전체 적격 후보 정렬: id, difficulty, rate, accepted, random")] = 'id',
    order: Annotated[Order, typer.Option(help="정렬 방향. 지표 동점은 번호 오름차순")] = Order.ASC,
    limit: Annotated[int, typer.Option(min=1, help="전체 필터 후 표시 개수")] = 20,
) -> None:
    try:
        sort_key = platforms.REGISTRY[platforms.DEFAULT_PLATFORM].policy.validate_list_options(sort, order)
    except FilterInputError as error:
        raise typer.BadParameter(str(error), param_hint=error.option or None) from error
    criteria = _criteria(min_tier, max_tier, min_rate, max_rate, min_accepted, max_accepted, status, user,
                         tier=tier, rate=rate, accepted=accepted)
    _run(criteria, limit, sort=sort_key, order=order)


@app.command(help="전체 적격 후보에서 중복 없이 추천. 티어는 사이트 검색 조건이며 표시 티어는 요청 범위 밖일 수 있습니다.",
             epilog=_LISTING_HELP)
def recommend(
    tier: TierRangeOption = [], rate: RateRangeOption = [], accepted: AcceptedRangeOption = [],
    min_tier: TierOption = None, max_tier: TierOption = None,
    min_rate: RateOption = None, max_rate: RateOption = None,
    min_accepted: AcceptedOption = None, max_accepted: AcceptedOption = None,
    min_solvers: Annotated[str | None, typer.Option(hidden=True, is_eager=True, callback=_reject_min_solvers)] = None,
    max_solvers: Annotated[str | None, typer.Option(hidden=True, is_eager=True, callback=_reject_max_solvers)] = None,
    status: StatusOption = Status.ALL, user: UserOption = "",
    count: Annotated[int, typer.Option(min=1, help="추천 개수")] = 1,
) -> None:
    criteria = _criteria(min_tier, max_tier, min_rate, max_rate, min_accepted, max_accepted, status, user,
                         tier=tier, rate=rate, accepted=accepted)
    _run(criteria, count, recommend=True)


@app.command("open", help="명시한 문제 번호만 기본 브라우저로 엽니다.")
def open_command(ids: Annotated[list[int], typer.Argument(min=1, help="양의 정수 문제 번호 (한 개 이상)")]) -> None:
    failed: list[str] = []
    try:
        links = platforms.REGISTRY[platforms.DEFAULT_PLATFORM].policy.problem_links(tuple(map(str, ids)))
    except FilterInputError as error:
        raise typer.BadParameter(str(error), param_hint=error.option or None) from error
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
