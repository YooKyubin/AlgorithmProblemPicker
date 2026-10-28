"""jpick commands and dependency composition."""

from importlib.metadata import version
from decimal import Decimal, InvalidOperation
import re
import webbrowser
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from .jungol import JungolSource
from .models import Known, Order, Progress, Rated, Result, SearchCriteria, SortKey, Status, Unrated
from .ports import SourceError
from .service import Picker

app = typer.Typer(invoke_without_command=True, no_args_is_help=True,
                  help="JUNGOL 문제 검색·추천. 티어 B5=Bronze V ~ R1=Ruby I (기존 1~30도 지원).")
out = Console(highlight=False, markup=False)
err = Console(stderr=True, highlight=False, markup=False)

_TIER_NAMES = tuple(f'{group}{level}' for group in 'BSGPDR' for level in range(5, 0, -1))
_TIER_VALUES = {name: value for value, name in enumerate(_TIER_NAMES, start=1)}

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


def _parse_tier(value: str, option: str) -> int:
    name = value.upper()
    if name in _TIER_VALUES:
        return _TIER_VALUES[name]
    if re.fullmatch(r'[0-9]+', value) and 1 <= int(value) <= 30:
        return int(value)
    raise typer.BadParameter("티어 경계는 B/S/G/P/D/R + 1~5 또는 정수 1~30이어야 합니다. "
                             "예: B5, S1, G5, R1", param_hint=option)


def _format_tier(value: int) -> str:
    return _TIER_NAMES[value - 1]


def _parse_range(value: str, metric: str) -> tuple[int | Decimal | None, int | Decimal | None]:
    option = f'--{metric}'
    parts = value.split('..')
    if len(parts) != 2 or not any(parts):
        raise typer.BadParameter("범위는 MIN..MAX, MIN.., ..MAX 형태로 지정하세요. 예: 1..10", param_hint=option)
    if metric == 'tier':
        lower, upper = (_parse_tier(part, option) if part else None for part in parts)
    else:
        pattern = r'[0-9]+(?:\.[0-9]+)?' if metric == 'rate' else r'[0-9]+'
        if any(part and not re.fullmatch(pattern, part) for part in parts):
            raise typer.BadParameter("범위는 MIN..MAX, MIN.., ..MAX 형태로 지정하세요. 예: 1..10", param_hint=option)
        convert = Decimal if metric == 'rate' else int
        lower, upper = (convert(part) if part else None for part in parts)
        maximum = 100 if metric == 'rate' else None
        if any(bound is not None and (bound < 0 or (maximum is not None and bound > maximum))
               for bound in (lower, upper)):
            allowed = f"0~{maximum}" if maximum is not None else "0 이상"
            raise typer.BadParameter(f"경계는 {allowed}이어야 합니다.", param_hint=option)
    if lower is not None and upper is not None and lower > upper:
        raise typer.BadParameter("하한은 상한 이하여야 합니다.", param_hint=option)
    return lower, upper


def _range_bounds(values: list[str], lower, upper, metric: str) -> tuple:
    if not values:
        if metric == 'tier':
            return (_parse_tier(lower, '--min-tier') if lower is not None else None,
                    _parse_tier(upper, '--max-tier') if upper is not None else None)
        return lower, upper
    option = f'--{metric}'
    conflicts = [f'--{name}-{metric}' for name, value in (('min', lower), ('max', upper)) if value is not None]
    if conflicts:
        raise typer.BadParameter(f"{', '.join(conflicts)}와 함께 지정할 수 없습니다. 한 가지 표기만 사용하세요.",
                                 param_hint=option)
    return _parse_range(values[0], metric)

_LISTING_HELP = (
    "범위 옵션은 MIN..MAX, MIN.., ..MAX 형태로 양 끝 포함이며 한 번만 지정합니다. "
    "기존 --min-*/--max-* 옵션은 유지하며 같은 지표의 범위 옵션과 혼용할 수 없습니다. "
    "명시적인 빈 통계는 미제공이며 실제 0과 다릅니다. 해당 지표 필터가 있으면 제외하고 없으면 미확인으로 표시합니다. "
    "더 불러오기 버튼이 없으면 현재 목록으로 완료하며 이후 지연 반영은 보장하지 않습니다."
)


def _reject_legacy(value: str | None, replacement: str) -> None:
    if value is not None:
        raise typer.BadParameter(f"{replacement}를 사용하세요. 맞힌 사람 수에서 정답 제출 수로 변경되었습니다. "
                                 "동일 사용자의 중복 정답 제출을 포함하므로 같은 숫자라도 결과가 달라질 수 있습니다.")


def _reject_min_solvers(value: str | None) -> None:
    _reject_legacy(value, '--min-accepted')


def _reject_max_solvers(value: str | None) -> None:
    _reject_legacy(value, '--max-accepted')


@app.callback()
def main(show_version: bool = typer.Option(False, "--version", is_eager=True)) -> None:
    if show_version:
        typer.echo(version("algorithm-problem-picker"))
        raise typer.Exit()


def _criteria(min_tier, max_tier, min_rate, max_rate, min_accepted, max_accepted, status, user,
              *, tier: list[str], rate: list[str], accepted: list[str]) -> SearchCriteria:
    min_tier, max_tier = _range_bounds(tier, min_tier, max_tier, 'tier')
    min_rate, max_rate = _range_bounds(rate, min_rate, max_rate, 'rate')
    min_accepted, max_accepted = _range_bounds(accepted, min_accepted, max_accepted, 'accepted')
    try:
        return SearchCriteria(min_tier, max_tier,
                              Decimal(min_rate) if min_rate is not None else None,
                              Decimal(max_rate) if max_rate is not None else None,
                              min_accepted, max_accepted, status, user)
    except (ValueError, InvalidOperation) as error:
        raise typer.BadParameter(str(error)) from error


def _progress(progress: Progress) -> None:
    err.print(f"{progress.stage} · 수집 {progress.collected} · Ctrl+C 취소")


def _metric(value, suffix="") -> str:
    return f"{value.value}{suffix}" if isinstance(value, Known) else "미확인"


def _present(result: Result, recommend: bool = False) -> None:
    table = Table("번호", "제목", "난이도", "정답률", "정답 제출 수", "링크", box=None, min_width=115)
    table.columns[-1].no_wrap = True
    table.columns[-1].overflow = 'ignore'
    table.columns[1].overflow = 'fold'
    for problem in result.problems:
        tier = _format_tier(problem.tier.value) if isinstance(problem.tier, Rated) else (
            "미정" if isinstance(problem.tier, Unrated) else "미확인")
        table.add_row(str(problem.id), problem.title, tier, _metric(problem.pass_rate, "%"),
                      _metric(problem.accepted_count), problem.url)
    if result.problems:
        out.print(table, soft_wrap=True)
    else:
        out.print("조건에 맞는 문제가 없습니다.")
    conditions = []
    for name in ("min_tier", "max_tier", "min_rate", "max_rate", "min_accepted", "max_accepted"):
        value = getattr(result.criteria, name)
        if value is not None:
            if name in ('min_tier', 'max_tier'):
                value = _format_tier(value)
            conditions.append(f"{name}={value}")
    conditions.append(f"status={result.criteria.status}")
    if result.user:
        conditions.append(f"기준 사용자 @{result.user.handle}")
    out.print("조건: " + ", ".join(conditions))
    out.print(f"조회 {result.fetched_count} · 적격 {result.eligible_count} · 요청 {result.requested_count} · "
              f"{'반환' if recommend else '표시'} {result.returned_count}")
    if recommend:
        out.print(f"부족 {result.shortage}개")
    out.print(f"조회 시각: {result.started_at.astimezone().isoformat()} ~ {result.finished_at.astimezone().isoformat()}")
    out.print("티어·정답률·정답 제출 수는 각 목록 관측 시점의 값입니다. 정답 제출 수는 동일 사용자의 중복 정답 제출을 포함합니다.")
    if result.omitted_unknown_count:
        err.print(f"필터 지표 미제공으로 {result.omitted_unknown_count}개 제외")


def _run(criteria: SearchCriteria, requested: int, recommend: bool = False,
         sort: SortKey = SortKey.ID, order: Order = Order.ASC) -> None:
    try:
        err.print("조회 시작 · Ctrl+C 취소")
        with JungolSource(report=err.print) as source:
            picker = Picker(source, report=_progress)
            result = picker.recommend(criteria, count=requested) if recommend else picker.list(
                criteria, limit=requested, sort=sort, order=order)
        _present(result, recommend=recommend)
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
    _reject_legacy('solvers' if sort == 'solvers' else None, '--sort accepted')
    try:
        sort_key = SortKey(sort)
    except ValueError as error:
        raise typer.BadParameter('정렬 기준: id, difficulty, rate, accepted, random', param_hint='--sort') from error
    criteria = _criteria(min_tier, max_tier, min_rate, max_rate, min_accepted, max_accepted, status, user,
                         tier=tier, rate=rate, accepted=accepted)
    if sort_key == SortKey.RANDOM and order == Order.DESC:
        raise typer.BadParameter("random과 --order desc를 함께 지정할 수 없습니다.")
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
    failed: list[int] = []
    for id in dict.fromkeys(ids):
        url = f"https://jungol.co.kr/problem/{id}"
        out.print(url, soft_wrap=True)
        try:
            opened = webbrowser.open(url)
        except (webbrowser.Error, OSError):
            opened = False
        if not opened:
            failed.append(id)
    if failed:
        err.print("기본 브라우저 전달 실패: " + ", ".join(map(str, failed)) + ". 출력된 링크를 직접 열어주세요.")
        raise typer.Exit(1)
