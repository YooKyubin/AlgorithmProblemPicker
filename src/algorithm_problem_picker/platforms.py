"""Static composition of platform information, pure policy and lazy sources."""

from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass

from .jungol import JungolSource
from .jungol_models import Problem, SearchCriteria, UserReference
from .jungol_policy import JungolPolicy
from .models import PlatformInfo, ProblemRecord
from .ports import PlatformPolicy, ProblemSource


@dataclass(frozen=True)
class PlatformBinding[P: ProblemRecord, C, U]:
    info: PlatformInfo
    policy: PlatformPolicy[P, C, U]
    source_factory: Callable[[Callable[[str], None]], AbstractContextManager[ProblemSource[P, C, U]]]


def _jungol_source(report: Callable[[str], None]) -> JungolSource:
    return JungolSource(report=report)


DEFAULT_PLATFORM = 'jungol'
_jungol_policy = JungolPolicy()
_jungol_binding: PlatformBinding[Problem, SearchCriteria, UserReference] = PlatformBinding(
    info=_jungol_policy.info, policy=_jungol_policy, source_factory=_jungol_source,
)
REGISTRY = {DEFAULT_PLATFORM: _jungol_binding}
