---
description: "003 사이트 목록 기준 티어·빈 통계·수집 종료 정책의 구현 작업"
---

# Tasks: 사이트 목록 기준의 티어·빈 통계·수집 종료 정책

**Input**: `specs/003-align-site-listing/`의 spec.md, plan.md, research.md, data-model.md, contracts/source.md, contracts/cli.md, quickstart.md

**Prerequisites**: 설계 문서와 `.specify/memory/constitution.md`. 기존 Python >=3.12, uv 잠금 의존성, 동기 Playwright/Chromium, pytest, Typer CliRunner를 사용한다. 새 의존성·프로젝트 초기화는 필요 없다.

**Tests**: spec.md의 User Scenarios & Testing 및 SC-001~008이 요구한 정책 전환 회귀를 포함한다. 새 정책 사례를 먼저 작성·실행해 기존 정책 때문에 실패하는지 확인한 뒤 구현한다. 이미 통과하는 보호 경계는 실패시키기 위해 변경하지 않는다. 제품 구현·테스트 실행·실사이트 수용은 이 작업 목록 생성 시점에는 미실행이다.

**Organization**: 세 P1 사용자 스토리를 명세 순서로 배치한다. 각 스토리는 해당 정책을 독립 검증할 수 있지만, 같은 `jungol.py`·테스트 파일을 수정하므로 기본 구현 순서는 US1 → US2 → US3이다. 실사이트의 최종 통합 수용은 세 정책 구현 후 수행한다.

## Format: `[ID] [P?] [Story] Description`

- 모든 작업은 `- [ ] T번호 [P?] [US번호?] 설명과 경로` 형식이다.
- `[P]`는 아래에 명시한 선행 작업 완료 후, 서로 다른 파일의 작업과 병렬 진행할 수 있다는 뜻이다. 같은 파일을 수정하는 작업은 병렬 실행하지 않는다.
- 스토리 단계에만 `[US1]`, `[US2]`, `[US3]`를 붙인다. 체크는 실제 구현·검증 완료 시에만 변경한다.

## Path Conventions

경로는 저장소 루트 기준이다. 제품은 `src/algorithm_problem_picker/`, 회귀는 `tests/`, HTML은 `tests/fixtures/jungol/`, 이번 실행 기록은 `specs/003-align-site-listing/quickstart.md`에 둔다. `001/T041`, `001/T042`는 과거 기능의 작업 번호이며 이 문서의 ID와 다르다.

001·002의 명세·계약·실행 이력은 보존한다. 이번 정책은 003의 대체 관계를 따른다. ISSUE-003의 누적 개수 동기화·진행 이벤트 변경, 영구 캐시, 상세 보강, 새 원격 접근 경로는 추가하지 않는다. 헌장 III의 영구 캐시 원칙과 다른 범위는 plan.md에 정당화된 기존 사용자 합의를 그대로 따른다.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 기존 작업 트리와 검증 환경을 확인한다.

- [X] T001 `pyproject.toml`·`uv.lock` 기준 Python >=3.12, 잠금 의존성, Chromium 준비 상태와 `003-align-site-listing` 브랜치·HEAD·dirty 상태를 확인하고 `specs/003-align-site-listing/quickstart.md`에 기록한다; 필요한 경우에만 `uv sync --locked --python 3.12`와 `uv run --locked playwright install chromium`을 실행하고 기존 미커밋 변경을 구현 기준으로 보존한다. 동일 가상환경 직접 실행이나 샌드박스 제한을 사용·관측하면 명령과 환경 문제를 별도로 기록한다.

**Checkpoint**: 실행 환경과 시작 상태가 기록됐다. 의존성 갱신·과거 성능 재측정은 선행 조건이 아니다.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 공유 도메인 경계와 최소 재생 자료를 확정한다. T002~T003 완료 후 스토리 구현을 시작한다.

- [X] T002 `src/algorithm_problem_picker/models.py`·`src/algorithm_problem_picker/ports.py`·`src/algorithm_problem_picker/service.py`와 기존 `tests/test_selection.py`·`tests/test_service.py`를 대조하고 아래 불변식을 유지할 경계를 `specs/003-align-site-listing/quickstart.md`에 기록한다. 값은 Rated의 "bool이 아닌 정수 1~30", Known[int]의 "bool이 아닌 정수 0 이상", Known[Decimal]의 "유한 Decimal 0~100"이다. SearchCriteria의 min_tier/max_tier는 "생략 가능. 지정하면 정수 1~30, 하한≤상한. 사이트 검색 조건으로 전달하며 `Rated.value`의 로컬 범위 검사에는 쓰지 않는다.", min_rate/max_rate는 "생략 가능. 유한 Decimal 0~100, 하한≤상한. 로컬 필터에서 양 끝 포함.", min_accepted/max_accepted는 "생략 가능. 정수 0 이상, 하한≤상한. 로컬 필터에서 양 끝 포함.", status는 "all/solved/unsolved. 기존 공개 사용자 기준을 유지한다.", user_handle은 "앞의 @ 한 개 정규화, 대소문자 보존. solved/unsolved는 정확한 핸들 필수, all+user는 입력 오류."를 따른다. Problem의 id는 "bool이 아닌 양의 정수. 고유성 기준.", title은 "비어 있지 않은 문자열.", url은 "해당 id의 `https://jungol.co.kr/problem/<id>`와 일치.", tier는 "Rated/Unrated/Unavailable. 표시 관측값을 요청 범위에 맞춰 보정하지 않는다.", pass_rate는 "Known[Decimal]/Unavailable.", accepted_count는 "Known[int]/Unavailable. 동일 사용자의 중복 정답 제출을 포함한다.", listed_at은 "시간대가 있는 관측 시각."이다. UserReference의 "정확한 handle·양의 account_id·시간대 있는 resolved_at"과 resolve_user/collect Protocol, 수집 성공 후에만 Processing·선택·Result를 수행하는 경계를 유지하며 테스트 전용 공개 API를 만들지 않는다.
- [X] T003 `tests/fixtures/jungol/tier-pagination.html`을 바탕으로 `tests/fixtures/jungol/site-listing.html`에 정상 Rated 8·10·13, 실제 0·정상 정답/정답률과 URL에 대응하는 공개 필터 UI를 제공하는 최소 합성 자료를 만든다; 기존 list.html·pagination.html·empty.html·user.html은 재사용한다. 모든 통계는 이 기본 fixture에서는 정상 수치로 두고 US2에서 셀을 변형하며, 추가/번호 목록은 기존 serve/html 방식으로 재생해 공통 프레임워크를 추가하지 않는다. 합성 번호·통계를 실사이트 최신 사실로 표시하지 않는다.

**Checkpoint**: 타입·Protocol을 확장하지 않고 새 정책을 재생할 수 있다. 준비·파싱·종료의 제품 변경은 각 스토리에서 수행한다.

---

## Phase 3: User Story 1 — 사이트가 제공한 티어 검색 결과로 조회·추천하기 (Priority: P1) 🎯 MVP

**Goal**: 수집기와 순수 필터 모두 정상 범위 밖 Rated를 보존하고 실제 표시값을 사용한다. 요청 조건 손실·배지 오류는 계속 실패한다.

**Independent Test**: 정상 수치만 있는 로컬 첫·번호·추가 목록을 티어 9~13·하한만·상한만으로 조회·추천한다. 범위 밖 Rated가 다른 조건을 만족하면 후보·추첨 모집단에 남고 실제 티어가 표시되며 경고가 없어야 한다. 미정·미확인 정책, URL/UI 손실과 잘못된 배지 실패는 유지한다. 이 증분은 US2의 새 빈 셀이나 US3의 새 종료 경로 없이 기존 완료 신호가 있는 fixture로 검증한다.

### Tests for User Story 1

- [X] T004 [P] [US1] `tests/test_jungol_dom.py`의 `test_rated_outside_range_has_diagnostics`를 보존 성공을 나타내는 이름·기대로 전환하고 `tests/fixtures/jungol/site-listing.html`로 최초·번호 페이지·더 불러오기 × 양쪽·하한만·상한만의 최소 매개변수화 회귀를 작성한다; 범위 안/밖 Rated의 ID·관측 티어와 추가 경고 부재를 확인한다. 요청 URL/UI 조건 누락·중복·변조, 공개 사용자 solvedBy/solvedByMode, 잘못된/누락/중복 배지 검증은 유지하고 원격 요청을 차단한다 (FR-001~004, SC-001).
- [X] T005 [P] [US1] `tests/test_selection.py`에서 `test_default_id_order_and_one_sided_bounds`의 Rated 제외 기대를 보존으로 바꾸고 양쪽/한쪽 경계·범위 밖만 있는 모집단·정답률/정답 제출 수 조건 탈락·실제 표시 티어 난이도 정렬을 검증한다; 티어 경계가 있으면 Unrated 제외·Unavailable 한 번 집계, 없으면 포함하는 기존 정책을 유지한다. `test_unknown_count_stops_at_first_active_filter`의 기대는 Rated가 수치 필터에 도달하므로 2→3으로 변경하고 `_within`의 수치 양끝 포함은 보존한다 (FR-003~004, FR-012, SC-001·006).
- [X] T006 [P] [US1] `tests/test_service.py`에 list/recommend와 양쪽/한쪽 경계에서 모든 Rated가 요청 범위 밖이어도 수치 조건 통과 시 적격 후보가 되는 사례를 추가한다; 추첨 모집단 전체·최초 관측·고유 개수·실제 티어 보존을 확인하고 정상 미정/미확인만 있는 기존 적격 0·미확인 제외 1 사례는 유지한다 (FR-003~004, FR-012, SC-001·006).
- [X] T007 [P] [US1] `tests/test_cli.py`에 list/recommend의 요청 티어 경계·실제 범위 밖 티어 출력과 티어 불일치 경고 부재, 티어 옵션이 사이트 검색 조건이라는 도움말 의미를 검증하는 사례를 작성한다; 기존 입력 범위 오류 2와 도움말/입력 오류의 공급자 시작 0건을 유지한다 (FR-004·014, SC-001·008).

### Implementation for User Story 1

- [X] T008 [P] [US1] T004의 새 정책 실패 확인 후 `src/algorithm_problem_picker/jungol.py`의 `_collect`에서 정상 Rated와 요청 min_tier/max_tier를 비교해 SourceAccessError를 발생시키는 분기만 제거한다; `/solved/0.svg`와 1~30 배지 검증, 표시값·최초 관측 보존 및 `_verify_filters`의 최초/후속 URL·origin·경로·공개 UI·사용자 조건 검증은 유지한다 (FR-001~004).
- [X] T009 [P] [US1] T005~T006의 새 정책 실패 확인 후 `src/algorithm_problem_picker/selection.py`의 `filter_listing`에서 정상 Rated의 요청 티어 `_within` 비교만 제거한다; Unrated/Unavailable의 경계 유무 정책과 티어 상태→정답률→정답 제출 수 순서, 고유 문제당 미확인 한 번 집계, 수치 `_within`, 실제 표시값 정렬·전체 고유 모집단 추천을 보존한다 (FR-003~004, FR-012).
- [X] T010 [P] [US1] T007의 도움말 기대 확인 후 `src/algorithm_problem_picker/cli.py`의 TierOption과 list/recommend 도움말에 티어가 사이트 검색 조건이며 표시 티어가 요청 범위 밖일 수 있음을 설명한다; 요청 조건·실제 표시값을 보존하고 새 옵션·불일치 경고·동의 흐름을 만들지 않는다 (FR-004·014, SC-008).
- [X] T011 [US1] T004~T010 후 `tests/test_jungol_dom.py`·`tests/test_selection.py`·`tests/test_service.py`·`tests/test_cli.py`의 US1 관련 사례를 실행하고 `specs/003-align-site-listing/quickstart.md`에 명령·판정·실패 원인/수정 근거를 기록한다; 새 빈 통계·과거 지연 종료 기대의 미해결 실패는 US2/US3로 명시하고 US1 회귀와 구분한다 (SC-001·006·008).

**Checkpoint**: 정상 수치·기존 완료 방식에서 사이트가 선택한 범위 밖 Rated를 조회·추천할 수 있다. 이 단계가 제안 MVP이며 전체 라이브 수용 완료를 뜻하지 않는다.

---

## Phase 4: User Story 2 — 통계가 미제공인 문제가 있어도 조회·추천하기 (Priority: P1)

**Goal**: 셀별 명시적 빈 표시를 준비 판정과 파서에서 같은 Unavailable로 읽고 0·임시 빈 값·구조 오류와 구분한다.

**Independent Test**: 첫·추가 목록에 정상 수치·실제 0·정답만/정답률만/둘 다 명시적 미제공을 섞는다. 해당 필터가 없으면 포함·미확인 표시, 최소/최대 필터가 있으면 고유 문제당 한 번 제외, 0~0은 실제 0만 통과해야 한다. 전부 제외돼도 코드 0·결과 없음/추천 부족이며 마커 없는 임시 값은 실제 값을 기다리고 잘못된 셀·수치는 실패한다. 종료는 아직 기존 완료 신호로 재생할 수 있다.

### Tests for User Story 2

- [X] T012 [P] [US2] `tests/test_jungol_dom.py`에 첫·추가 목록의 정답/정답률 각각과 둘 모두에 대해 `data-col-empty`가 있고 trim 텍스트가 빈 셀을 Unavailable로 수집하는 사례를 작성한다; 빈 속성값도 인정하고 같은 문제의 기존 빈 정답률 링크 예외·네 미제공 토큰·실제 0·정상 천 단위 정수·Decimal 표시 정밀도를 유지한다. 기본 fixture의 수치를 각 사례에서 최소 변형하며 추가 목록에는 기존 완료 신호를 제공한다 (FR-005·008, SC-002).
- [X] T013 [US2] T012 후 같은 `tests/test_jungol_dom.py`에 마커 없는 임시 정답/정답률이 이후 정상 수치가 되는 경우와 끝내 준비되지 않는 경우, 누락·중복 셀, 잘못된 비어 있지 않은 숫자와 빈 마커 동반 오류를 검증한다; 정답의 마커 없는 빈 앵커는 미제공으로 허용하지 않고 오류에 문제·지표가 식별되게 한다. 마커가 있어도 숫자 0·정상 수치는 우선하며 임시 값은 미제공/0으로 변환하지 않는다 (FR-005·008, SC-002).
- [X] T014 [P] [US2] `tests/test_selection.py`의 기존 accepted 경계·정렬·미확인 집계 사례를 재사용해 두 지표의 필터 없음/최소/최대/0~0, 복수 미제공·중복 번호·앞 필터 탈락과 양방향 미확인 마지막/동점 번호순을 최소 매개변수화로 보강한다; 미제공을 0으로 취급하지 않고 고유 제외 수를 한 번만 증가시키는지 확인한다 (FR-006~007, FR-012, SC-003·006).
- [X] T015 [P] [US2] `tests/test_service.py`에 통계 미제공을 포함하는 고정 공급자로 list/recommend의 필터 없는 포함, 해당 수치 조건으로 전부 제외된 정상 0개, fetched/eligible/returned·omitted_unknown_count·추천 shortage 및 중복 최초 관측을 검증한다; 이미 만족하는 처리 코드는 유지하고 새로운 진행 필드나 실패/취소 누적 개수 요구를 추가하지 않는다 (FR-006~007·012~013, SC-003·006).
- [X] T016 [P] [US2] `tests/test_cli.py`에 list/recommend의 두 통계 0/미확인 구분, 필터 미제공 제외 수의 stderr 안내, 모든 후보 제외 시 코드 0·결과 없음·실제 반환/부족 수를 검증한다; 기본 브라우저 호출은 차단하고 기존 출력 규칙으로 만족하면 제품 출력 코드를 변경하지 않는다 (FR-006~007, SC-003).

### Implementation for User Story 2

- [X] T017 [US2] T012~T016의 새 기대 확인 후 `src/algorithm_problem_picker/jungol.py`의 `_SNAPSHOT`에 rateEmpty/acceptedEmpty를 추가한다; data-model.md의 rates/accepted는 "각각의 통계 셀을 순서대로 읽은 trim 텍스트 배열. 배열 길이로 누락·중복 확인.", rateEmpty/acceptedEmpty는 "같은 셀 목록에서 추출한 `data-col-empty` 존재 여부의 boolean 배열. 빈 속성값도 true다.", rateLinks는 "정답률 셀 링크 대상. 기존 같은 문제 빈 링크의 미제공 지원에 사용.", links는 "해당 문제 셀의 링크·제목·배지·미정/미확인 정보. 기존 구조 검증 유지.", regular는 "일반 문제 표시 존재 여부."를 따른다. 텍스트와 표시 배열을 같은 셀 순서·개수로 생성하고 고정 열 번호·스타일·해시 클래스에 의존하지 않는다 (FR-005·008).
- [X] T018 [US2] T017 후 `src/algorithm_problem_picker/jungol.py`에 셀 정확히 1개·trim 빈 텍스트·해당 셀의 명시적 빈 표시를 함께 판별하는 비공개 공통 규칙을 만들고 `_wait_listing` 준비와 `_problem` 파싱에 같이 적용한다; 기존 미제공 토큰·같은 문제 빈 정답률 링크 예외를 유지하고 정답 제출 수로 링크 예외를 확대하지 않는다. 비어 있지 않은 텍스트는 숫자/토큰 규칙으로 읽어 정상 0·정밀도를 보존하며 잘못된 숫자·누락/중복·준비 실패를 Unavailable/0으로 감추지 않는다. 도메인 타입과 공개 경계를 늘리지 않는다 (FR-005~008).
- [X] T019 [US2] T012~T018 후 `tests/test_jungol_dom.py`·`tests/test_selection.py`·`tests/test_service.py`·`tests/test_cli.py`의 US1/US2 관련 검증을 실행해 범위 밖 Rated와 통계 미제공의 조합도 확인하고 `specs/003-align-site-listing/quickstart.md`에 결과를 기록한다; 보호 동작의 실패가 있을 때만 해당 기존 처리 책임 안에서 최소 수정하며 US3의 반대 종료 기대는 별도로 남긴다 (SC-001~003·006).

**Checkpoint**: 명시적 빈 통계 때문에 최초·추가 목록이 중단되지 않으며 미제공·실제 0·일시 미준비·오류가 구분된다.

---

## Phase 5: User Story 3 — 더 불러오기 버튼 상태에 따라 수집 완료하기 (Priority: P1)

**Goal**: 버튼·다음 번호 링크가 없고 현재 목록을 읽을 수 있으면 완료한다. 버튼이 있으면 계속 수집하고 번호 페이지·사용자 검색의 기존 준비 정책을 보존한다.

**Independent Test**: 최초 버튼 부재, 추가 후 버튼 유지/로딩/disabled/제거, 새 행 없는 최종 로드, 정상 빈 결과를 재생한다. 클릭 후 버튼 부재 경로는 목록 busy·pending·별도 완료 알림·두 번 동일 스냅샷·외부 루프 재대기로 차단되지 않아야 한다. 버튼 유지 진행 없음·중복 컨트롤·반복 페이지·접근/구조 오류·취소는 계속 실패/취소하며 최종 결과를 출력하지 않는다. 지연된 미래 행·버튼의 포함은 보장하지 않는다.

### Tests for User Story 3

- [X] T020 [P] [US3] `tests/test_jungol_dom.py`의 `test_cursor_disappears_before_delayed_rows`, `test_cursor_disappears_without_completion_evidence`, `test_cursor_waits_for_loading_and_delayed_next_button`, `test_cursor_empty_request_needs_public_completion`, `test_t041_delayed_rows_after_completed_request`, `test_t041_empty_request_alone_is_not_completion`, `test_t041_rows_before_next_control_do_not_finish_collection`를 버튼 부재 시 현재 목록 성공을 나타내는 이름·기대로 전환한다; 최초 부재·최종 새 ID 있음/없음·명시적 빈 결과와 누적 후보 보존을 포함한다. 클릭 후 부재 시 목록 busy·관련 pending·별도 완료 알림·이중 안정화·외부 재대기가 종료를 막지 않는지 확인하고, 평가 시점의 공개 DOM/로컬 route를 결정적으로 제어해 고정 sleep·실행 속도로 미래 후보 수를 맞추지 않는다 (FR-009~010·015, SC-004~005).
- [X] T021 [US3] T020 후 같은 `tests/test_jungol_dom.py`에서 버튼 유지·로딩/disabled·새 ID 진행·진행 없음 제한, 다음 번호 링크·반복/새 ID 없는 페이지·잘못된 next URL·중복 버튼/링크/동시 컨트롤·버튼 없는 깨진 표/배지/통계·접근 오류를 확인한다. `test_unrelated_loading_cycle_is_not_result_completion`을 listing 성공/user 기존 실패로 분리하고 목록 관찰자 정리 실패 분기는 추가 로드 대기 중 원래 KeyboardInterrupt 보존 사례로 대체한다; 사용자 관찰자 cleanup 실패·T042의 지연/동일 핸들/장식 변경·공개 사용자 조건 손실 검증은 유지한다. 테스트 삭제·skip/xfail로 반대 정책을 숨기지 않는다 (FR-001·008·011·013·015, SC-004~006).
- [X] T022 [P] [US3] `tests/test_service.py`에서 새 종료 기준으로 완료한 목록의 전체 고유 후보를 수집 후 필터·정렬·추첨하고 limit/count=1이어도 전체 모집단을 사용함을 확인한다; Result의 "`fetched_count >= eligible_count >= returned_count`, 고유 번호·최초 관측 유지.", "`returned_count = min(requested_count, eligible_count)`, requested_count는 양수.", "추천 shortage는 requested_count−returned_count이며 list의 shortage는 0이다.", "`0 <= omitted_unknown_count <= fetched_count−eligible_count`.", "시작·완료 시각은 시간대가 있고 finished_at≥started_at이다."를 유지한다. 기존 실패/취소의 Processing·필터·추첨·Result 금지 검증을 재사용하고 누적 개수 보존을 새 수용 조건으로 넣지 않는다 (FR-012~013, SC-006).
- [X] T023 [P] [US3] `tests/test_cli.py`에서 list/recommend의 유효한 현재 목록 완료는 코드 0으로 결과를 제공하고 실제 접근·구조·진행 실패와 Ctrl+C는 코드 1/130·최종 표/추천 stdout 없음으로 끝나는지 검증한다; stderr 실패/취소 안내·브라우저 정리, 기본값·solver 입력 오류 2·명시적 open 회귀를 유지하며 실패 누적 개수는 판정하지 않는다 (FR-011~013, SC-006).

### Implementation for User Story 3

- [X] T024 [US3] T020~T023의 새 기대 확인 후 `src/algorithm_problem_picker/jungol.py`의 `_wait_listing(previous)`에서 previous가 있는 클릭 후 모드에 접근 오류·중복 진행 컨트롤·현재 행/표 또는 명시적 빈 결과 검증을 유지한 컨트롤 부재 반환 경로를 일반 guard보다 먼저 둔다; 이 경로는 `_pending`·목록 busy 해제·두 번 동일 스냅샷·별도 완료 알림·새 ID를 종료 증거로 요구하지 않되 마커 없는 임시 통계의 준비와 구조/파싱 오류는 구분한다. 컨트롤이 남으면 기존 pending/busy/disabled 준비·새 ID·제한을 유지하고 next가 있으면 번호 페이지로 진행한다; 최초/번호 페이지의 일반 준비·안정화는 유지한다 (FR-005·008~011).
- [X] T025 [US3] T024 후 `src/algorithm_problem_picker/jungol.py`에서 `_LIST_UPDATE`, 목록용 update 인수·completed_load·관찰자 생성/정리를 제거하고 `_load_more(previous)`를 클릭→해당 대기로 단순화한다; `_collect`는 최초/번호/추가 로드가 반환한 snapshot을 다음 반복에서 소비하도록 무조건적인 두 번째 일반 `_wait_listing()`을 제거한다. 각 snapshot 처리 전 현재 URL·공개 UI·관측 접근 오류 검증, 고유 최초 관측 누적, next 진행·반복 방지·최소 1초 간격·탐색 30초/준비·동작 15초/50ms 확인을 유지한다. `_USER_UPDATE`·JSHandle import·사용자 대기/관찰자 수명과 성공/실패/취소 브라우저 정리는 보존한다. CompletedListing의 candidates는 "최초 관측을 유지한 고유 Problem의 tuple.", completed_at은 "적용된 수집 종료 기준을 만족한 시각. 시간대 필수."이며 `src/algorithm_problem_picker/models.py`의 관련 완료 의미 주석이 충돌할 때만 정합성을 수정한다 (FR-001·009~013).
- [X] T026 [US3] T020~T025 후 `tests/test_jungol_dom.py`·`tests/test_service.py`·`tests/test_cli.py`의 US3 및 번호 페이지/사용자 검색 보호 회귀를 실행하고 `specs/003-align-site-listing/quickstart.md`에 전환한 합성 기대와 유지한 오류 경계·실행 결과를 기록한다; 실제 JungolSource→Picker의 list/recommend·limit/count=1·중복 최초 관측·정렬/전체 후보 선택·상세 문서 요청 0건을 함께 확인한다. 새 고정 대기·종료 판정용 요청·공개 상태/API·ISSUE-003 필드는 추가하지 않는다 (SC-004~006, FR-015).

**Checkpoint**: 세 정책이 함께 동작하고 버튼 부재의 현재 목록 성공과 실제 실패/취소가 구분된다. 사용자 검색·번호 페이지는 기존 완료 규칙을 유지한다.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: 사용 안내·전체 회귀·원문 세 명령의 실사이트 수용을 마친다.

- [X] T027 [P] T026 후 `README.md`의 범위 밖 확정 티어 중단·빈 셀 일괄 오류·목록의 별도 공개 완료 근거 필수 안내를 현재 정책으로 바꾼다; 사이트 티어 검색 의미·표시값 보존, 명시적 빈 통계와 실제 0·필터 유무, 버튼 부재 현재 목록 완료와 미래 지연 반영 한계를 설명한다. 사용자 검색의 완료 근거 설명은 유지하고 검증 안내를 `specs/003-align-site-listing/quickstart.md`에 연결하며 001/002는 과거 정책·검증 이력으로 구분한다 (FR-014~015, SC-008).
- [X] T028 [P] T026 후 `src/algorithm_problem_picker/cli.py`의 list/recommend 관련 도움말과 조건/관측값 안내를 `specs/003-align-site-listing/contracts/cli.md`와 대조해 티어 사이트 검색·미제공과 0·버튼 부재 종료 의미를 일관되게 정리하고 `tests/test_cli.py`의 해당 도움말 회귀를 갱신한다; 요청 경계·관측 티어·현재 옵션/기본값/종료 코드·출력 채널을 유지하며 새 경고·옵션·확인 화면을 만들지 않는다 (FR-014, SC-008).
- [X] T029 T027~T028 후 `uv run --locked pytest -q`와 `uv run --locked jpick list --help`, `uv run --locked jpick recommend --help`를 실행해 전체 회귀·문서/출력 일치를 확인하고 `specs/003-align-site-listing/quickstart.md`에 명령·revision/dirty·환경·결과를 기록한다; `scripts/validate_live.py`·`scripts/benchmark_selection.py`·`scripts/benchmark_collection.py`의 기존 모델/Protocol 호환성도 검토하되 새 벤치 목표나 선택적 사용자 라이브 실행을 추가하지 않는다. 환경 제한·미실행·제품 실패를 통과와 구분하고 새 변경/실패 없이 동일 검증을 반복하지 않는다 (FR-015, SC-001~006·008).
- [X] T030 T029의 로컬 검증 통과 후 `specs/003-align-site-listing/quickstart.md`의 원문 세 명령 `uv run --locked jpick recommend --min-tier 9 --max-tier 13 --count 2`, `uv run --locked jpick recommend --min-tier 9 --max-tier 10 --count 2`, `uv run --locked jpick list --min-tier 1 --max-tier 1 --sort accepted --order desc --limit 5`를 실제 사이트에서 순차 실행하고 같은 파일에 각 명령·실행 시각(Asia/Seoul)·revision/dirty·환경·종료 코드·성공 시 수집/적격/반환 수·표시 정책·오류와 원시 진단을 기록한다; 정상 접근이면 새 정책으로 코드 0·결과 또는 정상 없음이어야 한다. 당시 문제/통계/550·200·100/250·134개를 고정 기대값으로 삼지 않고 무작위 결과에 특정 문제 포함을 요구하지 않는다. 사이트 장애/접근 제한·제품 결함·미실행을 구분하고 실패/미실행을 통과로 표시하지 않으며, 새로 관측한 버튼 제거 후 지연 반영은 재현 순서만 후속 근거로 기록한다 (SC-007, FR-015).

**Checkpoint**: 로컬 회귀와 실사이트 수용 결과를 구분해 기록했다. T030이 미실행·차단·실패면 SC-007 및 전체 수용 완료를 선언하지 않는다.

---

## Dependencies & Execution Order

### Phase Dependencies

```text
T001 Setup → T002~T003 Foundational
                    ↓
US1: T004~T007 tests → T008 / T009 / T010 → T011 checkpoint (MVP)
                    ↓
US2: T012 → T013, T014 / T015 / T016 tests → T017 → T018 → T019 checkpoint
                    ↓
US3: T020 → T021, T022 / T023 tests → T024 → T025 → T026 checkpoint
                    ↓
T027 README / T028 CLI → T029 full regression → T030 live acceptance
```

`/`는 서로 다른 파일의 병렬 기회를 뜻한다. 쉼표로 나열된 테스트도 모두 해당 구현 전 완료한다. 화살표는 선행 완료 조건이다.

### User Story Dependencies

- **US1**: Foundational 이후 독립 검증 가능하다. 새 빈 통계·새 완료 정책이 필요 없는 고정 자료로 MVP를 검증한다.
- **US2**: 정책 자체는 US1과 독립적이지만 `jungol.py`·selection/service/CLI 테스트 충돌과 결합 검증을 위해 기본 순서에서 T011 이후 시작한다. 새 빈 상태는 기존 완료 신호가 있는 목록으로 독립 검증한다.
- **US3**: 현재 목록 완료 경로에서 US2와 동일한 통계 준비/파싱 규칙을 사용하므로 T018에 의존한다. 기본 순서는 T019 이후다. 버튼 정책만 검증하는 사례는 정상 통계로 분리하고 사용자/번호 페이지 회귀를 함께 유지한다.
- **Polish**: T026 이후 T027/T028을 병렬 진행할 수 있다. T029는 둘 모두를 기다리며 T030은 로컬 회귀 통과 후 수행한다.

### Within Each User Story

새 정책 테스트 작성·실패 원인 확인 → 제품 변경 → 해당 스토리·이전 증분 회귀 → 기록 순서다. 목록 영역의 미래 반영을 기다리지 않는 정책을 사용자 검색의 지연 검증 제거로 확장하지 않는다. 스토리 체크포인트의 선별 검증과 최종 전체 회귀는 목적이 다르며 실패 원인을 숨기기 위해 선별하지 않는다.

### Parallel Opportunities

- US1 테스트 T004/T005/T006/T007은 서로 다른 네 파일에서 병렬 작성할 수 있다. 해당 테스트 완료 후 제품 T008/T009/T010도 서로 다른 세 파일에서 병렬 진행할 수 있다.
- US2 테스트는 DOM의 T012→T013을 순차 처리하면서 T014/T015/T016을 다른 파일에서 병렬 작성할 수 있다. snapshot과 파서를 바꾸는 T017→T018은 순차 처리한다.
- US3 테스트는 DOM의 T020→T021을 순차 처리하면서 T022/T023을 다른 파일에서 병렬 작성할 수 있다. 같은 수집기의 T024→T025는 순차 처리한다.
- 문서 T027과 CLI/테스트 T028은 병렬 가능하다. 모두 quickstart.md에 쓰는 검증 기록 작업과 실사이트 실행은 직렬 처리한다.
- `[P]`는 구현 시 선택 가능한 작업 분리다. 이 작업 목록을 생성하는 단계에서 에이전트 위임이나 제품 구현을 수행했다는 의미가 아니다.

## Parallel Example: User Story 1

T003 완료 후 다음 테스트를 함께 작성할 수 있다.

```text
T004: tests/test_jungol_dom.py — 최초/번호/추가 목록의 범위 밖 Rated 보존
T005: tests/test_selection.py — 사이트 티어 경계와 로컬 수치 조건 분리
T006: tests/test_service.py — 전체 Rated 후보의 조회/추천·개수
T007: tests/test_cli.py — 요청 경계/관측 티어·도움말
```

새 기대 확인 후 T008(jungol.py), T009(selection.py), T010(cli.py)을 병렬 처리하고 T011에서 통합 검증한다.

## Parallel Example: User Story 2

T011 완료 후 다음 테스트 묶음을 함께 작성할 수 있다.

```text
T012 → T013: tests/test_jungol_dom.py — 명시적 빈 셀과 임시 값/구조 오류
T014: tests/test_selection.py — 0~0·미제공·고유 제외 수·정렬
T015: tests/test_service.py — 모든 후보 제외·실제 개수·추천 부족
T016: tests/test_cli.py — 0/미확인·stdout/stderr·정상 0개
```

테스트 완료 후 T017→T018을 순서대로 처리하고 T019에서 통합 검증한다.

## Parallel Example: User Story 3

T019 완료 후 다음 테스트 묶음을 함께 작성할 수 있다.

```text
T020 → T021: tests/test_jungol_dom.py — 현재 목록 완료·오류/사용자/번호 보호
T022: tests/test_service.py — 전체 후보 처리·Result 불변식·실패/취소
T023: tests/test_cli.py — 정상 현재 목록 결과·실패/취소 무출력
```

테스트 완료 후 T024→T025를 함께 적용할 정책 증분으로 순차 처리한다. 대기 함수만 바꾸고 외부 재대기를 남긴 상태를 완료로 판정하지 않으며 T026에서 통합 검증한다.

## Implementation Strategy

### MVP First (User Story 1 Only)

1. T001~T003으로 환경·경계·fixture를 준비한다.
2. T004~T010으로 티어 수집 예외와 로컬 재필터를 함께 제거하고 CLI 의미를 맞춘다.
3. T011로 정상 수치·기존 완료 방식의 조회/추천을 검증한다. 이 범위가 US1 MVP다.
4. 이 체크포인트에서는 US2/US3와 실사이트 세 명령의 전체 해결을 주장하지 않는다. 전체 기능을 계속할 때는 아래 순서를 따른다.

### Incremental Delivery

1. US1 보존 정책 검증 후 US2를 더해 명시적 빈 통계와 수치 필터·표시를 검증한다.
2. US3에서 종료 분기·관찰자 수명·snapshot 소비 흐름을 맞추고 사용자 검색·번호 페이지 경계를 확인한다.
3. README·도움말을 정리하고 전체 회귀를 한 번 실행한다. 수정·새 실패가 있으면 관련 검증을 다시 수행한다.
4. 세 원문 라이브 명령을 순차 수용하고 실제 관측을 기록한다. 개발·합성 검증과 실사이트 성공 여부를 분리한다.

### Requirement Coverage

| 요구사항 | 주요 작업 | 검증 기준 |
| --- | --- | --- |
| FR-001~004 | T004~T011, T021, T025 | SC-001: 최초/번호/추가·양쪽/한쪽 경계·표시값·조건 손실/배지 오류 |
| FR-005, FR-008 | T012~T013, T017~T019, T024 | SC-002: 정상 수치/0/명시적 빈 값/임시 값/구조 오류 구분 |
| FR-006~007 | T014~T016, T019 | SC-003: 필터 유무·0~0·복수 미제공·정상 0개/부족 안내 |
| FR-009~011 | T020~T021, T024~T026 | SC-004~005: 버튼 상태·현재 목록·재대기 방지·번호/사용자 보호 |
| FR-012~013 | T005~T006, T014~T016, T022~T023, T025~T026 | SC-006: 고유 최초 관측·전체 후보·개수/정렬·실패/취소 결과 금지 |
| FR-014 | T007, T010, T027~T029 | SC-008: README·도움말·요청 조건/관측값의 일치 |
| FR-015 | T011, T019~T021, T026~T030 | 합성 기대 전환과 과거/신규 기록 분리, SC-007의 원문 세 명령 |

## Notes

- 총 30개: Setup 1개, Foundational 2개, US1 8개, US2 8개, US3 7개, Polish 4개. `[P]` 작업은 16개다.
- 기존 책임에서 이미 만족하는 수치 처리·정렬·출력을 재구현하지 않는다. 필요한 최소 회귀를 보강하고 오류를 드러내는 기존 경계를 유지한다.
- 추가 로드가 완료한 현재 목록은 새 정책의 정상 결과다. 실제 실패/취소 시의 부분 최종 결과 금지는 계속 적용한다.
- 제품 데이터·사용자 매핑·storage_state·HAR·추적 자료를 다음 실행용으로 저장하지 않는다. 로컬 HTML과 개발 검증 기록은 제품 캐시와 구분한다.
- 실사이트 접근 실패와 제품 결함을 구분하되 미실행·실패를 성공으로 기록하지 않는다. 과거 성능 보고서를 새 정책의 실측으로 표시하지 않는다.
