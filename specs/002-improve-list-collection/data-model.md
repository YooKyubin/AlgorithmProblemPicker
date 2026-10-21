# Data Model: 목록에서 완성되는 문제와 정답 제출 수

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

모든 객체는 실행 중 메모리에만 존재한다. 데이터베이스·파일 마이그레이션은 없다.
정상 부재를 명시적 값 타입으로 표현하고, 외부 표시를 해석하지 못한 경우는 예외로 경계를 넘긴다.

## 1. 값 상태

| 타입 | 의미 | 규칙 |
| --- | --- | --- |
| `Known[T]` | 알려진 지표 | 0도 알려진 값이다. |
| `Unavailable` | 명시적으로 미제공인 지표 | 누락·파싱 실패의 대체값이 아니다. |
| `Rated` | 확정 티어 | bool이 아닌 정수 1~30. |
| `Unrated` | 정상적으로 식별한 티어 미정 | 미확인과 구분해 표시한다. |

원시 데이터의 허용 표현은 [source 계약](contracts/source.md)을 따른다.
타입/수치 범위는 도메인 생성 경계에서 검증하고, 순수 처리의 각 전달 단계에서 반복 검증하지 않는다.

## 2. Problem

기존 `Candidate`와 상세 보강 후 `Problem`의 상속 구분을 없애고 단일 불변 dataclass를 사용한다.

| 필드 | 타입 | 검증·의미 |
| --- | --- | --- |
| `id` | `int` | bool이 아닌 양의 정수. |
| `title` | `str` | 공백뿐인 제목은 오류. |
| `url` | `str` | `https://jungol.co.kr/problem/<id>`와 일치. |
| `tier` | `Rated / Unrated / Unavailable` | 확인한 표시 상태를 보존. |
| `pass_rate` | `Known[Decimal] / Unavailable` | 유한한 0~100, 목록 표시 정밀도를 유지. |
| `accepted_count` | `Known[int] / Unavailable` | bool이 아닌 0 이상의 정수, 중복 정답 제출 포함. |
| `listed_at` | 시간대가 있는 `datetime` | 해당 목록 관측 시점. |

`solver_count`, `details_observed_at`은 제거한다. 별칭으로 새 값을 저장하지 않는다.
전체 제출 수와 맞힌 사람 수는 새 문제 모델의 필수 속성이 아니다.
목록을 읽은 뒤 상세 조회로 필드를 덮어쓰거나 보충하지 않는다.

## 3. SearchCriteria와 정렬

| 필드 | 형식 | 규칙 |
| --- | --- | --- |
| `min_tier`, `max_tier` | 선택적 정수 | 지정 시 1~30. |
| `min_rate`, `max_rate` | 선택적 Decimal | 지정 시 유한한 0~100. |
| `min_accepted`, `max_accepted` | 선택적 정수 | 지정 시 bool이 아닌 0 이상. |
| `status` | `all / solved / unsolved` | 기본 all. |
| `user_handle` | 문자열 | 기본 빈 문자열. solved/unsolved에서 정확한 공개 핸들 필수. |

- 각 범위는 양 끝을 포함한다. 생략한 경계는 제한하지 않으며 하한은 상한 이하여야 한다.
- 사용자 핸들 앞의 `@` 한 개만 정규화하고 대소문자는 보존한다. `all + user`는 입력 오류다.
- `min_solvers`, `max_solvers`는 도메인에서 제거한다. 레거시 입력은 CLI에서 거부하므로 이 객체에 도달하지 않는다.
- `SortKey`: `id`, `difficulty`, `rate`, `accepted`, `random`. `Order`: `asc`, `desc`.
- 기본은 id/asc. random/desc는 입력 오류다. 지표 동점과 미확정 그룹 내부는 번호 오름차순이다.
- 미정·미확인 지표는 정렬 방향에 관계없이 마지막이다.

## 4. UserReference

기존 `handle`, 양의 `account_id`, 시간대가 있는 `resolved_at`을 유지한다.
공개 사용자 선택 화면의 정확한 핸들에 대해서만 생성한다.
사용자를 확인하지 못한 경우에는 빈 사용자나 미풀이 사용자로 대체하지 않는다.

## 5. CompletedListing

| 필드 | 타입 | 의미 |
| --- | --- | --- |
| `candidates` | `tuple[Problem, ...]` | 전체 수집을 마친 고유 관측 문제. |
| `completed_at` | 시간대가 있는 datetime | 마지막 목록의 정상 완료를 확인한 시점. |

- 공급자는 전체 완료를 확인한 뒤에만 객체를 생성한다. 시간 초과·반복 페이지·입증되지 않은 종료는 실패다.
- 동일 ID가 여러 번 나타나면 최초 관측 레코드를 유지한다. 개수는 고유 ID 기준이다.
- 정상 미정·미확인은 수집 객체에 보존한다. 티어 조건의 후보에서 제외하는 작업은 순수 필터 책임이다.
- 범위 밖 확정 티어·구조 오류가 있으면 이 객체를 정상 반환하지 않는다.
- `CompletedListing`은 공급자의 완료 계약을 나타내며, 생성자 자체가 원격 완료를 증명하는 것은 아니다.

## 6. 필터 결과와 개수

별도 프레임워크 없이 기존 `filter_listing`의 선택 목록과 제외 개수 반환 방식을 유지한다.
판정 순서는 티어→정답률→정답 제출 수다. 적용하지 않은 지표 필터는 건너뛴다.

| 상황 | 적격 여부 | `omitted_unknown_count` 증가 |
| --- | --- | --- |
| 티어 조건 있음 + Unrated | 제외 | 없음 |
| 활성 필터의 Unavailable을 처음 만남 | 제외 | 문제당 1 |
| 앞선 필터의 알려진 값이 범위 밖 | 제외 | 없음. 이후 필터는 검사하지 않음 |
| 모든 적용 조건 통과 | 포함 | 없음 |
| 해당 지표 필터 없음 + Unavailable | 다른 조건에 따라 포함 가능 | 없음 |

복수 지표가 미확인이어도 한 문제를 여러 번 세지 않는다.
집계는 모든 결측 속성의 총량이 아니라 실제 필터 흐름에서 미확인 때문에 제외된 고유 문제 수다.

## 7. Result

기존 결과 외형을 유지하고 `problems` 원소를 새 Problem으로 사용한다.

- `criteria`, 선택적 `user`, `problems`.
- `fetched_count`: CompletedListing의 고유 관측 수. 정상 미정·미확인을 포함한다.
- `eligible_count`: 모든 조건을 통과한 전체 고유 후보 수.
- `omitted_unknown_count`: 앞 절의 미확인 제외 수.
- `started_at`, `finished_at`: 시간대가 있는 실행 시작·완료 시점.
- `requested_count`, `returned_count`, `shortage`: 요청·실제 개수와 추천 부족 수.

불변식은 `fetched_count >= eligible_count >= returned_count`, 고유 결과 ID,
`finished_at >= started_at`이다. 추천은 `returned_count = min(requested_count, eligible_count)`이며
`shortage = requested_count - returned_count`다. list의 shortage는 0이다.
완전 수집 후 후보 0개는 정상 Result이며 실패·취소는 Result로 반환하지 않는다.

## 8. 진행과 상태 전이

```text
Validated → [UserResolved] → Collecting → Processing → Complete
비종료 단계 → Failed 또는 Cancelled
```

- `Processing`에서 전체 후보 필터·정렬·추첨·결과 구성을 마친 후 Complete로 전이한다.
- `Progress.collected`는 확인한 고유 관측 개수다. `detailed`와 `Enriching`은 제거한다.
- CLI는 결과를 출력하는 별도 책임을 갖는다. 현재 실행 경로에서 사용하지 않는 `Presented`를 제거하며,
  출력 상태를 전달하기 위한 신규 공개 인터페이스를 만들지 않는다.
- 상태 전이 위반은 내부 불변식 assertion, 외부 데이터 오류는 SourceError 계열로 구분한다.

## 9. 진단과 개발용 시간 기록

`SourceSchemaError`는 문제 번호(확인 가능할 때), 지표, 원시 값 또는 누락/중복 사실을 포함한다.
범위 이탈 `SourceAccessError`는 문제 번호·확정 티어·요청 범위를 포함한다.
별도 범용 진단 프레임워크나 영구 로그 모델은 추가하지 않는다.

성능 기록은 개발 도구의 보고 자료다. revision/환경/fixture 해시, 명령, 후보·상세 개수,
반복별 전체/목록 시간과 중앙값을 담으며 제품 Result에 벤치마크 전용 필드를 추가하지 않는다.
