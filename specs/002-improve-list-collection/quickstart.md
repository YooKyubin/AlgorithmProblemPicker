# Quickstart & Validation: 002 목록 수집 개선

**Plan**: [plan.md](plan.md) | **Spec**: [spec.md](spec.md)

새 accepted 옵션과 목록 전용 경로의 실행 가이드다. 2026-10-21 구현·검증 결과는 아래 실행 기록에 있다.
002 최초 검증 당시에는 001/T041·T042 미해결로 최종 통합 수용과 T033을 미완료로 남겼다.
이후 선행 수정과 228개 일반 회귀 검증을 진행했고, 추가 검토에서 확인한 지연 버튼·중간 사용자 DOM 경계도 보완했다. 최신 결과는 [001 Phase 9 기록](../001-jungol-problem-picker/quickstart.md)을 따른다.
아래 T032의 결함 재현/xfail 기록은 수정 전 이력이다. T033의 최종 성능/문서 대조는 001 두 수정의 작업에 포함하지 않았으며, 2026-10-24 [T033 마감](#t033-마감-2026-10-24)에서 완료했다. 현재 정책과 검증은 [003 실행 기록](../003-align-site-listing/quickstart.md)을 따른다.

## 1. 준비

저장소 루트의 PowerShell에서 Python 3.12 이상과 uv를 사용한다.

```powershell
uv sync --locked --python 3.12
uv run --locked playwright install chromium
uv run --locked jpick --version
uv run --locked jpick list --help
uv run --locked jpick recommend --help
```

기존 잠금 의존성을 사용한다. 별도 DB·로그인·캐시 준비는 필요하지 않다.
도움말에는 accepted 수치 옵션과 정답 제출 수의 의미가 보이며 지원 정렬 값은 accepted를 포함한다.
solver 옵션은 정상 옵션으로 노출하지 않는다. 버전·도움말은 브라우저나 네트워크 조회를 시작하지 않는다.

## 2. 원격 요청 없는 회귀 검증

```powershell
uv run --locked pytest -q tests/test_selection.py tests/test_service.py tests/test_cli.py tests/test_jungol_dom.py
```

기존 fixture·고정 공급자·로컬 HTML route를 갱신해 검증한다. 기본 테스트는 원격 요청과 기본 브라우저 호출을 차단하며
Chromium이 필요한 DOM 검증만 로컬 HTML을 렌더링한다. 검증을 위해 제품 공개 API를 새로 만들지 않는다.

| 검증 영역 | 최소 입력·상황 | 기대 결과 |
| --- | --- | --- |
| 티어 정상 부재 | 첫/추가 목록의 범위 내·미정·미확인, 두 경계/하한만/상한만 | 수집 계속, 정상 부재는 후보 제외, 범위 내만 결과. 모두 제외되면 정상 0개. |
| 조건 보존 | 다음 링크·더 불러오기에서 티어·unrated·공개 사용자 조건 유지/변조 | 유지 시 전체 처리, 조건 손실 시 실패. |
| 티어 이상 | 범위 밖 확정 티어, 알 수 없는/중복 배지, 필수 구조 누락 | 범위 이탈과 파싱/구조 오류를 구분, 번호·값·범위 또는 지표 진단, 최종 결과 없음. |
| 범위 없는 티어 | Rated/Unrated/Unavailable과 양방향 난이도 정렬 | 정상 상태 모두 포함, 미확정 마지막과 상태 표시 구분. |
| 지표 구분 | 정답·시도·맞힌 사람이 서로 다른 값, 목록 정답률 | 정답만 accepted, 정답률 표시 정밀도 유지, 상세 보충 없음. |
| accepted 파싱 | 0, 정상 쉼표, 명시적 미제공, 빈/누락/중복 셀, 잘못된 쉼표·문자 | 알려진 0·정상 정수·명시적 부재만 수용. 구조·해석 실패를 0/미확인으로 바꾸지 않음. |
| 수치 필터 | 0·9·10·20·21·미제공, 범위 10~20과 한쪽 경계 | 양 끝 포함, 생략 경계 무제한, 미제공 제외 수 일치. 0~0은 실제 0만 포함. |
| 정렬·개수 | 여러 목록의 동점·미확인·중복 ID와 limit=1 | 전체 정렬 후 제한, 최초 ID 관측 유지, 미확인 마지막·동점 번호순. |
| 추천 | 여러 목록, count=1·충분·부족·0개 | 전체 고유 적격 후보를 선택에 전달, 동일 기회·중복 없음, 실제 개수와 안내 일치. |
| 입력 전환 | list/recommend의 옛 최소·최대 옵션, list의 sort solvers | 코드 2·대응 새 옵션·의미 변경 안내, 공급자 생성 0건. |
| 실패·취소 | 미완료 수집·접근 제한·해석 실패·Ctrl+C | 코드 1 또는 130, 일부 최종 결과 없음, 브라우저 정리. |
| 명시적 open | 중복 번호와 일부 전달 실패 | 기존 선택·중복 제거·실패 링크 동작 유지. 조회·추천은 기본 브라우저 호출 0건. |

정답 열의 미제공 표식 검증은 합성 사례다. 실제 사이트에서 관측했다고 기록하지 않는다.
파싱 규칙과 제외 개수의 정확한 의미는 [source 계약](contracts/source.md) 및 [데이터 모델](data-model.md)을 따른다.

### 상세 조회 0건의 독립 확인

공급자 Protocol에서 `read_details`를 삭제한 것만으로 검증을 마치지 않는다.
로컬 다중 목록을 실제 JungolSource로 실행하고 `/problem/<ID>` 문서 요청을 계수한다.
정답 제출 수 조건 없음/있음, list limit=1, recommend count=1, 공개 사용자 조건을 포함한 경우 모두 0건이어야 한다.
서비스 고정 공급자는 `resolve_user`와 `collect`만 제공해도 정상 완료되어야 한다.

## 3. 이전 옵션의 전환 안내

아래 입력은 조회를 시작하지 않고 코드 2와 대응 accepted 옵션·지표 의미 변경을 안내한다.

```powershell
uv run --locked jpick list --min-solvers 1000
uv run --locked jpick recommend --max-solvers 2000
uv run --locked jpick list --sort solvers
```

각 명령은 코드 2로 종료하고 각각 `--min-accepted`, `--max-accepted`, `--sort accepted`를 안내한다.
맞힌 사람 수에서 중복 정답 제출을 포함한 정답 제출 수로 바뀌었음을 설명하며 조회 진행·문제 결과는 출력하지 않는다.
자동 검증에서는 두 범위 옵션을 list/recommend 양쪽에서 확인하고 새 옵션과 섞어도 거부하는지 확인한다.

## 4. 새 사용법의 선택적 라이브 확인

이 단계부터는 실제 공개 사이트에 접근한다. 구현 후 기존 허용 범위와 접근 정책을 다시 확인한 상태에서 필요한 범위만 실행한다.
403·429·로그인 요구·챌린지에서는 중단하고 자동 재시도하지 않는다.

```powershell
# 정답 제출 수 10~10000, 정답률 80% 이상인 전체 후보 중 5개 표시
uv run --locked jpick list --min-tier 1 --max-tier 1 --min-rate 80 --min-accepted 10 --max-accepted 10000 --limit 5

# 정답 제출 수 양방향 정렬
uv run --locked jpick list --min-tier 1 --max-tier 1 --sort accepted --order asc --limit 5
uv run --locked jpick list --min-tier 1 --max-tier 1 --sort accepted --order desc --limit 5

# 지정 공개 사용자의 미풀이 문제 추천: 정답 제출 수는 인원수가 아님
uv run --locked jpick recommend --min-tier 9 --max-tier 14 --min-accepted 1000 --status unsolved --user yookyubin --count 2

# 별도 선택: 출력에서 확인한 문제 번호를 명시해 열기
uv run --locked jpick open 1000
```

결과의 모든 수치 조건과 지정 사용자 풀이 기준을 확인한다. 표 제목은 정답 제출 수여야 한다.
위 번호·사용자는 사용 예시이며 고정 결과·특정 개수 보장이 아니다. 후보 0개·부족은 정상일 수 있다.
count/limit이 작아도 전체 후보를 수집하므로 목록 수집 시간은 남는다.

기존 공개 사용자 집합 검증 도구도 목록 전용 흐름으로 갱신한 뒤 필요할 때 실행한다.

```powershell
uv run --locked python scripts/validate_live.py --user JUNGOL
```

같은 작은 티어·정답률 범위에서 solved/unsolved가 겹치지 않고 합집합이 all인지 확인한다.
조회 사이 통계나 사이트 상태가 바뀔 수 있으므로 불일치를 무조건 사용자 풀이 오류로 단정하지 않고 관측 조건을 기록한다.

## 5. 기존 로컬 처리 벤치

```powershell
uv run --locked python scripts/benchmark_selection.py
```

accepted 모델·필터로 갱신한 뒤 기존 10,000개 로컬 처리 검증을 유지한다.
이 수치는 브라우저·수집 비용을 포함하지 않으므로 SC-008의 변경 전후 수집 성능 증거로 사용하지 않는다.

## 6. 고정 다중 목록의 수집 시간 비교

구현할 `scripts/benchmark_collection.py`의 개발용 실행 계약은 다음과 같다.

```powershell
uv run --locked python scripts/benchmark_collection.py --baseline-ref c37208f5a80628df5d7126972d31461b2517177d --runs 3 --output specs/002-improve-list-collection/collection-benchmark.md
```

도구는 baseline commit을 임시 폴더에 추출하고 현재 소스와 별도 프로세스로 실행한다.
현재 브랜치·작업 파일·staged index는 바꾸지 않는다. 같은 Python 실행 파일과 의존성을 사용하고 실제 import 경로를 검증한다.
fixture와 harness는 현재 검증 도구의 같은 절대 경로를 두 프로세스에 전달한다.
기준 소스에 새 accepted 모델을 요구하는 import를 하지 않는다.

### 입력과 계측

- 고정된 2개 이상의 번호 페이지와 고유 후보 집합을 사용한다. 모든 후보는 정상 확정 티어·정상 수치이며 공개 사용자 조건은 생략한다.
- baseline이 정상 동작할 최소 상세 HTML도 같은 fixture 묶음에 포함한다. 변경 구현에서는 해당 fixture가 요청되면 실패다.
- 허용된 fixture 요청은 로컬로 공급하고 나머지 원격 요청을 차단한다. 실사이트·내부 API 응답을 저장하거나 해독하지 않는다.
- `list --sort id --order asc --limit 1`과 `recommend --count 1`을 각각 변경 전후 최소 3회 실행한다.
  두 지표 조건과 해당 지표 정렬을 생략해 같은 모집단을 비교한다. 추천 난수는 개발 도구 안에서 고정할 수 있다.
- 탐색 간격과 timeout은 양쪽 동일한 제품 기본값으로 유지한다. baseline의 상세 지연만 인위적으로 늘리지 않는다.
- CLI import 후 명령 호출 직전부터 결과 출력과 브라우저 정리 직후까지 전체 시간을 잰다.
  프로세스 시작/import 비용은 제외하고, 브라우저 생성·정리·조회·순수 처리·출력은 포함한다.
- `collect`를 감싼 개발 계측으로 목록 수집 시간을 분리하고 상세 문서 URL 요청을 별도 계수한다.
  계측을 위한 제품 Result 필드·공개 함수는 추가하지 않는다.

### 보고와 판정

보고서에는 환경/Python/브라우저/의존성, baseline/current revision·dirty 여부,
fixture와 harness 해시, 명령, 고유 후보·적격·반환 개수 및 각 실행 원시 수치를 기록한다.

| 명령 | 버전 | 반복 | 고유 관측/적격/반환 | 상세 요청 | 전체 시간 | 목록 수집 시간 |
| --- | --- | --- | --- | --- | --- | --- |
| list / recommend | baseline / current | 1~3 이상 | 실측 | 실측 | 실측 | 실측 |

위 표는 기록 형식이며 측정 결과가 아니다. 각 버전·명령의 전체/목록 시간 중앙값도 남긴다.
SC-008 통과에는 동일한 고유 후보·적격 집합, 양쪽 정상 완료, baseline 상세 요청 양수,
current 상세 요청 0, current 전체 시간 중앙값 감소가 모두 필요하다.
미통과 조건이 있으면 원인과 결과를 기록하고 성공으로 바꾸지 않는다.
이 결과는 로컬 재생에서의 구조적 개선 근거이며 실제 정올의 개선율로 일반화하지 않는다.

## 7. 통합 수용과 결과 기록 (002 최초 검증)

001의 [T041·T042](../001-jungol-problem-picker/tasks.md)는 별도 미완료 작업이다.
요청 완료와 공개 DOM 반영이 분리되는 기존 경계 사례의 수정·검증 결과를 최종 수용 전에 확인한다.
기존 테스트의 요청 완료+버튼 제거 기대를 완전 수집의 충분한 증거로 재사용하지 않는다.
이 선행 문제가 남아 있는 경우 정상 경로·지표 전환 통과와 별개로 해당 통합 수용을 미통과로 기록한다.
002 작업만으로 두 작업을 완료 표시하지 않는다.

구현 후 검증 기록에는 실행 날짜·revision·명령·통과/실패·수치·제약을 추가한다.
다음 표는 002 최초 검증 당시의 상태다. 개별 실행의 revision·명령·수치는 아래 기록과 성능 보고서를, 이후 마감 상태는 [T033 마감](#t033-마감-2026-10-24)을 따른다.

| 항목 | 구현·검증 상태 (2026-10-21) |
| --- | --- |
| 설계와 계약 검토 | 완료. |
| 제품 코드/README/검증 도구 변경 | 002 구현 완료. |
| 최소 회귀·상세 요청 0건 검증 | 219 passed, 알려진 별도 결함 재현 7 xfailed. |
| 변경 전후 시간 비교 | 최종 결과는 [수집 벤치 보고서](collection-benchmark.md)와 T031 기록 참고. |
| 선택적 라이브 수용 | 미실행. |
| T041·T042 관련 통합 수용 | 결함 재현, 미통과. T033 미완료. |

## 구현 실행 기록 (2026-10-21)

- T001: Python 3.12.13, uv 0.11.2, Typer 0.27.3, Rich 15.0.0, Playwright 1.64.0, pytest 9.1.1. 설치된 Chromium 156.0.8078.4 실행 확인. 추가 설치/의존성 변경 없음. 샌드박스의 Python 실행/uv 캐시 접근 문제 때문에 로컬 검증은 승인된 샌드박스 외부 실행을 사용한다.
- 시작 HEAD/baseline: `c37208f5a80628df5d7126972d31461b2517177d`. 브랜치 `002-improve-list-collection`; 시작 dirty 상태는 미추적 `specs/002-improve-list-collection/`만 존재하며 staged 변경 없음.
- T002: baseline commit 존재 확인. 기존 service.py는 전체 목록의 티어/정답률 필터 후 각 후보의 read_details를 호출한다. 기존 detail.html은 `/problem/1000`의 맞힌 사람 5,171을 재생할 수 있어 비교용으로 보존한다. 아직 성능 측정은 수행하지 않았다.
- 설정 확인: Git 저장소이며 Python용 .gitignore에 venv/bytecode/build/test/cache/env/IDE 패턴이 있다. Docker/ESLint/Prettier/npm/Terraform/Helm 설정은 없어 별도 ignore 파일은 불필요하다.
- T003~T009 (US1): 첫/번호 페이지/더 불러오기의 9~14·하한만·상한만 티어, 정상 미정/미확인 보존, 범위 이탈 진단, 누락/중복/알 수 없는 배지, 추가 로드 URL 중복/변조·UI 손실과 공개 사용자 조건을 로컬 재생했다. 신규 테스트의 기존 실패 2건을 먼저 확인한 뒤 수정. `uv run --locked pytest -q tests/test_jungol_dom.py tests/test_selection.py tests/test_service.py`: 99 passed (47.23s). 이후 추가한 모든 티어 제외 조회/추천 검증 `uv run --locked pytest -q tests/test_service.py -k all_unknown`: 2 passed. 전체 수집 후 정상 0개와 미확인 고유 제외 수 1 확인. 순수 티어 필터는 기존 로직 유지. 이 결과는 001/T041·T042 해결 근거가 아니다.
- T010~T023 (US2): accepted 생성/경계 신규 검증의 기존 실패를 확인한 뒤 단일 Problem·Processing·목록 정답 제출 수로 전환했다. `uv run --locked pytest -q tests/test_selection.py tests/test_service.py tests/test_cli.py tests/test_jungol_dom.py --maxfail=3`: 176 passed (61.14s). 실제 JungolSource의 list/recommend·각 1개·다중 목록·accepted 조건 유무·공개 사용자 all/solved/unsolved에서 상세 문서 요청 0건과 컨텍스트의 페이지 1개를 확인했다. `uv run --locked python scripts/benchmark_selection.py`: prepared=10000 eligible=4226 selected=5 seconds=0.006067. 이는 로컬 계산 시간이며 수집 성능이 아니다.
- T022~T023: `uv run --locked python scripts/benchmark_collection.py --runs 1 --output specs/002-improve-list-collection/collection-benchmark-smoke.md`: PASS. 고정 후보 4개로 baseline/current를 별도 프로세스·절대 import 경로에서 실행했다. 상세 요청 baseline 각 4/current 각 0. 시험 1회이므로 SC-008 최종 판정에는 사용하지 않는다. 별도 임시 fixture로 원격 URL route 차단·잘못된 소스 import 거부·상세 요청 위반의 실패 판정도 확인했다. 최종 3회 측정은 T031에 남긴다.
- T024~T029 (US3/정리): 옛 solver 범위 입력의 전환 메시지 부재 실패를 확인한 뒤 숨긴 문자열 거부 callback과 정렬 문자열 입구를 구현했다. `uv run --locked pytest -q tests/test_cli.py`: 48 passed (0.41s). 옛 범위 옵션 두 개/list·recommend/새 옵션 혼용/옛 정렬은 코드 2·대응 옵션·의미 변경 안내·공급자 생성 0건·stdout 무출력을 확인했다. help/version도 생성 0건. `jpick --version`은 0.1.0, 두 명령 도움말은 accepted만 지원한다. open은 테스트의 브라우저 대역만 사용했다. README·002 CLI/source 계약의 조건·정렬·관측·실패 설명을 대조했다.
- T029: src/scripts 검색에서 Candidate/solver_count/details_observed_at/read_details/Enriching/detailed/Presented/filter_solvers 제품 경로 잔재 없음. CLI의 solver 이름은 전용 거부 경로뿐이다. 새 의존성·캐시·조기 종료·부분 결과·내부 API·제품 테스트 전용 공개 API를 추가하지 않았다. origin/목록 경로 검증을 강화했고 누락 문제 셀을 조용히 버리는 경로도 제거했다.

### T032 외부 통합 게이트 평가

001 tasks.md의 T041·T042는 모두 `[ ]`이며 별도 수정/검증 근거가 없다. 이번 작업에서 해당 제품 로직과 001 체크박스를 수정하지 않았다.

| 선행 작업 | 로컬 재현 | 수용 |
| --- | --- | --- |
| 001/T041 | fetch 204 완료 → 버튼 제거 → 400ms 후 행 추가에서 list/recommend가 전체 4개 대신 3개로 성공한다. 빈 최종 요청도 공개 완료 증거 없이 성공한다. | 미통과 |
| 001/T042 | 요청 완료 후 지연되는 최초 검색·페이지 전환에서 이전 사용자 결과를 확정한다. 동일 핸들 갱신과 지연된 빈 결과도 이전 결과를 사용한다. | 미통과 |

`uv run --locked pytest -q tests/test_jungol_dom.py -k known_t04 -rx` 최초 재현: 6 xfailed (4.88s); 지연 빈 결과 1개도 최종 회귀에 포함한다. 이 테스트들은 알려진 범위 밖 결함을 `xfail(strict=True)` 및 구체 예외 타입으로 표시한다. 정상 회귀 통과와 구분하며, 예상 밖 예외/해결 후 XPASS는 테스트 실패가 되어 별도 수용 재검토를 요구한다.

T032는 평가·기록을 마쳤다. FR-012~014 완전성/사용자 확인 통합 수용 및 T033은 미완료다. 기존 요청 완료+버튼 제거 성공 테스트는 충분한 완료 증거로 간주하지 않는다. 고정 대기를 늘려 통과시키지 않았다. 선택적 라이브 검증은 실행하지 않았다.

### 최종 회귀 (T030)

- HEAD `c37208f5a80628df5d7126972d31461b2517177d` + 이 브랜치 작업 파일(dirty), 2026-10-21.
- `uv run --locked pytest -q`: **219 passed, 7 xfailed in 74.18s**. 7개는 위 001/T041·T042의 실제 재현이며 통합 수용 통과로 세지 않는다. 실패/취소 무출력·접근 제한·브라우저 정리·정상 빈 결과와 SC-001~007의 002 정상 경로를 검증했다.
- `uv run --locked python scripts/benchmark_selection.py`: prepared=10000 eligible=4226 selected=5 seconds=0.005141 (Windows 11, Python 3.12.13). 순수 처리 비용만 측정했다.
- 기본 테스트의 원격 사이트 요청/실제 기본 브라우저 전달 없음. 원본 detail.html 및 001 문서는 보존했다.

### 최종 수집 성능 (T031)

`uv run --locked python scripts/benchmark_collection.py --baseline-ref c37208f5a80628df5d7126972d31461b2517177d --runs 3 --output specs/002-improve-list-collection/collection-benchmark.md`: **PASS**.

[최종 보고서](collection-benchmark.md)에 12개 원시 표본·환경·두 revision/dirty·실제 import 경로·fixture/harness/소스 해시·명령·출력을 보존했다. 각 실행의 고유 관측/적격/반환은 4/4/1로 동일하고 baseline 상세 문서 요청은 각 4건, current는 각 0건이었다.

| 명령 | baseline 전체 중앙값 | current 전체 중앙값 | baseline 목록 중앙값 | current 목록 중앙값 |
| --- | ---: | ---: | ---: | ---: |
| list | 5.488668s | 1.575584s | 1.073797s | 1.224385s |
| recommend | 5.474308s | 1.563238s | 1.080322s | 1.211870s |

전체 시간은 감소했고 목록 수집 자체는 매 페이지 UI 재검증으로 소폭 증가했다. 상세 탐색 제거에 따른 로컬 구조 개선의 근거이며 실사이트 개선율을 뜻하지 않는다. 기본 탐색 간격·제한은 변경하지 않았다.

### 요구사항과 남은 수용 조건

| 요구사항/성과 | 근거·판정 |
| --- | --- |
| FR-001~005 / SC-001~002 | 첫/추가 페이지의 티어·필터 보존·정상 부재·구조 진단 회귀 통과. |
| FR-006~010 / SC-003~004 | accepted 파싱·경계·0/미확인·정렬·정밀도·지표 의미 회귀 통과. |
| FR-011 / SC-005 | 실제 목록 전용 경로·상세 문서 0건 회귀 및 최종 벤치 통과. |
| FR-012~014 / SC-006 | 002 정상 경로의 공개 사용자·전체 후보·중복·부족/빈 결과·실패/취소 회귀 통과. 001/T041·T042 지연 DOM 경계의 최종 통합 수용은 미통과. |
| FR-015~018 / SC-007 | 전환 안내·입력 오류의 생성 0건·출력/진행·open 회귀 통과. |
| FR-019 / SC-008 | 같은 후보, 각 3회, 상세 baseline 양수/current 0, 전체 중앙값 감소: PASS. |
| FR-020 | 공개 DOM 경계 유지, 로컬 원격 차단/접근 제한/정리 검증, 새로운 원격 경로 없음. 선택적 라이브 미실행. |

T001~T032 **32개 완료**. T033의 문서 대조·검증 기록은 정리했으나, 작업 정의상 001/T041·T042의 별도 수정·검증이 충족되어야 완료 표시할 수 있으므로 `[ ]`로 유지한다. 새 성능 보고서가 해당 선행 결함의 해결을 의미하지 않는다. 선택적인 사전/사후 Git 커밋 훅은 실행하지 않았다.

## T033 마감 (2026-10-24)

### 검토 기준과 근거

- 브랜치: `003-align-site-listing`. 검토 HEAD: `e9a702a7cf7c333212717b26dade5b95c025e3a2`. 시작 작업 트리는 깨끗했으며 이번 변경은 문서만 포함한다.
- T030: 위 002 실행의 219 passed / 7 xfailed를 보존한다. 7개를 통과로 바꾸지 않고 이후 수정 근거와 구분했다.
- T031: [원본 성능 보고서](collection-benchmark.md)의 12개 표본·revision/dirty·환경·해시·실제 import 경로를 대조했다. list/recommend 각각 baseline/current 3회, 동일 후보 4/4/1, 상세 요청 각 4건/0건이다. 전체 중앙값은 list 5.488668→1.575584초, recommend 5.474308→1.563238초다. 이는 당시 구현의 로컬 재생 결과이며 현재 HEAD의 새 성능 측정이 아니다.
- T032 후속 근거: [001 Phase 9 및 추가 보완 기록](../001-jungol-problem-picker/quickstart.md#phase-9-후속-수정-t041t042-2026-10-21)과 [완료된 T041·T042](../001-jungol-problem-picker/tasks.md#phase-9-convergence)를 확인했다. 최초 수정의 228 passed 이후 추가 경계를 보완한 241 passed, skip/xfail 없음까지 구분했다.
- 현재 정책의 검증: [003 최종 완료 기록](../003-align-site-listing/quickstart.md#최종-완료-상태)의 375 passed, [실사이트 기록](../003-align-site-listing/live-validation-2026-10-24.md)의 세 명령 종료 코드 0·3/3 PASS를 확인했다. 현행 jungol.py·cli.py·models.py·selection.py의 SHA-256은 해당 실사이트 기록의 네 해시와 모두 일치한다.
- 이번 문서 마감에서는 제품 테스트·수집 성능 측정·실사이트 실행을 새로 수행하지 않았다. 002의 선택적 사용자별 라이브 분할 검증은 여전히 미실행이며, 003의 세 명령 수용을 그 검증으로 대신 표시하지 않는다.

### 요구사항·성과와 현재 정책 대조

| 002 요구사항/성과 | 마감 판정과 근거 |
| --- | --- |
| FR-001~002 / SC-001~002의 조건 유지·정상 부재 처리 | 요청 티어·미정 제외·공개 사용자 조건 검증과 정상 미정/미확인 제외를 유지한다. T030 이후 001 수정 및 003의 첫/번호/추가 목록 회귀 근거를 확인했다. |
| FR-003 / SC-001~002의 범위 밖 확정 티어 실패·반환 범위 보장 | 003 FR-001~004·SC-001로 대체됐다. 사이트 결과의 정상 Rated를 보존하므로 옛 실패·제외 기대를 현재 요구로 남기지 않는다. |
| FR-004~005 | 티어 상태·양방향 미확정 마지막 정렬과 구조/파싱 오류 진단을 유지한다. 명시적인 빈 통계를 미제공으로 인정하는 범위는 003 FR-005~008·SC-002~003을 따른다. |
| FR-006~010 / SC-003~004 | 목록 accepted의 의미·경계·0/미제공·양방향 정렬·동점 번호순·정답률 정밀도는 유지한다. 기존 T030·003 회귀와 README/CLI 안내를 대조했다. |
| FR-011 / SC-005 | 목록 전용 단일 Problem·상세 요청 0건을 유지한다. T031 당시 baseline/current 비교와 이후 001·003 회귀 근거를 확인했다. |
| FR-012~014 / SC-006 | 지정 사용자·고유 전체 후보·균등 비복원 추천·부족/0개·실패/취소 결과 금지를 유지한다. T041·T042는 별도 완료됐고 사용자 검색 보호 회귀도 유지한다. 목록 종료 기준은 003 FR-009~013·SC-004~006으로 대체돼 미래 지연 행·버튼의 포함을 보장하지 않는다. |
| FR-015~018 / SC-007 | accepted 옵션·옛 solver 입력 오류 2·의미 변경 안내·관측/진행·종료 코드·명시적 open을 유지한다. 현재 README와 003 CLI 계약/회귀 근거를 대조했다. 실패·취소 누적 개수 보존은 003 범위 밖이다. |
| FR-019 / SC-008 | T031의 원본 보고서가 당시 동일 후보·각 3회·전체/목록 시간 분리·상세 요청 제거·전체 중앙값 감소를 입증한다. 이후 변경의 성능까지 측정한 것으로 해석하지 않는다. |
| FR-020 | 공개 DOM·기존 순차 접근·접근 제한 시 중단·브라우저 정리를 유지한다. 새 원격 경로·캐시·제품 코드를 추가하지 않았다. 선택적 사용자 라이브 미실행은 그대로 기록한다. |

### 완료와 범위

T030·T031의 실제 결과, T032 이후 선행 수정의 완료·검증, 003의 정책 대체와 현재 수용 근거를 대조했다. `plan.md`·`tasks.md`·README에 같은 마감 상태와 근거를 연결했으며 **T033 및 T001~T033 전체를 완료**로 표시한다. 과거 미통과·미실행·성능 기록은 해당 시점의 이력으로 보존한다.

이번 마감은 별도 제품 기능을 추가하지 않는다. IDEA-001 조기 종료, ISSUE-003 진행 개수 동기화와 `solverCount` URL 필터는 포함하지 않는다.
