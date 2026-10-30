# Platform Contract: 정책과 수집기의 조합

실제 코드의 시그니처·필드명은 구현에서 일관되게 정하되 이 책임과 실행 순서를 유지한다. 공통 모델은 [data-model.md](../data-model.md), 사용자 입력은 [cli.md](cli.md)를 따른다.

## 구성과 타입 경계

P는 플랫폼 고유 문제, C는 고유 조건, U는 고유 사용자 참조다. 공통 문제 프로토콜은 id/title/url/listed_at만 제공한다. 문제 ID는 플랫폼 내부 해시 가능한 값이며 공통 코드가 숫자·문자열 순서를 강제하지 않는다. 정올은 기존 숫자 ID·URL·타입 검증을 유지한다.

```text
PlatformBinding[P,C,U]
  info: PlatformInfo
  policy: PlatformPolicy[P,C,U]
  source_factory(report) -> ContextManager[ProblemSource[P,C,U]]

PlatformPolicy[P,C,U]                  # 모두 순수한 연산
  parse_filters(raw) -> C
  validate_list_options(sort, order) -> 플랫폼 정렬 선택
  filter_listing(problems, criteria) -> (eligible, omitted_unknown_count)
  sort_problems(problems, sort, order) -> ordered problems
  columns / format_row(problem)
  format_conditions(criteria, user) / observation_notes
  problem_links(raw_ids) -> 고유 ProblemLink 목록

ProblemSource[P,C,U]                   # 외부 데이터 접근 경계
  prepare_user(criteria) -> U | None
  collect(criteria, user) -> CompletedListing[P]
```

정적 registry는 플랫폼 이름을 이 바인딩으로 해석한다. 기본 등록은 jungol 하나다. 정책 생성·지원 정보 조회에는 I/O가 없다. 팩터리는 검증이 끝난 실행에서만 호출한다. 레지스트리 타입을 이유로 문제/조건을 `dict[str, Any]`로 바꾸거나 검증을 제거하지 않는다. 조립 지점이 같은 P/C/U 조합을 보장한다.

## 공통 실행 소유권

| 계층 | 소유 책임 | 소유하지 않는 책임 |
| --- | --- | --- |
| CLI | 문법, 명시 옵션 출처, 플랫폼 지원 검사, Rich 출력·스트림·종료 코드, open 브라우저 전달 | 정올 값 규칙, DOM 파싱, 추천 알고리즘 복제 |
| platforms 조립 | 지원 정보·순수 정책·수집기 팩터리 연결 | 사이트 접속, 전역 help 변이, 동적 플러그인 탐색 |
| Picker | 사용자 준비·진행·완전 수집·순수 처리 호출·집계·정렬 후 limit/공통 추천 | criteria 내부 필드, 정올 enum/URL/티어 해석 |
| 공통 selection | 고유 문제 추출과 중복 없는 무작위 선택 | 플랫폼별 필터·난이도·통계 의미 |
| 플랫폼 순수 정책 | 해당 플랫폼의 값 검증·필터·정렬·표시 데이터·링크 | 콘솔/브라우저/접속·새 추천 흐름 |
| 플랫폼 source | 허용된 데이터 접근·사용자 식별·완료 기준·정리 | CLI 옵션 무시, partial listing을 완료로 위장 |

공통 실행은 validate → source factory → 단일 with → prepare_user → collect → filter → sort/공통 recommend → Result → 공통 표시다. 사용자 참조가 None이 아닐 때 UserResolved를 보고한다. 정올 prepare_user는 핸들이 있으면 기존 resolve_user를 호출한다. 사용자 조건 미지원 플랫폼은 사전 지원 검사를 통과한 무조건 실행에서 None을 정상 반환한다.

공통 service/selection에는 플랫폼 키 분기·구체 수집기 import·Jungol 타입 검사·티어 필드 접근이 없어야 한다. 정올의 수집 DOM·페이지 진행·실패·수명 정책을 바꾸지 않고, import와 사용자 준비 연결만 조정한다. 기존 테스트의 monkeypatch 위치는 이 소유권 이동에 맞춰 변경한다.

## 데이터 의미와 지원 정보 일관성

- info는 명령 이름별 지원 필터를 명시한다. 범위/경계 옵션이 하나의 속성에 속해도 오류에는 실제 지정 이름을 보존한다.
- 정책은 지원한다고 선언한 값에 대해서만 파싱한다. CLI가 지원 여부를 먼저 검사하며 정책에서 누락된 파서를 기본 허용으로 취급하지 않는다.
- 정올의 retired_options는 지원 필터 목록과 별개인 거부 진단이다. 공통 검사에서 해당 이름을 폐기 입력 진단으로 전달하고 정올 정책이 기존 전환 안내 후 반드시 코드 2로 거부한다. 이름만 남긴 허용 경로나 별칭을 만들지 않는다.
- 플랫폼마다 속성명·단위·난이도 타입이 달라도 자체 모델과 표시 규칙을 사용한다. 다른 지표를 대신 계산하거나 정올 속성을 가짜 값으로 추가하지 않는다.
- 미지원 속성의 결과 열을 생략하고, 개별 미제공은 그 플랫폼의 명시적인 값 상태로 표시한다. 정올의 기존 미제공 집계 순서는 그대로 유지한다.
- 지원 정렬 키는 별도로 검증한다. 속성을 지원하지 않으면서 정올의 해당 지표 정렬을 조용히 id 정렬로 바꾸지 않는다.
- 플랫폼 구성 오류는 초기화 때 경고하고 해당 기능 사용 시 실패한다. 다른 플랫폼 바인딩으로 대신 실행하지 않는다.

## 생명주기와 오류

- source_factory 호출 전 모든 입력 검증을 완료한다. 도움말·version·open은 팩터리 호출 0회다.
- 컨텍스트 진입/수집/사용자 식별 실패는 기존 SourceError 계열로 전파하고 공통 CLI가 코드 1을 처리한다. 입력 오류는 CLI 경계에서 플랫폼·옵션 정보를 가진 코드 2로 변환한다.
- 실패·취소는 Complete 결과를 만들지 않는다. 생성된 자원은 기존 with 정리 정책을 따른다.
- CompletedListing은 완전 수집 후에만 생성하며, 중복 ID는 첫 레코드를 보존한다. 추천·정렬은 완료 전에 실행하지 않는다.
- open은 모든 입력을 검증한 고유 링크 목록을 반환받은 뒤 브라우저에 전달한다. 소스 prepare/collect와 독립이다.

## 합성 플랫폼 검증 계약

테스트의 일반 구성 경계에 `test-platform` 바인딩을 주입한다. 제품 레지스트리·일반 help에는 남기지 않는다. 전용 CLI/추천 함수를 만들지 않는다.

| 검증 특성 | 합성 예와 기대 |
| --- | --- |
| 정올과 다른 난이도 | 합성 난도 점수 100~200을 유효한 --tier 값으로 사용. 정올 1~30 변환으로 거부하지 않음 |
| 다른 URL/모델 | 테스트용 도메인 URL과 자체 문제 타입 사용. 네트워크 요청 없이 고정 데이터 반환 |
| 미지원 필터 | accepted·사용자 조건 등 일부를 지원 정보에서 제외. 기본 실행 허용, 명시한 all/0/무효·반복 입력은 코드 2 |
| 표시 | 합성 난도 의미를 안내하고 정올 미지원 통계 열·정올 전용 주의 문구를 노출하지 않음 |
| 중복·문제 링크 | 정올과 같은 숫자 ID라도 선택 플랫폼 URL만 전달. 수집의 중복 ID는 첫 레코드 보존 |
| 공통 추천 | 동일 Picker/selection의 sample 호출, 전체 후보 처리·고유 선택·부족 처리 유지 |
| 격리 | 정올 source 생성·resolve_user·브라우저 URL 호출 0회. 미지원 입력에서는 합성 source 생성도 0회 |

합성 규칙은 프로그래머스 실제 속성이나 자동 접근 허가에 대한 주장이 아니다. 향후 실제 플랫폼 추가 시 지원 정보·자체 typed 모델/정책·수집·링크 연결을 구현하되 세 명령과 추천 알고리즘을 복제하지 않는다.
