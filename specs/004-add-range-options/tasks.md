# Tasks: 티어·정답률·정답 제출 수 범위 옵션 추가

**Input**: `specs/004-add-range-options/`의 설계 문서
**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [CLI 계약](contracts/cli.md), [quickstart.md](quickstart.md)
**Branch**: `004-add-range-options`
**Created**: 2026-10-28

**Tests**: 명세 SC-002~005와 계획의 행동 검증을 충족하기 위해 테스트 작업을 포함한다. 테스트는 실제 CLI 인자→고정 공급자→Picker/selection→결과·진단을 검증한다. 파서 내부 구현을 복제하거나 동일 문법을 DOM 테스트에 반복하지 않는다.

**Organization**: 공통 기반 이후 US1(P1) → US2(P2) → US3(P2) 순으로 완성한다. 각 스토리의 테스트를 구현보다 먼저 작성하고 관련 검증을 수행한다. 이미 공통 기반으로 통과하는 사례는 보존하며, 일부러 실패하도록 코드를 훼손하지 않는다. 새 미구현 동작의 실패와 기존 동작의 통과를 구분해 기록한다.

## Format: `[ID] [P?] [Story] Description`

- 모든 작업은 체크박스·연속 ID·정확한 파일 경로를 가진다.
- `[P]`는 의존 선행 작업이 끝난 뒤 서로 다른 파일에서 병렬 진행할 수 있다는 뜻이다.
- `[US1]`·`[US2]`·`[US3]`은 명세의 사용자 스토리다. Setup·Foundational·Polish에는 붙이지 않는다.
- 아래 경로는 저장소 루트 기준이다. 작업 완료 표시와 실행 결과 기록은 구현 단계에서 갱신한다.

## Path Conventions

기존 단일 Python 패키지를 유지한다. 제품 변경은 `src/algorithm_problem_picker/cli.py`, 행동 검증은 `tests/test_cli.py`, 사용 안내는 `README.md`에 집중한다. 실행 근거는 `specs/004-add-range-options/quickstart.md`에 남긴다. 새로운 의존성·공개 Range 모델·영구 캐시·별도 테스트 전용 API는 추가하지 않는다.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 현재 환경과 회귀 기준을 확인한다. 새 프로젝트나 의존성을 초기화하지 않는다.

- [X] T001 `pyproject.toml`·`uv.lock`과 활성 `.specify/feature.json`·브랜치를 확인하고, 이미 준비된 Python 3.12+/잠금 환경에서 `uv run --locked pytest -q tests/test_cli.py`로 기존 CLI 기준을 확인한 명령·리비전·결과를 `specs/004-add-range-options/quickstart.md`에 기록한다. 환경이 준비돼 있으면 의존성 설치를 반복하지 않는다.

**Checkpoint**: 기존 CLI 회귀 기준과 환경 문제가 구분돼 있고 004 설계 문서를 기준으로 구현할 수 있다.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 세 지표와 두 명령이 공유할 비공개 입력 처리 기반을 준비한다. 기존 도메인·서비스는 변경하지 않는다.

- [X] T002 `src/algorithm_problem_picker/cli.py`에 세 새 옵션이 공유할 Typer `list[str]` 옵션 선언 규칙과 출현 횟수 callback을 준비한다. `data-model.md`의 “각 새 옵션의 기본값은 빈 목록이다.”와 “0개는 생략, 1개는 범위 해석 대상, 2개 이상은 입력 오류다.”를 적용하고 수신/기본 목록을 수정하지 않는다. 반복 오류는 해당 옵션명을 포함한 BadParameter로 전달하며 원시 argv나 `typer._click`을 직접 다루지 않는다.
- [X] T003 `src/algorithm_problem_picker/cli.py`에 `..` 분리·경계 전체 문법 검사·해석된 경계 쌍을 반환하는 비공개 공통 helper를 추가한다. “`None`은 생략된 경계다. 실제 숫자 0과 구분해야 한다.”와 “새 옵션이 지정되면 적어도 한 경계가 있어야 한다. 양쪽 경계가 있으면 하한≤상한이어야 한다.”를 적용한다. “따옴표를 제거한 셸 인자 그대로 검사한다. trim·기호 제거·자동 보정은 하지 않는다.”를 적용한다. 숫자는 ASCII, 정수 문법은 `[0-9]+`, 정답률 문법은 `[0-9]+(?:\.[0-9]+)?`로 한정하고 단일값·추가 구분자·공백·자동 보정을 허용하지 않는다. CLI 밖에 새 타입이나 검사를 전파하지 않는다.

**Checkpoint**: 출현 횟수·문법·경계 생략을 공통 처리할 기반이 준비됐다. 사용자에게 옵션을 노출하는 연결과 외부 동작 검증은 US1에서 수행한다.

---

## Phase 3: User Story 1 - 하나의 옵션으로 각 지표의 범위 지정하기 (Priority: P1) — MVP

**Goal**: 두 명령에서 세 새 옵션의 닫힌 범위를 기존 min/max 조건에 연결하고 같은 목록에 대한 조회·추천 의미를 유지한다.

**Independent Test**: 고정 목록에서 두 명령 × 세 지표의 6개 닫힌 범위 조합과 복수 지표를 기존 옵션과 비교한다. 동일 SearchCriteria·적격 후보·조회 순서/개수를 확인하고, 추천은 같은 후보 집합 안에서 개수·중복·부족을 확인한다.

### Tests for User Story 1

- [X] T004 [US1] `tests/test_cli.py`에 기존 `source_factory`·`problem`을 재사용한 두 명령 × 세 지표의 6개 닫힌 범위 계약 검증과 세 지표 동시 사용 검증을 먼저 추가한다. 499/500/750/1000/1001 제출 수, 40.49/40.5/60.25/80/80.01 정답률로 경계 포함을 확인하고 기존 표기와 같은 SearchCriteria·조건 출력·정렬·표시 제한·추천 개수/후보/부족을 관측한다. 티어 범위 밖 Rated 보존과 사용자 풀이 조건·정렬 옵션의 조합도 포함하며, 새로운 옵션이 연결되기 전 실패 이유를 확인한다.

### Implementation for User Story 1

- [X] T005 [US1] `src/algorithm_problem_picker/cli.py`의 공통 해석기에 지표별 변환·수치 제한·경계 역전을 연결한다. 모델 표의 tier “int 또는 None”·“1~30”, rate “Decimal 또는 None”·“0~100”, accepted “int 또는 None”·“0 이상”을 그대로 적용하고 “소수는 정답률에서만 허용하며 Decimal로 직접 변환한다.”를 지킨다. 해당 옵션의 param_hint와 오류 이유를 제공하고 `models.py`의 기존 불변식 검증을 유지한다.
- [X] T006 [US1] `src/algorithm_problem_picker/cli.py`의 `list_command`·`recommend`에 `--tier`·`--rate`·`--accepted`를 추가하고 공통 `_criteria` 생성 경로에서 해석된 경계를 기존 여섯 min/max 필드에 합류시킨다. 세 옵션을 함께 쓸 수 있게 하고 기존 여섯 옵션·status/user·정렬·개수·`_present`의 조건 표시를 보존한다. 입력 검사가 끝난 후에만 `_run`으로 진입하며 `jungol.py`·`service.py`·`selection.py`에 새 필터를 추가하지 않는다.
- [X] T007 [US1] `tests/test_cli.py`의 T004 신규 사례와 기존 관련 사례를 실행해 닫힌 범위·복수 지표·추천·출력 동등성을 확인하고 명령·성공/실패·미실행 근거를 `specs/004-add-range-options/quickstart.md`에 기록한다. 시각과 무작위 개별 표본 자체를 비교하지 않는다.

**Checkpoint**: US1을 단독 시연할 수 있다. 기존 여섯 경계 옵션 대신 세 범위 옵션으로 같은 조건을 지정한다. 이는 내부 MVP 확인 지점이며 전체 기능 완료나 배포 요청을 뜻하지 않는다.

---

## Phase 4: User Story 2 - 필요한 경계만 입력하고 기존 명령 유지하기 (Priority: P2)

**Goal**: 열린 범위와 같은 경계를 지원하고 옵션 생략·0·미제공·기존 명령·서로 다른 지표의 표기 혼합을 보존한다.

**Independent Test**: 두 명령 × 세 지표 × 하한만/상한만의 12개 조합을 기존 표기와 비교한다. US1의 6개와 합쳐 기본 18개 조합을 충족하고, 같은 경계·정상 빈 결과·기존 옵션만 사용하는 경우를 추가 확인한다.

### Tests for User Story 2

- [X] T008 [US2] `tests/test_cli.py`에 12개 열린 범위 조합을 먼저 추가하고 `0..0`, `1..1`, `30..30`, `47.45..47.45`, 실제 0/미제공 구분·고유 제외 수·모두 제외·추천 부족을 검증한다. 새 옵션 생략 시 여섯 경계와 기본값 보존, 기존 옵션만 사용하는 성공/오류·전환 경고 없음, 서로 다른 지표의 신·구 표기 혼용, 등호/일반 값 전달과 새 표기 순서 변경을 기존 조건·출력과 비교한다. 파서 함수 단위 검증 대신 공개 CLI 경로를 사용한다.

### Implementation for User Story 2

- [X] T009 [US2] `src/algorithm_problem_picker/cli.py`의 범위 해석·`_criteria` 연결을 완성해 열린 경계와 미지정 지표를 보존한다. “새 옵션이 생략되면 같은 지표의 기존 min/max 값을 사용한다.”와 “새 옵션이 없는 지표는 기존 문법과 검증을 따른다. 새 옵션의 엄격한 문법을 기존 옵션에 소급하지 않는다.”를 적용한다. 0을 거짓값으로 생략하지 않고 Decimal을 반올림하지 않으며, 기존 `Result.criteria`와 min/max 조건 출력에 생략 경계를 추가하지 않는다.
- [X] T010 [US2] `tests/test_cli.py`의 US1·US2 사례를 실행해 기본 18개 조합·같은 경계·0/미제공·기존 명령·혼합 표기의 조건/후보/출력 동등성을 확인하고 `specs/004-add-range-options/quickstart.md`에 결과를 기록한다. 서비스·필터의 이미 검증된 로직을 복제하는 테스트나 DOM 문법 테스트를 추가하지 않는다.

**Checkpoint**: US2의 열린 범위·호환성 가치를 고정 목록으로 독립 검증할 수 있고 US1의 닫힌 범위가 계속 통과한다.

---

## Phase 5: User Story 3 - 잘못된 범위를 조회 전에 고치고 사용법 확인하기 (Priority: P2)

**Goal**: 잘못된 범위·같은 지표의 표기 충돌·반복을 명확하게 거부하고 두 도움말과 README로 새 문법을 안내한다.

**Independent Test**: 두 명령에서 오류의 종료 2·옵션명·이유·공급자 미생성·결과 없음과 도움말/README 계약 일치를 확인한다. 문법 오류에는 예시, 혼용에는 충돌 옵션을 확인한다.

### Tests for User Story 3

- [X] T011 [US3] `tests/test_cli.py`에 두 명령·세 옵션의 잘못된 입력과 충돌 계약 검증을 먼저 추가한다. 값 누락·빈 문자열/`--name=`·`..`·단일 숫자·구분자 오류·음수/수치 초과/역전·정답률 외 소수·부호/쉼표/%/공백/지수/비ASCII/이름/NaN/Infinity를 다루고, 같은 지표 min/max 각각과의 혼용을 양쪽 순서·같은 값·기존 값 0·한쪽씩 보완하는 경우에도 검증한다. 같은 값/다른 값 및 등호/일반 표기 반복도 종료 2로 확인하며, 모든 오류에서 source_factory 호출 없음·stdout 결과 없음·조회 시작 안내 없음을 확인한다.
- [X] T012 [US3] `tests/test_cli.py`에 `list --help`·`recommend --help` 계약 검증을 추가해 세 새 옵션·여섯 기존 옵션·닫힌/열린 범위·수치/최대 1회/혼용 제한·사이트 티어 의미를 확인한다. 옵션명과 이유, 전달된 값의 문법 오류 예시, 혼용 진단의 충돌 옵션, 숨겨진 solver 거부와 help/version의 공급자 미생성도 검증하며 새 미구현 진단·도움말의 실패를 확인한다.

### Implementation for User Story 3

- [X] T013 [US3] `src/algorithm_problem_picker/cli.py`의 공통 조건 생성에서 “새 옵션이 있고 같은 지표의 기존 경계 중 하나라도 None이 아니면 충돌이다.”를 적용한다. callback의 반복 검사와 공통 범위 해석기의 문법·수치·순서 진단을 T011~T012 계약에 맞춰 완성하고 정확한 옵션/충돌 이름과 수정 이유를 제공한다. 전달된 값의 문법 오류에는 예시를 붙이고 값 누락은 Typer 기본 진단을 유지한다. callback에서 다른 옵션의 처리 순서에 의존하거나 모델 오류 문구로 지표를 추정하지 않는다.
- [X] T014 [P] [US3] `src/algorithm_problem_picker/cli.py`의 두 명령 도움말·새 옵션 metavar를 `MIN..MAX`와 세 범위 형태, 수치 제한·양 끝 포함·최대 1회·같은 지표 혼용 금지·기존 옵션 유지에 맞춘다. 기존 사이트 티어·미제공/0·수집 종료 설명과 기본값은 유지한다. T011~T013 이후 T015와 병렬 진행할 수 있다.
- [X] T015 [P] [US3] `README.md`에 세 새 옵션의 규칙과 대응하는 기존 옵션, 열린 범위·같은 경계·혼용/반복 오류를 설명하고 세 지표를 함께 쓰는 조회 및 열린 범위를 쓰는 추천 예시를 각각 하나 이상 추가한다. 티어 검색 의미·중복 정답 제출·기존 solver 전환 안내를 보존하고 `specs/004-add-range-options/contracts/cli.md`와 문구를 대조한다. T011~T013 이후 T014와 병렬 진행할 수 있다.
- [X] T016 [US3] `tests/test_cli.py` 전체와 `specs/004-add-range-options/quickstart.md`의 도움말·브라우저 없는 오류 수동 명령을 실행해 US1~US3·기존 CLI 진단/기본값/solver/help/version/open 회귀를 확인하고 같은 quickstart 파일에 결과를 기록한다. README 예시와 도움말이 계약과 상충하지 않는지도 검토한다.

**Checkpoint**: 모든 사용자 스토리가 동작하고 입력 오류는 조회 전에 멈춘다. 구현 완료 판단은 최종 전체 회귀와 문서 정합성 확인 후 수행한다.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: 기존 처리 경계와 전체 회귀를 확인하고 실제 검증 상태를 기록한다.

- [X] T017 `specs/004-add-range-options/quickstart.md`의 전체 회귀 절차에 따라 `uv run --locked pytest -q`를 실행해 `tests/test_cli.py`·`tests/test_selection.py`·`tests/test_service.py`·`tests/test_jungol_dom.py`를 포함한 기존 회귀를 확인하고 명령·결과·환경 제한을 quickstart에 기록한다. 통과 후 새 변경·실패·미해결 우려가 없으면 동일 회귀를 반복하지 않는다. 실사이트 통합 확인은 quickstart의 선택 사항으로 분리하고 미실행이면 그 사실을 기록한다.
- [X] T018 `specs/004-add-range-options/spec.md`의 FR-001~015·SC-001~005를 `src/algorithm_problem_picker/cli.py`·`tests/test_cli.py`·`README.md`와 최종 대조하고 요구사항별 구현/검증 근거와 남은 제한을 `specs/004-add-range-options/quickstart.md`에 기록한다. diff와 `git diff --check`로 새 의존성·도메인/서비스/수집 정책 변경·영구 캐시가 추가되지 않았음을 확인하며 실제 완료한 작업만 `specs/004-add-range-options/tasks.md`에 표시한다.

**Checkpoint**: 004의 필수 검증과 문서 정합성 결과가 추적 가능하고, 선택적 실사이트 실행 여부가 제품 회귀와 구분돼 있다.

## Dependencies & Execution Order

### Phase Dependencies

```text
Phase 1 T001
  → Phase 2 T002 → T003
  → US1 T004 → T005 → T006 → T007
  → US2 T008 → T009 → T010
  → US3 T011 → T012 → T013 → (T014 ∥ T015) → T016
  → Phase 6 T017 → T018
```

- T014와 T015는 같은 완료 지점 T013을 기다리고 서로 의존하지 않는다. T016은 두 작업 모두 완료된 뒤 실행한다.
- 각 테스트 작성 작업은 해당 스토리의 제품 구현보다 먼저 수행한다. 신규 동작의 실패 원인과 이미 통과하는 기존/공통 기반 사례를 구분한다.
- US2는 US1에서 연결한 옵션을 확장하고 US3는 그 정상 입력 흐름에 오류/안내 계약을 완성한다. 같은 `cli.py`·`tests/test_cli.py`를 수정하므로 스토리 간 병렬 편집은 하지 않는다.
- 스토리의 독립 검증은 자신의 고정 입력·기대값만으로 가치를 입증한다는 뜻이며, 공통 기반이나 앞선 구현의 재사용을 금지하지 않는다.
- 각 스토리의 검증 기록과 최종 검증은 `quickstart.md`를 공유하므로 병렬로 기록하지 않는다. 실제 실패나 후속 수정이 생기면 그 영향을 받는 검증만 다시 수행한다.

### Parallel Opportunities

`[P]`는 T014·T015 두 작업에만 부여했다. 테스트와 구현 대부분은 동일 파일을 사용하거나 선행 테스트에 의존하므로 병렬 표시하지 않았다. 병렬 실행 예시는 작업 배치 설명이며 별도 에이전트나 새 채팅을 자동 생성하라는 지시가 아니다.

## Parallel Example: User Story 1

```text
T004 tests/test_cli.py 작성·신규 옵션 실패 확인
→ T005·T006 src/algorithm_problem_picker/cli.py 구현
→ T007 검증·기록
```

같은 파일의 단계적 연결과 테스트 선행 조건 때문에 US1 내부의 독립 병렬 작업은 없다.

## Parallel Example: User Story 2

```text
T008 tests/test_cli.py 열린 범위·호환성 검증 작성
→ T009 src/algorithm_problem_picker/cli.py 보완
→ T010 검증·기록
```

US1의 공통 CLI 연결을 재사용하므로 US1 완료 후 순차 진행한다.

## Parallel Example: User Story 3

```text
T011·T012 테스트 작성 → T013 입력 오류 처리 완료
  ├─ T014 src/algorithm_problem_picker/cli.py 도움말
  └─ T015 README.md 사용법
두 작업 합류 → T016 CLI 회귀·오류 수동 확인·기록
```

## Implementation Strategy

### MVP First (User Story 1 Only)

T001~T007로 두 명령의 세 닫힌 범위를 연결하고 독립 검증한다. 고정 목록에서 기존 표기와 같은 조건·후보·결과 의미가 확인되면 간결한 입력의 핵심 가치를 시연할 수 있다. 이후 US2·US3를 계속 완료하며 MVP 확인 지점을 승인 요청이나 임의 중단 이유로 삼지 않는다.

### Incremental Delivery

1. 공통 입력 기반을 준비한다.
2. US1에서 닫힌 범위·복수 지표·추천을 연결한다.
3. US2에서 열린 범위·동일 경계·기존 명령 호환성을 완성한다.
4. US3에서 오류·혼용·반복·사용 안내를 완성한다.
5. 전체 회귀와 FR/SC 대조를 마치고 실제 결과를 보고한다.

## Requirements Coverage

| 요구사항 / 성공 기준 | 작업 |
| --- | --- |
| FR-001 / SC-001 | T004, T006, T007 |
| FR-002~003 / SC-002 | T003~T010 |
| FR-004~007 / SC-002~003 | T003~T005, T008, T011, T013 |
| FR-008~010 / SC-003 | T002, T011~T013, T016 |
| FR-011~013 / SC-002~004 | T004, T006~T010, T017 |
| FR-014 / SC-005 | T012, T014~T016 |
| FR-015 / SC-004~005 | T004, T006, T008~T010, T018 |

## Notes

총 18개 작업: Setup 1개, Foundational 2개, US1 4개, US2 3개, US3 6개, Polish 2개. 2026-10-28 T001~T018을 모두 완료했다. 전체 회귀 643개가 통과했으며 상세 실행 근거와 선택적 실사이트 미실행은 quickstart.md에 기록했다.

헌장 III의 영구 캐시 제외는 [plan.md](plan.md)의 기존 정당화 예외를 승계한다. 이 기능에 필요하지 않은 캐시·인증·데이터 접근·브라우저 구조 변경이나 별도 성능 프로젝트를 작업으로 만들지 않는다. 자동 커밋이 꺼져 있으므로 단계별 커밋을 필수 완료 조건으로 두지 않는다.
