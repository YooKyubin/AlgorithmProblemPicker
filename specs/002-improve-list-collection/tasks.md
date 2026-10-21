---
description: "002 티어 수집 안정화와 정답 제출 수 기반 목록 전용 조회·추천 작업 목록"
---

# Tasks: 안정적인 티어 수집과 정답 제출 수 기반 조회·추천

**Input**: `specs/002-improve-list-collection/`의 설계 문서
**Created**: 2026-10-21
**Branch**: `002-improve-list-collection`
**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [CLI 계약](contracts/cli.md), [수집 계약](contracts/source.md), [quickstart.md](quickstart.md)

**Tests**: 명세 SC-001~008과 원문 이슈의 최소 회귀 검증 요구에 따라 필요한 테스트를 포함한다. 기존 네 테스트 모듈을 확장·전환하며 중복 테스트나 테스트 전용 제품 API를 추가하지 않는다.
**Organization**: US1(P1) → US2(P1) → US3(P2) 순서로 기능을 검증한다. US1은 기존 모델에서 먼저 완성할 수 있고, US2에서 모델을 전환할 때 US1 검증을 보존한다.

## Format: `[ID] [P?] [Story] Description`

- 모든 작업은 `- [ ] TNNN [P?] [USn?] 설명과 파일 경로` 형식이다.
- `[P]`는 선행 작업이 완료된 뒤 다른 파일의 작업과 병렬 수행할 수 있다는 뜻이다. 태스크 ID만 보고 병렬 실행하지 말고 아래 의존성을 따른다.
- `[US1]`, `[US2]`, `[US3]`는 명세의 동일 번호 사용자 스토리에 대응한다. Setup·Foundational·Polish에는 스토리 라벨을 붙이지 않는다.
- 체크 표시는 실제 작업·검증 완료를 뜻한다. 이 문서를 생성한 것만으로 코드나 테스트를 완료 표시하지 않는다.

## Path Conventions

모든 작업 경로는 저장소 루트 기준이다. 제품 코드는 `src/algorithm_problem_picker/`, 검증은 `tests/`, 개발 도구는 `scripts/`, 이번 기록은 `specs/002-improve-list-collection/`에 둔다.
001 자료는 이전 구현 이력이다. `001/T041`, `001/T042`는 이번 문서의 태스크와 다른 기존 작업이다.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 기존 프로젝트를 재초기화하지 않고 실행 환경과 변경 전 비교 기준을 확보한다.

- [X] T001 `pyproject.toml`·`uv.lock` 기준 Python 3.12 이상과 잠금 의존성·Chromium 설치 상태를 확인하고 필요한 경우에만 `uv sync --locked --python 3.12` 및 `uv run --locked playwright install chromium`을 실행한다; 설치·환경·현재 revision과 dirty 상태를 `specs/002-improve-list-collection/quickstart.md`에 기록하고 새 의존성은 추가하지 않는다.
- [X] T002 기준 commit `c37208f5a80628df5d7126972d31461b2517177d`의 존재와 `src/algorithm_problem_picker/service.py`의 상세 보강 흐름 및 `tests/fixtures/jungol/detail.html`의 재생 가능성을 확인하고 baseline revision·기존 상세 fixture 보존 근거를 `specs/002-improve-list-collection/quickstart.md`에 기록한다; 현재 브랜치·작업 파일·staged index는 변경하지 않는다.

**Checkpoint**: 설치 상태와 비교 기준이 기록되었으며 기존 코드의 성능을 이미 측정한 것으로 표현하지 않는다.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 두 P1 스토리가 공유할 목록·필터 UI 검증 자료를 준비한다. 이 단계 이후 US1을 시작한다.

- [X] T003 `tests/fixtures/jungol/list.html`·`tests/fixtures/jungol/pagination.html`을 현재 파서와 호환되게 유지하면서 각 목록 행에 서로 다른 정답·시도·정답률을 제공하고, `tests/fixtures/jungol/tier-pagination.html`에 첫/추가 목록의 범위 내·미정·미확인 및 공개 필터 UI를 재생할 최소 자료를 만든다; 문제 ID는 고정하고 기존 `detail.html`은 baseline 검증 자료로 보존하며 정답 열 미제공 표식은 합성 자료임을 구분한다.

**Checkpoint**: 공통 HTML 자료가 준비되었다. 제품 모델·공급자·CLI 전환은 각 스토리에서 수행한다.

---

## Phase 3: User Story 1 — 미정·미확인 티어가 섞여 있어도 조건에 맞는 문제 찾기 (Priority: P1) 🎯 MVP

**Goal**: 티어 범위에서 정상 미정·미확인은 제외하고 끝까지 수집하며, 범위 밖 확정 티어와 구조·파싱 오류는 식별 가능한 실패로 유지한다.

**Independent Test**: 로컬 첫/추가 목록에서 티어 9~14·하한만·상한만을 조회·추천해 정상 부재로 중단되지 않고 범위 안 결과만 반환하는지 확인한다. 별도 범위 이탈·파싱 실패는 최종 결과 없이 실패해야 한다. 이 증분은 기존 solver 처리에서도 검증할 수 있다.

### Tests for User Story 1

새 검증은 구현 전에 실행해 현재 실패 원인을 확인한다. 기존 동작을 이미 만족하는 사례는 불필요하게 실패시키지 않는다.

- [X] T004 [P] [US1] `tests/test_jungol_dom.py`에 최초·다음 페이지·더 불러오기에서 미정/미확인 수집 계속, 두 경계/한쪽 경계, 범위 밖 확정 티어의 번호·읽은 티어·요청 범위 진단, 알 수 없는/누락/중복 배지의 구조 실패 및 URL·공개 UI 필터 손실을 검증하는 최소 매개변수화 사례를 추가한다; 지정 공개 사용자의 `solvedBy`·`solvedByMode` 유지도 확인하고 원격 요청은 차단한다 (FR-001~005, FR-012, FR-020).
- [X] T005 [P] [US1] `tests/test_selection.py`·`tests/test_service.py`에 티어 범위가 없을 때 세 상태 포함·양방향 미확정 마지막/번호순, 범위가 있을 때 미정·미확인 제외 및 모두 제외된 정상 0개를 검증한다; `Rated`의 "bool이 아닌 정수 1~30.", `Unavailable`의 "누락·파싱 실패의 대체값이 아니다."를 보존하고, 미확인 제외는 고유 문제당 한 번이며 Unrated 제외는 미확인 수에 넣지 않는지 확인한다 (FR-002, FR-004, SC-001~002).

### Implementation for User Story 1

- [X] T006 [US1] `src/algorithm_problem_picker/jungol.py`의 `_collect`에서 범위 밖 `Rated`만 필터 적용 실패로 처리하고 정상 `Unrated`·`Unavailable`은 수집 레코드에 보존해 기존 `selection.py`의 티어 필터가 제외하도록 바꾼다; 범위 이탈은 문제 번호·확정 티어·요청 하한/상한 및 제한 없음 경계를 포함한 `SourceAccessError`로 전달한다 (FR-001~004).
- [X] T007 [US1] `src/algorithm_problem_picker/jungol.py`의 티어 해석·오류 생성에서 `/solved/0.svg`·검증된 무배지 표현·명시적 난이도 미확인을 유지하고 임의 배지 누락/중복/미해석을 `SourceSchemaError`로 구분한다; 진단에 확인 가능한 문제 번호·지표·원시 값/누락 사실을 포함하고 번호도 파손되면 원시 링크와 번호 확인 실패를 안내한다 (FR-005).
- [X] T008 [US1] `src/algorithm_problem_picker/jungol.py`의 `_collect`·`_verify_filters`에서 최초 목록과 모든 다음 페이지·더 불러오기 후 `type=problem`·`sort=idAsc`·지정 minTier/maxTier·unrated 및 지정 공개 사용자 조건을 URL과 공개 적용 UI로 검증한다; 한쪽 티어 경계도 exclude를 유지하고 필수 조건 중복·손실·변조는 실패시키며 로그인 사용자용 status·내부 요청 해독·고정 대기 증가를 도입하지 않는다 (FR-001, FR-012, FR-020).
- [X] T009 [US1] T004~T008 후 `tests/test_jungol_dom.py`·`tests/test_selection.py`·`tests/test_service.py`의 US1 관련 검증을 실행하고 정상 0개·범위 만족·실패 진단 결과를 `specs/002-improve-list-collection/quickstart.md`에 기록한다; T005에서 기존 순수 필터가 이미 계약을 만족하면 해당 제품 코드는 유지하고, 001/T041·T042가 이 작업으로 해결됐다고 기록하지 않는다 (SC-001~002).

**Checkpoint**: US1의 티어 수집 증분을 독립 검증할 수 있다. accepted 지표와 solver 전환을 포함한 002 전체 완료 판정은 이후 단계에서 한다.

---

## Phase 4: User Story 2 — 목록의 정답 제출 수로 상세 조회 없이 조회·추천하기 (Priority: P1)

**Goal**: 목록에서 완성된 문제만으로 전체 후보를 필터·정렬·추천하고 상세 요청을 없앤다.

**Independent Test**: 정답·시도·맞힌 사람 값이 서로 다른 고정 다중 목록에서 accepted 0/10/20/미제공, 양방향 정렬, limit/count=1 및 충분·부족·0개를 확인한다. 실제 수집 경로의 상세 문서 요청이 0건이어야 한다. 성능의 최종 실측은 모든 코드 변경 뒤 T031에서 수행한다.

### Tests for User Story 2

US1 체크포인트 후 다음 네 테스트 작업은 서로 다른 파일에서 작성할 수 있다. 새 동작이 필요한 사례의 실패를 확인한 뒤 모델·제품 구현을 진행한다.

- [X] T010 [P] [US2] `tests/test_jungol_dom.py`의 상세 통계 검증을 목록 정답 셀 검증으로 전환하고 0·정상 천 단위 쉼표·`-`/`—`/미확인/미제공·빈/누락/중복 셀·잘못된 쉼표·내부 공백·음수·소수·미해석 문자열을 구분한다; 정답률 표시 정밀도 유지와 실제 JungolSource list/recommend의 조건 유무·개수 1·다중 목록·공개 사용자 조건에서 `/problem/<ID>` 문서 요청 0건을 검증하고 baseline 전용 상세 HTML은 보존한다 (FR-005~006, FR-010~012, SC-003, SC-005).
- [X] T011 [P] [US2] `tests/test_selection.py`에 accepted 0/9/10/20/21/미제공의 양끝·한쪽 경계, 0~0, 잘못된 경계·음수/소수/bool, 지표 동점·미확인 양방향 정렬, 앞 필터 탈락·복수 미확인에서 문제당 한 번의 제외 수를 검증한다; 정답률 Decimal과 기존 무작위 전체 고유 후보 선택 검증은 보존한다 (FR-007~010, FR-013~014, SC-003~004).
- [X] T012 [P] [US2] `tests/test_service.py`의 고정 공급자를 resolve_user/collect만 제공하도록 전환할 검증을 작성하고 전체 수집 완료 전 필터/정렬/추첨·최종 결과 금지, 뒤 페이지 포함·최초 중복 레코드 유지·부족/0개·실패/취소·새 상태/개수를 검증한다; 기존 상세 실패 사례는 수집 실패 사례로 대체하고 상세 보강을 모두 수행해야 한다는 기대는 제거한다 (FR-011~014, FR-017, SC-005~006).
- [X] T013 [P] [US2] `tests/test_cli.py`에 새 accepted 수치 옵션·정렬·출력 제목·0/미확인·조건 요약과 실제 수집/처리 진행을 검증하는 최소 사례를 추가하고, 입력 오류의 공급자 시작 0건 및 실패/취소 무출력을 유지한다; 레거시 전환 안내의 구체 검증은 US3/T024에 둔다 (FR-006~009, FR-017, SC-003~006).

### Implementation for User Story 2

- [X] T014 [US2] `src/algorithm_problem_picker/models.py`에서 Candidate/Problem 상속을 목록 전용 불변 Problem 하나로 합치고 `tests/conftest.py`의 공통 생성기를 accepted_count 기준으로 바꾼다; 데이터 모델의 id "bool이 아닌 양의 정수.", title "공백뿐인 제목은 오류.", url "`https://jungol.co.kr/problem/<id>`와 일치.", tier "확인한 표시 상태를 보존.", pass_rate "유한한 0~100, 목록 표시 정밀도를 유지.", accepted_count "bool이 아닌 0 이상의 정수, 중복 정답 제출 포함.", listed_at "해당 목록 관측 시점." 및 "시간대가 있는 `datetime`"을 적용하고 Known/Unavailable을 유지하며 solver_count·details_observed_at과 값 별칭은 제거한다 (FR-005~006, FR-010~011).
- [X] T015 [US2] `src/algorithm_problem_picker/models.py`의 SearchCriteria를 min_accepted/max_accepted로 전환한다; 티어 경계는 "지정 시 1~30.", 정답률 경계는 "지정 시 유한한 0~100.", accepted 경계는 "지정 시 bool이 아닌 0 이상.", status는 "all / solved / unsolved"·"기본 all.", user_handle은 "기본 빈 문자열. solved/unsolved에서 정확한 공개 핸들 필수.", 범위는 "각 범위는 양 끝을 포함한다. 생략한 경계는 제한하지 않으며 하한은 상한 이하여야 한다."를 그대로 지키고, @ 한 개 정규화·대소문자·all+user 오류를 보존한다; SortKey는 `id`, `difficulty`, `rate`, `accepted`, `random`, Order는 `asc`, `desc`, 기본 id/asc 및 random/desc 오류로 정리하고 UserReference의 "양의 `account_id`, 시간대가 있는 `resolved_at`" 및 "공개 사용자 선택 화면의 정확한 핸들에 대해서만 생성한다."를 유지한다 (FR-007, FR-009, FR-012).
- [X] T016 [US2] `src/algorithm_problem_picker/models.py`의 CompletedListing.candidates를 `tuple[Problem, ...]`로 전환하고 completed_at의 "마지막 목록의 정상 완료를 확인한 시점." 및 "시간대가 있는 datetime", "동일 ID가 여러 번 나타나면 최초 관측 레코드를 유지한다. 개수는 고유 ID 기준이다."를 유지한다; Result의 "`fetched_count >= eligible_count >= returned_count`", "`finished_at >= started_at`", 고유 ID, "`returned_count = min(requested_count, eligible_count)`", "`shortage = requested_count - returned_count`", "list의 shortage는 0이다."와 started_at/finished_at의 "시간대가 있는 실행 시작·완료 시점."을 보존한다; Progress.collected는 "확인한 고유 관측 개수다."를 따르고 상태는 `Validated → [UserResolved] → Collecting → Processing → Complete`, 비종료 단계의 Failed/Cancelled와 불변식 assertion으로 정리한다; detailed·Enriching·Presented를 제거하고 `src/algorithm_problem_picker/ports.py`의 Protocol에서 read_details와 Candidate 의존성을 삭제한다 (FR-011, FR-013~014, FR-017).
- [X] T017 [P] [US2] T014~T016 후 `src/algorithm_problem_picker/jungol.py`의 snapshot·행 파서가 `td[data-col="정답"]` 정확히 한 개에서 바깥 공백만 제거한 ASCII 정수/올바른 천 단위 쉼표 정수 또는 명시적 네 미제공 표식을 읽어 Problem을 반환하게 한다; 빈 셀/빈 앵커/누락/중복/미해석은 진단 있는 실패로 유지하고 정답률의 기존 확인된 표시·관측 시점과 US1 티어/조건 검증을 보존하며 상세 페이지 생성·read_details·상세 대기와 통계 보충 경로를 제거한다 (FR-005~006, FR-010~012).
- [X] T018 [P] [US2] T014~T016 후 `src/algorithm_problem_picker/selection.py`에서 filter_solvers를 제거하고 filter_listing 한 흐름으로 티어→정답률→accepted를 검사해 고유 문제당 미확인 제외를 한 번만 계산한다; 미정 제외는 미확인 수에 넣지 않고 해당 필터가 없으면 부재 값을 포함하며, accepted 양방향 정렬·미확인 마지막·동점 번호순과 전체 고유 후보의 sample/shuffle을 유지한다 (FR-002, FR-004, FR-007~010, FR-013~014).
- [X] T019 [US2] T017·T018 후 `src/algorithm_problem_picker/service.py`에서 전체 CompletedListing 수신→Processing→순수 필터→전체 정렬 후 제한 또는 전체 균등 비복원 추천→Result 구성→Complete 순서로 바꾸고 상세 루프·상세 개수를 제거한다; fetched_count는 전체 고유 관측 수, eligible_count는 모든 조건 통과 수, omitted_unknown_count는 실제 필터 흐름의 미확인 제외 수로 설정하며 실패·취소에서 부분 Result를 반환하지 않는다 (FR-008, FR-011~014, FR-017).
- [X] T020 [P] [US2] T019 후 `src/algorithm_problem_picker/cli.py`의 정상 경로에 `--min-accepted`·`--max-accepted`·`--sort accepted`와 새 SearchCriteria를 연결하고 표·조건·관측 시점·수집/Processing 진행을 정답 제출 수에 맞춘다; 중복 정답 제출 포함 의미와 0/미확인을 표시하고 실제로 없는 상세 단계·개수를 제거하며 stdout/stderr, 기본 개수, 종료 코드 0/1/2/130과 명시적 open을 유지한다; 정상 solver 옵션은 제거하고 전용 전환 안내는 US3에서 완성한다 (FR-006~009, FR-016~018).
- [X] T021 [P] [US2] T019 후 `scripts/benchmark_selection.py`를 accepted 모델과 통합 필터로 바꾸고 `scripts/validate_live.py`를 상세 없는 목록 필터로 바꾼다; 기존 10,000개 로컬 처리 검증과 작은 공개 사용자 all/solved/unsolved 집합 검증을 유지하며 이 단계에서 선택적 라이브 도구를 자동 실행하거나 로컬 계산 시간을 수집 개선 실측으로 설명하지 않는다 (FR-010~013, FR-019~020).
- [X] T022 [US2] T020·T021 후 `scripts/benchmark_collection.py`와 `tests/fixtures/jungol/benchmark/`의 고정 2개 이상 번호 목록·baseline 전용 최소 상세 HTML을 만들고 `--baseline-ref`·`--runs`·`--output` 개발 계약을 구현한다; 기준 commit 임시 추출·별도 프로세스·동일 Python/의존성/절대 fixture·harness 경로·실제 import 경로 확인으로 두 버전을 격리하고 원격 요청을 차단한다; 같은 후보로 list id/asc/limit=1과 recommend count=1을 계측하되 사용자·solver/accepted 조건/정렬은 생략하고 기본 탐색 간격을 유지하며 CLI import 후부터 출력·브라우저 정리까지의 전체 시간, collect 시간, 상세 URL 횟수·원시 표본·각 중앙값·revision/dirty/환경/해시를 보고한다; 조건 불일치나 상세 요청/current 중앙값 판정 실패는 비정상 종료하고 제품 공개 API는 늘리지 않는다 (FR-019~020, SC-008).
- [X] T023 [US2] T010~T022 후 `tests/test_jungol_dom.py`·`tests/test_selection.py`·`tests/test_service.py`·`tests/test_cli.py`의 US1/US2 검증과 `scripts/benchmark_selection.py`를 실행해 새 모델 전환 후에도 티어 동작·전체 후보·실제 상세 요청 0건·순수 처리 결과를 확인하고 `specs/002-improve-list-collection/quickstart.md`에 실행 명령·revision·결과를 기록한다; 벤치 도구의 기준 소스 import·원격 차단·실패 판정도 로컬 재생으로 확인하되 최종 각 3회 성능 보고는 T031에 남긴다 (SC-001~006, SC-008).

**Checkpoint**: 새 지표의 정상 조회·추천이 독립 실행되고 상세 조회가 없다. 레거시 입력의 상세 전환 안내는 US3 전에는 완료된 것으로 간주하지 않는다.

---

## Phase 5: User Story 3 — 바뀐 지표의 의미와 사용법 이해하기 (Priority: P2)

**Goal**: 새 옵션의 의미를 일관되게 안내하고 기존 solver 옵션을 명시적 입력 오류와 대응 안내로 거부한다.

**Independent Test**: list/recommend의 옛 최소·최대 옵션 및 list의 sort solvers가 각각 코드 2·새 옵션·지표 의미 변경을 안내하며 공급자 생성이 0건인지 확인한다. 도움말·표·README와 명시적 open이 계약과 일치해야 한다.

### Tests for User Story 3

- [X] T024 [US3] `tests/test_cli.py`에 list/recommend의 `--min-solvers`·`--max-solvers`, list의 `--sort solvers`, 새/옛 옵션 혼용을 코드 2·대응 accepted 옵션·맞힌 사람 수에서 정답 제출 수로 변경 안내·공급자 생성/조회 시작 0건·최종 결과 무출력으로 검증한다; 기존 source_factory는 생성자도 계수하도록 보강하고 help/version 무조회, 새 옵션 의미·레거시 도움말 비노출, 기존 open 중복/실패 링크 검증을 유지한다 (FR-015~018, SC-007).

### Implementation for User Story 3

- [X] T025 [P] [US3] T024 후 `src/algorithm_problem_picker/cli.py`에서 두 옛 범위 옵션을 숨긴 문자열 입력과 비공개 거부 callback으로만 인식하고 `BadParameter`로 대응 새 옵션·중복 정답 제출 포함 의미 변경을 안내한다; sort는 문자열 입구에서 solvers를 먼저 거부한 후 정상 SortKey로 바꾸어 일반 Enum 오류가 전환 안내를 가리지 않게 하며, 모델·서비스에는 옛 필드/별칭을 남기지 않고 새/옛 혼용도 `_run`·공급자 생성 전에 거부한다 (FR-015~016).
- [X] T026 [P] [US3] T024 후 `README.md`의 예시·옵션 표·처리 순서·진행 설명을 목록 전용 accepted 지표로 갱신하고 같은 숫자라도 맞힌 사람 수와 결과가 달라질 수 있음을 설명한다; `--min-solvers → --min-accepted`, `--max-solvers → --max-accepted`, `--sort solvers → --sort accepted`의 오류/전환 안내와 중복 제출 포함 의미, 전체 수집 원칙·선택적 open·캐시 제외를 명시한다 (FR-015~018).
- [X] T027 [US3] T025·T026 후 `tests/test_cli.py`를 실행하고 `jpick --version`, list/recommend 도움말 및 옛 옵션 거부를 수집 없이 확인해 `specs/002-improve-list-collection/quickstart.md`에 코드·메시지·공급자 0건 결과를 기록한다; open은 기존 테스트의 기본 브라우저 대역으로 검증하고 선택하지 않은 문제를 실제로 열지 않는다 (SC-007).
- [X] T028 [US3] `src/algorithm_problem_picker/cli.py`·`README.md`·`specs/002-improve-list-collection/contracts/cli.md`·`specs/002-improve-list-collection/contracts/source.md`의 옵션·명칭·미확인·정렬·종료 상태·관측 시점 설명을 대조해 실제 구현과 맞추고 필요한 문구를 수정한다; `specs/001-jungol-problem-picker/`는 과거 계약 이력으로 보존하며 현재 지원 기능처럼 solver 수치를 안내하는 문구를 새 경로에 남기지 않는다 (FR-016~018).

**Checkpoint**: 세 스토리의 사용자 경로가 동작하며 기존 solver 입력은 조회를 시작하지 않는다. 최종 회귀·시간 비교와 외부 선행 조건의 수용 판정은 남아 있다.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: 최종 코드 기준의 최소 검증·성능 기록·범위 검토를 마친다.

- [X] T029 `src/algorithm_problem_picker/models.py`·`ports.py`·`jungol.py`·`selection.py`·`service.py`·`cli.py` 및 `scripts/`를 검색해 Candidate/solver_count/details_observed_at/read_details/Enriching/detailed의 제품 경로 잔재와 잘못된 imports를 정리한다; 옛 옵션 거부·과거 자료·baseline fixture 참조는 목적에 맞게 유지하고, 새 원격 접근·캐시·부분 결과·조기 종료·테스트 전용 공개 API가 추가되지 않았는지 `specs/002-improve-list-collection/plan.md`의 게이트와 대조한다 (FR-011, FR-016~020).
- [X] T030 T029 후 `tests/test_selection.py`·`tests/test_service.py`·`tests/test_cli.py`·`tests/test_jungol_dom.py`를 `uv run --locked pytest -q`로 실행하고 `scripts/benchmark_selection.py` 결과와 함께 `specs/002-improve-list-collection/quickstart.md`에 기록한다; 실패·취소·접근 제한·브라우저 정리·정상 빈 결과를 포함해 SC-001~007을 확인하고 실패/미실행을 통과로 기록하지 않는다.
- [X] T031 T030 후 `uv run --locked python scripts/benchmark_collection.py --baseline-ref c37208f5a80628df5d7126972d31461b2517177d --runs 3 --output specs/002-improve-list-collection/collection-benchmark.md`를 실행해 list/recommend 각각 baseline/current 최소 3회, 동일 후보·정상 완료·baseline 상세 양수/current 0·전체 시간 중앙값 감소를 확인한다; 원시 전체/목록 시간과 각 중앙값·환경·revision/dirty·해시를 보고서에 남기고 `specs/002-improve-list-collection/quickstart.md`에 링크와 판정을 추가하며 라이브 성능 개선율로 일반화하지 않는다 (FR-019, SC-008).
- [X] T032 `specs/001-jungol-problem-picker/tasks.md`의 기존 T041·T042 수정 상태·근거를 확인하고 `tests/test_jungol_dom.py`·`tests/test_service.py`에서 요청 완료 후 지연된 행/사용자 결과, 빈 최종 로드·동일 핸들 갱신 경계의 재현 또는 선행 검증 결과를 대조해 `specs/002-improve-list-collection/quickstart.md`에 통합 수용 상태를 기록한다; 이 태스크는 평가·기록이며 별도 두 수정의 구현/완료 표시는 포함하지 않고, 근거가 없거나 결함이 남으면 관련 수용을 미통과로 남기며 고정 대기 증가로 대체하지 않는다 (FR-012~014, plan 통합 게이트).
- [ ] T033 `specs/002-improve-list-collection/quickstart.md`·`plan.md`·`tasks.md`와 `README.md`를 최종 revision의 검증·성능 보고에 맞춰 정리하고 FR-001~020/SC-001~008의 근거·미실행·실패를 대조한다; T030·T031 통과와 T032의 외부 통합 수용 근거를 모두 확인한 경우에만 이 최종 태스크를 완료 표시하고, 미해결 T041·T042가 있으면 다른 구현·검증 기록은 보존하되 이 체크박스와 해당 통합 수용은 미완료로 남긴다.

**Checkpoint**: 전체 완료는 코드 변경·최소 회귀·성능 기준과 외부 통합 게이트가 실제로 충족된 경우에만 선언한다. 선택적 라이브 실행은 quickstart를 따라 수행 여부와 한계를 기록하며 미실행을 라이브 통과로 표시하지 않는다.

---

## Dependencies & Execution Order

### Phase Dependencies

```text
T001 → T002 → T003
                 ↓
        US1: T004~T009 (P1, 최초 MVP)
                 ↓
        US2: T010~T023 (P1, 지표/모델/목록 전용 전환)
                 ↓
        US3: T024~T028 (P2, 이전 입력 거부/사용법)
                 ↓
        T029 → T030 → T031 ──────→ T033

001/T041·T042의 별도 수정·검증 → T032의 수용 평가 → T033
```

T032의 평가·기록은 앞서 수행할 수 있지만 최종 수용은 필요한 선행 수정·검증을 확인한 뒤다.
미해결이면 T033을 완료할 수 없다. 이를 이유로 무관한 002 구현·회귀·성능 기록까지 중단하지 않는다.

### User Story Dependencies

- US1은 공통 HTML 자료 이후 기존 모델로 독립 검증한다. US2·US3를 먼저 구현할 필요가 없다.
- US2는 US1의 수집기 변경을 보존하며 같은 파일의 모델·수집·서비스를 바꾸므로 순차 통합한다.
  T014~T020은 하나의 API 전환 묶음이므로 중간 import/모델 불일치를 완성된 제품 상태로 취급하지 않는다.
- US3는 US2의 정상 accepted CLI가 완성된 뒤 시작한다. 별도 레거시 거부와 문서·메시지 검증으로 독립 수용한다.
- 각 스토리는 자기 체크포인트에서 검증 가능하지만, 같은 수집기·CLI 파일을 바꾸므로 세 스토리 전체를 동시 구현하지 않는다.

### Within Each User Story

- US1: T004와 T005를 병렬 작성 → T006 → T007 → T008 → T009.
- US2: T010~T013을 병렬 작성 → T014 → T015 → T016 → T017과 T018 병렬 → T019 → T020과 T021 병렬 → T022 → T023.
- US3: T024 → T025와 T026 병렬 → T027 → T028.
- 새 동작을 검증하는 테스트는 해당 구현 전에 실패 원인을 확인한다. 이후 필요한 스토리 검증을 통과시킨다.
- 모든 구현 변경이 끝난 뒤 T029 정리 → T030 최종 회귀 → T031 최종 성능을 수행한다. 새 변경 없이 같은 검증을 반복하지 않는다.

### Parallel Opportunities

서로 다른 파일에 있는 **12개 [P] 작업**을 조건부로 병렬 수행할 수 있다.
T004/T010은 같은 DOM 테스트 파일, T005/T011은 같은 선택 테스트 파일, T013/T024는 같은 CLI 테스트 파일이므로 스토리 경계를 넘어 겹쳐 실행하지 않는다.
T017과 T018, T020과 T021, T025와 T026은 명시한 공통 선행 조건 이후에만 병렬 가능하다.

---

## Parallel Example: User Story 1

T003 완료 후:

```text
T004: tests/test_jungol_dom.py의 티어/필터 보존 계약 검증
T005: tests/test_selection.py·tests/test_service.py의 티어 후보/정렬 검증
```

두 검증 작업이 준비되면 같은 `jungol.py`를 바꾸는 T006~T008은 순차 진행한다.

## Parallel Example: User Story 2

US1 완료 후 T010~T013은 각각 다른 테스트 파일에서 작성 가능하다.
T014~T016 완료 후 제품 변경 예시는 다음과 같다.

```text
T017: src/algorithm_problem_picker/jungol.py의 accepted 추출·상세 경로 제거
T018: src/algorithm_problem_picker/selection.py의 통합 필터·accepted 정렬
```

둘을 통합한 T019 이후 T020(CLI)과 T021(기존 개발 스크립트)도 병렬 가능하다.

## Parallel Example: User Story 3

T024 완료 후:

```text
T025: src/algorithm_problem_picker/cli.py의 레거시 거부·전환 안내
T026: README.md의 새 사용법·지표 의미·전환 표
```

완료 후 T027·T028에서 동작과 설명을 대조한다.

---

## Implementation Strategy

### MVP First (User Story 1)

1. Setup과 공통 HTML 자료를 준비한다.
2. US1의 최소 회귀 → 티어 수집/진단 수정 → 독립 검증을 완료한다.
3. 여기까지를 티어 중단 문제에 대한 최초 MVP로 시연할 수 있다. solver→accepted 변경까지 완료됐다고 안내하지 않는다.

### Incremental Delivery

1. US1을 보존하며 US2의 단일 모델·목록 전용 경로·정상 accepted CLI를 전환한다.
2. US3에서 기존 solver 입력을 반드시 오류/새 옵션 안내로 끝내고 README와 도움말을 맞춘다.
3. 최종 정리·회귀 뒤 변경 전후 성능을 기록한다. 외부 완전성 선행 작업이 남아 있으면 해당 수용을 분리해 표시한다.
4. 실제 완료한 작업만 체크한다. 현재 실행 상태는 각 태스크 체크박스와 아래 기록을 따른다.

### Parallel Team Strategy

병렬 구현을 사용할 경우 위 예시의 서로 다른 파일만 나누고 공통 선행 조건 완료를 확인한다.
이 문서의 병렬 가능 표시는 현재 대화에서 보조 에이전트를 실행하라는 지시가 아니라 작업 분할 정보다.
영구 캐시·조기 종료·내부 API·별도 T041/T042 수정을 추가 범위로 포함하지 않는다.

## Requirement Traceability

| 요구사항·성과 | 작업 |
| --- | --- |
| FR-001~005 / SC-001~002 | T003~T010, T014, T017~T018, T023, T030 |
| FR-006~010 / SC-003~004 | T010~T011, T013~T015, T017~T018, T020~T023, T030 |
| FR-011~014 / SC-005~006 | T010, T012, T016~T023, T029~T030, T032~T033 |
| FR-015~018 / SC-007 | T013, T016, T020, T024~T030 |
| FR-019 / SC-008 | T002, T021~T023, T031, T033 |
| FR-020 | T001, T004, T008, T010, T017, T021~T023, T029~T030 |

## Notes

- 총 **33개**: Setup 2, Foundational 1, US1 6, US2 14, US3 5, Polish 5.
- 모델 제약은 T014~T016에 데이터 모델 문구를 인용했다. 새로운 의사결정을 구현자에게 남기지 않는다.
- 정답 열의 네 미제공 토큰은 합성 계약이다. 빈 값·새 표시를 임의로 정상 미확인으로 바꾸지 않는다.
- 001/T041·T042의 상태를 평가하는 것은 두 수정의 구현 권한·완료 판정으로 확대하지 않는다.
- 선택적 라이브 결과는 고정 기대값이나 성능 비교의 통제 자료로 사용하지 않는다. 실제 미실행은 미실행으로 기록한다.
- 생성 시점에는 구현/검증을 수행하지 않았으며, 실제 실행 결과는 [quickstart.md](quickstart.md)에 기록했다. T033은 별도 001/T041·T042 수정·검증까지 미완료로 유지한다.
