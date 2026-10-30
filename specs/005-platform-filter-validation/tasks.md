# Tasks: algo-pick 플랫폼 선택과 지원 필터 검증

**Input**: `specs/005-platform-filter-validation/`의 설계 문서
**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [CLI 계약](contracts/cli.md), [플랫폼 계약](contracts/platform.md), [quickstart.md](quickstart.md)
**Branch**: `005-platform-filter-validation`
**Created**: 2026-10-30

**Tests**: 명세의 독립 검증·SC-001~006과 계획의 최소 행동 검증을 위한 작업을 포함한다. 기존 정올 테스트를 우선 재사용하고 새 동작은 실제 CLI→구성 경계→Picker/정책→출력·호출 기록으로 검증한다. 각 스토리에서 새 테스트를 먼저 작성해 미구현 동작의 실패를 확인한다. 이미 통과하는 보존 사례는 억지로 실패시키지 않는다. 파서 구현을 복제하거나 문서 변경만을 위한 새 테스트를 만들지 않는다.

**Organization**: Setup → Foundational → US1(P1) → US2(P1) → US3(P1) → US4(P1) → US5(P2) → Polish. 기반의 소유권 이동은 기존 행동을 보존하며, 이후 각 스토리는 별도의 수용 기준으로 완성한다. 모든 체크박스는 구현 단계에서 갱신한다.

## Format: `[ID] [P?] [Story] Description`

- `[P]`는 명시된 선행 작업 완료 후 서로 다른 파일에서 함께 진행할 수 있는 작업이다. 이전 단계의 의존성을 생략한다는 뜻이 아니다.
- `[US1]`~`[US5]`는 명세의 사용자 스토리이며 Setup·Foundational·Polish에는 붙이지 않는다.
- 경로는 저장소 루트 기준이며 모든 작업은 정확한 대상 파일을 명시한다.

## Path Conventions

기존 단일 Python 3.12+ 패키지 `src/algorithm_problem_picker/`와 `tests/`를 유지한다. 신규 제품 모듈은 `jungol_models.py`, `jungol_policy.py`, `platforms.py`, 신규 테스트 파일은 `tests/test_platforms.py`다. 배포 패키지·모듈 이름과 잠금 의존성을 유지한다. 영구 캐시·동적 플러그인 로더·범용 속성 엔진·테스트 전용 공개 API·실제 신규 사이트 수집기는 추가하지 않는다. 헌장 I·III의 제한적 예외는 `plan.md`의 근거를 따르고 헌장 원문은 변경하지 않는다.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 기존 환경·회귀 기준을 확인한다. 새 프로젝트 초기화나 의존성 업그레이드는 필요하지 않다.

- [X] T001 `pyproject.toml`·`uv.lock`·현재 브랜치와 `specs/005-platform-filter-validation/plan.md`의 범위를 확인하고, 준비된 잠금 환경에서 `uv run --locked pytest -q tests/test_cli.py tests/test_selection.py tests/test_service.py tests/test_jungol_dom.py tests/test_export_tool.py`로 기존 기준을 확인해 명령·리비전·환경·결과를 `specs/005-platform-filter-validation/quickstart.md`에 기록한다. 필요한 환경 준비만 수행하고 실제 사이트·기본 브라우저는 사용하지 않는다.

**Checkpoint**: 기존 실패·환경 제약을 기능 구현 실패와 구분할 수 있다.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 공통 흐름의 정올 결합을 분리하고 모든 스토리가 사용할 typed 정책·소스 조합을 준비한다. 이 단계 완료 전 사용자 스토리 작업을 시작하지 않는다.

- [X] T002 `src/algorithm_problem_picker/jungol_models.py`로 기존 `models.py`의 Problem·Rated·Unrated·SearchCriteria·UserReference·Status·SortKey와 관련 검증을 이동한다. 데이터 모델의 “기존 id/title/url/tier/pass_rate/accepted_count/listed_at 전체. 정올 URL과 번호의 일치 유지”, “1~30 확정 티어 / 정상 미정 티어. 기존 의미·검증 유지”, “기존 여섯 경계, status, user_handle. Decimal·수치 범위·경계 순서·핸들 정규화·사용자 조합 검증 유지”, “기존 handle/account_id/resolved_at. 숫자 계정 ID 규칙은 정올에만 적용”, “정올 입력 의미와 지원 값. 공통 정책의 전역 제약으로 사용하지 않음”을 적용한다. 기존 양의 정수 ID·유한 Decimal 0~100·0 이상 정수 제출 수·시간대·핸들 불변식과 enum 값을 약화하지 않으며 import 호환성만을 위한 재수출은 만들지 않는다.
- [X] T003 `src/algorithm_problem_picker/models.py`와 `src/algorithm_problem_picker/ports.py`에 ProblemRecord, PlatformInfo/FilterCapability, 불변 RawFilterInput, ValidatedRequest, ProblemLink, 제네릭 CompletedListing[P]/Result[P,C,U], PlatformPolicy[P,C,U]/ProblemSource[P,C,U]를 정의한다. 지원 정보는 “key는 정적 레지스트리에서 유일. 기본 제품 값은 jungol 하나. 외부 작업 없이 조회 가능”, “한 의미 그룹의 범위/기존 경계 이름을 명시. 허용 값은 플랫폼 정책과 같은 선언을 사용하며 설명만으로 별도 검증기를 만들지 않음”을 따른다. raw 필드는 “알려진 각 필터의 raw 문자열 또는 반복 범위 문자열 tuple. 플랫폼 숫자·enum으로 변환하기 전 값”, “Context 출처가 COMMANDLINE인 정확한 옵션 이름의 집합. 값의 truthiness로 추정하지 않음”을 따른다. 문제 프로토콜은 id/title/url/listed_at만 제공하며 “id(해시 가능한 플랫폼 내부 식별자)”에 수치·문자열 정렬을 강제하지 않는다. 완료 목록은 “공급자의 완료 기준을 만족한 뒤에만 생성하며 같은 id는 첫 관측 레코드를 보존한다.”를, 결과는 “현재 Result의 시간대·집계 순서·고유성·반환 개수·부족 불변식을 그대로 유지한다.”를 적용한다. user U 또는 None과 Known[T]·Unavailable·Order·진행 상태·오류 계열을 보존하고 소스 포트는 prepare_user/collect, 순수 정책 포트는 파싱·정렬 검증·필터·표시·링크를 제공한다.
- [X] T004 `src/algorithm_problem_picker/jungol_policy.py`로 `cli.py`의 정올 범위/티어/조건 파싱·표시·URL 규칙과 `selection.py`의 정올 filter_listing/sort_problems를 옮겨 순수 정책으로 묶는다. “정올 처리 순서는 `tier → rate → accepted`다.”와 “고유 문제당 첫 실패만 반영한다.”를 보존한다. 정책은 콘솔·소스·브라우저를 소유하지 않으며 기존 문법·필터·정렬 기대를 유지한다. 기존 CLI 호출부도 이동한 정책을 사용하도록 함께 조정해 중복 구현을 남기지 않는다.
- [X] T005 `src/algorithm_problem_picker/platforms.py`에 PlatformBinding[P,C,U]와 정적 레지스트리를 만들고 정올 지원 정보·순수 정책·지연 source_factory를 조립한다. tier/rate/accepted/사용자 그룹별 실제 옵션 이름·의미·단위·허용 값·조합·정렬 정보를 선언하고 retired_options를 분리한다. “다른 플랫폼이 일부 옵션만 지원하면 option_names에 명시한 것만 허용한다.”와 “미지원은 이 지원 정보의 부재이며 문제 값 sentinel이 아니다.”를 적용하며 기본 등록은 jungol 하나다. 정책/지원 정보 생성에 I/O를 넣지 않고 팩터리 호출을 실행 시점까지 지연한다. 구성 오류의 구체 검증은 T016에서 완성한다.
- [X] T006 `src/algorithm_problem_picker/service.py`·`src/algorithm_problem_picker/selection.py`·`src/algorithm_problem_picker/jungol.py`를 typed 포트에 연결한다. Picker는 조건 내부 필드를 읽지 않고 prepare_user → 완전 수집 → 정책 필터 → 정책 정렬 후 limit 또는 공통 중복 없는 recommend → Result를 한 흐름으로 처리한다. “None 사용자 참조는 사용자 조건을 요청하지 않은 정상 상태다.”와 “사용자 준비 결과가 None이 아닐 때만 UserResolved를 보고한다.”를 적용한다. 정올 prepare_user만 기존 resolve_user를 호출하며 DOM 본문·페이지/실패/정리 정책은 유지한다. 공통 서비스·selection에서 구체 정올 import/키 분기/티어 접근을 제거하고 첫 레코드 보존·전체 후보 random.sample·진행/실패/취소를 유지한다.
- [X] T007 `tests/conftest.py`·`tests/test_cli.py`·`tests/test_selection.py`·`tests/test_service.py`·`tests/test_jungol_dom.py`의 타입 import·고정 소스·정책/팩터리 주입·monkeypatch 위치를 새 소유 모듈에 맞춘다. 기존 행동 기대는 유지하고 일반 구성 경계에서 source factory·prepare_user/resolve_user·collect·브라우저 호출을 관측/차단한다. T001의 관련 회귀를 실행해 기준과 비교하고 `specs/005-platform-filter-validation/quickstart.md`에 결과를 기록한다. 테스트 전용 제품 API는 추가하지 않는다.

**Checkpoint**: 정올 모델/정책/접근의 책임이 분리되고 기존 회귀를 보존한다. 제네릭 공통 흐름과 지연 구성 경계가 준비됐다.

---

## Phase 3: User Story 1 - algo-pick에서 정올을 기본으로 사용하기 (Priority: P1) — MVP

**Goal**: 새 실행 이름과 루트 플랫폼 선택으로 기존 세 명령을 제공한다.

**Independent Test**: 동일 고정 목록에서 생략/명시 jungol × list/recommend/open의 6개 조합을 비교한다. 조회 조건·순서·집계, 추천 후보·개수·중복·부족, 고유 URL 전달과 help/version의 소스 미생성을 관측한다. 무작위 표본과 실행 시각 자체의 일치는 요구하지 않는다.

### Tests for User Story 1

- [X] T008 [US1] `tests/test_cli.py`에 기본/명시 jungol의 6개 조합과 루트/세 명령 help·version 검증을 먼저 추가한다. list 기본 20개·recommend 기본 1개·전체 후보 처리·사용자 조건·출력 스트림을 비교하고, open은 `1000 1000 1001`의 입력 순서 고유 URL·일부 실패에도 전 링크 시도·코드 1을 검증한다. 무효 ID가 중간에 있어도 브라우저 호출 0회이며 help/version/open은 source factory 0회임을 확인한다.

### Implementation for User Story 1

- [X] T009 [US1] `pyproject.toml`의 `[project.scripts]` 실행 키를 `algo-pick` 하나로 변경한다. 배포 이름 `algorithm-problem-picker`와 내부 모듈 이름은 유지하고 jpick 호환 키를 추가하지 않는다. 새 설치 메타데이터로 확인하며 기존 사용자 환경의 옛 launcher를 자동 삭제하지 않는다.
- [X] T010 [US1] `src/algorithm_problem_picker/cli.py`의 루트 callback에 명령 앞의 `--platform`과 기본 jungol 선택·Context 바인딩을 연결하고, `_run`에서 선택 팩터리의 단일 with → 공통 Picker → 공통 표시를 호출한다. 출력은 정책의 columns/format_row/format_conditions/observation_notes를 사용하며 “열 수와 행 길이의 일치는 내부 불변식이다.”를 assertion으로 확인한다. open은 raw ID 전체를 선택 정책으로 검증한 후 “입력 순서대로 중복 제거된 링크를 만든다.”를 적용하고 모든 고유 URL을 출력/전달한다. “중간 번호가 무효이면 아무 링크도 열지 않는다.”와 소스 미생성을 지키며 정올 URL 생성·모델 필드 접근을 CLI에서 제거한다. 기본/명시 플랫폼·실행 이름·옵션 위치를 루트 help에 안내하고 기존 코드 0/1/2/130·스트림을 보존한다.
- [X] T011 [US1] `src/algorithm_problem_picker/jungol_policy.py`에서 정올 링크 생성·행/조건·관측 주의 문구를 완성한다. 양의 정수 ID·URL 일치·티어 약칭/미정/미확인·정답률 원래 Decimal 정밀도·중복 정답 제출 의미를 유지하고 정올의 기존 표·조건·주의 문구를 재현한다.
- [X] T012 [US1] `tests/test_cli.py`의 US1 사례와 관련 `tests/test_service.py`를 실행하고 `uv run --locked algo-pick --version`·루트/세 명령 help 및 새 설치 console_scripts가 `{'algo-pick'}`인지 확인해 `specs/005-platform-filter-validation/quickstart.md`에 기록한다. 메타데이터가 오래됐으면 해당 패키지만 재설치하고 무관한 잠금 변경은 만들지 않는다.

**Checkpoint**: US1의 새 명령·기본/명시 정올 6개 흐름을 독립 시연할 수 있다. 전체 기능 완료를 뜻하지 않는다.

---

## Phase 4: User Story 2 - 미지원 플랫폼과 필터를 접속 전에 확인하기 (Priority: P1)

**Goal**: 명시한 모든 미지원 필터를 값 해석보다 먼저 알리고 외부 작업 전에 실패한다.

**Independent Test**: unknown/빈 이름/programmers와 합성 플랫폼의 미지원 범위·하한·상한·사용자 옵션·복수 옵션을 두 명령에서 거부한다. 플랫폼+실제 옵션명·stderr·코드 2·결과 없음과 양쪽 source factory/사용자 조회/수집/브라우저 0회를 확인한다.

### Tests for User Story 2

- [X] T013 [US2] `tests/test_platforms.py`에 일반 레지스트리 구성 경계로만 주입하는 비공개 합성 모델·정책·고정 소스·호출 기록을 준비하고 미지원 입력 계약을 먼저 검증한다. 합성 난도 100~200과 다른 URL을 사용하며 accepted/사용자 조건을 미지원으로, 복수 오류 사례에서는 tier/rate도 미지원으로 선언한다. 두 명령에서 범위/기존 min/max·0·명시적 `--status all`·`--user ''`·복수 미지원·무효/반복 값과 폐기 입력 혼합을 검사하고 생략 기본값은 허용한다. unknown/빈 이름/programmers는 세 명령에서 거부한다. 모든 외부 호출 0회·stdout 결과 없음·코드 2와 플랫폼/옵션명을 관측하며 구성 오류(중복 키·옵션 중복 소유·미정의 연결·출력 불일치·기본 누락)는 초기 경고와 영향받은 실행 코드 1을 검증한다. 테스트 종료 후 제품 등록은 jungol 하나여야 한다.

### Implementation for User Story 2

- [X] T014 [P] [US2] `src/algorithm_problem_picker/cli.py`의 모든 필터를 raw 문자열·반복 범위 목록으로 받고 하위 `typer.Context.get_parameter_source(name)`의 공개 결과 `name == 'COMMANDLINE'`에서 정확한 supplied_options를 구성한다. 데이터 모델의 “값이 0·빈 문자열·all이어도 명시 여부를 보존한다.”, “범위는 모든 출현을 보존하고 지원 검사 후 반복을 거부한다.”, “기존 단일 경계 옵션 반복은 현재 파서의 동작을 유지한다.”를 적용한다. 자동 int/Status 변환과 eager 반복/legacy callback을 제거해 지원 검사 뒤로 이동하고 출처 누락은 내부 assertion으로 다룬다. argv 재파싱·별도 Click/private enum import는 하지 않는다.
- [X] T015 [US2] `src/algorithm_problem_picker/cli.py`의 list/recommend 공통 진입에서 선택 확인 → 명시 필터 전체 지원 검사 → 정책 값/조합 파싱·공통 비필터 검증 → 팩터리 호출 순서를 강제한다. 미지원은 원래 옵션명을 중복 없이 전부 stderr에 플랫폼 이름과 출력하고 코드 2로 끝낸다. retired_options는 지원 필터로 승격하지 않고 전체 미지원 검사 뒤 전용 거부 진단으로 전달한다. 빈/오타/대소문자 변형/미등록 플랫폼은 가능한 값 안내와 코드 2로 거부한다. 값 누락·알 수 없는 옵션은 기존 Typer 문법 오류에 맡기며 오류 시 진행/결과를 출력하지 않는다. T014 이후 수행한다.
- [X] T016 [P] [US2] `src/algorithm_problem_picker/platforms.py`에서 “등록 시 중복 플랫폼 키·한 옵션의 중복 소유·정의하지 않은 옵션 연결·지원 속성과 출력 선언 불일치를 검사한다.”를 구현한다. “구성 오류는 초기화 때 경고하고 해당 플랫폼 사용 시 실패한다.”와 “기본 플랫폼 누락을 다른 플랫폼 선택으로 숨기지 않는다.”를 적용하고 사용자 오타 코드 2와 내부 구성 코드 1을 구분한다. T013의 실패 검증 후 T014와 병렬 진행할 수 있다.
- [X] T017 [US2] `tests/test_platforms.py`의 미지원/구성 오류 사례와 `tests/test_cli.py`의 입력 오류 회귀를 실행해 두 명령·세 플랫폼 오류 흐름의 진단/우선순위/외부 호출 0회를 확인하고 `specs/005-platform-filter-validation/quickstart.md`에 기록한다. 유효하지 않은 비필터 옵션이 함께 있을 때의 우선순위는 고정하지 않는다.

**Checkpoint**: 생략과 명시적 기본값을 구분하며 잘못된 미지원 값이 지원 검사보다 먼저 해석되지 않는다.

---

## Phase 5: User Story 3 - 선택한 플랫폼의 의미에 맞게 조건 입력하기 (Priority: P1)

**Goal**: 정올의 문법을 보존하면서 값·정렬·도움말을 선택 플랫폼의 규칙으로 처리한다.

**Independent Test**: 정올의 기존 유효/무효 범위·사용자 조건·legacy 안내와 합성 난도 100~200의 유효/무효 판정을 실제 CLI로 확인한다. 오류는 플랫폼·옵션·이유·코드 2와 source 미생성을, 도움말은 선택 플랫폼 규칙·미지원 안내·팩터리 0회를 확인한다.

### Tests for User Story 3

- [ ] T018 [P] [US3] `tests/test_cli.py`의 기존 범위/경계/사용자/정렬 회귀를 보존하고 이동 과정의 빈틈만 보완한다. B5~R1 대소문자/1~30, 열린/닫힌/동일 경계, Decimal 정밀도, 역전·100 초과·반복·혼용·사용자 조합·random+desc·개수 오류·legacy 전환을 확인한다. 기존 accepted 경계의 `+1`·공백·전각 숫자·`1_000` 허용과 새 범위 ASCII 문법의 차이도 확인하고 오류의 플랫폼·옵션·이유 및 외부 작업 0회를 관측한다.
- [ ] T019 [P] [US3] T013의 합성 구성을 재사용해 `tests/test_platforms.py`에 정올 밖 난도 100~200의 유효/무효 입력·미지원 정렬 거부·자체 의미/단위 표시와 선택 플랫폼 help 검증을 추가한다. 루트/하위 help·version에서 팩터리 0회, 합성 help에서 정올 규칙을 지원 규칙으로 안내하지 않음, 순차 플랫폼 help 실행 간 전역 설명 오염 없음도 확인한다.

### Implementation for User Story 3

- [ ] T020 [US3] `src/algorithm_problem_picker/jungol_policy.py`의 parse_filters/validate_list_options를 완성한다. 데이터 모델의 “raw 필드에는 아직 의미 검증된 숫자라는 가정을 두지 않는다.”와 “필터와 정렬은 서로 다른 지원 항목이다.”를 적용한다. B5~R1/1~30·유한 Decimal 0~100·0 이상 제출 수·양 끝 포함·적어도 한 경계·하한≤상한·신구 혼용/범위 반복 금지·all/solved/unsolved·정확한 핸들·선행 @ 한 개·대소문자 보존을 유지한다. 기존 경계는 int(text)의 허용 문법을 보존하고 새 범위의 엄격한 문법을 확대 적용하지 않는다. retired_options와 `--sort solvers`는 대체 옵션·지표 변경을 안내한 뒤 반드시 거부한다. 정책 오류에 실제 옵션·이유를 담아 CLI가 플랫폼 이름과 코드 2로 표시하도록 한다.
- [ ] T021 [US3] `src/algorithm_problem_picker/cli.py`의 공통 옵션 설명을 플랫폼 중립으로 정리하고 eager `--help` callback(`expose_value=False`)에서 `ctx.get_help()`와 선택 바인딩의 지원 필터·미지원 옵션·의미·단위·허용 값·조합·정렬 안내를 출력한다. 본문/소스 실행 전에 종료하며 command 전역 help를 변이하지 않는다. 정올 규칙과 help는 같은 지원 선언을 사용하고 루트 help는 실제 등록 jungol만 안내한다.
- [ ] T022 [US3] `tests/test_cli.py`·`tests/test_platforms.py`의 US3 사례를 실행하고 `algo-pick --platform jungol list --help`·`recommend --help`의 실제 표시도 확인해 정올 문법 회귀와 합성 규칙 격리 결과를 `specs/005-platform-filter-validation/quickstart.md`에 기록한다.

**Checkpoint**: 플랫폼별 값 해석과 도움말이 일치하며 정올 규칙이 합성 플랫폼에 강제되지 않는다.

---

## Phase 6: User Story 4 - 속성 미지원과 개별 값 미제공을 구분하기 (Priority: P1)

**Goal**: 정올의 0·미제공·미정 티어·첫 실패 집계를 보존하고 미지원 속성은 후보/결측 집계/열에서 분리한다.

**Independent Test**: 고정 정올 목록의 통계 0/양수/미제공·미정/미확인/범위 밖 확정 티어·중복 문제에 필터 유무를 조합한다. 고유 적격/제외 수·양방향 정렬·미확인 표시·빈 결과/부족 코드 0을 확인하고 합성 플랫폼의 미지원 열/집계 부재를 확인한다.

### Tests for User Story 4

- [ ] T023 [P] [US4] `tests/test_selection.py`의 이동한 정올 정책 회귀를 재사용해 통계 필터 생략/0..0·미제공·중복 첫 레코드·첫 실패 tier→rate→accepted·앞선 수치 탈락 뒤 결측 미집계·Unrated와 Unavailable 차이·검색 경계 밖 Rated 보존을 확인한다. 기존 정렬 동점/양방향 결측 위치·전체 후보 정렬 후 제한·중복 없는 공통 추천 기대를 유지하고 부족한 사례만 추가한다.
- [ ] T024 [P] [US4] `tests/test_cli.py`에서 두 명령의 실제 0/미확인/미정 표시·고유 제외 수 stderr·정상 빈 결과/추천 부족 코드 0을 검증한다. 기존 실패/취소 코드 1/130·부분 stdout 결과 없음도 유지하며 정책 추출로 이미 통과하는 사례는 재작성하지 않는다.

### Implementation for User Story 4

- [ ] T025 [US4] `src/algorithm_problem_picker/jungol_policy.py`의 값 상태·필터/정렬 경계를 점검하고 T023/T024에서 드러난 회귀를 수정한다. “해당 필터 있으면 기존 순서로 제외·집계, 없으면 다른 조건 만족 시 포함하고 미확인”, “정상 숫자. 0..0 조건 통과, 미제공으로 취급하지 않음”, “기존 미정 표시, 티어 조건에서는 제외하되 미제공 제외 수에 넣지 않음”을 적용한다. “범위 밖 Rated 티어는 사이트 검색과 표시 값의 차이를 보존하며 다시 수치로 제외하지 않는다.”를 유지하고 전역 결측 사전 집계를 만들지 않는다.
- [ ] T026 [US4] `src/algorithm_problem_picker/cli.py`에서 정책이 반환한 열/행/조건만 렌더링하고 “필터 명시 시 코드 2. 생략 시 제외/미제공 집계 없음, 해당 출력 열 생략”을 플랫폼 미지원 속성에 적용한다. 개별 미제공만 정책의 미확인 문자열을 사용하며 공통 표시에 가짜 정올 필드·정올 전용 주의 문구를 주입하지 않는다. 빈 결과·부족·시각·진행·집계·오류의 기존 출력 채널과 종료 코드를 유지한다.
- [ ] T027 [US4] `tests/test_selection.py`·`tests/test_cli.py`·`tests/test_platforms.py`의 값 상태/출력 사례를 실행해 정올 후보/집계 보존과 합성 플랫폼의 미지원 열·결측 집계 부재를 확인하고 `specs/005-platform-filter-validation/quickstart.md`에 기록한다. 합성 표시 검증이 없으면 같은 `tests/test_platforms.py`의 고정 목록 사례를 보완한다.

**Checkpoint**: 미지원과 미제공이 구분되고 0·티어 검색 의미·고유 제외 수·정상 빈 결과가 보존된다.

---

## Phase 7: User Story 5 - 공통 사용 흐름을 유지하며 플랫폼 연결하기 (Priority: P2)

**Goal**: 제품에 새 사이트를 추가하지 않고 합성 바인딩 하나로 동일 세 명령과 공통 추천 흐름의 확장성을 입증한다.

**Independent Test**: T013의 합성 구성으로 자체 모델/조건·난도 100~200·다른 URL·일부 미지원 필터를 제공한다. 실제 list/recommend/open이 정올 호출 없이 실행되고 공통 sample·전체 후보·고유성/부족·정리 정책을 사용함을 확인한다.

### Tests for User Story 5

- [ ] T028 [P] [US5] `tests/test_platforms.py`에서 기존 합성 fixture를 확장해 동일 CLI의 list/recommend/open 완전 흐름을 검증한다. 자체 typed 문제/조건·정올과 같은 ID의 다른 URL·중복 ID 첫 레코드·전체 적격 후보·공통 selection의 sample 호출·고유 추천/부족을 관측한다. 합성 전용 CLI/Picker/recommend 없이 구성만 주입하고 정올 소스/사용자 조회/정올 URL 전달 0회, open의 팩터리 0회와 테스트 후 jungol 단독 등록을 확인한다.
- [ ] T029 [P] [US5] `tests/test_service.py`의 고정 소스를 제네릭 정책 계약에 맞춰 재사용하고 prepare_user가 None인 정상 흐름·None이 아닌 참조에서만 UserResolved 보고·완료 전 필터/정렬/sample 0회·소스 진입/식별/수집 실패·Ctrl+C에서 정리/부분 결과 금지를 확인한다. 기존 오류별 회귀 기대를 유지하고 `tests/test_platforms.py`와 동일한 성공 시나리오를 중복 작성하지 않는다.

### Integration for User Story 5

- [ ] T030 [US5] `src/algorithm_problem_picker/service.py`·`src/algorithm_problem_picker/selection.py`·`src/algorithm_problem_picker/ports.py`·`src/algorithm_problem_picker/platforms.py`의 조합을 T028/T029로 검증하고 남은 계약 위반을 수정한다. 공통 service/selection에 정올 import·플랫폼 키 분기·조건 필드 해석이 없는지 확인하며 문제/조건을 `dict[str, Any]`로 바꾸거나 모델 검증을 제거하지 않는다. 합성 구성에 필요한 연결은 기존 일반 경계로 해결하고 테스트 전용 공개 API는 만들지 않는다. 결과와 FR-016/SC-005의 관측 근거를 `specs/005-platform-filter-validation/quickstart.md`에 기록한다.

**Checkpoint**: 지원 정보·정책·팩터리·링크 조합만으로 동일 세 명령과 공통 추천을 재사용할 수 있다.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: 현재 사용 자료·내보내기·최종 수용 결과를 정합화한다.

- [ ] T031 [P] `README.md`의 현재 실행 예시를 algo-pick으로 변경하고 `--platform`의 명령 앞 위치·jungol 기본값/단독 실지원·기본 조회/명시 추천/직접 열기 예시·지원 필터/값/미지원 오류와 jpick 실행 키 변경을 안내한다. 패키지/모듈 이름·정올 데이터 의미는 유지하며 프로그래머스 수집이 제공된다고 쓰지 않는다.
- [ ] T032 [P] `docs/integration.md`·`docs/standalone.md`의 설치/실행/배포 예시를 algo-pick·`tools/algo-pick`으로 정리하고 플랫폼 위치·기본값·필터 지원 확인법·새 수집기 미제공 범위를 맞춘다. 과거 specs/검증 이력을 일괄 개명하거나 기존 외부 복사본 폴더를 이동하지 않는다.
- [ ] T033 [P] `examples/vscode/tasks.json`·`scripts/export_tool.py`의 현재 실행 이름/예시 폴더/도움말을 algo-pick으로 변경하고 VS Code input ID와 참조를 함께 맞춘다. `tests/test_export_tool.py`의 기존 템플릿 경로 기대·fixture만 필요한 만큼 조정해 새 모듈을 포함하는 기존 src 전체 내보내기·무덮어쓰기·해시/메타데이터·캐시/환경 제외 계약을 재사용한다. 문서 전용 테스트는 추가하지 않는다.
- [ ] T034 `specs/005-platform-filter-validation/quickstart.md`의 기본 수용을 수행한다. 관련 `tests/test_platforms.py`·`tests/test_cli.py`·`tests/test_selection.py`·`tests/test_service.py`·`tests/test_export_tool.py` 확인 후 `uv run --locked pytest -q`를 한 번 실행하고 설치 console_scripts·help/version·접속 없는 오류·현재 문서/VS Code 참조를 점검한다. 기존 환경이 허용하면 존재하지 않는 `dist/algo-pick-005-validation` 또는 다른 새 경로로 `scripts/export_tool.py`를 실행해 독립 복사본 sync·새 명령 version/help를 확인한다. `plan.md`의 FR-001~016/SC-001~006 추적표에 맞춰 실제 결과·환경 제약·선택적 미실행을 quickstart에 기록한다. 기본 수용은 원격/실제 브라우저 호출 없이 완료하며 선택적 실사이트 절차는 별도로 구분한다. 새 변경·실패가 없으면 전체 검증을 반복하지 않는다.

**Checkpoint**: 현재 사용자 자료와 설치 실행 키가 일치하고 모든 스토리의 실제 검증 근거가 남는다.

---

## Dependencies & Execution Order

### Phase Dependencies

1. Setup T001 이후 Foundational T002 → T003 → T004 → T005 → T006 → T007을 수행한다. 소유권 이동 중 같은 파일을 수정하므로 기반 작업은 순차 진행한다.
2. US1은 기반 이후 T008 → T009 → T010 → T011 → T012로 진행한다. US1 완료가 새 CLI를 이용하는 후속 수용 검증의 기준이다.
3. US2는 US1 이후 T013 → (T014와 T016 병렬 가능) → T015 → T017로 진행한다. T015는 T014에 의존하며 T017은 두 구현 경로 완료를 기다린다.
4. US3은 US2 이후 T018/T019 병렬 → T020 → T021 → T022로 진행한다. 값 해석 전에 지원 검사가 보장돼야 한다.
5. US4는 US3 이후 T023/T024 병렬 → T025 → T026 → T027로 진행한다. T027은 T013의 합성 구성도 재사용한다.
6. US5는 US4 이후 T028/T029 병렬 → T030으로 진행한다. 실제 확장 경계 구현은 기반과 US1~4에서 제공하며 이 스토리는 추가 사이트 없이 끝까지 검증한다.
7. Polish T031/T032/T033은 US5 이후 서로 병렬 진행 가능하다. T034는 모든 변경 완료 후 수행한다.

### User Story Dependency Graph

```text
Setup → Foundational → US1 (P1, 내부 MVP) → US2 (P1) → US3 (P1) → US4 (P1) → US5 (P2)
                                                                               ↓
                                                        T031 || T032 || T033 → T034
```

스토리의 검증 기준은 독립적이지만, 이 기존 코드 리팩터링은 같은 CLI/정책/테스트 파일을 공유하므로 구현 순서는 위처럼 직렬화한다. 스토리 전체를 서로 무조건 병렬 실행하지 않는다. US2에서 만든 합성 fixture는 US3~5가 같은 일반 구성 경계를 검증하는 데 재사용한다.

### Within Each User Story

- 새 계약 테스트를 먼저 작성하고 미구현 부분의 실패 이유를 확인한다. 기존 보존 회귀는 계속 통과해야 한다.
- 모델/포트 → 순수 정책/서비스 → CLI 연결 → 실제 출력/호출 관측 순서를 유지한다.
- `[P]`가 없는 같은 파일 작업은 동시에 수행하지 않는다. 각 체크포인트에서 관련 검증만 실행하고 최종 전체 회귀는 T034에 모은다.

### Parallel Opportunities

- US1은 `cli.py`·정올 정책 연결과 설치 메타데이터를 순차 완성하므로 스토리 내부 병렬 작업을 지정하지 않는다.
- US2: T013 이후 CLI raw 입력 T014와 registry 구성 검증 T016.
- US3: `tests/test_cli.py`의 정올 회귀 T018과 `tests/test_platforms.py`의 합성 규칙 T019.
- US4: `tests/test_selection.py`의 정책 회귀 T023과 `tests/test_cli.py`의 표시 회귀 T024.
- US5: `tests/test_platforms.py`의 세 명령 계약 T028과 `tests/test_service.py`의 생명주기 계약 T029.
- Polish: README T031, 가이드 T032, VS Code/export T033. quickstart 결과 기록 작업은 병렬로 수정하지 않는다.

## Parallel Example: User Story 1

```text
병렬 지정 없음: T008 → T009 → T010 → T011 → T012
같은 CLI/정책 연결이 완성된 뒤 6개 실행 조합을 함께 검증한다.
```

## Parallel Example: User Story 2

```text
선행: T013 완료
Task T014: src/algorithm_problem_picker/cli.py의 raw 값·명시 출처 수집
Task T016: src/algorithm_problem_picker/platforms.py의 구성 오류 검증
이후 T015에서 CLI 지원 검사 순서를 연결하고 T017에서 통합 검증
```

## Parallel Example: User Story 3

```text
선행: US2 완료
Task T018: tests/test_cli.py의 정올 값·문법 회귀
Task T019: tests/test_platforms.py의 합성 값·정렬·help 계약
이후 T020/T021 구현과 T022 검증
```

## Parallel Example: User Story 4

```text
선행: US3 완료
Task T023: tests/test_selection.py의 값 상태·첫 실패·정렬 회귀
Task T024: tests/test_cli.py의 0/미확인/빈 결과·스트림 회귀
이후 T025/T026 점검·수정과 T027 검증
```

## Parallel Example: User Story 5

```text
선행: US4 완료
Task T028: tests/test_platforms.py의 동일 세 명령·공통 sample 경로
Task T029: tests/test_service.py의 제네릭 사용자 준비·완료·실패 생명주기
이후 T030에서 실제 조합·격리 검증
```

## Implementation Strategy

### MVP First (User Story 1 Only)

1. T001~T007로 기존 행동을 보존하며 공통 기반을 준비한다.
2. T008~T012로 새 실행 이름·기본/명시 정올 세 명령을 완성한다.
3. 고정 공급자로 US1을 독립 검증한다. 이는 내부 MVP 확인 지점이며 미지원 검사·의미/결측·확장 계약의 최종 완료는 아니다.

### Incremental Delivery

1. US2에서 명시 입력과 지원 여부를 값 해석 전에 검증한다.
2. US3에서 정올/합성 값 의미·정렬·도움말을 연결한다.
3. US4에서 미지원/미제공/0·티어 검색·고유 집계 보존을 검증한다.
4. US5에서 실제 신규 수집기 없이 동일 명령/추천 경로 확장을 입증한다.
5. T031~T034로 사용자 자료·내보내기·최종 전체 회귀와 검증 기록을 완성한다.

### Parallel Team Strategy

여러 구현자가 있는 경우 위에 명시한 5개 병렬 묶음만 분담하고 공통 파일 변경은 합친 뒤 다음 단계로 넘어간다. 이 문서의 병렬 예시는 실행 가능성을 설명하며 현재 작업 목록 생성 단계에서 구현이나 에이전트 실행을 요청하지 않는다.

## Notes

- 총 34개 작업: Setup 1, Foundational 6, US1 5, US2 5, US3 5, US4 5, US5 3, Polish 4.
- `[P]` 작업은 11개이며 US2·US3·US4·US5·Polish의 5개 병렬 묶음에 속한다.
- 모든 제품 입력 검증은 외부 작업 전에 완료한다. help/version/open은 조회용 팩터리를 생성하지 않는다.
- 실제 프로그래머스 지원·자동 탐색·영구 캐시·기존 외부 폴더 이동·헌장 원문 개정은 이 목록에 없다.
- 검증 결과는 실행한 사실만 기록한다. 환경 제약이나 선택적 미실행을 성공으로 표시하지 않는다.
