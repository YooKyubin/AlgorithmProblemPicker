# Research: JUNGOL 문제 검색·추천 CLI

조사일: 2026-10-19. 기존 [조사 기록](discovery.md)에 이어 계획에 필요한 결정을 정리한다.
아래의 설계 결정과 실제 사이트에서 검증한 범위를 구분한다.

## 1. 공개 화면 기반 연동

- **Decision**: 동기 Playwright와 Chromium으로 정올이 렌더링한 공개 DOM을 읽는다.
  비영구 브라우저 컨텍스트 한 개에서 목록·상세 페이지를 순차 탐색한다.
- **Rationale**: 사이트가 자체적으로 수행하는 렌더링·필터·페이지 이동을 사용하면서,
  인증성 헤더와 바이너리 프로토콜을 직접 재구현할 필요가 없다.
- **Alternatives considered**: 문서화되지 않은 내부 API 직접 호출은 사용 정책과 계약이 없어 제외한다.
  정적 HTML만 파싱하는 방식은 커서 방식의 더 불러오기 동작까지 해결하지 못해 선택하지 않는다.
- **Evidence**: [공개 API 모듈](https://jungol.co.kr/_app/immutable/chunks/CMlQ6Drv.js),
  [문제 목록 모듈](https://jungol.co.kr/_app/immutable/chunks/6tH2-dSg.js),
  [Playwright 동기 API](https://playwright.dev/python/docs/library).
- 내부 상태·페이지 전역 변수·직렬화된 앱 데이터는 런타임 데이터 계약으로 사용하지 않는다.

## 2. 접근 정책과 범위

- **Decision**: 개인용·비상업적 공개 문제 메타데이터 검색과 링크 반환으로 한정한다.
  사용자가 지정한 공개 핸들·ID만 실행 중 사용하고 계정 목록·프로필·제출 코드 수집은 하지 않는다.
- **Rationale**: [robots.txt](https://jungol.co.kr/robots.txt)는 일반 에이전트에
  `Allow: /`와 `search=yes`를 제공한다. [이용약관](https://jungol.co.kr/about/provision)은
  개인 이용 외 복제·제3자 제공, 무승낙 영업, 타인 개인정보 수집·저장을 제한한다.
  읽은 원문에서 위 범위의 개인 메타데이터 검색에 대한 별도 승인 필수 조항이나
  모든 공개 DOM 자동 탐색을 금지하는 문구는 확인하지 못했다.
- **Alternatives considered**: 내부 API 사용, 상업적 배포·재판매, 사용자 정보 축적은 이번 범위 밖이다.
- **판단의 한계**: 위 근거를 이번 제한된 검색 설계에 적용한 판단이다.
  모든 자동화나 내부 API 이용에 대한 포괄적 허가를 확보했다는 뜻은 아니다.
  공개 사용자 선택 UI의 존재도 개인정보 대량수집 승인으로 해석하지 않는다.
- 탐색은 한 번에 하나씩 시작하며, 탐색·더 불러오기 시작 간격은 최소 1초로 둔다.
  403·429·챌린지·로그인 요구에서는 중단한다. 자동 재시도와 제한 우회는 하지 않는다.

## 3. 지정 사용자의 풀이 여부

- **Decision**: `--user`의 공개 핸들을 사이트의 사용자 선택 UI에서 정확히 식별하고,
  사이트가 반환한 숫자 ID에 `solvedByMode=include/exclude`를 적용한다.
  `status=solved/unsolved`는 로그인 사용자용이므로 사용하지 않는다.
- **Rationale**: 로그인 정보나 별도 풀이 기록 없이 명세의 공개 사용자 기준을 유지한다.
  사용자를 찾지 못하거나 정확한 핸들이 여러 개면 오류로 끝내고 첫 검색 결과를 임의 선택하지 않는다.
- **Alternatives considered**: 로그인 세션 저장과 사용자의 제출 이력을 직접 수집하는 방식은 불필요하다.
- **Live evidence**: 비로그인 상태의 공개 사용자 `@JUNGOL`(ID 146040)에 대해
  [include 목록](https://jungol.co.kr/problem?solvedBy=146040&solvedByMode=include&type=problem)은
  2356·2799번을 표시했다.
  [exclude와 검색 조합](https://jungol.co.kr/problem?solvedBy=146040&solvedByMode=exclude&type=problem&search=2356)은
  다른 검색 결과를 표시했고 첫 결과 묶음에 2356번이 없었다.
  검색은 유사 결과도 반환하므로 결과 0개나 전체 집합의 여집합을 검증했다고 주장하지 않는다.
- 전체 include/exclude 분할과 오답만 있는 사용자는 기본 테스트의 고정 데이터로 검증하고,
  라이브 수용 검증에서는 작은 후보 범위와 알려진 공개 풀이 표본으로 다시 확인한다.

## 4. 지표 의미와 DOM 계약

- **Decision**: 목록의 정답률 문자열을 Decimal로 읽고, 후보 상세의
  `title="맞힌 사람"` 통계에서 푼 사람 수를 읽는다.
  티어는 해당 문제에 속한 `/solved/<번호>.svg` 배지를 1~30으로 해석한다.
- 목록에서 관측한 티어·정답률은 사전 필터와 최종 결과에 그대로 유지한다.
  상세에서는 푼 사람 수만 보강해 조회 도중 지표 변경으로 필터와 표시가 어긋나지 않게 한다.
- **Rationale**: [1000번 공개 문제](https://jungol.co.kr/problem/1000)의 화면과 HTML에서
  맞힌 사람 5,171명, 정답 제출 6,510회, 전체 제출 13,720회를 별도로 확인했다.
  티어 배지는 `/solved/1.svg`이며 공개 설명에는 Bronze V가 표시된다.
  전체 제출 수를 푼 사람 수로 대신 읽지 않는다.
- **Alternatives considered**: 응답에 포함된 `rank.solvedUsr`는 조사 근거로만 확인했다.
  이 직렬화 필드를 직접 추출하는 런타임 연동은 선택하지 않는다.
  DOM이 바뀌었을 때 API나 다른 숫자로 조용히 대체하지 않는다.
- 알려진 레이아웃의 명시적인 미정·빈 지표만 값 없음으로 취급한다.
  필수 요소 누락·중복·파싱 실패는 사이트 구조 변경 오류다.
  값 없음과 실제 0은 구분한다.
- 지표의 필터 경계는 표시 정밀도를 따른다. 47.45%는 정확히 Decimal("47.45")로 비교한다.
  정답 제출 비율을 더 정밀하게 재계산하지 않는다.

## 5. 전체 후보와 페이지 종료

- **Decision**: `type=problem`, 안전하게 적용 가능한 티어·풀이 조건으로 목록을 좁힌다.
  서버 정렬은 번호 오름차순으로 고정하고, 최종 정렬·표시 제한은 로컬 메모리에서 수행한다.
- **Rationale**: 난이도 서버 정렬은 미정 문제를 자동 제외하므로 명세와 다른 결과를 만들 수 있다.
  정답률·임의의 푼 사람 수 범위·무작위 선택은 화면의 URL 조건으로 처리되지 않는다.
- **Evidence**: 일반 문제 또는 풀이 조건을 사용한 실제 화면에 `더 불러오기` 버튼이 있었다.
  [목록 모듈](https://jungol.co.kr/_app/immutable/chunks/6tH2-dSg.js)은
  `type`·풀이·푼 사람 조건에서 커서 방식으로 전환한다.
- 번호 페이지는 실제 다음 링크를 따라가고, 커서 페이지는 일반 더 불러오기 버튼을 누른다.
  읽은 문제 ID를 합치며 마지막 응답의 중복 ID는 최초로 관측한 레코드를 유지한다.
  로딩 완료 뒤 새 ID·정상 종료·오류 중 하나를 확인한다.
  버튼이 사라졌다는 이유만으로 로딩 중 상태를 종료로 처리하지 않는다.
  같은 페이지 반복이나 더 불러오기 이후 진행 없는 상태는 완전성 오류다.
- 목록 전체 수집 → 저비용 티어·정답률 필터 → 남은 후보 상세 통계 조회 →
  푼 사람 수 필터 → 최종 정렬·추첨 순서로 처리한다.
  정답률로 이미 탈락한 문제의 상세 조회는 생략한다.
  정상적으로 남은 후보는 출력 개수 제한 전에 필요한 상세 정보를 확보한다.

## 6. 최소 기술 구성과 수명

- **Decision**: Python 3.12 이상, uv, Typer, Rich, 동기 Playwright, pytest를 사용한다.
  초기 검증 기준은 Python 3.12와 Chromium이다. 라이브러리 버전은 구현 시 해결해 uv.lock에 고정한다.
- **Rationale**: README와 일치하고 단일 사용자 도구에 별도 비동기 실행기·웹 서버·DB가 필요 없다.
  공급자 Protocol 하나로 외부 조회와 순수 필터·정렬을 분리한다.
- **Alternatives considered**: asyncio·병렬 크롤러·영구 브라우저 프로필·저장 DB는 이번 규모에 불필요하다.
- 실행마다 새 비영구 컨텍스트를 사용하고, 성공·실패·취소 모두에서 닫는다.
  문제 목록·사용자 매핑·브라우저 상태를 다음 실행용으로 저장하지 않는다.
  의존성 및 Chromium 설치 파일은 개발 도구이며 문제 캐시와 구분한다.
- [Python 버전 지원](https://devguide.python.org/versions/),
  [uv 잠금·동기화](https://docs.astral.sh/uv/concepts/projects/sync/),
  [비영구 BrowserContext](https://playwright.dev/python/docs/api/class-browsercontext),
  [DOM 로케이터](https://playwright.dev/python/docs/locators),
  [Decimal](https://docs.python.org/3/library/decimal.html).

## 7. 오류·출력·검증

- **Decision**: stdout은 결과, stderr는 진행·진단에 사용한다.
  종료 코드는 성공·정상 빈 결과·추천 부족 0, 작업 실패 1, 입력 오류 2, 취소 130으로 한다.
  탐색 제한 30초, DOM 동작·준비 확인 제한 15초를 기본으로 둔다.
- **Rationale**: 불완전 수집과 정상적인 결과 없음이 구분되어야 한다.
  domcontentloaded 이후 결과 또는 명시적인 빈 상태를 기다린다.
  고정 긴 대기와 networkidle을 완료 판정으로 사용하지 않는다.
- **Alternatives considered**: 실패를 빈 목록으로 바꾸는 대체 동작, 무한 대기·재시도는 사용하지 않는다.
- **Decision**: 완료된 고유 적격 후보에 표준 `random.sample`을 한 번 적용한다.
  무작위 정렬은 `shuffle`을 사용한다.
- **Rationale**: 문서화된 균등 비복원 추출을 사용하고 전체 고유 후보 전달을 검증한다.
  빈도 통계로 CI 통과 여부를 정하는 불안정한 테스트는 추가하지 않는다.
- 최소 테스트는 경계·미정값·동점, 두 페이지 후보 포함, 부족·중복,
  DOM 통계 구분·진행·구조 오류, CLI 입력·취소·명시적 열기를 검증한다.
  기본 테스트는 네트워크 없이 실행하며 라이브 검증은 명시적으로 선택한다.
- [random](https://docs.python.org/3/library/random.html),
  [Playwright 페이지 API](https://playwright.dev/python/docs/api/class-page),
  [Rich 진행 표시](https://rich.readthedocs.io/en/stable/progress.html),
  [Typer 테스트](https://typer.tiangolo.com/tutorial/testing/),
  [pytest monkeypatch](https://docs.pytest.org/en/stable/how-to/monkeypatch.html).

## 연구 결과

설계를 결정하지 못한 항목은 없다. 사이트의 모든 사용자·모든 페이지를 라이브로 검증한 것은 아니다.
배포별 DOM 변화와 라이브 수용 검증은 위 데이터 접근 계약 및 검증 절차로 다룬다.
캐싱 제외는 기존 헌장 III보다 우선하는 이번 사용자의 명시적 범위 변경으로 기록한다.
