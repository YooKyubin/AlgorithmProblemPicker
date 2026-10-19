# Data Model: JUNGOL 문제 검색·추천

모든 레코드는 실행 중 메모리에만 존재한다. DB·문제 캐시·로그인 상태 저장은 없다.

## Problem

| 필드 | 의미·규칙 |
| --- | --- |
| id | 양의 정수. 중복 제거와 문제 식별의 유일한 키 |
| title | 공백이 아닌 공개 문제 제목 |
| url | 정올 HTTPS 문제 URL. 번호와 일치해야 함 |
| tier | 1~30인 Rated, 명시적인 Unrated, 확인 불가인 Unavailable 중 하나 |
| pass_rate | Decimal 0~100인 Known 또는 명시적인 미제공인 Unavailable |
| solver_count | 0 이상의 정수인 Known 또는 명시적인 미제공인 Unavailable |
| listed_at / details_observed_at | 시간대 정보가 있는 목록 지표 / 상세 푼 사람 수의 조회 시각 |

Known(0)은 Unavailable과 다르다. 단순 빈 컬렉션과 달리 지표의 부재는 의미 있는 상태이므로
명시적인 값 객체로 표현한다. DOM 파싱 실패나 접근 실패를 Unavailable로 바꾸지 않는다.
URL은 정올 문제 링크만 허용하며 외부 호스트 링크를 수집 대상으로 따라가지 않는다.
티어·정답률은 목록에서 관측한 값을 유지한다. 상세 조회는 푼 사람 수만 보강하며,
지표가 서로 다른 시점의 관측값일 수 있음을 두 조회 시각으로 구분한다.

## SearchCriteria

| 필드 | 의미·규칙 |
| --- | --- |
| min_tier / max_tier | 각각 생략 또는 1~30. 지정된 하한은 상한 이하여야 함 |
| min_rate / max_rate | 각각 생략 또는 유한 Decimal 0~100 |
| min_solvers / max_solvers | 각각 생략 또는 0 이상의 정수 |
| status | all / solved / unsolved |
| user_handle | status가 solved/unsolved일 때 필수. 앞의 @는 한 번 제거하고 대소문자 보존 |

모든 경계는 포함한다. 생략은 제한 없음이며 지표 값 없음과는 다른 의미다.
입력 단계에서 한 번 검증한 불변 조건을 내부 함수마다 재검증하지 않는다.
사용자 지정 없이 solved/unsolved를 요청하면 브라우저 실행 전에 입력 오류로 끝낸다.
all과 user를 동시에 지정하면 사용 의도가 불명확하므로 입력 오류로 안내한다.

## UserReference

정확한 공개 handle과 정올 숫자 account_id, resolved_at으로 구성한다.
입력 핸들과 정확히 일치하는 사이트 검색 결과만 사용할 수 있다.
검색 결과 목록을 저장하거나 다른 사용자 정보를 출력하지 않는다.
사용자가 없거나 식별이 모호하거나 공개 조건을 사용할 수 없으면 공급자 오류다.

## CandidateCollection

문제 요약은 id·title·url·tier·pass_rate·listed_at을 포함한다.
각 페이지 또는 로드 묶음에는 새로 관측한 문제, 종료 여부, 진행 정보가 있다.
같은 ID가 다시 나오면 최초 레코드를 유지한다.
전체 목록이 정상 종료된 후에만 CompletedListing으로 전환한다.

상태 전이는 다음과 같다.

`Validated → UserResolved(필요 시) → Collecting → Enriching → Complete → Presented`

Collecting에는 목록 전체 조회와 ID 중복 제거가 포함된다.
Enriching에는 저비용 필터와 필요한 상세 통계 조회가 포함된다.
어느 단계에서든 Failed 또는 Cancelled로 끝날 수 있으며 Complete를 건너뛰고
결과를 발표할 수 없다. 진행용 개수는 최종 결과로 취급하지 않는다.

## Result

| 필드 | 의미 |
| --- | --- |
| criteria | 실제 적용한 검색 조건 |
| user | 풀이 조건 적용 시 확인된 UserReference |
| problems | 고유 적격 Problem 목록 |
| fetched_count / eligible_count | 전체 조회 고유 개수 / 모든 필터 통과 개수 |
| omitted_unknown_count | 필요한 지표가 명시적으로 미제공이라 제외된 후보 수 |
| started_at / finished_at | 작업의 시간대 포함 시작·완료 시각 |
| requested_count / returned_count | 추천 요청 개수와 실제 반환 개수. 조회는 표시 개수와 실제 개수 |
| shortage | 추천 후보가 요청보다 적을 때의 차이 |

결과는 완전 조회 성공일 때만 생성한다. 후보 부족과 0개는 정상 결과다.
필터에 필요한 지표가 미제공이면 해당 문제를 제외하고 제외 개수를 안내한다.
필터가 없는 미제공 지표는 결과에 남기고 '미확인'으로 출력한다.

## 정렬·선택 규칙

- 기본 정렬은 ID 오름차순이다.
- 지표 정렬 키는 알려진 값, 요청 방향의 지표 값, ID 오름차순이다.
  값 없음은 방향과 관계없이 마지막이며, tier의 Unrated와 Unavailable도 마지막이다.
  같은 값 없음 그룹에서는 ID 오름차순을 따른다.
- 수치 필터가 지정된 지표의 Unavailable은 탈락한다.
  티어 범위를 하나라도 지정하면 Unrated도 탈락한다.
- 전체 필터·정렬 이후에 표시 제한을 적용한다.
- 추천은 완성된 고유 후보에서 sample로 뽑고, 반환 순서는 추출 순서다.
- 실행 사이의 추천 중복 방지나 사용자 풀이 상태 변경·저장은 하지 않는다.
