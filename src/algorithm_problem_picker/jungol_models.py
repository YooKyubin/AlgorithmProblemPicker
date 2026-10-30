"""Validated JUNGOL problem, search and user values."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from .models import Known, Unavailable, _aware


@dataclass(frozen=True)
class Unrated:
    pass


@dataclass(frozen=True)
class Rated:
    value: int

    def __post_init__(self) -> None:
        if type(self.value) is not int or not 1 <= self.value <= 30:
            raise ValueError("티어는 1~30 정수여야 합니다.")


@dataclass(frozen=True, kw_only=True)
class Problem:
    id: int
    title: str
    url: str
    tier: Rated | Unrated | Unavailable
    pass_rate: Known[Decimal] | Unavailable
    accepted_count: Known[int] | Unavailable
    listed_at: datetime

    def __post_init__(self) -> None:
        if type(self.id) is not int or self.id <= 0:
            raise ValueError("문제 번호는 양의 정수여야 합니다.")
        if not self.title.strip():
            raise ValueError("문제 제목이 비어 있습니다.")
        if self.url != f"https://jungol.co.kr/problem/{self.id}":
            raise ValueError("문제 URL과 번호가 일치하지 않습니다.")
        if not isinstance(self.tier, (Rated, Unrated, Unavailable)):
            raise ValueError("알 수 없는 티어 상태입니다.")
        if isinstance(self.pass_rate, Known):
            rate = self.pass_rate.value
            if not isinstance(rate, Decimal) or not rate.is_finite() or not 0 <= rate <= 100:
                raise ValueError("정답률은 유한 Decimal 0~100이어야 합니다.")
        elif not isinstance(self.pass_rate, Unavailable):
            raise ValueError("알 수 없는 정답률 상태입니다.")
        if isinstance(self.accepted_count, Known):
            count = self.accepted_count.value
            if type(count) is not int or count < 0:
                raise ValueError("정답 제출 수는 0 이상의 정수여야 합니다.")
        elif not isinstance(self.accepted_count, Unavailable):
            raise ValueError("알 수 없는 정답 제출 수 상태입니다.")
        _aware(self.listed_at)


class Status(StrEnum):
    ALL = "all"
    SOLVED = "solved"
    UNSOLVED = "unsolved"


class SortKey(StrEnum):
    ID = "id"
    DIFFICULTY = "difficulty"
    RATE = "rate"
    ACCEPTED = "accepted"
    RANDOM = "random"


@dataclass(frozen=True)
class SearchCriteria:
    min_tier: int | None = None
    max_tier: int | None = None
    min_rate: Decimal | None = None
    max_rate: Decimal | None = None
    min_accepted: int | None = None
    max_accepted: int | None = None
    status: Status = Status.ALL
    user_handle: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "status", Status(self.status))
        supplied_user = bool(self.user_handle)
        handle = self.user_handle.removeprefix("@")
        object.__setattr__(self, "user_handle", handle)
        for name in ("min_tier", "max_tier"):
            value = getattr(self, name)
            if value is not None and (type(value) is not int or not 1 <= value <= 30):
                raise ValueError("티어는 1~30 정수여야 합니다.")
        for name in ("min_rate", "max_rate"):
            value = getattr(self, name)
            if value is not None and (
                not isinstance(value, Decimal) or not value.is_finite() or not 0 <= value <= 100
            ):
                raise ValueError("정답률은 유한 소수 0~100이어야 합니다.")
        for name in ("min_accepted", "max_accepted"):
            value = getattr(self, name)
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError("정답 제출 수는 0 이상의 정수여야 합니다.")
        for metric in ("tier", "rate", "accepted"):
            lower, upper = getattr(self, f"min_{metric}"), getattr(self, f"max_{metric}")
            if lower is not None and upper is not None and lower > upper:
                raise ValueError(f"{metric}: 하한은 상한 이하여야 합니다.")
        if self.status != Status.ALL and (not handle.strip() or handle.startswith("@")):
            raise ValueError("solved/unsolved에는 정확한 --user 핸들이 필요합니다.")
        if self.status == Status.ALL and supplied_user:
            raise ValueError("--status all과 --user를 함께 지정할 수 없습니다.")


@dataclass(frozen=True)
class UserReference:
    handle: str
    account_id: int
    resolved_at: datetime

    def __post_init__(self) -> None:
        if not self.handle.strip() or type(self.account_id) is not int or self.account_id <= 0:
            raise ValueError("정확한 사용자 핸들과 숫자 ID가 필요합니다.")
        _aware(self.resolved_at)
