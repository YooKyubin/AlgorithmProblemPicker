"""The single boundary between use cases and the public JUNGOL source."""

from typing import Protocol

from .models import Candidate, CompletedListing, Problem, SearchCriteria, UserReference


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


class ProblemSource(Protocol):
    def resolve_user(self, handle: str) -> UserReference: ...

    def collect(self, criteria: SearchCriteria, user: UserReference | None) -> CompletedListing: ...

    def read_details(self, candidate: Candidate) -> Problem: ...
