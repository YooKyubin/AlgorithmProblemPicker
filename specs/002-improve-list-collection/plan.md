# Implementation Plan: 안정적인 티어 수집과 정답 제출 수 기반 조회·추천

**Branch**: `002-improve-list-collection` | **Date**: 2026-10-20 | **Spec**: [spec.md](spec.md)

**Input**: `specs/002-improve-list-collection/spec.md`

**현재 상태 (2026-10-24)**: T033 문서 대조를 마쳐 002를 마감했다. 아래 설계·위험·2026-10-21 검증 상태는 당시 이력이며, 최신 판정은 [T033 마감 기록](quickstart.md#t033-마감-2026-10-24)을 따른다. 현재 티어·빈 통계·더 불러오기 종료 정책은 [003 명세의 대체 관계](../003-align-site-listing/spec.md#기존-요구사항과-대체-관계)가 우선한다.

## Summary

티어 범위 조회에서 정상 미정·미확인을 제외하되 수집은 계속하고,
범위 밖 확정 티어·구조 변경·파싱 실패는 원인이 식별되는 실패로 유지한다.
목록의 정답 제출 수를 새 필터·정렬·출력 지표로 삼아 후보별 상세 탐색을 제거한다.

목록에서 완성된 `Problem`을 반환하는 단일 모델과 기존 공급자 Protocol을 사용한다.
전체 수집 → 순수 필터 → 정렬 또는 균등 비복원 추천 → 출력 흐름을 유지한다.
기존 solver 옵션은 입력 오류 2와 새 accepted 옵션 안내로 종료하며 브라우저를 시작하지 않는다.
설계 근거는 [research.md](research.md), 구체적인 데이터와 계약은 [data-model.md](data-model.md) 및
[CLI 계약](contracts/cli.md)·[공급자 계약](contracts/source.md)을 따른다.

## Technical Context

**Language/Version**: Python 3.12 이상. 기존 타입 문법과 dataclass/Enum/Decimal을 유지한다.

**Primary Dependencies**: 기존 Typer, Rich, 동기 Playwright/Chromium, uv. `uv.lock`의 버전을 사용하고 새 의존성을 추가하지 않는다.

**Storage**: 실행 중 메모리만 사용한다. 문제·사용자·브라우저 상태의 영구 저장은 없다. 개발용 고정 HTML과 명시적으로 저장한 검증 보고서는 제품 캐시가 아니다.

**Testing**: pytest, CliRunner, 고정 공급자, Playwright의 로컬 route HTML 재생. 원격 요청과 기본 브라우저 열기는 기본 검증에서 차단한다.

**Target Platform**: 기존 데스크톱 터미널 CLI. 현재 검증 기준은 Windows/PowerShell, Python 3.12 이상과 Chromium이다.

**Project Type**: 단일 Python CLI 패키지.

**Performance Goals**: list/recommend의 문제 상세 요청 0건. 같은 다중 목록 자료로 변경 전후 각 3회 이상 실행해 전체 소요 시간 중앙값 감소와 목록 수집 시간을 별도로 기록한다. 절대 완료 시간이나 라이브 개선율을 미리 정하지 않는다.

**Constraints**: 공개 DOM만 읽기, 비영구 컨텍스트 한 개, 탐색·더 불러오기 시작 최소 1초 간격, 탐색 30초/DOM 준비 15초 기본값 유지. 내부 API 직접 호출·응답 해독·앱 내부 상태·자동 재시도·접근 제한 우회는 사용하지 않는다. 전체 목록 완료 전 결과 출력과 개수 기반 조기 종료는 허용하지 않는다.

**Scale/Scope**: 개인용 JUNGOL 공개 일반 문제 조회·추천. 티어·정답률·정답 제출 수와 지정 공개 사용자 풀이 조건. 플랫폼 확대·로그인·캐시·IDEA-001은 제외한다.

## Constitution Check

계획 진입 전과 Phase 1 설계 후 동일한 기준으로 검토했다. 아래 PASS는 설계 적합성 판정이며 구현 수용 검증 통과를 뜻하지 않는다.

| 원칙 | 계획 진입 전 | 설계 후 | 적용 근거 |
| --- | --- | --- | --- |
| I. JUNGOL에 집중 | PASS | PASS | 기존 CLI와 공개 일반 문제 범위만 변경한다. |
| II. 허용된 데이터 접근 | PASS | PASS | 기존 공개 DOM 계약을 승계하고 상세 탐색을 제거한다. 새로운 원격 접근 경로를 추가하지 않는다. |
| III. 로컬 데이터 우선 | 승인된 범위 예외 | 승인된 범위 예외 | 명세와 원문 이슈에서 캐시 제외를 명시했다. 중복 없는 추천은 유지한다. |
| IV. 단순한 구조 | PASS | PASS | 기존 공급자·서비스·순수 처리·CLI 분리를 유지하고 상세 계층을 제거한다. |
| V. 명확한 동작과 검증 | PASS | PASS | 미제공/실패, 지표 전환, 완료/취소를 구분하며 최소 회귀와 재생 벤치를 계획한다. |

헌장 III의 영구 캐시 요구와의 차이는 이번 기능의 명시적 범위에 근거한 예외다.
다른 미정당화 위반이나 설계상 미결정 사항은 없다.
다만 기존 T041·T042의 알려진 구현 결함은 후술한 통합 수용 제약이며, 설계 PASS로 해결됐다고 판단하지 않는다.

## Project Structure

### Documentation (this feature)

```text
specs/002-improve-list-collection/
├── spec.md
├── checklists/requirements.md
├── plan.md
├── research.md
├── data-model.md
├── contracts/
│   ├── cli.md
│   └── source.md
└── quickstart.md
```

`tasks.md`에 구현 순서와 실제 완료 상태를 기록한다.
001 산출물은 이전 동작과 미완료 작업의 이력으로 보존하고 002 계약을 새 구현의 기준으로 삼는다.

### Source Code (repository root)

다음은 구현 시 변경할 경로다. 이 계획 작성 단계에서는 제품 코드를 수정하지 않는다.

```text
src/algorithm_problem_picker/
├── models.py           # 단일 Problem, accepted 조건, Processing 상태
├── ports.py            # resolve_user/collect만 남긴 Protocol
├── jungol.py           # 정답 셀 추출·티어 진단·상세 탐색 제거
├── selection.py        # 목록의 세 지표 필터와 accepted 정렬
├── service.py          # 전체 수집 후 처리, 상세 루프 제거
└── cli.py              # accepted 옵션·옛 옵션 거부·출력/진행 갱신

tests/
├── conftest.py
├── test_selection.py
├── test_service.py
├── test_cli.py
├── test_jungol_dom.py
└── fixtures/jungol/    # 최소 정상/경계/구조 오류·추가 로드 자료

scripts/
├── benchmark_selection.py   # 기존 로컬 계산 검증의 지표 전환
├── validate_live.py         # 상세 없는 공개 사용자 집합 검증
└── benchmark_collection.py  # 신규: baseline/current 로컬 재생 비교

README.md                   # 사용법·지표 의미·전환 안내·목록 전용 흐름
```

**Structure Decision**: 패키지 구조는 유지한다. 수집기만 DOM과 사이트 URL을 알고,
서비스는 Protocol과 모델만, 순수 선택 로직은 모델만 참조한다.
개발용 벤치 도구는 제품 코드 밖에서 기존 경계를 계측한다.
과거 상세 HTML은 baseline 재생에 필요하면 검증 자료로 남기며 제품 조회에서는 사용하지 않는다.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
| --- | --- | --- |
| 헌장 III의 영구 캐시를 구현하지 않음 | 이번 명세와 원문 이슈가 캐시를 명시적으로 제외함 | 캐시 추가는 사용자 범위를 벗어나며 별도 저장·갱신·만료 정책이 필요함 |

## Phase 0 — 조사 결과

[research.md](research.md)에 결정·근거·대안을 정리했다.

- 정상적인 티어 부재는 수집 레코드에 보존하고 순수 필터에서 제외한다. 확정 티어의 범위 이탈만 필터 적용 오류다.
- 정답 열은 단일 셀과 엄격한 정수 형식을 검증한다. 명시적 미제공 표식은 새 설계 계약이며 실제 사이트 관측이라고 주장하지 않는다.
- Candidate/Problem 보강 모델을 단일 Problem으로 합치고 상세용 브라우저 페이지·메서드·진행 개수를 제거한다.
- CLI 입구에서 레거시 옵션을 거부해 새 옵션 안내가 일반 Enum 오류에 묻히지 않게 한다.
- 기존 계산 벤치만으로 수집 개선을 입증할 수 없으므로 별도 로컬 재생 비교를 설계한다.

## Phase 1 — 설계와 구현 순서

### 1. 도메인과 경계 전환

`Problem`에 목록 관측 `accepted_count`를 포함한다. `SearchCriteria`의 solver 경계를 accepted 경계로,
`SortKey.SOLVERS`를 `ACCEPTED`로 교체한다. `Candidate`, 상세 관측 시각과 상세 공급자 메서드는 제거한다.
`CompletedListing.candidates`의 원소는 Problem으로 바꾸고 최초 ID 관측 유지·전체 완료 의미는 지킨다.
Progress는 수집→Processing→Complete 흐름과 실패·취소를 지원한다. 상세 개수는 제거한다.

### 2. 수집기와 순수 처리 전환

목록 snapshot에 정답 열을 추가하고 공개 결과의 준비 상태를 확인한 뒤 파싱한다.
티어 파서의 정상 상태 구분을 유지하며 구조·해석 오류에는 진단을 보강한다.
첫 목록과 추가 로드마다 요청 조건과 공개 적용 상태·확정 티어를 검증한다.
상세용 페이지 생성·read_details·상세 대기 코드를 제거한다.

전체 완료 객체를 받은 후 티어·정답률·정답 제출 수를 한 번의 순수 필터로 처리한다.
활성 필터에서 미확인으로 제외된 문제를 한 번만 세고 정렬·추천은 전체 적격 집합에 수행한다.
현재 `random.sample`과 `shuffle`, 동점·미확인 정렬 규칙을 재사용한다.

### 3. CLI와 사용법 전환

새 수치 옵션은 최소 0인 정수와 범위 검증을 적용한다.
두 레거시 범위 옵션은 숨긴 거부 경로만 두며 실제 도메인 값으로 전달하지 않는다.
정렬 문자열은 비공개 변환 경로에서 solvers 전환 안내 후 정상 Enum으로 바꾼다.
표·요약·관측 시점·도움말을 정답 제출 수로 통일하고 중복 정답 제출 포함 의미를 설명한다.
실제 처리에 없는 상세 진행 안내를 제거한다. README와 두 기존 개발 스크립트도 갱신한다.

### 4. 회귀 검증과 성능 기록

기존 네 테스트 모듈의 상세 보강 기대를 목록 전용 기대로 교체한다.
추가 검증은 아래 추적표의 경계에 집중하고 동작을 그대로 복제하는 중복 테스트는 만들지 않는다.
별도 수집 벤치 도구는 고정 다중 목록을 원격 요청 없이 재생한다.
기준 commit을 임시 추출한 별도 프로세스와 현재 구현을 같은 자료로 비교하고 원시 시간과 중앙값을 기록한다.
구체적인 실행 명령과 수용 판정은 [quickstart.md](quickstart.md)를 따른다.

## Requirement Traceability & Validation

| 요구사항 | 설계 위치 | 최소 검증 |
| --- | --- | --- |
| FR-001~005 / SC-001~002 | source 계약, 수집기, 티어 필터 | 첫/추가 목록의 미정·미확인, 양쪽/한쪽 경계, 범위 이탈 진단, 파싱/구조 실패, 범위 없는 정렬 |
| FR-006~010 / SC-003~004 | 모델, 목록 정답 파서, 순수 필터/정렬 | 서로 다른 정답·시도·맞힌 사람 값, 0/미제공/경계/쉼표, 양방향 정렬·동점·미확인, 정답률 표시값 유지 |
| FR-011~014 / SC-005~006 | Protocol, 서비스, 전체 완료 객체 | 전체 완료 전 선택 금지, 요청 개수 1/조건 생략에도 상세 0건, 중복 제거·충분/부족/0개, 실패·취소 무출력, 지정 사용자 조건 |
| FR-015~018 / SC-007 | CLI 계약, README | 옛 옵션 코드 2·대응 안내·공급자 생성 0건, 새 도움말/표/진행, 기존 종료 상태·명시적 open |
| FR-019 / SC-008 | 수집 벤치와 quickstart | 고정 다중 목록·동일 후보·각 3회 이상, 전체/목록 시간 분리, 상세 요청 baseline 양수/current 0, 중앙값 감소 |
| FR-020 | source 계약, 접근 오류 경계 | 원격 미승인 경로 없음, 로컬 검증 원격 차단, 접근 제한 시 실패·정리 유지 |

## Known Risks & Integration Gates

- **기존 수집 완전성**: 001 T041은 요청 완료 후 지연된 목록 반영, T042는 사용자 검색 결과 반영에 관한 미완료 작업이다.
  별도 수정·검증 결과를 확인해야 하며 002 범위의 정상 경로 통과만으로 최종 통합 수용을 승인하지 않는다.
  해당 사례에서 완료·사용자 확인을 증명하지 못하면 실패해야 한다. 고정 대기 증가를 해결책으로 사용하지 않는다.
- **미제공 표시**: 정답 열의 미제공 토큰은 합성 자료로 계약을 검증한다. 실제 관측 근거가 없는 빈 셀은 계속 오류다.
  라이브에서 새 표현을 발견하면 원시 표시와 의미를 확인한 뒤 계약을 갱신한다.
- **시간 해석**: 로컬 재생은 후보를 고정하기 위한 검증이다. 실사이트의 개선율이나 전체 목록 수집 시간의 상한을 보장하지 않는다.
  baseline과 변경 구현의 후보 집합이 다르거나 전체 중앙값이 감소하지 않으면 SC-008을 미통과로 기록한다.
- **문서 일관성**: 현재 동작 안내는 README와 002 계약을 갱신한다. 001은 역사 자료로 남기며 기존 solver 요구와 충돌할 때 002가 우선한다.
- **최종 설계 재검토**: Phase 1 후 새 의존성·새 원격 접근·저장 계층·테스트 전용 공개 API가 추가되지 않았음을 확인했다.
  설계 게이트는 통과했다. 아래 구현 검토와 [quickstart 실행 기록](quickstart.md)은 실제 결과를 구분한다.

## 구현 검토 (2026-10-21)

단일 목록 Problem·accepted 필터/정렬·상세 탐색 제거·옛 옵션 거부·사용법과 개발 도구를 구현했다.
새 의존성·원격 접근 경로·캐시·조기 종료·부분 결과·테스트 전용 제품 공개 API는 추가하지 않았다.
회귀는 `uv run --locked pytest -q`: 219 passed, 7 xfailed다. 7개는 001/T041·T042의 범위 밖 결함을 재현한 것이며 수용 통과가 아니다.
고정 다중 목록 성능 결과는 [collection-benchmark.md](collection-benchmark.md)에 환경·revision/dirty·소스/fixture/harness 해시와 함께 기록한다.
실사이트 검증은 미실행이다. T032 평가에서 선행 결함이 재현되었으므로 최종 통합 수용과 T033은 미완료로 남긴다.

## T033 최종 검토 (2026-10-24)

검토 HEAD는 `e9a702a7cf7c333212717b26dade5b95c025e3a2`다. T030·T031의 실제 회귀·성능 결과와 [001 Phase 9 후속 수정·추가 보완](../001-jungol-problem-picker/quickstart.md#phase-9-후속-수정-t041t042-2026-10-21), [003 최종 완료 상태](../003-align-site-listing/quickstart.md#최종-완료-상태)를 확인했다.

- T041·T042의 최초 미통과는 수정 전 이력이다. 두 작업은 별도로 완료됐고, 003의 전체 회귀는 375 passed, 실사이트 세 명령은 3/3 PASS로 기록돼 있다. 현재 제품 네 파일의 SHA-256도 003 실사이트 기록과 일치한다.
- 002의 범위 밖 확정 티어 실패, 빈 통계 처리와 별도 목록 완료 근거 요구는 003에서 명시적으로 대체됐다. 사용자 검색·번호 페이지·실제 실패/취소의 최종 결과 금지와 목록 전용 accepted 처리는 유지한다.
- T031의 list/recommend 각 3회 비교와 상세 요청 baseline 각 4건/current 0건, 전체 시간 중앙값 감소는 당시 통제 조건의 성능 근거다. 이 문서 마감에서 성능을 재측정하거나 현재 revision의 성능으로 일반화하지 않는다.
- FR-001~020/SC-001~008의 유지·대체·실행 제약을 [마감 추적표](quickstart.md#t033-마감-2026-10-24)에 정리하고 README·작업 목록을 맞췄다. 제품 변경 없이 T033을 완료 처리한다.
