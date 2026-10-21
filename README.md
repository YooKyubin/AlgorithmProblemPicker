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
| `--min-tier`, `--max-tier` | 1~30. 1=Bronze V, 30=Ruby I |
| `--min-rate`, `--max-rate` | 소수 0~100, % 기호 없이 |
| `--min-accepted`, `--max-accepted` | 0 이상의 정수, 동일 사용자의 중복 정답 제출을 포함한 정답 제출 수 |
| `--status` | `all`(기본), `solved`, `unsolved` |
| `--user` | 정확한 공개 핸들. 앞의 @ 한 개 허용, 대소문자 보존 |
| `list --sort` | `id`(기본), `difficulty`, `rate`, `accepted`, `random` |
| `list --order` | `asc`(기본), `desc`. `random + desc`는 입력 오류 |
| `list --limit` | 양의 정수, 기본 20 |
| `recommend --count` | 양의 정수, 기본 1 |

모든 범위는 양 끝을 포함하고 생략한 경계는 제한하지 않는다. 티어 범위가 있으면 정상 미정·미확인 문제를 후보에서 제외하고 수집을 계속한다. 지표가 미제공이면 해당 지표 필터에서 제외하고 개수를 알린다. 필터가 없으면 미확인으로 남긴다. 실제 0은 미확인과 구분한다. 미정·미확인은 양방향 지표 정렬에서 마지막이며 동점은 번호 오름차순이다. 범위 밖 확정 티어나 구조·해석 실패는 진단과 함께 중단한다.

`solved/unsolved`에는 `--user`가 필요하며 `all + user`는 오류다. 정확한 계정이 없거나 모호하면 실패한다. 오답만 제출한 문제도 unsolved다. 사용자 로그인이나 풀이 기록 변경은 제공하지 않는다.

전체 목록 수집 → 티어·정답률·정답 제출 수 필터 → 전체 적격 후보 정렬·추천 → 표시 제한 순서다. `limit/count`가 작아도 전체 후보를 읽으며, 목록에서 확인한 값만 사용해 상세 문서 요청 없이 결과를 출력한다. 후보 부족과 0개는 정상 성공이다.

정답 제출 수는 정답 처리된 제출 횟수로, 동일 사용자의 중복 정답 제출도 포함한다. 맞힌 사람 수·전체 제출 수와 다르며 같은 숫자의 조건이라도 결과가 달라질 수 있다. 예를 들어 `--min-accepted 1000`은 1,000명 이상이 풀었다는 뜻이 아니다.

기존 입력은 코드 2로 거부하고 아래 전환을 안내한다. 새 옵션과 섞어도 조회를 시작하지 않으며, 옛 입력을 새 지표의 별칭으로 처리하지 않는다.

| 기존 입력 | 새 입력 |
|---|---|
| `--min-solvers` | `--min-accepted` |
| `--max-solvers` | `--max-accepted` |
| `--sort solvers` | `--sort accepted` |

## 진행과 종료

결과 표·조건·개수·조회 시각·링크는 stdout, 진행·제외 안내·오류는 stderr에 출력한다. 실제 수집/결과 처리(Processing) 단계와 고유 수집 개수를 표시하며 `Ctrl+C`로 취소할 수 있다. 실패·취소 시 일부 후보로 만든 결과를 출력하지 않는다.

| 종료 코드 | 의미 |
|---|---|
| 0 | 성공, 정상 빈 결과와 추천 부족 포함 |
| 1 | 접속·사용자 식별·DOM 구조·완전성·기본 브라우저 전달 실패 |
| 2 | 잘못된 옵션·범위·개수·사용자 조건 |
| 130 | Ctrl+C 취소 |

`list/recommend`는 숨겨진 비영구 Chromium을 사용한다. `open`만 기본 브라우저에 링크를 전달한다. 전달 성공은 페이지 존재나 로딩 완료를 보장하지 않으며 일부 실패 시 모든 링크와 실패 번호를 출력한다.

## 데이터 접근과 한계

정올이 렌더링한 공개 DOM만 읽는다. 내부 API 직접 호출·응답 해독·앱 전역 상태 추출은 사용하지 않는다. 한 컨텍스트에서 탐색을 순차 수행하고 탐색/추가 로드 시작 간격을 최소 1초로 제한한다. 탐색 제한은 30초, DOM 준비/동작 제한은 15초다. 접근 제한·챌린지·로그인 요구에서는 중단하며 자동 재시도하지 않는다.

정답률은 목록 표시값과 정밀도를 Decimal로 보존해 비교하며 다른 통계로 재계산하지 않는다. 정답 제출 수는 목록의 정답 열에서만 읽는다. 각 목록의 관측 시점 값이므로 전체 사이트의 한 시점 스냅샷은 보장하지 않는다. DOM이 바뀌면 오류로 중단할 수 있다. 정답 열의 `-`·`—`·`미확인`·`미제공` 허용은 합성 검증 계약이며 실제 관측을 주장하지 않는다. 빈 셀·누락·해석 실패는 정상 미제공으로 바꾸지 않는다.

기존 기획의 **로컬 캐싱은 이번 구현 범위에서 제외**했다. 문제·사용자·브라우저 상태는 다음 실행용으로 저장하지 않는다. 가상환경과 Chromium 설치 파일은 도구 의존성이다. 공개 API 지원을 확보한 것은 아니며 접근 근거와 한계는 [research.md](specs/001-jungol-problem-picker/research.md)에 기록했다.

## 검증

```powershell
uv run --locked pytest -q
uv run --locked python scripts/benchmark_selection.py
uv run --locked python scripts/benchmark_collection.py --baseline-ref c37208f5a80628df5d7126972d31461b2517177d --runs 3 --output specs/002-improve-list-collection/collection-benchmark.md
```

기본 테스트는 고정 공급자와 로컬 HTML로 동작하며 원격 요청과 기본 브라우저 호출을 차단한다. 실제 검증과 성능 측정, 알려진 통합 수용 제약은 [002 quickstart.md](specs/002-improve-list-collection/quickstart.md)에 기록한다. 수집 벤치는 고정 다중 목록을 별도 프로세스에서 비교하며 실제 사이트의 개선율을 뜻하지 않는다. 기존 [001 기록](specs/001-jungol-problem-picker/quickstart.md)은 이전 구현 이력이다.

현재 요청 완료 뒤 공개 DOM이 늦게 반영되는 목록·사용자 검색 경계의 기존 001/T041·T042가 남아 있다. 해당 재현은 별도 xfail 테스트로 추적하며, 002의 최종 통합 수용은 이 선행 수정·검증을 기다린다.
