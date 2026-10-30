"""Typed boundaries for pure platform policies and external data access."""

from collections.abc import Sequence
from typing import Protocol

from .models import CompletedListing, Order, PlatformInfo, ProblemLink, ProblemRecord, RawFilterInput


class FilterInputError(ValueError):
    def __init__(self, message: str, option: str = ''):
        super().__init__(message)
        self.option = option


class SourceError(Exception):
    """A source operation failed; no partial result may be presented."""


class UserResolutionError(SourceError):
    pass


class SourceAccessError(SourceError):
    pass


class SourceSchemaError(SourceError):
    pass


class SourceCompletenessError(SourceError):
    pass


class ProblemSource[P: ProblemRecord, C, U](Protocol):
    def prepare_user(self, criteria: C) -> U | None: ...

    def collect(self, criteria: C, user: U | None) -> CompletedListing[P]: ...


class PlatformPolicy[P: ProblemRecord, C, U](Protocol):
    @property
    def info(self) -> PlatformInfo: ...

    @property
    def columns(self) -> tuple[str, ...]: ...

    @property
    def observation_notes(self) -> tuple[str, ...]: ...

    def parse_filters(self, raw: RawFilterInput) -> C: ...

    def validate_list_options(self, sort: str, order: Order) -> str: ...

    def filter_listing(self, problems: Sequence[P], criteria: C) -> tuple[list[P], int]: ...

    def sort_problems(self, problems: Sequence[P], sort: str, order: Order) -> list[P]: ...

    def format_row(self, problem: P) -> tuple[str, ...]: ...

    def format_conditions(self, criteria: C, user: U | None) -> str: ...

    def problem_links(self, raw_ids: Sequence[str]) -> tuple[ProblemLink, ...]: ...
