# Implementation Plan: JUNGOL 문제 검색·추천 CLI

**Branch**: `001-jungol-problem-picker` | **Date**: 2026-10-19 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-jungol-problem-picker/spec.md`

## Summary

JUNGOL 공개 일반 문제를 조건으로 조회하고, 지표별 정렬·중복 없는 무작위 추천과
선택한 문제의 기본 브라우저 열기를 제공한다. 풀이 여부는 지정한 공개 사용자를 기준으로 한다.
로컬 캐싱과 로그인은 구현하지 않는다.

Python CLI에서 정올의 정상 공개 화면을 동기 Playwright로 읽는다.
사이트가 지원하는 티어·풀이 조건으로 목록을 좁히고, 모든 페이지를 읽은 뒤
정답률·푼 사람 수 필터와 최종 정렬·추첨을 메모리에서 수행한다.
정답률로 탈락한 후보는 상세 조회를 생략하고, 나머지는 상세의 '맞힌 사람' 통계를 읽는다.
목록의 티어·정답률은 유지하고 상세에서 덮어쓰지 않아 필터와 최종 표시 값을 일치시킨다.
내부 API 호출·바이너리 응답 해석·페이지 전역 상태 접근은 사용하지 않는다.

Phase 0 조사 결과는 [research.md](research.md)에 정리했다.
Phase 1 설계는 [데이터 모델](data-model.md), [CLI 계약](contracts/cli.md),
[공급자 계약](contracts/source.md), [검증 가이드](quickstart.md)로 확정한다.
이번 명령은 설계까지 수행하며 tasks.md와 애플리케이션 코드는 다음 단계에서 생성한다.

## Technical Context

**Language/Version**: Python 3.12 이상. 최초 지원·검증 환경은 Python 3.12.

**Primary Dependencies**: Typer, Rich, 동기 Playwright + Chromium, uv.
정확한 라이브러리 버전은 구현 시 uv로 해결하고 uv.lock에 고정한다.

**Storage**: 실행 중 메모리만 사용. 영구 문제 목록·DB·사용자 프로필·로그인 상태 저장 없음.

**Testing**: pytest, Typer CliRunner, 최소 로컬 HTML fixture, 공급자·브라우저 호출 대체.
기본 테스트는 오프라인이며 실제 정올 수용 검증은 별도로 실행한다.

**Target Platform**: Windows 10/11 터미널과 기본 웹 브라우저.
다른 OS 전용 지원·배포 작업은 최초 범위에 추가하지 않는다.

**Project Type**: 단일 Python CLI 패키지. 콘솔 명령 jpick.

**Performance Goals**: 준비된 10,000개 후보의 로컬 필터·정렬·추첨은 개발 PC에서 1초 이내를 목표로 한다.
외부 사이트 조회 시간은 별도이며 고정 완료 시간은 약속하지 않는다.
네트워크 대기 중 단계·수집 개수와 Ctrl+C 안내를 유지하고,
취소 시 현재 작업을 중단한 뒤 조회용 브라우저를 정리한다.
시간 목표는 설계상 목표이며 이번 문서 작업에서 측정한 결과가 아니다.

**Constraints**: 한 컨텍스트, 동시 데이터 탐색 1개, 탐색·더 불러오기 시작 간격 최소 1초.
탐색 timeout 30초, DOM 준비·동작 timeout 15초.
403·429·챌린지·로그인 요구·구조 변경에서는 실패하며 자동 재시도하지 않는다.
목록·상세 조회가 끝나기 전에 결과를 추첨하거나 표시 제한으로 후보를 줄이지 않는다.

**Scale/Scope**: 개인 사용자 한 명, 정올의 공개 일반 문제 전체와 공개 기준 사용자 한 명.
전체 개수와 소요 시간은 동적으로 달라진다. 후보 전체를 담는 O(N) 메모리를 사용하며
문제 본문·제출 코드·계정 목록·제출 내역·타 플랫폼은 수집하지 않는다.

## Constitution Check

*GATE: Phase 0 전 원칙별 적용 여부를 확인하고, Phase 1 설계 후 다시 확인했다.*

| 원칙 | 사전 확인 | 설계 후 확인 |
| --- | --- | --- |
| I. JUNGOL에 집중 | 공개 정올 CLI 범위 | PASS: 타 플랫폼·계정 기능 추가 없음 |
| II. 허용된 데이터 접근 | 공개 메타데이터 검색 근거와 내부 API 허가를 구분해 조사 | PASS: robots의 search=yes와 개인 이용 범위에 맞춘 공개 DOM 검색. 자세한 근거·한계는 research 2절 |
| III. 로컬 데이터·중복 없는 추천 | 사용자가 캐싱 제외를 명시 | PASS: 해당 지시를 우선한 예외, 실행 중 메모리와 중복 없는 추천 유지 |
| IV. 단순한 구조 | CLI·조회·로컬 처리 분리 | PASS: 단일 패키지·공급자 Protocol 하나, 웹 서버·DB·비동기 실행기 없음 |
| V. 명확한 동작과 검증 | 불완전 결과와 정상 빈 결과 구분 | PASS: 종료 코드·최소 테스트·명시적 수집 완료 계약 |
| 개인 코딩 지침 | coding-style.md 확인 | PASS: 외부 경계에서 검증, 오류 은폐 없는 공급자, 테스트용 공개 API 추가 없음 |

공개 화면 검색에 관한 근거를 내부 API 사용이나 개인정보 축적의 포괄 허가로 확대하지 않는다.
접근 제한을 만나면 중단하며 다른 접근 방식으로 조용히 바꾸지 않는다.
최초 사전 검토에서 남은 접근 방식·지표·페이지 처리 질문은 research.md의 결정으로 해소했다.

## Project Structure

### Documentation (this feature)

```text
specs/001-jungol-problem-picker/
├── spec.md
├── discovery.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── cli.md
│   └── source.md
└── checklists/
    └── requirements.md
```

tasks.md는 이 명령에서 만들지 않는다.

### Source Code (repository root)

아래는 구현 예정 구조이며 이 단계에서는 파일을 생성하지 않는다.

```text
pyproject.toml
uv.lock
src/algorithm_problem_picker/
├── __init__.py
├── cli.py
├── models.py
├── selection.py
├── service.py
├── ports.py
└── jungol.py
tests/
├── test_selection.py
├── test_service.py
├── test_jungol_dom.py
├── test_cli.py
└── fixtures/
    └── jungol/
```

**Structure Decision**: 기존 소스가 없으므로 src 레이아웃의 작은 단일 패키지를 사용한다.
cli는 옵션·출력과 의존성 조립, service는 유스케이스 흐름,
selection은 순수 필터·정렬·추첨, jungol은 공개 DOM 탐색을 담당한다.
models는 데이터와 불변 조건, ports는 공급자 Protocol 하나를 정의한다.
기본 브라우저 열기는 cli의 open 경로에서 표준 webbrowser를 사용한다.

### 처리 순서와 검증 연결

1. 입력을 한 번 검증한다. 사용자·범위·개수 오류는 Chromium 시작 전 코드 2로 끝낸다.
2. 필요한 경우 공개 사용자 선택 UI로 정확한 핸들을 해석한다.
   사용자의 숫자 ID와 include/exclude 조건을 목록에 적용한다. FR-003~004.
3. 티어·풀이 조건을 적용한 일반 문제 목록을 끝까지 읽고 번호로 중복 제거한다.
   페이지 반복·더 불러오기 중단·필터 미적용을 실패로 처리한다. FR-001~002·008·013.
4. 티어·정답률 필터 후 남은 문제의 상세 통계를 순차 조회한다.
   맞힌 사람 수를 읽고 인원수 필터를 적용한다. 명시적인 미제공 값은
   spec의 제외·미확인 정책을 따르고 제외 개수를 알린다. FR-005~006·012.
5. 목록은 전체 후보를 정렬·셔플한 뒤 limit을 적용한다.
   추천은 전체 고유 후보에 random.sample을 한 번 적용한다. FR-007~010.
6. 결과·조건·개수·조회 시각은 stdout, 진행·진단은 stderr에 표시한다.
   실패·Ctrl+C에서는 최종 표를 내보내지 않고 자원을 정리한다. FR-013·014·016.
7. open은 명시된 번호만 기본 브라우저에 전달하고 실패 시 링크를 남긴다. FR-011.
8. 최소 오프라인 테스트와 opt-in 라이브 표본 검증으로 SC-001~006을 확인한다.
   균등성은 문서화된 sample과 전체 고유 후보 전달을 검증하며 빈도 기반 CI를 추가하지 않는다.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
| --- | --- | --- |
| 헌장 III의 영구 캐시 요구 제외 | 이번 사용자가 로컬 캐싱 제외를 명시했고 spec에 반영함 | 영구 캐시는 현재 사용자 지시와 충돌. 실행 중 메모리 처리는 유지 |

그 외 정당화가 필요한 원칙 위반이나 추가 계층은 없다.
