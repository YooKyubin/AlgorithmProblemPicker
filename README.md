# JUNGOL 문제 검색·추천 CLI

`jpick`은 정올의 공개 일반 문제를 조건으로 조회하고, 전체 적격 후보에서 중복 없이 추천하는 개인용 Python CLI다. Python 3.12 이상과 uv, Chromium을 사용한다.

## 설치

저장소 루트에서 실행한다.

```powershell
uv sync --locked --python 3.12
uv run playwright install chromium
uv run jpick --help
uv run jpick --version
```

## 사용법

```powershell
# 티어 1, 정답률 80% 이상인 전체 후보를 확인하고 5개 표시
uv run jpick list --min-tier 1 --max-tier 1 --min-rate 80 --limit 5

# 정답률이 높은 순서 (동점은 번호 오름차순)
uv run jpick list --min-tier 1 --max-tier 1 --min-rate 80 --sort rate --order desc

# 정답 제출 10건 이상인 전체 적격 후보에서 3개 추천 (중복 정답 제출 포함)
uv run jpick recommend --min-tier 1 --max-tier 1 --min-rate 80 --min-accepted 10 --count 3

# 정답 제출 수가 많은 순서
uv run jpick list --min-tier 1 --max-tier 1 --sort accepted --order desc --limit 5

# 지정한 공개 사용자가 푼 문제 / 아직 정답 처리하지 않은 문제
uv run jpick list --user JUNGOL --status solved
uv run jpick list --user '@JUNGOL' --status unsolved --min-tier 1 --max-tier 1 --min-rate 80

# 명시한 번호만 기본 브라우저로 열기 (1000은 한 번만 전달)
uv run jpick open 1000 1000 1001
```

| 옵션 | 값 / 기본값 |
|---|---|
| `--min-tier`, `--max-tier` | 사이트 티어 검색 조건 1~30. 1=Bronze V, 30=Ruby I |
| `--min-rate`, `--max-rate` | 소수 0~100, % 기호 없이 |
| `--min-accepted`, `--max-accepted` | 0 이상의 정수, 동일 사용자의 중복 정답 제출을 포함한 정답 제출 수 |
| `--status` | `all`(기본), `solved`, `unsolved` |
| `--user` | 정확한 공개 핸들. 앞의 @ 한 개 허용, 대소문자 보존 |
| `list --sort` | `id`(기본), `difficulty`, `rate`, `accepted`, `random` |
| `list --order` | `asc`(기본), `desc`. `random + desc`는 입력 오류 |
| `list --limit` | 양의 정수, 기본 20 |
| `recommend --count` | 양의 정수, 기본 1 |

모든 범위는 양 끝을 포함하고 생략한 경계는 제한하지 않는다. 티어 옵션은 사이트에 전달하는 검색 조건이다. 사이트가 제공한 확정 티어가 요청 범위 밖이어도 수집·추천 후보에 보존하고 실제 표시 티어를 그대로 사용한다. 티어 범위가 있으면 정상 미정·미확인 티어는 후보에서 제외한다. 요청한 검색 조건이 손실되거나 표시 구조·값을 해석할 수 없으면 진단과 함께 중단한다.

명시적인 빈 정답 제출 수·정답률은 미제공으로 처리한다. 해당 지표 필터가 있으면 제외하고 고유 문제당 한 번 제외 수를 알린다. 필터가 없으면 다른 조건을 만족하는 문제를 포함하고 통계는 ‘미확인’으로 표시한다. 실제 0은 0으로 유지하며 0~0 조건에서 미제공을 0으로 취급하지 않는다. 미정·미확인은 양방향 지표 정렬에서 마지막이며 동점은 번호 오름차순이다.

`solved/unsolved`에는 `--user`가 필요하며 `all + user`는 오류다. 정확한 계정이 없거나 모호하면 실패한다. 오답만 제출한 문제도 unsolved다. 사용자 로그인이나 풀이 기록 변경은 제공하지 않는다.

수집 종료 기준까지 목록 수집 → 티어 상태·정답률·정답 제출 수 필터 → 전체 적격 후보 정렬·추천 → 표시 제한 순서다. `limit/count`가 작아도 종료 기준까지 모든 고유 후보를 읽으며, 목록에서 확인한 값만 사용해 상세 문서 요청 없이 결과를 출력한다. 후보 부족과 0개는 정상 성공이다.

정답 제출 수는 정답 처리된 제출 횟수로, 동일 사용자의 중복 정답 제출도 포함한다. 맞힌 사람 수·전체 제출 수와 다르며 같은 숫자의 조건이라도 결과가 달라질 수 있다. 예를 들어 `--min-accepted 1000`은 1,000명 이상이 풀었다는 뜻이 아니다.

기존 입력은 코드 2로 거부하고 아래 전환을 안내한다. 새 옵션과 섞어도 조회를 시작하지 않으며, 옛 입력을 새 지표의 별칭으로 처리하지 않는다.

| 기존 입력 | 새 입력 |
|---|---|
| `--min-solvers` | `--min-accepted` |
| `--max-solvers` | `--max-accepted` |
| `--sort solvers` | `--sort accepted` |

## 진행과 종료

결과 표·조건·개수·조회 시각·링크는 stdout, 진행·제외 안내·오류는 stderr에 출력한다. 실제 수집/결과 처리(Processing) 단계와 고유 수집 개수를 표시하며 `Ctrl+C`로 취소할 수 있다. 실패·취소 시 일부 후보로 만든 결과를 출력하지 않는다.

더 불러오기 버튼이 있으면 계속 수집하고, 버튼과 다음 번호 링크가 없으면 읽을 수 있는 현재 목록 또는 명시적인 빈 결과로 완료한다. 새 행이 없는 최종 로드도 같은 기준이며 별도의 목록 영역 완료 알림을 요구하지 않는다. 다음 번호 링크가 있으면 해당 페이지를 계속 확인한다. 로딩 중이거나 disabled인 버튼은 존재하는 상태이며, 버튼이 남아 있어도 수집이 진행되지 않으면 제한 시간 뒤 실패한다. 버튼 부재 시점 이후의 지연 반영이나 사이트가 누락한 문제까지 포함한다는 보장은 없다.

| 종료 코드 | 의미 |
|---|---|
| 0 | 성공, 정상 빈 결과와 추천 부족 포함 |
| 1 | 접속·사용자 식별·DOM 구조·완전성·기본 브라우저 전달 실패 |
| 2 | 잘못된 옵션·범위·개수·사용자 조건 |
| 130 | Ctrl+C 취소 |

`list/recommend`는 숨겨진 비영구 Chromium을 사용한다. `open`만 기본 브라우저에 링크를 전달한다. 전달 성공은 페이지 존재나 로딩 완료를 보장하지 않으며 일부 실패 시 모든 링크와 실패 번호를 출력한다.

## 데이터 접근과 한계

정올이 렌더링한 공개 DOM만 읽는다. 내부 API 직접 호출·응답 해독·앱 전역 상태 추출은 사용하지 않는다. 한 컨텍스트에서 탐색을 순차 수행하고 탐색/추가 로드 시작 간격을 최소 1초로 제한한다. 탐색 제한은 30초, DOM 준비/동작 제한은 15초다. 접근 제한·챌린지·로그인 요구에서는 중단하며 자동 재시도하지 않는다.

정답률은 목록 표시값과 정밀도를 Decimal로 보존해 비교하며 다른 통계로 재계산하지 않는다. 정답 제출 수는 목록의 정답 열에서만 읽는다. 각 목록의 관측 시점 값이므로 전체 사이트의 한 시점 스냅샷은 보장하지 않는다. DOM이 바뀌면 오류로 중단할 수 있다. 정답 열의 `-`·`—`·`미확인`·`미제공` 허용은 합성 검증 계약이며 실제 관측을 주장하지 않는다. 새 빈 통계는 해당 셀 정확히 한 개·빈 텍스트·그 셀의 `data-col-empty` 표시가 함께 있을 때만 미제공이다. 기존 같은 문제를 가리키는 빈 정답률 링크 예외도 유지한다. 마커 없는 임시 빈 값은 준비를 기다리며, 셀 누락·중복·잘못된 숫자를 미제공이나 0으로 바꾸지 않는다.

기존 기획의 **로컬 캐싱은 이번 구현 범위에서 제외**했다. 문제·사용자·브라우저 상태는 다음 실행용으로 저장하지 않는다. 가상환경과 Chromium 설치 파일은 도구 의존성이다. 공개 API 지원을 확보한 것은 아니며 접근 근거와 한계는 [research.md](specs/001-jungol-problem-picker/research.md)에 기록했다.

## 검증

```powershell
uv run --locked pytest -q
uv run --locked python scripts/benchmark_selection.py
uv run --locked python scripts/benchmark_collection.py --baseline-ref c37208f5a80628df5d7126972d31461b2517177d --runs 3 --output specs/002-improve-list-collection/collection-benchmark.md
```

기본 테스트는 고정 공급자와 로컬 HTML로 동작하며 원격 요청과 기본 브라우저 호출을 차단한다. 현재 정책의 구현·실사이트 검증 결과는 [003 quickstart.md](specs/003-align-site-listing/quickstart.md)에 기록한다. [002 기록](specs/002-improve-list-collection/quickstart.md)의 성능 측정·통합 수용 제약과 [001 기록](specs/001-jungol-problem-picker/quickstart.md)은 당시 정책의 이력이다. 수집 벤치는 고정 다중 목록을 별도 프로세스에서 비교하며 실제 사이트의 개선율을 뜻하지 않는다. 과거 측정을 003의 새 성능 측정으로 해석하지 않는다.

002의 최종 문서·검증 근거 대조(T033)는 2026-10-24 완료했다. [마감 기록](specs/002-improve-list-collection/quickstart.md#t033-마감-2026-10-24)에 선행 결함의 해결 근거와 003에서 대체된 정책, 과거 성능 측정의 적용 범위를 정리했다.

003에서 목록의 001/T041 완료 정책을 버튼 부재 시 현재 목록 완료로 대체했다. 지연된 미래 행·버튼을 포함하는 합성 기대도 같은 기준으로 전환했다. 사용자 검색의 001/T042는 기존 정책을 유지한다. 사용자 결과의 장식 변경과 같은 핸들 재렌더링만으로 현재 검색의 완료를 확정하지 않으며, 확인 근거가 없으면 이전 사용자 대신 오류를 반환한다. 목록과 사용자 검색의 지연 합성 사례를 실사이트에서 관측한 사실로 설명하지 않는다.
