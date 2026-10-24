# Implementation Plan: 사이트 목록 기준의 티어·빈 통계·수집 종료 정책

**Branch**: `003-align-site-listing` | **Date**: 2026-10-22 | **Spec**: [spec.md](spec.md)

**Input**: `specs/003-align-site-listing/spec.md` 및 [002 후속 이슈의 최신 합의](../002-improve-list-collection/post-implementation-issues.md)

## Summary

사이트의 티어 검색 결과에 포함된 정상 `Rated` 문제를 보존하고, 명시적인 빈 정답·정답률은 `Unavailable`로 처리한다.  
더 불러오기에서는 버튼과 다음 번호 링크가 없고 현재 목록을 읽을 수 있으면 완료한다. 별도 목록 영역 완료 알림과 미래 지연 반영을 필수로 기다리지 않는다.

기존 `ProblemSource → Picker → selection → CLI` 경계와 도메인 타입을 유지한다. 티어 요청 범위 비교는 수집기와 순수 필터 양쪽에서 제거한다.  
DOM 스냅샷에 통계 셀의 명시적 빈 상태를 보존하고 준비 판정·파서에 동일하게 적용한다. 목록용 관찰자를 제거하고, 추가 로드가 반환한 스냅샷을 외부 루프에서 다시 일반 대기로 막지 않도록 소비 흐름을 정리한다.

번호 페이지·공개 사용자 검색, 접근·구조 오류, 실패·취소의 최종 결과 금지는 유지한다. ISSUE-003의 개수 동기화는 제외한다.  
설계 결정은 [research.md](research.md), 구체적인 계약은 [공급자](contracts/source.md)·[CLI](contracts/cli.md)를 따른다.

## Technical Context

**Language/Version**: Python >=3.12. 조사 환경은 Python 3.12.13이며 기존 타입 문법·dataclass·Decimal을 사용한다.

**Primary Dependencies**: 잠금 파일의 Typer·Rich·동기 Playwright/Chromium, 개발 의존성 pytest와 기존 uv 도구. 조사 환경은 Typer 0.27.3, Rich 15.0.0, Playwright 1.64.0, pytest 9.1.1이다. 새 의존성은 없다.

**Storage**: 실행 중 고유 후보를 메모리에 보관한다. 영구 캐시·사용자 매핑·브라우저 상태 저장은 추가하지 않는다. 고정 HTML과 개발 검증 기록은 제품 캐시가 아니다.

**Testing**: 기존 pytest, Typer CliRunner, 고정 공급자와 로컬 route HTML 재생을 확장한다. 기본 회귀에서 원격 요청과 실제 기본 브라우저 호출을 차단한다. 실사이트 수용은 별도 실행·기록한다.

**Target Platform**: 데스크톱 터미널 CLI. 검증 기준은 Windows/PowerShell과 기존 Python/Chromium 환경이다.

**Project Type**: 단일 Python CLI 패키지.

**Performance Goals**: 정상 list/recommend의 문제 상세 요청 0건, 종료 판정용 새 원격 요청·고정 대기 0개. 요청 개수와 무관하게 해당 종료 기준까지 수집한다. 절대 완료 시간·개선율·새 벤치마크 목표를 추가하지 않는다.

**Constraints**: 공개 DOM만 읽고 기존 순차 접근을 유지한다. 탐색/추가 로드 시작 최소 1초 간격, 탐색 30초·준비/동작 15초 제한과 50ms 확인 간격을 유지한다. 더 불러오기 종료를 위해 별도 안정화 시간·목록 로딩 종료·관련 요청 종료를 추가 증거로 강제하지 않는다. 명시적 빈 상태와 구조 오류는 구분한다.

**Scale/Scope**: 개인용 JUNGOL 공개 일반 문제 조회·추천의 ISSUE-001·002만 포함한다. 실패·취소 개수 동기화, 사용자 검색 재설계, 번호 페이지 완료 정책 변경, 상세 보강·전체 문제은행 재수집·영구 캐시·다른 플랫폼은 제외한다.

## Constitution Check

계획 진입 전 원칙과 범위 예외를 확인했고, Phase 1 설계 후 같은 기준으로 재검토했다. 아래 판정은 설계 게이트이며 구현·라이브 수용 통과를 의미하지 않는다.

| 원칙 | 계획 진입 전 | 설계 후 | 근거 |
| --- | --- | --- | --- |
| I. JUNGOL에 집중 | PASS | PASS | 기존 공개 일반 문제 CLI만 변경한다. |
| II. 허용된 데이터 접근 | PASS | PASS | 002의 공개 DOM 접근 근거·한계를 승계한다. 내부 API 직접 호출·응답 해독·앱 내부 상태·접근 우회·새 원격 경로를 추가하지 않는다. |
| III. 로컬 데이터 우선 | 정당화된 범위 예외 | 정당화된 범위 예외 | 기존 사용자 합의와 003 Assumptions에 따라 영구 캐시를 제외하고, 실행 중 메모리 후보로 순수 처리·중복 없는 추천을 유지한다. |
| IV. 단순한 구조 | PASS | PASS | 기존 Protocol·모델을 유지하고 목록 관찰자 및 중복 대기를 줄인다. 통계 판별은 비공개 공통 규칙으로 한정한다. |
| V. 명확한 동작과 검증 | PASS | PASS | 새 종료 정책·표시 의미를 명시하고 구조 오류·실패·취소를 구분한다. 변경되는 합성 기대와 실사이트 수용을 분리한다. |

헌장 III의 캐시 원칙과 다른 범위는 새로 확장한 예외가 아니라 002의 사용자 합의를 003에서 유지하는 것이다.  
그 밖의 미정당화 위반과 미결정 설계 항목은 없다. 이번 단계에서 헌장이나 과거 명세를 다시 쓰지 않는다.

## Project Structure

### Documentation (this feature)

```text
specs/003-align-site-listing/
├── spec.md
├── checklists/requirements.md
├── plan.md
├── research.md
├── data-model.md
├── contracts/
│   ├── source.md
│   └── cli.md
└── quickstart.md
```

`tasks.md`는 다음 `$speckit-tasks` 단계에서 작성한다. 001·002 산출물과 기존 검증 이력은 보존하고, 003의 대체 관계를 현재 계약의 기준으로 삼는다.

### Source Code (repository root)

```text
src/algorithm_problem_picker/
├── jungol.py       # 스냅샷·빈 통계·더 불러오기 대기·티어 예외 제거
├── selection.py    # Rated의 요청 범위 재비교만 제거
├── cli.py          # 티어 검색 조건의 도움말 의미 정리
├── models.py       # 타입·불변식 유지, 필요한 완료 의미 주석만 정합성 확인
├── ports.py        # resolve_user/collect Protocol 유지
└── service.py      # 수집 완료 후 처리·실패/취소 흐름 유지

tests/
├── test_jungol_dom.py
├── test_selection.py
├── test_service.py
├── test_cli.py
└── fixtures/jungol/

scripts/
├── validate_live.py
├── benchmark_selection.py
└── benchmark_collection.py
README.md
```

**Structure Decision**: 기존 단일 패키지 구조를 유지한다. 기능 변경은 수집기·순수 티어 필터와 사용자 안내에 집중하고, 도메인·서비스·공개 경계는 확장하지 않는다. 기존 검증 도구는 호환성을 확인하며 신규 벤치나 제품 옵션을 만들지 않는다.

## Phase 0: Research 결과

[research.md](research.md)의 R1~R7에 따라 다음 결정을 확정했다.

- 수집·최종 필터의 확정 티어 범위 비교를 함께 제거하고 입력·배지·요청 조건 검증은 유지한다.
- `acceptedEmpty`·`rateEmpty` 셀별 표시와 비공개 공통 판별을 사용한다. 정답률의 기존 같은 문제 빈 링크 지원은 유지한다.
- 최초/번호 페이지 준비와 클릭 후 더 불러오기 종료 경로를 분리한다. 컨트롤이 없고 현재 목록을 읽을 수 있으면 추가 완료 증거를 기다리지 않는다.
- `_LIST_UPDATE`와 목록 관찰자만 제거한다. 사용자 검색의 `_USER_UPDATE`·`JSHandle`·정리는 보존한다.
- `_collect`는 각 로드가 반환한 스냅샷을 재사용한다. URL/UI·접근·행·중복 컨트롤 검증을 제거하지 않는다.
- 합성 테스트를 현재 목록 완료 정책에 맞추고, ISSUE-003은 API·진행 상태·검증 게이트에 추가하지 않는다.

## Phase 1: Design & Contracts 결과

- [data-model.md](data-model.md): 타입·불변식, 내부 스냅샷의 빈 상태 근거, 완료 의미와 진행 상태 전이.
- [contracts/source.md](contracts/source.md): 요청 전달, 통계 파싱, 초기/추가/번호 페이지 준비와 종료, 오류·수명 계약.
- [contracts/cli.md](contracts/cli.md): 기존 명령·종료 코드, 사이트 검색 조건 의미, 미제공 표시·정렬·실패 처리.
- [quickstart.md](quickstart.md): 준비·정책 전환 회귀·전체 회귀·원문 세 명령의 후속 라이브 수용과 기록 방법.

설계 후 게이트는 위 Constitution Check와 같고, 추가 범위 예외·새 의존성·새 공개 경계는 없다.

### 구현 순서와 검증 경계

1. 범위 밖 티어 보존과 명시적 빈 통계의 최소 재생 사례를 작성하고, 기존 정책 때문에 실패하는 경계를 확인한다.
2. 티어 수집 예외·순수 범위 제외를 함께 바꾸고 준비 판정·파서에 명시적 빈 표현을 반영한다.
3. 더 불러오기 종료 분기·관찰자 제거·스냅샷 소비 흐름을 함께 바꾼다. 번호 페이지·사용자 검색과 오류 경계를 보존한다.
4. 과거 지연 합성 테스트·목록 관찰자 테스트와 티어 제외 수 기대를 갱신한다. 사용자 검색·실패·취소 회귀는 유지한다.
5. CLI 도움말·README를 새 의미로 맞추고 최소 회귀 후 전체 회귀를 실행한다. 이후 세 라이브 명령과 실제 검증 기록을 남긴다.

| 요구사항 | 설계·검증 근거 |
| --- | --- |
| FR-001~004 / SC-001 | source 조건·티어 계약, 순수 필터·DOM의 최초/번호/추가 목록과 양쪽/한쪽 경계 |
| FR-005~008 / SC-002~003 | 셀별 빈 표시·파서/준비 공통 판별, 실제 0·미제공·임시 빈 값·구조 오류 및 정상 후보 0개 |
| FR-009~011 / SC-004~005 | 추가 로드 모드와 재대기 제거, 버튼 유지/제거·새 행 없음·중복 컨트롤·번호/사용자 보존 |
| FR-012~013 / SC-006 | 고유 후보·최초 관측·정렬/추천·실패/취소 최종 결과 금지, 진행 개수 요구 제외 |
| FR-014~015 / SC-007~008 | CLI/README 의미·합성 기대 전환, 원문 세 명령과 실제 수용 기록 |

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
| --- | --- | --- |
| 헌장 III의 영구 캐시 원칙과 달리 실행 중 메모리만 사용 | 기존 사용자 합의와 003 범위가 영구 캐시를 제외한다. | 영구 캐시 도입은 별도의 데이터 수명·무효화 요구를 추가해 이번 수정 범위를 벗어난다. 실행 중 메모리 후보로 기존 순수 처리와 중복 없는 추천을 충족한다. |

## 검증 상태

Phase 0 조사와 Phase 1 설계 문서 작성 및 정합성 검토만 수행했다.  
시작 HEAD는 `0c1565b86bd44f546a2e1954c8653762c24428e4`이며 기존 제품·테스트·문서의 미커밋 변경을 기준으로 조사했다. 코드 변경·제품 테스트·실사이트 재검증을 수행했다고 주장하지 않는다.
