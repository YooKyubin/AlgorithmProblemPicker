# Research: 안정적인 티어 수집과 정답 제출 수 기반 조회·추천

**Date**: 2026-10-20
**Spec**: [spec.md](spec.md)
**Baseline revision**: `c37208f5a80628df5d7126972d31461b2517177d`

이번 조사는 기존 코드·잠금 파일·로컬 검증 자료와 [원문 이슈](../001-jungol-problem-picker/post-implementation-issues.md)를 대조한 설계 조사다.
새 라이브 조회·성능 측정은 수행하지 않았다. 기존 관측 사실, 새 설계 결정, 구현 시 검증할 내용을 구분한다.

## 1. 기존 기술과 접근 경계 유지

- **Decision**: Python 3.12 이상, uv, Typer, Rich, 동기 Playwright/Chromium, pytest를 재사용하고 `uv.lock`을 유지한다. 새 의존성은 추가하지 않는다.
- **Rationale**: [프로젝트 설정](../../pyproject.toml)과 기존 모듈로 목록 수집·순수 처리·CLI를 모두 구성할 수 있다. 이번 문제는 라이브러리 교체가 아니라 상세 보강 단계와 지표 의미의 변경이다.
- **Alternatives considered**: 비동기 수집기·병렬 상세 탐색·캐시·내부 API 호출은 불필요하거나 명세 범위 밖이다.
- **Evidence**: [기존 접근 조사](../001-jungol-problem-picker/research.md)의 공개 DOM·접근 간격·제한 대응 정책을 승계한다. 이는 새 접근 허가를 확인했다는 뜻이 아니다. 구현 시 접근 제한이나 정책 변경을 확인하면 기존처럼 중단한다.

## 2. 정상적인 티어 부재와 실제 필터 오류 분리

- **Decision**: `Rated`, `Unrated`, `Unavailable`을 유지한다. `_collect`는 범위 밖의 `Rated`만 `SourceAccessError`로 실패시키고, 정상 미정·미확인 레코드는 전체 수집 결과에 보존한다. 이후 `filter_listing`에서 티어 조건에 따라 제외한다.
- **Rationale**: [현재 수집기](../../src/algorithm_problem_picker/jungol.py)의 범위 검사가 모든 비확정 티어까지 필터 오류로 묶는다. [순수 필터](../../src/algorithm_problem_picker/selection.py)는 이미 미정·미확인을 제외할 수 있다. 수집 레코드를 보존하면 조회 수와 미확인 제외 수를 잃지 않는다.
- **Alternatives considered**: 공급자에서 즉시 폐기하면 중복 ID와 제외 개수를 별도로 관리해야 한다. 범위 밖 확정 티어를 조용히 제외하거나 파싱 예외를 미확인으로 바꾸는 방식은 실제 오류를 숨긴다.
- **Diagnostic decision**: 범위 밖 티어는 문제 번호·읽은 티어·요청 하한/상한을 포함한다. 구조·해석 오류는 가능한 문제 번호·대상 지표·읽은 값 또는 누락 사실을 포함한다. 번호 자체가 파손되면 해당 사실과 원시 링크를 표시한다.

## 3. 최초·추가 목록의 필터 보존

- **Decision**: `type=problem`, `sort=idAsc`, `minTier`, `maxTier`, `unrated`를 유지한다. 사용자 조건은 확인된 `solvedBy`와 `solvedByMode=include/exclude`를 사용한다. 로그인 사용자용 `status` 조건은 사용하지 않는다.
- **Rationale**: 기존 코드가 최초 URL과 매 반복의 URL 조건을 확인하고 있으며, 사이트 필터 UI도 최초에 확인한다. 다음 페이지·더 불러오기 후에도 URL과 공개 UI의 적용 상태 및 반환된 확정 티어 범위를 확인하도록 확장한다.
- **Alternatives considered**: 내부 요청 본문·응답 해독·앱 전역 상태를 읽어 적용 여부를 추정하는 방식은 기존 접근 계약 밖이다. 정답 제출 수·정답률을 확인되지 않은 서버 조건으로 보내지 않는다.
- **Validation**: 두 경계·하한만·상한만, 첫 목록·다음 페이지·더 불러오기, 공개 사용자 조건 보존 및 조건 변조 실패를 로컬 UI 자료로 확인한다. 적용 UI를 증명할 수 없으면 조건을 생략하지 않고 실패한다.

## 4. 목록 정답 제출 수의 의미와 파싱

- **Decision**: 해당 문제 행의 `td[data-col="정답"]` 정확히 한 개에서 `accepted_count`를 읽는다. `시도`·`정답률`·상세의 맞힌 사람 수를 대신 읽지 않는다. 정답률은 기존 `Decimal` 표시값을 유지한다.
- **Rationale**: [기존 목록 자료](../../tests/fixtures/jungol/list.html)에 정답·시도·정답률이 별도 열로 존재한다. 원문 ISSUE-002는 정답 제출 수와 중복을 제외한 맞힌 사람 수가 다른 지표임을 확인했다.
- **Numeric decision**: 바깥 공백을 제거한 ASCII 숫자열 또는 올바른 천 단위 쉼표 정수를 허용한다. `0`은 알려진 값이다. 음수·소수·잘못된 쉼표·알 수 없는 문자열·셀 누락/중복은 오류다.
- **Absence decision**: `-`, `—`, `미확인`, `미제공`만 명시적 미제공으로 해석한다. 이는 기존 정답률 파서의 `_EMPTY` 관행을 정답 열에도 적용하는 새 설계 계약이다. 기존 자료에서 정답 열의 미제공 표시를 실제 관측한 것은 아니다. 빈 정답 셀·빈 링크는 미제공으로 인정하지 않는다. 이 구분은 합성 자료로 검증하고 라이브 관측과 혼동하지 않는다.
- **Alternatives considered**: 빈 값을 0으로 바꾸기, 모든 비숫자를 미제공으로 처리하기, 상세 조회로 보충하기, 정답률을 재계산하기는 선택하지 않는다.

## 5. 단일 문제 모델과 목록 전용 흐름

- **Decision**: `Candidate`와 상세 보강 후 `Problem`을 목록에서 완성되는 `Problem` 하나로 합친다. `accepted_count`와 `listed_at`을 보유하고 `solver_count`, `details_observed_at`, `read_details`, 상세용 페이지 및 상세 준비 코드를 제거한다.
- **Rationale**: 기존 분리는 상세 보강 때문에 존재한다. [서비스](../../src/algorithm_problem_picker/service.py)는 조건·요청 개수와 관계없이 후보별 `read_details`를 수행한다. 해당 반복을 제거해야 상세 비용이 사라진다.
- **Boundary decision**: `ProblemSource`는 `resolve_user`와 `collect`만 갖는다. `CompletedListing.candidates`라는 컬렉션 이름은 유지하되 원소를 `Problem`으로 바꾼다. 브라우저·DOM·URL은 공급자 안에만 둔다.
- **Alternatives considered**: 호환용 solver 필드나 사용하지 않는 상세 메서드를 남기면 의미 혼동과 유지 비용이 생긴다. 새로운 공급자 계층·자료 저장소는 필요하지 않다.

## 6. 전체 후보·카운트·진행 의미

- **Decision**: 전체 수집 완료 후 한 번의 순수 필터에서 티어→정답률→정답 제출 수를 확인한다. 미확인 때문에 제외된 문제는 최초로 적용된 해당 사유에서 한 번만 센다. `Unrated` 제외는 미확인 제외 수에 포함하지 않는 기존 동작을 유지한다.
- **Rationale**: `fetched_count`는 중복 제거한 전체 관측 수, `eligible_count`는 모든 조건 통과 수다. 공급자에서 미정·미확인을 보존해야 두 수치의 의미가 유지된다. 중복 ID는 최초 관측 레코드를 유지한다.
- **Progress decision**: `Enriching`을 `Processing`으로 바꾸고 `detailed`를 제거한다. 서비스의 성공은 정렬·추첨 및 결과 구성까지 끝난 `Complete`다. CLI 출력은 별도 책임이며 실제로 사용하지 않는 `Presented` 상태를 위해 새 전달 경로를 만들지 않는다.
- **Alternatives considered**: 표시 개수로 조기 종료, 일부 목록으로 추천, 실패를 후보 부족으로 처리하는 방식은 제외한다. 기존 `random.sample`·`shuffle`, 동점 번호순·미확인 마지막 정렬은 유지한다.

## 7. 기존 solver 옵션은 전환 안내와 함께 거부

- **Decision**: 정상 사용자 옵션은 `--min-accepted`, `--max-accepted`, `--sort accepted`다. 기존 `--min-solvers`·`--max-solvers`는 숨겨진 문자열 입력과 비공개 거부 callback으로만 받아 `BadParameter`로 종료한다. 실제 검색 조건으로 전달하지 않는다.
- **Sort decision**: `--sort`는 CLI 입구에서 문자열을 받아 비공개 변환 함수가 `solvers`를 먼저 거부하고, 나머지를 `SortKey`로 변환한다. 모델의 `SortKey`에는 `SOLVERS`를 남기지 않는다.
- **Rationale**: Enum에서 기존 값만 삭제하면 일반 변환 오류가 먼저 발생해 요구한 전환 안내를 누락할 수 있다. 거부 처리는 `_run`과 브라우저 생성 전에 끝나야 한다. 사용자가 대화에서 이 정책을 명시적으로 확인했다.
- **Alternatives considered**: 새 지표의 허용 별칭으로 solvers를 재사용하는 방안은 채택하지 않는다. 커스텀 CLI 프레임워크나 테스트 전용 공개 함수도 만들지 않는다.
- **Validation**: list/recommend의 두 레거시 범위 옵션과 list의 옛 정렬을 코드 2·대응 옵션 안내·공급자 생성 0건으로 검증한다. 도움말에는 정상 새 옵션만 표시한다.

## 8. 재현 가능한 변경 전후 시간 비교

- **Decision**: 신규 개발 도구 `scripts/benchmark_collection.py`가 고정된 두 개 이상의 공개 목록 HTML과 baseline용 상세 HTML을 로컬 route로 재생한다. 기본 원격 요청은 모두 차단한다. 제품 런타임에 벤치마크용 공개 API를 추가하지 않는다.
- **Baseline decision**: 위 baseline revision을 `git archive` 등으로 임시 폴더에 추출해 현재 코드와 별도 프로세스로 실행한다. 같은 Python 환경·잠금 의존성·harness·fixture를 사용하고 각 프로세스의 실제 import 경로를 확인한다. 현재 브랜치나 staged index를 바꾸지 않는다.
- **Measurement decision**: CLI 모듈 import 후 명령 호출 직전부터 결과 출력·브라우저 정리 직후까지 `perf_counter`로 잰다. 두 버전 모두 브라우저 생성·정리, 목록·상세 조회, 로컬 처리·출력을 포함하고 프로세스/모듈 시작 비용은 제외한다. `collect` 래퍼로 목록 수집 시간을 따로 기록한다.
- **Controls**: 정상 확정 티어·알려진 수치를 가진 동일 고유 후보를 사용한다. 사용자 조건과 solver/accepted 조건·정렬은 생략하고 `list --sort id --order asc --limit 1` 및 `recommend --count 1`을 각각 3회 이상 비교한다. 탐색 간격·fixture 제공 시점·콘솔 환경은 양쪽 동일하게 유지한다.
- **Evidence to record**: baseline/current revision과 dirty 여부, 의존성·fixture·harness 해시, Python/OS/브라우저 버전, 명령, 목록 수·관측/적격/반환 개수, 상세 URL 요청 수, 반복별 전체/목록 시간, 각각의 중앙값. 기준 구현은 상세 요청이 1건 이상, 변경 구현은 0건이어야 하며 후보 집합이 같아야 한다.
- **Rationale**: [기존 계산 벤치마크](../../scripts/benchmark_selection.py)는 브라우징을 제외하므로 SC-008의 증거로 부족하다. 라이브 실행은 같은 후보와 통계를 고정할 수 없다.
- **Alternatives considered**: 가짜 공급자에 임의 지연만 넣기, 서로 다른 지표 조건으로 같은 후보라고 가정하기, 라이브 단발 측정으로 개선율을 주장하기는 제외한다. baseline 상세 fixture는 이 재생 도구에 한해 보존할 근거가 있다.
- **Interpretation**: 로컬 재생은 상세 경로 제거 효과를 검증한다. 실제 정올의 개선율·완료 시간을 보장하지 않는다. 중앙값이 줄지 않으면 원인을 조사하고 성공으로 기록하지 않는다.

## 9. 기존 완전성 문제와 범위

- **Decision**: [001 tasks](../001-jungol-problem-picker/tasks.md)의 T041(요청 완료와 목록 반영 분리)·T042(사용자 검색 결과 반영)는 별도 작업으로 유지한다. 002 변경으로 완료했다고 표시하지 않는다.
- **Rationale**: 현재 요청 완료 카운터만으로 DOM 완료를 인정하는 경계가 남아 있다. 상세 보강 제거는 해당 경계를 해결하지 않는다.
- **Integration gate**: 전체 완료·사용자 확인을 입증하지 못하는 사례는 002에서도 실패해야 한다. 최종 통합 수용 시 기존 경계 사례를 다시 확인하고, 선행 수정이 미완료면 관련 수용 상태를 미통과로 기록한다. 정상 경로 통과를 두 이슈 해결의 증거로 삼지 않는다.
- **Alternatives considered**: 002 범위에 두 작업을 몰래 편입하거나 고정 대기를 늘려 완료로 추정하는 방법은 선택하지 않는다.

## 결론과 남은 검증

구현을 설계할 미결정 항목은 없다. 정답 열의 미제공 표식은 설계 가정으로 명시했고 합성/라이브 근거를 구분한다.
코드 변경, 새 검증 도구 작성, 회귀 실행과 성능 실측은 후속 구현 작업이다.
