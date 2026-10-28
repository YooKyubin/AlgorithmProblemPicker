# Implementation Plan: 티어·정답률·정답 제출 수 범위 옵션 추가

**Branch**: `004-add-range-options` | **Date**: 2026-10-28 | **Spec**: [spec.md](spec.md)

**Input**: `specs/004-add-range-options/spec.md`

## Summary

`list`와 `recommend`에 `--tier`, `--rate`, `--accepted`를 추가한다. `하한..상한`·`하한..`·`..상한`을 기존 `SearchCriteria`의 여섯 경계로 변환하고 기존 경계 옵션을 보존한다.

구현은 `cli.py`의 옵션 선언, 비공개 범위 해석·혼용 검증, 공통 조건 생성에 집중한다. Typer의 문자열 목록 옵션으로 모든 출현을 받은 후 2회 이상은 거부한다. 원시 인자 재해석이나 새로운 파서·의존성을 추가하지 않는다. 수집기·서비스·필터·도메인 모델·결과 형식은 그대로 활용한다.

문법·수치·혼용 오류는 정확한 옵션명과 이유를 알리고 공급자 생성 전 종료 코드 2로 끝낸다. 설계 근거는 [research.md](research.md), 사용자 계약은 [contracts/cli.md](contracts/cli.md)를 따른다.

## Technical Context

**Language/Version**: Python >=3.12. 조사 환경은 Python 3.12.13이며 기존 Annotated·Decimal을 사용한다.

**Primary Dependencies**: 잠금 환경의 Typer 0.27.3, Rich 15.0.0, Playwright 1.64.0, 개발 의존성 pytest 9.1.1과 uv. 이 Typer는 내부 `typer._click`을 포함하며 별도 Click 배포판이 없다. 새 의존성·잠금 파일 변경은 필요하지 않다.

**Storage**: 옵션은 명령 실행 중에만 존재한다. 문제 후보는 기존 실행 중 메모리를 사용하고 영구 캐시·설정 저장·스키마 변경을 추가하지 않는다.

**Testing**: pytest와 Typer CliRunner, 기존 `tests/test_cli.py`의 `source_factory`·`problem` fixture를 활용한다. CLI 입력→실제 Picker/selection→출력 경로는 고정 공급자로 검증하며 브라우저·원격 요청은 발생시키지 않는다. 기존 DOM 재생은 전체 회귀에서 활용한다.

**Target Platform**: 기존 데스크톱 터미널 CLI, Windows/PowerShell을 검증 기준으로 삼는다.

**Project Type**: 단일 Python CLI 패키지.

**Performance Goals**: 세 지표의 양쪽 경계 옵션을 6개에서 3개로 줄인다. 범위 해석을 위한 원격 요청·브라우저 실행·고정 대기는 0건이다. 새로운 처리 속도나 벤치마크 목표는 도입하지 않는다.

**Constraints**: ASCII 숫자·명시적 `..`만 허용한다. 정답률은 Decimal로 보존한다. 같은 지표의 새/기존 표기 혼용과 새 옵션 반복은 오류다. 티어의 사이트 검색 의미, 0/미제공 구분, 기존 옵션의 해석과 오류를 유지한다.

**Scale/Scope**: 두 명령 × 세 지표 × 세 범위 형태의 18개 기본 조합과 호환성·오류 경계를 다룬다. `open`, 복수 범위, 단일 숫자 축약, camelCase 별칭, 데이터 접근·수집 정책·영구 캐시는 범위 밖이다.

## Constitution Check

계획 진입 전에 헌장과 선행 합의를 검토했다. Phase 1 설계 완료 후 같은 기준으로 다시 평가했다. 아래는 설계 게이트 판정이며 제품 테스트 통과를 의미하지 않는다.

| 원칙 | 계획 진입 전 | 설계 후 | 근거 |
| --- | --- | --- | --- |
| I. JUNGOL에 집중 | PASS | PASS | 기존 JUNGOL 조회·추천의 입력만 확장한다. |
| II. 허용된 데이터 접근 | PASS | PASS | 공개 DOM 기반 접근과 수집 수명을 그대로 사용하며 새 원격 경로나 직접 내부 API 호출을 추가하지 않는다. |
| III. 로컬 데이터 우선 | 정당화된 기존 예외 | 정당화된 기존 예외 | 003과 004 명세의 합의대로 영구 캐시는 제외하고, 실행 중 후보에 대한 로컬 처리와 중복 없는 추천을 유지한다. |
| IV. 단순한 구조 | PASS | PASS | CLI 내 비공개 공통 처리만 추가하고 기존 모델·포트·서비스 경계를 확장하지 않는다. |
| V. 명확한 동작과 검증 | PASS | PASS | 잘못된 입력은 공급자 생성 전에 지표별로 진단하고 기존 고정 공급자 테스트로 핵심 동작을 검증한다. |

헌장 III와 현재 동작의 차이는 [003 계획](../003-align-site-listing/plan.md)의 범위 예외를 승계한다. 004가 새로 도입한 위반이 아니며, 이 기능을 위해 영구 캐시나 헌장 개정을 추가하지 않는다. 미정당화 위반과 미결정 설계 항목은 없다.

## Project Structure

### Documentation (this feature)

```text
specs/004-add-range-options/
├── spec.md
├── checklists/requirements.md
├── plan.md
├── research.md
├── data-model.md
├── contracts/
│   └── cli.md
└── quickstart.md
```

`tasks.md`는 다음 `$speckit-tasks` 단계에서 생성한다. 기존 명세와 품질 체크리스트는 보존한다.

### Source Code (repository root)

```text
src/algorithm_problem_picker/
├── cli.py          # 변경: 세 옵션, 반복·범위·혼용 검사, 공통 조건 생성
├── models.py       # 유지: SearchCriteria 타입·불변식
├── service.py      # 유지: 전체 후보 처리·조회/추천
├── selection.py    # 유지: 필터·정렬·무작위 추천
├── jungol.py       # 유지: 공개 목록 접근·사이트 검색 조건 전달
└── ports.py        # 유지: ProblemSource 계약

tests/
├── test_cli.py       # 변경: 새 입력과 기존 표기의 동등성·오류·도움말
├── test_selection.py # 기존 회귀 활용
├── test_service.py   # 기존 회귀 활용
└── test_jungol_dom.py # 기존 로컬 DOM 회귀 활용

README.md             # 변경: 새 표기·열린 범위·혼용 규칙·예시
```

**Structure Decision**: 기존 단일 패키지를 유지한다. 작은 비공개 함수로 반복·문법·범위 변환과 혼용 검사를 공통화하고, 범위 프레임워크·공개 Range 모델·새 모듈·테스트 전용 API를 만들지 않는다. 기존 수집·도메인 처리 코드는 동등성을 확인하는 회귀 대상이다.

## Phase 0: Research 결과

[research.md](research.md)의 R1~R6에서 설계를 확정했다.

- 문자열 목록 옵션은 출현 횟수를 보존한다. 공통 callback은 2회 이상을 거부하고 목록은 변경하지 않는다.
- 범위 해석은 `..` 분리 후 각 경계의 전체 문법을 검사한다. 단일값·빈 범위·추가 구분자·공백·부호·비ASCII 숫자·정답률 외 소수를 거부한다.
- CLI 경계에서 지표별 숫자 제한과 경계 역전을 확인해 정확한 `param_hint`로 오류를 전달한다. 모델의 기존 검증은 직접 Python 호출의 불변식으로 보존한다.
- 같은 지표의 기존 경계는 `is not None`으로 검사해 0도 혼용으로 판단한다. 다른 지표의 표기는 자유롭게 조합한다.
- 새 표기만 공통 경계로 변환하고 기존 표기 경로는 기존 변환·검증을 따른다. 사용자 풀이·정렬 검증은 기존 순서를 보존한다.
- 기본 검증은 고정 목록을 사용한다. 변화하는 실사이트 목록을 두 번 조회해 결과 일치를 판단하지 않는다.

## Phase 1: Design & Contracts 결과

- [data-model.md](data-model.md): 원시 출현 목록·경계 쌍·SearchCriteria 매핑과 검증 책임.
- [contracts/cli.md](contracts/cli.md): 범위 문법·수치 제한·반복/혼용·출력/종료 코드·호환성 계약.
- [quickstart.md](quickstart.md): 구현 후 실행할 최소 회귀·전체 회귀·도움말·오류 명령·선택적 실사이트 확인.

설계 후에도 헌장 게이트와 범위 예외는 같다. 제품 코드·테스트·README는 이번 계획 단계에서 수정하지 않는다.

### 구현 흐름

1. 세 새 옵션을 `list[str]`로 선언하고 기본값은 빈 목록으로 둔다. 빈 목록과 전달 목록을 수정하지 않으며, callback으로 반복을 거부한다. 도움말 metavar는 `MIN..MAX`와 열린 범위 설명을 사용한다.
2. `cli.py`의 비공개 해석기가 구분자·경계 문법을 검사하고 정수 또는 Decimal 경계 쌍으로 변환한다. 지표별 수치/순서 오류에 해당 옵션을 지정한다.
3. 공통 조건 생성 경로에서 같은 지표의 신·구 표기 충돌을 검사한다. 새 표기가 없으면 기존 경계 값을 그대로 사용하고, 있으면 변환한 경계를 기존 SearchCriteria 필드에 전달한다.
4. 모든 입력 검사 후에만 기존 `_run`에 진입한다. 서비스·수집기·출력 코드는 기존 조건 객체를 소비한다.
5. `tests/test_cli.py`에 행동 검증을 추가하고 README·도움말을 맞춘다. 관련 회귀 후 전체 회귀를 한 번 실행한다.

반복 입력은 callback에서, 혼용은 모든 옵션 값이 준비된 공통 조건 생성 경로에서 검사한다. callback 실행 순서에 의존해 다른 옵션을 조회하지 않는다. 둘 이상의 오류가 동시에 있으면 어느 것을 먼저 알릴지는 고정하지 않되, 항상 조회 전에 유효한 오류를 보고해야 한다.

### 검증 범위와 요구사항 추적

| 요구사항 / 성공 기준 | 설계·검증 |
| --- | --- |
| FR-001~003 / SC-001~002 | 두 명령·세 옵션·세 범위의 18개 기본 입력을 기존 표기와 비교하고, 같은 경계·세 지표 조합을 보강한다. |
| FR-004~007 / SC-002~003 | 0·최대 티어·소수 정답률·정확한 소수 경계와 숫자 문법·수치 제한 오류를 CliRunner로 검증한다. |
| FR-008~010 / SC-003 | 기존 min/max 각각과의 혼용, 양쪽 순서, 같은 값·다른 값 반복, 빈 값·값 누락을 두 명령에서 검증한다. source_factory 호출 목록은 비어 있어야 한다. |
| FR-011~013 / SC-002~004 | 기존 SearchCriteria 전달과 실제 Picker/selection 결과의 경계 포함·미제공·0·범위 밖 Rated·정렬·개수·부족 처리를 고정 목록에서 비교한다. |
| FR-014 / SC-005 | 두 도움말·README의 세 옵션과 열린 범위·기존 옵션 유지·혼용 제한 및 조회/추천 예시를 확인한다. |
| FR-015 / SC-004~005 | 새 표기 조건이 기존 min/max 이름으로 정확히 표시되고 생략한 경계가 추가되지 않는지 확인한다. |

파서 함수 자체를 복제하는 테스트 대신 공개 CLI 입력에서 관측 가능한 조건·결과·진단을 검증한다. 기존 서비스·필터 테스트를 다시 작성하지 않으며, 입력 문법을 DOM 테스트에 복제하지 않는다. 추천은 후보 집합·개수·중복·부족으로 검증하며 임의 추출 순서의 일치는 요구하지 않는다.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
| --- | --- | --- |
| 헌장 III의 영구 캐시 원칙과 달리 실행 중 메모리만 사용 | 선행 사용자 합의와 004 명세가 영구 캐시를 제외한다. | 영구 캐시는 데이터 수명·무효화 정책을 별도로 요구하고 범위 옵션 추가에 필요하지 않다. 기존 실행 중 후보로 로컬 필터와 중복 없는 추천을 유지한다. |

## 검증 상태

2026-10-28 현재 Phase 0 조사와 Phase 1 설계·문서 정합성 확인을 수행했다. 조사 시작 HEAD는 `9bad679c0f441e284265e492ffc56a39fde69169`다. 설치된 Typer에 대한 메모리 내 최소 동작 실험만 수행했으며, 제품 구현·제품 테스트·실사이트 수용은 후속 단계다.
