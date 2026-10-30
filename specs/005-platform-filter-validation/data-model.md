# Data Model: 플랫폼별 지원 정보와 typed 처리 경계

이 문서는 [명세](spec.md)의 엔터티를 구현 가능한 타입과 검증 책임으로 정리한다. 저장 스키마나 영구 상태를 추가하지 않는다.

## 1. PlatformInfo와 FilterCapability

| 타입 | 필드 | 규칙 |
| --- | --- | --- |
| PlatformInfo | key, display_name, filters, retired_options, 속성/출력 설명, 지원 정렬 안내 | key는 정적 레지스트리에서 유일. 기본 제품 값은 jungol 하나. 외부 작업 없이 조회 가능 |
| FilterCapability | key, option_names, meaning, unit, value_help, combination_help | 한 의미 그룹의 범위/기존 경계 이름을 명시. 허용 값은 플랫폼 정책과 같은 선언을 사용하며 설명만으로 별도 검증기를 만들지 않음 |

정올은 tier·rate·accepted·사용자 조건을 제공한다. 사용자 그룹 안에서도 `--status`와 `--user`의 실제 옵션 이름을 보존한다. 다른 플랫폼이 일부 옵션만 지원하면 option_names에 명시한 것만 허용한다. 미지원은 이 지원 정보의 부재이며 문제 값 sentinel이 아니다.

retired_options는 지원 필터와 분리된 폐기 입력 진단 목록이다. 정올의 `--min-solvers`·`--max-solvers`를 포함하며 대체 옵션과 기존 지표 전환 설명을 보관한다. 공통 검사는 이를 무시하거나 지원 필터로 선언하지 않고 해당 플랫폼의 전용 거부 진단으로 넘긴다. 진단은 반드시 코드 2로 끝나며 조건을 생성하지 않는다. 다른 미지원 필터도 함께 있으면 그 전체 지원 검사가 먼저다. 다른 플랫폼에서 이 폐기 이름을 선언하지 않았다면 일반 미지원으로 거부한다.

등록 시 중복 플랫폼 키·한 옵션의 중복 소유·정의하지 않은 옵션 연결·지원 속성과 출력 선언 불일치를 검사한다. 구성 오류는 초기화 때 경고하고 해당 플랫폼 사용 시 실패한다. 기본 플랫폼 누락을 다른 플랫폼 선택으로 숨기지 않는다. 사용자 오타(코드 2)와 내부 구성 오류(코드 1)를 구분한다. 타입/내부 결과 불변식은 assertion으로 확인한다.

## 2. RawFilterInput과 ValidatedRequest

RawFilterInput은 CLI 경계의 실행 중 불변 값이다.

| 필드 | 의미 |
| --- | --- |
| values | 알려진 각 필터의 raw 문자열 또는 반복 범위 문자열 tuple. 플랫폼 숫자·enum으로 변환하기 전 값 |
| supplied_options | Context 출처가 COMMANDLINE인 정확한 옵션 이름의 집합. 값의 truthiness로 추정하지 않음 |

값이 0·빈 문자열·all이어도 명시 여부를 보존한다. 범위는 모든 출현을 보존하고 지원 검사 후 반복을 거부한다. 기존 단일 경계 옵션 반복은 현재 파서의 동작을 유지한다. raw 필드에는 아직 의미 검증된 숫자라는 가정을 두지 않는다.

ValidatedRequest는 선택 플랫폼의 고유 조건 C와 공통 실행 선택(조회/추천, 요청 개수, 정렬 방향 등)을 포함한다. `list`의 정렬 키는 플랫폼 정책에서 검증하며, 정올 SortKey를 모든 플랫폼에 강제하지 않는다. 알려진 정올 지표를 지원하지 않는 플랫폼에서 해당 정렬을 요청하면 실행 전에 코드 2로 안내한다. 필터와 정렬은 서로 다른 지원 항목이다.

검증 책임은 다음 한 방향으로 나눈다.

1. Typer: 옵션 존재·인자 개수·값 누락 등 기본 문법과 공통 비필터 타입.
2. CLI 공통 지원 검사: supplied_options와 선택 플랫폼 option_names 비교. 미지원 이름을 모두 출력.
3. 플랫폼 순수 정책: 그 플랫폼의 값·범위·조합·문제 번호 검증. 정올 legacy 전환 안내도 여기서 처리.
4. 플랫폼 모델 생성자: 직접 Python 구성 시에도 필요한 불변식 보존. 내부 단계에서 사용자 입력 검사를 반복하지 않음.

## 3. 문제와 플랫폼 전용 타입

공통 ProblemRecord 프로토콜은 `id`(해시 가능한 플랫폼 내부 식별자), `title`, `url`, `listed_at`만 읽는다. 공통 코드는 id에 산술·티어 비교·문자열 변환 후 정렬을 수행하지 않는다. 정올 id는 기존 양의 정수 그대로이며 정렬은 숫자 기준이다. 한 실행의 플랫폼 안에서만 중복을 제거하고 플랫폼을 섞어 집계하지 않는다.

| 정올 전용 타입 | 유지할 필드·검증 |
| --- | --- |
| Problem | 기존 id/title/url/tier/pass_rate/accepted_count/listed_at 전체. 정올 URL과 번호의 일치 유지 |
| Rated / Unrated | 1~30 확정 티어 / 정상 미정 티어. 기존 의미·검증 유지 |
| SearchCriteria | 기존 여섯 경계, status, user_handle. Decimal·수치 범위·경계 순서·핸들 정규화·사용자 조합 검증 유지 |
| UserReference | 기존 handle/account_id/resolved_at. 숫자 계정 ID 규칙은 정올에만 적용 |
| Status / SortKey | 정올 입력 의미와 지원 값. 공통 정책의 전역 제약으로 사용하지 않음 |

이 타입은 `jungol_models.py`가 소유한다. 기존 import와 고정 fixture는 소유 모듈로 조정하며, 이전 Python import 경로 호환성만을 위한 재수출 계층은 요구하지 않는다. JungolSource DOM 파싱 본문과 모델 불변식을 약화하지 않는다.

Known[T]·Unavailable과 관측 시각 유틸은 공통 값으로 재사용할 수 있다. 플랫폼은 필요한 속성만 가진 자체 typed 문제/조건/사용자 모델을 정의한다. 정올 필드 전체를 비정올 문제에 채워 넣지 않는다.

## 4. 속성 값 상태

| 상태 | 위치 | 필터·표시 |
| --- | --- | --- |
| 플랫폼 속성 미지원 | PlatformInfo에서 부재 | 필터 명시 시 코드 2. 생략 시 제외/미제공 집계 없음, 해당 출력 열 생략 |
| 지원 속성의 개별 값 미제공 | 문제의 Unavailable | 해당 필터 있으면 기존 순서로 제외·집계, 없으면 다른 조건 만족 시 포함하고 미확인 |
| 실제 0 | Known(0) 또는 정답률 Known(Decimal('0')) | 정상 숫자. 0..0 조건 통과, 미제공으로 취급하지 않음 |
| 정올 미정 티어 | Unrated | 기존 미정 표시, 티어 조건에서는 제외하되 미제공 제외 수에 넣지 않음 |

정올 처리 순서는 `tier → rate → accepted`다. 앞선 실제 수치 조건에서 제외된 문제의 뒤쪽 미제공 값을 추가 집계하지 않는다. 고유 문제당 첫 실패만 반영한다. 범위 밖 Rated 티어는 사이트 검색과 표시 값의 차이를 보존하며 다시 수치로 제외하지 않는다.

## 5. CompletedListing[P]와 Result[P,C,U]

- CompletedListing: candidates tuple[P], completed_at. 공급자의 완료 기준을 만족한 뒤에만 생성하며 같은 id는 첫 관측 레코드를 보존한다.
- Result: 플랫폼 고유 criteria C, user U 또는 None, problems tuple[P], fetched/eligible/requested/returned/omitted/shortage 집계, started_at/finished_at. 한 실행의 플랫폼 바인딩과 함께 표시한다.
- 현재 Result의 시간대·집계 순서·고유성·반환 개수·부족 불변식을 그대로 유지한다. 후보/필터/추천 집계는 동일 플랫폼 데이터만 포함한다.
- None 사용자 참조는 사용자 조건을 요청하지 않은 정상 상태다. 미지원 요청을 None으로 바꿔 무시하는 수단으로 사용하지 않는다.

## 6. Presentation과 ProblemLink

플랫폼 정책은 순수한 열 제목, 문제 행 문자열, 조건 요약, 관측값 주의 문구를 제공한다. Rich Console·stderr·종료 코드는 소유하지 않는다. 공통 CLI가 표·집계·빈 결과·부족·조회 시각·미제공 제외 안내를 렌더링한다. 열 수와 행 길이의 일치는 내부 불변식이다.

ProblemLink는 검증된 플랫폼 내부 식별자의 표시 문자열과 해당 플랫폼 URL이다. open 입력 전체를 먼저 검증한 뒤 입력 순서대로 중복 제거된 링크를 만든다. 중간 번호가 무효이면 아무 링크도 열지 않는다. 이 과정에 소스 컨텍스트나 네트워크가 필요하지 않다.

## 7. 상태 전이

```text
platform 선택 → 명시 입력 수집 → 지원 검증 → 값/조합 검증
  → source 생성/진입 → Validated
  → [UserResolved] → Collecting → Processing → Complete → 공통 표시
```

입력 오류는 source 생성 전에 종료한다. 사용자 준비 결과가 None이 아닐 때만 UserResolved를 보고한다. 실패는 Failed, Ctrl+C는 Cancelled로 전이하고 컨텍스트를 정리한다. 완료 목록이 없으면 필터·정렬·추천·결과 표시를 실행하지 않는다. open과 help/version은 이 수집 상태 전이에 진입하지 않는다.
