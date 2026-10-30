"""Platform-neutral values shared by the CLI, policies and source boundary."""

from collections.abc import Hashable, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from types import MappingProxyType
from typing import Protocol


FILTER_OPTION_NAMES = (
    '--tier', '--min-tier', '--max-tier', '--rate', '--min-rate', '--max-rate',
    '--accepted', '--min-accepted', '--max-accepted', '--status', '--user',
    '--min-solvers', '--max-solvers',
)
RANGE_FILTER_OPTIONS = frozenset({'--tier', '--rate', '--accepted'})


def now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("조회 시각에는 시간대가 필요합니다.")


@dataclass(frozen=True)
class Known[T]:
    value: T


@dataclass(frozen=True)
class Unavailable:
    pass


class Order(StrEnum):
    ASC = "asc"
    DESC = "desc"


class ProblemRecord(Protocol):
    @property
    def id(self) -> Hashable: ...

    @property
    def title(self) -> str: ...

    @property
    def url(self) -> str: ...

    @property
    def listed_at(self) -> datetime: ...


@dataclass(frozen=True)
class FilterCapability:
    key: str
    option_names: tuple[str, ...]
    meaning: str
    unit: str
    value_help: str
    combination_help: str
    commands: tuple[str, ...] = ('list', 'recommend')


@dataclass(frozen=True)
class RetiredOption:
    option_name: str
    replacement: str
    reason: str


@dataclass(frozen=True)
class PlatformInfo:
    key: str
    display_name: str
    filters: tuple[FilterCapability, ...]
    retired_options: tuple[RetiredOption, ...]
    columns: tuple[str, ...]
    observation_notes: tuple[str, ...]
    sort_help: str


@dataclass(frozen=True)
class RawFilterInput:
    values: Mapping[str, str | tuple[str, ...]] = field(default_factory=dict)
    supplied_options: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        object.__setattr__(self, 'values', MappingProxyType(dict(self.values)))
        object.__setattr__(self, 'supplied_options', frozenset(self.supplied_options))


@dataclass(frozen=True)
class ValidatedRequest[C]:
    criteria: C
    requested_count: int
    random_selection: bool = False
    sort: str = 'id'
    order: Order = Order.ASC

    def __post_init__(self) -> None:
        if type(self.requested_count) is not int or self.requested_count <= 0:
            raise ValueError("개수는 양의 정수여야 합니다.")


@dataclass(frozen=True)
class ProblemLink:
    label: str
    url: str


@dataclass(frozen=True)
class CompletedListing[P: ProblemRecord]:
    """Created only after the provider's collection completion criterion is met."""

    candidates: tuple[P, ...]
    completed_at: datetime = field(default_factory=now)

    def __post_init__(self) -> None:
        first: dict[Hashable, P] = {}
        for candidate in self.candidates:
            first.setdefault(candidate.id, candidate)
        object.__setattr__(self, "candidates", tuple(first.values()))
        _aware(self.completed_at)


class Stage(StrEnum):
    VALIDATED = "Validated"
    USER_RESOLVED = "UserResolved"
    COLLECTING = "Collecting"
    PROCESSING = "Processing"
    COMPLETE = "Complete"
    FAILED = "Failed"
    CANCELLED = "Cancelled"


@dataclass
class Progress:
    stage: Stage = Stage.VALIDATED
    collected: int = 0

    def advance(self, stage: Stage) -> None:
        allowed = {
            Stage.VALIDATED: {Stage.USER_RESOLVED, Stage.COLLECTING},
            Stage.USER_RESOLVED: {Stage.COLLECTING},
            Stage.COLLECTING: {Stage.PROCESSING},
            Stage.PROCESSING: {Stage.COMPLETE},
        }
        assert stage in allowed.get(self.stage, set()) or (
            stage in {Stage.FAILED, Stage.CANCELLED}
            and self.stage not in {Stage.COMPLETE, Stage.FAILED, Stage.CANCELLED}
        ), f"Invalid progress transition: {self.stage} → {stage}"
        self.stage = stage


@dataclass(frozen=True)
class Result[P: ProblemRecord, C, U]:
    criteria: C
    user: U | None
    problems: tuple[P, ...]
    fetched_count: int
    eligible_count: int
    omitted_unknown_count: int
    started_at: datetime
    finished_at: datetime
    requested_count: int
    shortage: int = 0

    @property
    def returned_count(self) -> int:
        return len(self.problems)

    def __post_init__(self) -> None:
        _aware(self.started_at)
        _aware(self.finished_at)
        assert self.finished_at >= self.started_at
        assert self.fetched_count >= self.eligible_count >= self.returned_count
        assert len({problem.id for problem in self.problems}) == self.returned_count
        assert self.requested_count > 0
        assert self.returned_count == min(self.requested_count, self.eligible_count)
        assert 0 <= self.omitted_unknown_count <= self.fetched_count - self.eligible_count
        assert self.shortage in {0, self.requested_count - self.returned_count}
