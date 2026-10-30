"""Static composition of platform information, pure policy and lazy sources."""

from collections.abc import Callable, Iterable, Iterator, Mapping
from contextlib import AbstractContextManager
from dataclasses import dataclass
import warnings

from .jungol import JungolSource
from .jungol_models import Problem, SearchCriteria, UserReference
from .jungol_policy import JungolPolicy
from .models import FILTER_OPTION_NAMES, PlatformInfo, ProblemRecord
from .ports import PlatformPolicy, ProblemSource

DEFAULT_PLATFORM = 'jungol'


class PlatformConfigurationError(Exception):
    pass


@dataclass(frozen=True)
class PlatformBinding[P: ProblemRecord, C, U]:
    info: PlatformInfo
    policy: PlatformPolicy[P, C, U]
    source_factory: Callable[[Callable[[str], None]], AbstractContextManager[ProblemSource[P, C, U]]]


class PlatformRegistry(Mapping[str, PlatformBinding]):
    def __init__(self, bindings: Iterable[PlatformBinding], default: str = DEFAULT_PLATFORM):
        self._bindings: dict[str, PlatformBinding] = {}
        self._errors: dict[str, list[str]] = {}
        for binding in bindings:
            key = binding.info.key
            if key in self._bindings:
                self._errors.setdefault(key, []).append('중복 플랫폼 키')
            else:
                self._bindings[key] = binding
            errors = self._binding_errors(binding)
            if errors:
                self._errors.setdefault(key, []).extend(errors)
        if default not in self._bindings:
            self._errors.setdefault(default, []).append('기본 플랫폼 누락')
        for key, errors in self._errors.items():
            warnings.warn(f'플랫폼 구성 오류 {key}: ' + '; '.join(errors), RuntimeWarning, stacklevel=2)

    @staticmethod
    def _binding_errors(binding: PlatformBinding) -> list[str]:
        errors: list[str] = []
        owned: set[str] = set()
        for capability in binding.info.filters:
            if not capability.commands or set(capability.commands) - {'list', 'recommend'}:
                errors.append(f'{capability.key}: 정의하지 않은 명령 연결')
            for option in capability.option_names:
                if option not in FILTER_OPTION_NAMES:
                    errors.append(f'{option}: 정의하지 않은 옵션 연결')
                if option in owned:
                    errors.append(f'{option}: 옵션 중복 소유')
                owned.add(option)
        for retired in binding.info.retired_options:
            if retired.option_name not in FILTER_OPTION_NAMES:
                errors.append(f'{retired.option_name}: 정의하지 않은 폐기 옵션 연결')
            if retired.option_name in owned:
                errors.append(f'{retired.option_name}: 옵션 중복 소유')
            owned.add(retired.option_name)
        if binding.info != binding.policy.info:
            errors.append('지원 정보와 정책 선언 불일치')
        if (binding.info.columns != binding.policy.columns or
                binding.info.observation_notes != binding.policy.observation_notes):
            errors.append('지원 정보와 출력 선언 불일치')
        return errors

    def __getitem__(self, key: str) -> PlatformBinding:
        if key in self._errors:
            raise PlatformConfigurationError(f'플랫폼 구성 오류 {key}: ' + '; '.join(self._errors[key]))
        return self._bindings[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._bindings)

    def __len__(self) -> int:
        return len(self._bindings)


def _jungol_source(report: Callable[[str], None]) -> JungolSource:
    return JungolSource(report=report)


_jungol_policy = JungolPolicy()
_jungol_binding: PlatformBinding[Problem, SearchCriteria, UserReference] = PlatformBinding(
    info=_jungol_policy.info, policy=_jungol_policy, source_factory=_jungol_source,
)
REGISTRY = PlatformRegistry((_jungol_binding,))
