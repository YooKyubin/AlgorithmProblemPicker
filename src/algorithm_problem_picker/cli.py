"""jpick commands and dependency composition."""

from importlib.metadata import version
from decimal import Decimal, InvalidOperation
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
                  help="JUNGOL 문제 검색·추천. 티어 1=Bronze V, 30=Ruby I.")
out = Console(highlight=False, markup=False)
err = Console(stderr=True, highlight=False, markup=False)

TierOption = Annotated[int | None, typer.Option(min=1, max=30, help="티어 1=Bronze V ~ 30=Ruby I (포함)")]
RateOption = Annotated[str | None, typer.Option(help="정답률 0~100 소수, % 없이 (포함)")]
AcceptedOption = Annotated[int | None, typer.Option(min=0, help="정답 제출 수, 동일 사용자의 중복 정답 제출 포함 (경계 포함)")]
StatusOption = Annotated[Status, typer.Option(help="공개 기준 사용자 풀이 여부")]
UserOption = Annotated[str, typer.Option("--user", help="정확한 공개 핸들. @ 접두사 허용")]


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


def _criteria(min_tier, max_tier, min_rate, max_rate, min_accepted, max_accepted, status, user) -> SearchCriteria:
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
        tier = str(problem.tier.value) if isinstance(problem.tier, Rated) else (
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


@app.command("list", help="전체 후보를 조회합니다. 티어 1=Bronze V ~ 30=Ruby I.")
def list_command(
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
    criteria = _criteria(min_tier, max_tier, min_rate, max_rate, min_accepted, max_accepted, status, user)
    if sort_key == SortKey.RANDOM and order == Order.DESC:
        raise typer.BadParameter("random과 --order desc를 함께 지정할 수 없습니다.")
    _run(criteria, limit, sort=sort_key, order=order)


@app.command(help="전체 적격 후보에서 중복 없이 추천. 티어 1=Bronze V ~ 30=Ruby I.")
def recommend(
    min_tier: TierOption = None, max_tier: TierOption = None,
    min_rate: RateOption = None, max_rate: RateOption = None,
    min_accepted: AcceptedOption = None, max_accepted: AcceptedOption = None,
    min_solvers: Annotated[str | None, typer.Option(hidden=True, is_eager=True, callback=_reject_min_solvers)] = None,
    max_solvers: Annotated[str | None, typer.Option(hidden=True, is_eager=True, callback=_reject_max_solvers)] = None,
    status: StatusOption = Status.ALL, user: UserOption = "",
    count: Annotated[int, typer.Option(min=1, help="추천 개수")] = 1,
) -> None:
    criteria = _criteria(min_tier, max_tier, min_rate, max_rate, min_accepted, max_accepted, status, user)
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
