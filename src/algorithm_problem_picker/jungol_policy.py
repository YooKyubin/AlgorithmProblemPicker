"""Pure JUNGOL input, filtering, ordering, presentation and link rules."""

from collections.abc import Sequence
from decimal import Decimal, InvalidOperation
import random
import re

from .jungol_models import Problem, Rated, SearchCriteria, SortKey, Status, Unrated, UserReference
from .models import FilterCapability, Known, Order, PlatformInfo, ProblemLink, RawFilterInput, RetiredOption, Unavailable
from .ports import FilterInputError

_TIER_NAMES = tuple(f'{group}{level}' for group in 'BSGPDR' for level in range(5, 0, -1))
_TIER_VALUES = {name: value for value, name in enumerate(_TIER_NAMES, start=1)}
_RANGE_HELP = 'MIN..MAX, MIN.., ..MAX, 양 끝 포함. 한 번만 지정하며 같은 지표의 범위/경계 옵션 혼용 금지'
_LEGACY_REASON = ('맞힌 사람 수에서 정답 제출 수로 변경되었습니다. '
                  '동일 사용자의 중복 정답 제출을 포함하므로 같은 숫자라도 결과가 달라질 수 있습니다.')

JUNGOL_INFO = PlatformInfo(
    key='jungol', display_name='정올',
    filters=(
        FilterCapability('tier', ('--tier', '--min-tier', '--max-tier'),
                         '사이트 검색 조건이며 표시 티어는 요청 범위 밖일 수 있습니다.', '티어',
                         f'{_TIER_NAMES[0]}~{_TIER_NAMES[-1]}, 대소문자 무관 (기존 1~30도 지원)', _RANGE_HELP),
        FilterCapability('rate', ('--rate', '--min-rate', '--max-rate'),
                         '목록에 표시된 정답률, 재계산하지 않음', '%', '0~100 유한 정수·소수, % 없이', _RANGE_HELP),
        FilterCapability('accepted', ('--accepted', '--min-accepted', '--max-accepted'),
                         '정답 제출 수, 동일 사용자의 중복 정답 제출 포함', '제출', '0 이상 정수', _RANGE_HELP),
        FilterCapability('user', ('--status', '--user'), '공개 기준 사용자 풀이 여부', '',
                         ', '.join(Status), 'all 기본, solved/unsolved에는 정확한 --user 필요. '
                         'all + user 거부, 선행 @ 한 개 허용, 대소문자 보존'),
    ),
    retired_options=(
        RetiredOption('--min-solvers', '--min-accepted', _LEGACY_REASON),
        RetiredOption('--max-solvers', '--max-accepted', _LEGACY_REASON),
    ),
    columns=('번호', '제목', '난이도', '정답률', '정답 제출 수', '링크'),
    observation_notes=('티어·정답률·정답 제출 수는 각 목록 관측 시점의 값입니다. '
                       '정답 제출 수는 동일 사용자의 중복 정답 제출을 포함합니다.',),
    sort_help=', '.join(SortKey) + '; random과 --order desc 혼용 금지, 지표 동점은 번호 오름차순',
)


def _parse_tier(value: str, option: str) -> int:
    name = value.upper()
    if name in _TIER_VALUES:
        return _TIER_VALUES[name]
    if re.fullmatch(r'[0-9]+', value) and 1 <= int(value) <= 30:
        return int(value)
    raise FilterInputError("티어 경계는 B/S/G/P/D/R + 1~5 또는 정수 1~30이어야 합니다. "
                           "예: B5, S1, G5, R1", option=option)


def _format_tier(value: int) -> str:
    return _TIER_NAMES[value - 1]


def _parse_range(value: str, metric: str) -> tuple[int | Decimal | None, int | Decimal | None]:
    option = f'--{metric}'
    parts = value.split('..')
    if len(parts) != 2 or not any(parts):
        raise FilterInputError("범위는 MIN..MAX, MIN.., ..MAX 형태로 지정하세요. 예: 1..10", option=option)
    if metric == 'tier':
        lower, upper = (_parse_tier(part, option) if part else None for part in parts)
    else:
        pattern = r'[0-9]+(?:\.[0-9]+)?' if metric == 'rate' else r'[0-9]+'
        if any(part and not re.fullmatch(pattern, part) for part in parts):
            raise FilterInputError("범위는 MIN..MAX, MIN.., ..MAX 형태로 지정하세요. 예: 1..10", option=option)
        convert = Decimal if metric == 'rate' else int
        lower, upper = (convert(part) if part else None for part in parts)
        maximum = 100 if metric == 'rate' else None
        if any(bound is not None and (bound < 0 or (maximum is not None and bound > maximum))
               for bound in (lower, upper)):
            allowed = f"0~{maximum}" if maximum is not None else "0 이상"
            raise FilterInputError(f"경계는 {allowed}이어야 합니다.", option=option)
    if lower is not None and upper is not None and lower > upper:
        raise FilterInputError("하한은 상한 이하여야 합니다.", option=option)
    return lower, upper


def _range_bounds(values: tuple[str, ...], lower, upper, metric: str) -> tuple:
    if len(values) > 1:
        raise FilterInputError('범위 옵션은 한 번만 지정하세요.', option=f'--{metric}')
    if not values:
        if metric == 'tier':
            return (_parse_tier(lower, '--min-tier') if lower is not None else None,
                    _parse_tier(upper, '--max-tier') if upper is not None else None)
        return lower, upper
    option = f'--{metric}'
    conflicts = [f'--{name}-{metric}' for name, value in (('min', lower), ('max', upper)) if value is not None]
    if conflicts:
        raise FilterInputError(f"{', '.join(conflicts)}와 함께 지정할 수 없습니다. 한 가지 표기만 사용하세요.",
                               option=option)
    return _parse_range(values[0], metric)


def _within(value, lower, upper) -> bool:
    return (lower is None or value >= lower) and (upper is None or value <= upper)


def _value(raw: RawFilterInput, option: str) -> str | None:
    value = raw.values.get(option)
    assert value is None or isinstance(value, str)
    return value


def _ranges(raw: RawFilterInput, option: str) -> tuple[str, ...]:
    value = raw.values.get(option, ())
    assert isinstance(value, tuple)
    return value


def _accepted_boundary(raw: RawFilterInput, option: str) -> int | None:
    value = _value(raw, option)
    if value is None:
        return None
    try:
        count = int(value)
    except ValueError as error:
        raise FilterInputError('정답 제출 수는 0 이상의 정수여야 합니다.', option=option) from error
    if count < 0:
        raise FilterInputError('정답 제출 수는 0 이상의 정수여야 합니다.', option=option)
    return count


def _metric(value, suffix: str = '') -> str:
    return f'{value.value}{suffix}' if isinstance(value, Known) else '미확인'


class JungolPolicy:
    info = JUNGOL_INFO

    @property
    def columns(self) -> tuple[str, ...]:
        return self.info.columns

    @property
    def observation_notes(self) -> tuple[str, ...]:
        return self.info.observation_notes

    def parse_filters(self, raw: RawFilterInput) -> SearchCriteria:
        for retired in self.info.retired_options:
            if _value(raw, retired.option_name) is not None:
                raise FilterInputError(f'{retired.replacement}를 사용하세요. {retired.reason}',
                                       option=retired.option_name)
        min_tier, max_tier = _range_bounds(_ranges(raw, '--tier'), _value(raw, '--min-tier'),
                                         _value(raw, '--max-tier'), 'tier')
        min_rate, max_rate = _range_bounds(_ranges(raw, '--rate'), _value(raw, '--min-rate'),
                                         _value(raw, '--max-rate'), 'rate')
        min_accepted, max_accepted = _range_bounds(_ranges(raw, '--accepted'),
            _accepted_boundary(raw, '--min-accepted'), _accepted_boundary(raw, '--max-accepted'), 'accepted')
        status = _value(raw, '--status')
        user = _value(raw, '--user')
        try:
            return SearchCriteria(min_tier, max_tier,
                                  Decimal(min_rate) if min_rate is not None else None,
                                  Decimal(max_rate) if max_rate is not None else None,
                                  min_accepted, max_accepted,
                                  Status.ALL if status is None else status, '' if user is None else user)
        except (ValueError, InvalidOperation) as error:
            raise FilterInputError(str(error)) from error

    @staticmethod
    def validate_list_options(sort: str, order: Order) -> SortKey:
        if sort == 'solvers':
            raise FilterInputError(f'--sort accepted를 사용하세요. {_LEGACY_REASON}', option='--sort')
        try:
            sort_key = SortKey(sort)
        except ValueError as error:
            raise FilterInputError('정렬 기준: ' + ', '.join(SortKey), option='--sort') from error
        if sort_key == SortKey.RANDOM and Order(order) == Order.DESC:
            raise FilterInputError('random과 --order desc를 함께 지정할 수 없습니다.')
        return sort_key

    @staticmethod
    def filter_listing(problems: Sequence[Problem], criteria: SearchCriteria) -> tuple[list[Problem], int]:
        selected: list[Problem] = []
        omitted = 0
        seen: set[int] = set()
        tier_filter = criteria.min_tier is not None or criteria.max_tier is not None
        rate_filter = criteria.min_rate is not None or criteria.max_rate is not None
        accepted_filter = criteria.min_accepted is not None or criteria.max_accepted is not None
        for problem in problems:
            if problem.id in seen:
                continue
            seen.add(problem.id)
            if tier_filter:
                if isinstance(problem.tier, Unavailable):
                    omitted += 1
                    continue
                if not isinstance(problem.tier, Rated):
                    continue
            if rate_filter:
                if isinstance(problem.pass_rate, Unavailable):
                    omitted += 1
                    continue
                if not _within(problem.pass_rate.value, criteria.min_rate, criteria.max_rate):
                    continue
            if accepted_filter:
                if isinstance(problem.accepted_count, Unavailable):
                    omitted += 1
                    continue
                if not _within(problem.accepted_count.value, criteria.min_accepted, criteria.max_accepted):
                    continue
            selected.append(problem)
        return selected, omitted

    @staticmethod
    def sort_problems(problems: Sequence[Problem], sort: str = SortKey.ID,
                      order: Order = Order.ASC) -> list[Problem]:
        if sort == SortKey.RANDOM:
            shuffled = list(problems)
            random.shuffle(shuffled)
            return shuffled
        if sort == SortKey.ID:
            return sorted(problems, key=lambda problem: problem.id, reverse=order == Order.DESC)
        attribute = {SortKey.DIFFICULTY: 'tier', SortKey.RATE: 'pass_rate', SortKey.ACCEPTED: 'accepted_count'}[sort]
        direction = -1 if order == Order.DESC else 1

        def key(problem: Problem):
            metric = getattr(problem, attribute)
            known = isinstance(metric, (Known, Rated))
            return (not known, direction * metric.value if known else 0, problem.id)

        return sorted(problems, key=key)

    @staticmethod
    def format_row(problem: Problem) -> tuple[str, ...]:
        tier = _format_tier(problem.tier.value) if isinstance(problem.tier, Rated) else (
            '미정' if isinstance(problem.tier, Unrated) else '미확인')
        return (str(problem.id), problem.title, tier, _metric(problem.pass_rate, '%'),
                _metric(problem.accepted_count), problem.url)

    @staticmethod
    def format_conditions(criteria: SearchCriteria, user: UserReference | None) -> str:
        conditions: list[str] = []
        for name in ('min_tier', 'max_tier', 'min_rate', 'max_rate', 'min_accepted', 'max_accepted'):
            value = getattr(criteria, name)
            if value is not None:
                if name in ('min_tier', 'max_tier'):
                    value = _format_tier(value)
                conditions.append(f'{name}={value}')
        conditions.append(f'status={criteria.status}')
        if user is not None:
            conditions.append(f'기준 사용자 @{user.handle}')
        return ', '.join(conditions)

    @staticmethod
    def problem_links(raw_ids: Sequence[str]) -> tuple[ProblemLink, ...]:
        ids: list[int] = []
        for raw in raw_ids:
            try:
                number = int(raw)
            except ValueError as error:
                raise FilterInputError('문제 번호는 양의 정수여야 합니다.', option='ID') from error
            if number <= 0:
                raise FilterInputError('문제 번호는 양의 정수여야 합니다.', option='ID')
            ids.append(number)
        return tuple(ProblemLink(str(number), f'https://jungol.co.kr/problem/{number}')
                     for number in dict.fromkeys(ids))
