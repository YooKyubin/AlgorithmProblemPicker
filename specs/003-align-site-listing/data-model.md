# Data Model: 사이트 목록의 관측값과 완료 경계

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

기존 도메인 타입과 공개 경계를 유지한다. 신규 영구 저장 모델·통계 상태·진행 이벤트는 만들지 않는다.  
변경되는 것은 확정 티어의 검색 조건 의미, 공급자 내부의 명시적 빈 상태 근거와 `CompletedListing` 생성 기준이다.

## 값과 부재 상태

| 타입 | 값·검증 | 003 의미 |
| --- | --- | --- |
| `Rated` | bool이 아닌 정수 1~30 | 표시 티어를 그대로 유지한다. 요청 경계 밖이어도 정상 상태다. |
| `Unrated` | 정상 미정 표현 | 티어 조건이 있으면 제외하고, 없으면 포함하는 기존 정책을 유지한다. |
| `Unavailable` | 정상 미확인 티어 또는 명시적 미제공 통계 | 파싱 실패의 대체값이 아니다. 확인된 빈 통계 표현이 이 상태에 추가된다. |
| `Known[int]` | bool이 아닌 정수 0 이상 | 정답 제출 수. 0은 미제공과 다르다. |
| `Known[Decimal]` | 유한 Decimal 0~100 | 정답률. 목록 표시값과 정밀도를 보존하며 재계산하지 않는다. |

## SearchCriteria

| 필드 | 규칙·적용 위치 |
| --- | --- |
| `min_tier`, `max_tier` | 생략 가능. 지정하면 정수 1~30, 하한≤상한. 사이트 검색 조건으로 전달하며 `Rated.value`의 로컬 범위 검사에는 쓰지 않는다. |
| `min_rate`, `max_rate` | 생략 가능. 유한 Decimal 0~100, 하한≤상한. 로컬 필터에서 양 끝 포함. |
| `min_accepted`, `max_accepted` | 생략 가능. 정수 0 이상, 하한≤상한. 로컬 필터에서 양 끝 포함. |
| `status` | all/solved/unsolved. 기존 공개 사용자 기준을 유지한다. |
| `user_handle` | 앞의 @ 한 개 정규화, 대소문자 보존. solved/unsolved는 정확한 핸들 필수, all+user는 입력 오류. |

티어 경계가 하나라도 있으면 사이트에 미정 제외를 요청한다. 수집된 정상 `Unrated`는 제외하고 `Unavailable` 티어는 미확인 제외 수에 한 번 반영한다.  
경계가 없으면 두 상태를 포함한다. 확정 티어는 어느 경계에서든 다른 로컬 조건 검사로 진행한다.

## Problem

| 필드 | 불변식 |
| --- | --- |
| `id` | bool이 아닌 양의 정수. 고유성 기준. |
| `title` | 비어 있지 않은 문자열. |
| `url` | 해당 id의 `https://jungol.co.kr/problem/<id>`와 일치. |
| `tier` | Rated/Unrated/Unavailable. 표시 관측값을 요청 범위에 맞춰 보정하지 않는다. |
| `pass_rate` | Known[Decimal]/Unavailable. |
| `accepted_count` | Known[int]/Unavailable. 동일 사용자의 중복 정답 제출을 포함한다. |
| `listed_at` | 시간대가 있는 관측 시각. |

같은 번호가 여러 목록에 나타나면 최초 관측 `Problem`을 유지한다. 지표 미제공 때문에 수집 레코드를 먼저 버리지 않는다.

## 공급자 내부 Row Snapshot

DOM 구조를 검증할 수 있도록 기존 배열 형태와 문제 링크 정보를 유지한다. 아래 필드는 공급자 내부에서만 사용하고 도메인·CLI로 노출하지 않는다.

| 필드 | 형태·용도 |
| --- | --- |
| `links` | 해당 문제 셀의 링크·제목·배지·미정/미확인 정보. 기존 구조 검증 유지. |
| `rates`, `accepted` | 각각의 통계 셀을 순서대로 읽은 trim 텍스트 배열. 배열 길이로 누락·중복 확인. |
| `rateEmpty`, `acceptedEmpty` | 같은 셀 목록에서 추출한 `data-col-empty` 존재 여부의 boolean 배열. 빈 속성값도 true다. |
| `rateLinks` | 정답률 셀 링크 대상. 기존 같은 문제 빈 링크의 미제공 지원에 사용. |
| `regular` | 일반 문제 표시 존재 여부. |

텍스트와 빈 표시 배열은 같은 셀 순서·개수로 생성한다. 이 관계는 내부 추출 불변식이며 구조 오류를 빈 목록으로 바꾸지 않는다.

### 통계 분류

| 관측 | 분류·동작 |
| --- | --- |
| 셀 1개, 정상 비어 있지 않은 숫자 | 숫자를 파싱한다. 빈 표시가 함께 있어도 정상 수치가 우선이다. |
| 셀 1개, 기존 미제공 토큰 | Unavailable. 기존 토큰 계약을 유지한다. |
| 셀 1개, 빈 텍스트, 그 셀의 명시적 빈 표시 | 새로 지원하는 Unavailable. 준비 판정도 읽을 수 있는 셀로 인정한다. |
| 정답률 셀 1개, 빈 텍스트, 링크 대상이 유일한 문제 href와 일치 | 기존 Unavailable 호환 규칙 유지. 정답 제출 수로 확대하지 않는다. |
| 명시적 표시 없는 빈 정답·허용 근거 없는 빈 통계 | 임시 미준비 상태로 기다린다. 준비 실패를 Unavailable로 바꾸지 않는다. |
| 셀 누락·중복 또는 잘못된 비어 있지 않은 수치 | 구조·파싱 실패. 빈 표시가 있어도 오류를 숨기지 않는다. |

확인된 표현과 기존 미제공 토큰의 구체적인 문법은 [공급자 계약](contracts/source.md)을 따른다.

## CompletedListing

| 필드 | 규칙 |
| --- | --- |
| `candidates` | 최초 관측을 유지한 고유 Problem의 tuple. |
| `completed_at` | 적용된 수집 종료 기준을 만족한 시각. 시간대 필수. |

더 불러오기에서 다음 번호 링크와 버튼이 없고 현재 목록을 읽을 수 있으면 생성할 수 있다. 새 행이 없는 최종 로드와 명시적인 빈 검색 결과도 포함한다.  
번호 페이지에서는 기존 페이지 진행·반복 방지·새 ID 확인을 유지한다. 사이트가 누락한 문제나 종료 판정 뒤 늦게 반영되는 문제까지 포함한다는 의미는 아니다.

## 필터·정렬·개수

- 티어 상태 제외 → 정답률 → 정답 제출 수 순서를 유지하되 확정 티어의 요청 범위 비교만 제거한다.
- 활성 수치 필터에서 미제공이면 제외하고 미확인 제외 수를 한 번만 늘린다. 앞선 조건으로 탈락하면 뒤 조건을 집계하지 않는다.
- 필터 없는 미제공은 포함 가능하며 지표 양방향 정렬에서 마지막이다. 동점·미확정 그룹은 번호 오름차순이다.
- 확정 티어가 범위 밖이어도 난이도 정렬은 실제 표시값으로 수행한다.
- 모든 후보가 제외돼도 정상 0개다. 미정 티어 제외는 미확인 제외 수에 포함하지 않는 기존 정책을 유지한다.

## UserReference, Result, Progress

`UserReference`의 정확한 handle·양의 account_id·시간대 있는 resolved_at과 공개 사용자 확인 규칙은 유지한다.

`Result`는 기존 필드와 불변식을 유지한다.

- `fetched_count >= eligible_count >= returned_count`, 고유 번호·최초 관측 유지.
- `returned_count = min(requested_count, eligible_count)`, requested_count는 양수.
- 추천 shortage는 requested_count−returned_count이며 list의 shortage는 0이다.
- `0 <= omitted_unknown_count <= fetched_count−eligible_count`.
- 시작·완료 시각은 시간대가 있고 finished_at≥started_at이다.

진행 상태는 `Validated → [UserResolved] → Collecting → Processing → Complete`이며 비종료 단계에서 Failed/Cancelled로 전이할 수 있다.  
공급자가 성공한 뒤에만 필터·정렬·추첨·Result를 수행한다. 실패·취소는 최종 결과를 생성하지 않는다. 실패·취소 시 누적 개수 보존을 위한 `Progress`·콜백·예외 필드 변경은 하지 않는다.
