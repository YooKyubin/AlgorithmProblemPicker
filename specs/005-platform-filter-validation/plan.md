# Implementation Plan: algo-pick 플랫폼 선택과 지원 필터 검증

**Branch**: `005-platform-filter-validation` | **Date**: 2026-10-30 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/005-platform-filter-validation/spec.md`

## Summary

실행 이름을 `algo-pick`으로 바꾸고 공통 `--platform`으로 세 명령의 대상을 선택한다. 실제 지원은 정올만 제공하며 생략 시 정올이다. 지원하지 않는 필터는 지정한 옵션을 모두 안내하고 외부 작업 전에 코드 2로 거부한다.

공통 CLI·수집 완료 이후의 추천 흐름은 한 벌을 유지한다. 정올의 조건·문제 검증·순수 필터·정렬·표시·링크 규칙을 정올 정책으로 옮기고, 명시적인 지원 정보와 수집기 팩터리를 조합한다. 제네릭 서비스는 플랫폼별 조건을 해석하지 않는다. 새 플랫폼을 위한 모든 속성의 공통 모델이나 범용 필터 엔진은 만들지 않는다.

## Technical Context

**Language/Version**: Python >=3.12. 조사 환경 Python 3.12.13, 기존 dataclass·Protocol과 Python 3.12 제네릭 표기를 사용한다.

**Primary Dependencies**: 기존 Typer 0.27.3, Rich 15.0.0, Playwright 1.64.0, pytest 9.1.1 및 uv. 새 의존성·업그레이드는 계획하지 않는다. Typer의 공개 Context를 사용하고 외부 Click/private enum을 import하지 않는다.

**Storage**: 실행 중 메모리의 완료 목록만 사용한다. 영구 캐시·설정 저장·플랫폼 자동 감지는 추가하지 않는다.

**Testing**: pytest, Typer CliRunner, 고정 문제 공급자, 기존 정올 로컬 HTML 재생. 검증용 플랫폼은 구성 경계에만 주입하고 일반 플랫폼 목록에 노출하지 않는다. 기본 검증에서 실제 사이트·기본 브라우저 호출을 차단한다.

**Target Platform**: Python 데스크톱 터미널 CLI. Windows/PowerShell을 주 검증 환경으로 삼고 현재 macOS 사용 안내와 OS 독립 예제를 유지한다.

**Project Type**: 단일 Python CLI 패키지.

**Performance Goals**: 미지원/잘못된 플랫폼 입력과 도움말에서 소스 생성·원격 접근 0회. 정올의 페이지 수집 정책과 완료 기준을 유지하며 추가 요청·대기·상세 조회를 도입하지 않는다. 별도 속도 개선 목표는 없다.

**Constraints**: 미지원 검사 후 플랫폼 값 검증, 그 뒤 수집기 생성. 정올의 Decimal 정밀도·티어 검색 의미·첫 실패 기준 제외 집계·0/미제공 구분·전체 후보 처리·추천 중복 방지·종료 코드·출력 채널을 보존한다.

**Scale/Scope**: 실제 플랫폼 1개, 공통 명령 3개, 정올 필터 그룹 4개와 비공개 합성 검증 플랫폼 1개. 프로그래머스 수집·통합 검색·플러그인 자동 탐색·문제 전체 속성 통일은 제외한다.

## Constitution Check

계획 진입 전과 Phase 1 설계 후 검토 결과다. PASS는 설계 판정이며 제품 실행 테스트 결과가 아니다.

| 원칙 | 계획 진입 전 | 설계 후 | 판정 근거와 한계 |
| --- | --- | --- | --- |
| I. JUNGOL에 집중 | 정당화된 범위 예외 | 정당화된 범위 예외 | 이번 사용자 요구로 플랫폼 선택·지원 정보 연결 경계를 허용한다. 실지원은 정올뿐이며 프로그래머스 수집은 계속 제외한다. |
| II. 허용된 데이터 접근 | PASS | PASS | 정올 공개 DOM 접근을 유지한다. 새 사이트 허가·지표 의미를 추측하지 않고 합성 플랫폼만 검증한다. |
| III. 로컬 데이터 우선 | 정당화된 기존 예외 | 정당화된 기존 예외 | 003·004 합의대로 영구 캐시를 추가하지 않으며, 완료 목록의 메모리 내 필터·정렬·중복 없는 추천을 유지한다. |
| IV. 단순한 구조 | PASS | PASS | 현재 코드에 있는 정올 결합을 포트·정올 정책으로 분리한다. 플랫폼별 CLI/추천 복제나 범용 속성 엔진은 만들지 않는다. |
| V. 명확한 동작과 검증 | PASS | PASS | 값 해석 전 지원 검증·코드 2와 외부 작업 0회를 검증하고 기존 정올 회귀를 유지한다. |

헌장 원문은 변경하지 않는다. I에 대한 이번 기능의 범위 조정은 위 표와 Complexity Tracking에 명시한 제한적 예외이며, 신규 사이트 운영 전체를 승인하는 개정이 아니다. III는 [004 계획](../004-add-range-options/plan.md)의 예외를 승계한다. 미정당화 위반·미결정 설계 항목은 없다.

## Project Structure

### Documentation (this feature)

```text
specs/005-platform-filter-validation/
├── spec.md
├── checklists/requirements.md
├── plan.md
├── research.md
├── data-model.md
├── contracts/
│   ├── cli.md
│   └── platform.md
└── quickstart.md
```

`tasks.md`는 다음 `$speckit-tasks` 단계에서 생성한다.

### Source Code (repository root)

```text
src/algorithm_problem_picker/
├── cli.py            # 공통 명령·입력 출처·지원 검증·출력·브라우저 전달
├── platforms.py      # 신규: 정적 레지스트리, 정책+source factory 조합
├── ports.py          # 플랫폼 정책과 제네릭 source/문제 프로토콜
├── models.py         # 공통 지원 정보·원시 입력·완료 목록·결과·진행 상태
├── jungol_models.py  # 신규: 기존 정올 타입과 검증의 소유권 이동
├── jungol_policy.py  # 신규: 정올 파싱·필터·정렬·표시·문제 URL 규칙
├── jungol.py         # 기존 DOM 본문 보존, prepare_user 연결·import 조정
├── service.py        # 제네릭 Picker, 완전 수집 후 공통 실행 흐름
└── selection.py      # 플랫폼 독립 고유 문제 추출·무작위 추천

tests/
├── test_platforms.py  # 신규: 합성 플랫폼을 통한 실제 CLI/서비스 계약
├── test_cli.py        # 기본/명시 플랫폼·출처·오류·help·open
├── test_selection.py  # 기존 정올 순수 정책 회귀, 공통 추천 회귀
├── test_service.py    # source/policy 주입 조정, 기존 흐름 회귀
├── test_jungol_dom.py # 기존 DOM 회귀, 타입 import 조정
├── test_export_tool.py
└── conftest.py        # 고정 문제·구성 경계 주입

pyproject.toml             # project.scripts의 실행 키 변경
README.md
docs/integration.md
docs/standalone.md
examples/vscode/tasks.json
scripts/export_tool.py    # 현재 도움말·예시 개명
```

**Structure Decision**: 기존 단일 패키지와 동기 수집을 유지한다. `jungol_models.py`는 순수 모델, `jungol_policy.py`는 순수 정책, `jungol.py`는 데이터 접근이다. `platforms.py`만 구체 정책과 팩터리를 조립하며 CLI/서비스는 포트를 소비한다. 테스트 전용 등록 API·동적 플러그인 로더·하위 CLI를 만들지 않는다.

## Phase 0: Research 결과

[research.md](research.md)의 R1~R9에서 미지 항목을 해결했다.

- 루트 callback에서 플랫폼을 고르고 하위 Context의 파라미터 출처로 명시한 필터를 식별한다.
- raw 필터 값은 지원 검사 뒤에만 플랫폼이 파싱한다. 범위 반복·legacy callback도 그 뒤로 이동한다.
- 공통 eager help callback이 플랫폼 지원 표를 덧붙인다. help 때문에 수집기를 만들지 않는다.
- 정올 전용 타입과 정책을 분리하고 공통 서비스는 조건 내부 필드를 읽지 않는다.
- 미지원은 지원 정보, 미제공은 문제 값 상태로 분리한다. 정올 필터 순서와 제외 집계를 그대로 보존한다.
- 실행 키와 현재 사용 자료를 함께 개명하고 배포 패키지·내부 모듈 이름은 유지한다.

## Phase 1: Design & Contracts 결과

- [data-model.md](data-model.md): 지원 정보, 원시 입력 출처, 타입 소유권, 결과·진행 상태.
- [contracts/cli.md](contracts/cli.md): 공통 옵션 위치, 필터 검증 순서, help·open·출력·종료 코드.
- [contracts/platform.md](contracts/platform.md): typed 정책·source factory·공통 추천과 합성 플랫폼 계약.
- [quickstart.md](quickstart.md): 구현 후 수행할 설치·CLI·고정 공급자·내보내기 수용 절차.

### 구현 순서

1. 정올 타입·필터·정렬·포맷 규칙을 소유 모듈로 이동하고 기존 검증을 보존한다. 제네릭 완료 목록·결과·문제 프로토콜로 공통 처리의 정올 의존을 끊는다.
2. 플랫폼 정보·순수 정책·source factory를 조립한다. 기본 레지스트리는 정올 하나다. 정올 source에 prepare_user를 연결하고 공통 Picker에 순수 정책을 주입한다.
3. CLI 필터를 raw 입력으로 받고 명시 옵션과 원래 옵션 이름을 수집한다. 미지원 전체 검사 후 정책 파싱과 공통 개수·정렬 옵션 검증을 마치고 수집기를 생성한다.
4. 공통 출력은 정책의 열·행·조건·주의 문구를 사용하되 집계·빈 결과·진행·스트림은 공통 유지한다. open은 전 번호 검증 후 고유 링크만 브라우저로 전달한다.
5. 실행 키와 현재 배포/통합 자료를 변경한다. 일반 구성 경계에 합성 플랫폼을 주입해 확장 검증하고 기존 정올 회귀·내보내기 검증을 수행한다.

### 검증과 요구사항 추적

| 요구사항 / 성공 기준 | 최소 관측 검증 |
| --- | --- |
| FR-001~004 / SC-001,003,006 | 세 명령 × 기본/명시 정올 6개 흐름, unknown/빈/programmers 거부, 설치 실행 키·version·직접 open 링크 |
| FR-005~009 / SC-002,003 | 두 명령의 범위/경계 미지원, 명시적 all·빈 user, 복수 미지원, 무효·반복 값이 섞인 미지원, 소스 팩터리·사용자 조회·외부 작업 0회 |
| FR-010,013 / SC-001,004 | 정올의 약칭/숫자·범위·기존 경계 문법, 사용자 조건, 사이트 경계 밖 확정 티어, 정렬·동점·전체 후보 처리 |
| FR-011~014 / SC-004 | 0/미제공, 첫 실패 순서·고유 제외 수, 미지원 열 생략, 정상 빈 결과·부족, 실패/취소의 정리·부분 출력 금지 |
| FR-015 / SC-006 | 기본/선택 플랫폼 help, 실제 지원 목록, 사용 문서·VS Code 입력 연결·내보내기 안내 정합성 |
| FR-016 / SC-005 | 합성 플랫폼의 다른 난도/URL/지원 필터를 동일 세 명령으로 실행, 정올 호출 0회, 공통 sample 경로 사용 |

기존 선택·서비스·DOM 테스트는 이동한 모듈과 주입 지점만 조정하고 행동 기대를 약화하지 않는다. 테스트는 파서 구현을 복제하지 않고 실제 CLI 결과·호출·진단을 확인한다. 문서 변경 전용 테스트를 늘리지 않으며 기존 export 테스트를 활용한다. 관련 검증 후 전체 pytest를 한 번 수행한다. 고정 조건의 무작위 결과 자체 일치를 요구하지 않는다.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
| --- | --- | --- |
| 헌장 I의 플랫폼 통합 제외와 달리 선택·연결 경계 추가 | 이번 사용자 요구가 명시적으로 플랫폼별 지원 검증과 복제 없는 확장을 요청한다. 실제 수집은 정올만 유지한다. | 정올에 직접 조건문만 추가하면 다른 플랫폼 데이터가 정올 검증에 묶이고 확장 시 공통 흐름을 복제하게 된다. |
| 헌장 III의 영구 캐시 대신 실행 중 메모리만 사용 | 선행 사용자 합의와 이번 정올 동작 보존 요구를 따른다. | 영구 캐시는 데이터 수명·갱신 정책을 새로 요구하므로 이번 범위와 무관하다. |

제네릭 source/정책 포트는 위 예외를 필요한 크기로 제한한다. 타입 검증 완화·속성 사전 통합·테스트만을 위한 공개 API는 허용하지 않는다.

## 검증 상태

2026-10-30 Phase 0 로컬 조사·최소 CliRunner 실험과 Phase 1 설계 정합성을 확인했다. 이 단계에서는 제품 코드·설정·헌장 원문을 변경하지 않았다. 제품 pytest·실사이트 수용·빌드/내보내기 실행은 구현 후 [quickstart.md](quickstart.md)에 따라 수행한다.
