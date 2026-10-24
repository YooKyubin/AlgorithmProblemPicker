# Quickstart: 003 구현 후 검증 안내

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Contracts**: [source](contracts/source.md)·[cli](contracts/cli.md)

이 문서는 후속 구현의 실행·수용 안내다. 아래 명령의 통과를 이번 계획 단계에서 확인한 것은 아니다.  
합성 회귀, 실제 사이트 수용, 과거 001·002 실행 기록을 구분한다.

## 준비

Windows/PowerShell에서 저장소 루트와 `003-align-site-listing` 브랜치를 확인한다. Python 3.12 이상·uv·잠금 의존성과 Playwright Chromium이 필요하다.

```powershell
Set-Location '.'
git branch --show-current
uv sync --locked --python 3.12
uv run --locked playwright install chromium
uv run --locked jpick --help
```

이미 의존성과 브라우저가 준비돼 있으면 설치를 반복할 필요는 없다. 새 의존성이나 잠금 파일 갱신을 이 기능의 선행 작업으로 두지 않는다.  
샌드박스의 uv 캐시·브라우저 실행 제한은 환경 문제로 따로 기록한다. 설치된 동일 가상환경을 직접 사용한 경우 명령·실행 경로도 기록한다.

```powershell
.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider
```

## 1. 정책 전환의 최소 회귀

구현 전에는 새 기대가 기존 정책 때문에 실패하는 경계를 확인하고, 구현 후 아래 모듈을 검증한다. 기본 테스트는 로컬 HTML과 고정 공급자를 사용하며 원격 요청·실제 기본 브라우저 열기를 차단한다.

```powershell
uv run --locked pytest -q tests/test_jungol_dom.py tests/test_selection.py tests/test_service.py tests/test_cli.py
```

| 범위 | 확인할 결과 |
| --- | --- |
| 티어 최초·번호 페이지·더 불러오기, 양쪽·한쪽 경계 | 정상 범위 밖 Rated 보존, 표시값 유지, 다른 수치 조건 적용. 티어 차이만의 실패·제외·경고 없음. |
| 요청·배지 검증 | URL/UI 조건 손실·배지 오류는 계속 실패. 정상 미정·미확인 티어 정책 유지. |
| 정답·정답률의 명시적 빈 표시 | 첫·추가 목록 모두 Unavailable로 수집. 기존 정답률 빈 링크 지원 유지. |
| 숫자·오류 경계 | 실제 0/0~0과 미제공 구분. 임시 빈 값은 이후 실제 값을 읽고, 셀 누락·중복·잘못된 숫자는 오류. 빈 마커로 오류를 숨기지 않음. |
| 필터·표시 | 필터 없는 미제공은 포함 가능·미확인 표시. 활성 필터는 고유 문제당 한 번 제외. 모두 제외해도 정상 0개·부족 안내. |
| 더 불러오기 종료 | 버튼 있음은 계속 수집. 버튼 없음은 읽을 수 있는 현재 목록으로 완료. 새 행 없음·별도 알림 없음도 같은 기준. |
| 대기 재진입 방지 | 최종 버튼 부재 경로가 목록 busy·pending·이중 스냅샷·외부 루프의 일반 재대기로 다시 막히지 않음. |
| 보호 경계 | 다음 번호 링크·반복 페이지·중복 컨트롤·버튼 유지 진행 없음·접근 오류·실패/취소 처리 유지. |
| 보존 경계 | 사용자 검색의 의미 있는 결과 반영·지연·동일 핸들·관찰자 정리와 Ctrl+C 원예외 보존. |
| 고유 후보와 선택 | 최초 관측·중복 제거·동점/미확정 정렬·표시/추천 1개·전체 적격 후보 선택 유지. 상세 문서 요청 0건. |

### 과거 기대를 바꿀 사례

- `test_rated_outside_range_has_diagnostics`는 티어 차이로 실패하는 기대를 보존 성공으로 바꾸고 이름도 새 정책에 맞춘다. UI 손실·배지 오류 테스트와 섞지 않는다.
- `test_default_id_order_and_one_sided_bounds`의 정상 Rated 제외 기대를 보존으로 바꾼다.
- `test_unknown_count_stops_at_first_active_filter`의 현재 자료는 Rated가 수치 필터에 도달하면서 미확인 제외 수가 2→3으로 바뀐다. 정상 미정·미확인만 있는 서비스 사례의 적격 0·미확인 제외 1은 유지한다.
- `test_cursor_disappears_before_delayed_rows`, `test_cursor_disappears_without_completion_evidence`, `test_cursor_empty_request_needs_public_completion`과 관련 T041 사례는 버튼 부재 시 현재 목록 성공으로 전환한다.
- `test_t041_rows_before_next_control_do_not_finish_collection` 등은 미래 버튼·행을 반드시 포함하는 기대를 제거한다. 버튼 부재를 평가하는 시점의 현재 목록을 결정적으로 제어하고 고정 sleep·실행 속도에 따른 후보 수를 정답으로 삼지 않는다.
- `test_unrelated_loading_cycle_is_not_result_completion`은 listing과 user 분기를 새 범위에 맞게 분리한다. listing은 버튼 부재 현재 목록 성공, user는 기존 결과 완료 검증을 유지한다.
- 목록 관찰자 정리 실패 분기는 삭제된 수명에 맞춰 정리하고 추가 로드 대기 중 취소 전파를 확인한다. 사용자 관찰자 정리 실패 분기는 유지한다.

테스트를 삭제·skip/xfail 처리해 반대 정책을 숨기지 않는다. 바뀐 기대와 유지하는 오류 경계를 함께 기록한다.  
실패·취소 시 최종 표·추천 결과가 없는지는 검증하지만 누적 개수 보존을 통과 조건으로 추가하지 않는다.

## 2. 전체 회귀와 안내

관련 검증 통과 후 전체 회귀와 명령 도움말을 확인한다. 새 변경·실패가 없으면 동일 검증을 반복하지 않는다.

```powershell
uv run --locked pytest -q
uv run --locked jpick list --help
uv run --locked jpick recommend --help
```

README·도움말·조건 출력이 [CLI 계약](contracts/cli.md)과 일치해야 한다. 티어 조건의 사이트 검색 의미, 미제공과 0, 버튼 부재 종료를 확인한다.  
기존 solver 입력 오류·사용자 조건·기본값·정렬·종료 코드·명시적 open 회귀는 유지한다. 과거 성능 보고서를 003의 새 성능 측정으로 표시하지 않는다.

## 3. 실사이트 수용

로컬 회귀를 마친 뒤 원문 세 명령을 실제 사이트에서 실행한다. 아래는 SC-007의 후속 수용 항목이며 이번 계획에서 실행하지 않았다.

```powershell
uv run --locked jpick recommend --min-tier 9 --max-tier 13 --count 2
uv run --locked jpick recommend --min-tier 9 --max-tier 10 --count 2
uv run --locked jpick list --min-tier 1 --max-tier 1 --sort accepted --order desc --limit 5
```

| 명령 | 기대 결과 |
| --- | --- |
| 티어 9~13 추천 | 사이트 목록의 정상 범위 밖 티어 때문에 실패하지 않음. 해당 문제는 적격 후보에 포함 가능하며 무작위 결과에 반드시 뽑힐 필요는 없음. 표시 티어 보정 없음. |
| 티어 9~10 추천 | 명시적 빈 통계를 수집 가능. 계속되는 목록은 진행하고 버튼 부재 시 현재 목록으로 완료. |
| 티어 1·accepted 내림차순·5개 | 빈 통계를 미제공으로 구분하고 정상 완료 후 전체 적격 후보를 정렬·제한. 미확인 마지막·동점 번호순. |

사이트가 정상 접근 가능한 경우 코드 0으로 실제 결과 또는 정상적인 결과 없음을 제공해야 한다. 실패·취소 시 최종 결과 미제공은 그대로 적용한다.  
2026-10-21의 문제·통계·550/200/100개 로그·250/134개 관측을 고정 기대값으로 쓰지 않는다. 사이트 장애·접근 제한과 제품 결함은 원시 진단으로 구분해 기록하고 실패·미실행을 통과로 표시하지 않는다.

각 실행의 명령, 실행 시각(Asia/Seoul), revision/dirty 상태, 환경, 종료 코드, 수집·적격·반환 개수, 표시 정책과 오류 유무를 기록한다. 실패·취소의 누적 수집 개수 일치는 별도 수용 조건으로 두지 않는다.  
버튼 제거 후 지연 반영이 실사이트에서 새로 관측되면 순서·재현 조건을 기록해 후속 정책 보완 근거로 남긴다. 관측 전에 완료 조건을 다시 복잡하게 바꾸지 않는다.

## 실행 기록 상태

| 항목 | 2026-10-22 계획 단계 상태 |
| --- | --- |
| 현재 코드·기존 관측 자료 조사 | 완료. 읽기 전용 연구 결과를 research.md에 통합. |
| Phase 0·Phase 1 설계·헌장 정합성 | 문서 작성·검토 완료. 영구 캐시 범위 예외 명시. |
| 제품 구현·정책 전환 회귀·전체 회귀 | 미실행. 후속 구현 작업. |
| 원문 세 명령의 실사이트 수용 | 미실행. SC-007 통과 근거 없음. |
| 제품 변경 성능 측정 | 미실행. 이번 기능에 새 성능 개선 목표를 추가하지 않음. |

실제 구현 후 이 기록에 실행 명령·판정·근거를 추가한다. 명세 품질 체크리스트와 설계 게이트의 완료를 구현 완료로 해석하지 않는다.

## 2026-10-24: US1 구현 기록 (T001~T011)

이번 실행 범위는 T011까지다. US2의 새 빈 통계와 US3의 버튼 부재 완료 정책, 최종 README 정리·전체 수용은 후속 작업이다.

### T001: 시작 상태와 환경

- 브랜치: `003-align-site-listing`. 시작 HEAD: `0c1565b86bd44f546a2e1954c8653762c24428e4`.
- 시작 dirty: README.md, specs/001-jungol-problem-picker/{quickstart,tasks}.md, specs/002-improve-list-collection/quickstart.md, src/algorithm_problem_picker/jungol.py, tests/test_jungol_dom.py가 수정돼 있었다. specs/002-improve-list-collection/post-implementation-issues.md와 specs/003-align-site-listing/은 untracked였다. 기존 변경을 보존한다.
- `.venv\Scripts\python.exe`: Python 3.12.13. Playwright 1.64.0, Typer 0.27.3, Rich 15.0.0, pytest 9.1.1, uv 0.11.2. 기존 잠금 의존성을 사용하며 재설치·lock 갱신은 하지 않았다.
- Chromium: `%LOCALAPPDATA%/ms-playwright/chromium-1248/chrome-win64/chrome.exe`. 설치된 브라우저의 headless 실행·종료 확인 PASS, 외부 사이트 요청 없음.
- 샌드박스 안의 Playwright driver 시작이 반환되지 않아 중단했다. 같은 환경의 샌드박스 밖 실행에서는 정상 시작·종료했다. DOM 회귀는 이 환경에서 로컬 route로 실행하고, 순수/CLI 회귀는 기존 가상환경을 직접 사용한다.
- `.gitignore`의 `.venv/`, `__pycache__/`, `*.py[cod]`, pytest/coverage, build/dist, egg-info, 환경 파일·편집기 임시 파일 제외를 확인했다. 다른 기술용 ignore 파일은 필요 없다.
- `check-prerequisites.ps1 -Json -RequireTasks -IncludeTasks`가 이 기능 경로를 반환했다. requirements.md는 16/16 checked이며 체크리스트는 수정하지 않았다.

### T002~T003: 유지할 경계와 재생 자료

- models.py의 Rated 1~30 정수(bool 제외), 정답 제출 수 0 이상 정수(bool 제외), 유한 Decimal 정답률 0~100, 각 경계의 하한≤상한, 공개 사용자 조건·@ 한 개 정규화가 이미 검증된다. 이 검증은 유지한다.
- Problem의 양의 ID·비어 있지 않은 제목·ID와 일치하는 URL·세 티어 상태·Known/Unavailable 통계·시간대 있는 listed_at, UserReference의 정확한 핸들·양의 account_id·시간대 있는 resolved_at을 유지한다. 새 타입·공개 API는 추가하지 않는다.
- ports.py의 resolve_user/collect Protocol을 유지한다. service.py는 CompletedListing 성공 후에만 Processing→필터→정렬/추첨→Result로 진행하며 실패·취소에서 최종 결과를 만들지 않는다. 모델·서비스를 새로 구현하지 않는다.
- `tests/fixtures/jungol/site-listing.html`에 Rated 8/10/13과 정상 통계·실제 0, 요청 URL에 대응하는 공개 필터 UI를 추가했다. 고정 번호·수치는 합성 자료다. 기존 정상 미정/미확인·빈 결과·사용자 fixture는 보존했다.

### T004~T007: 제품 변경 전 새 기대 확인

```powershell
.venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider tests/test_jungol_dom.py tests/test_selection.py tests/test_service.py tests/test_cli.py -k 'rated_site or all_rated_outside or tier_help or site_tier_bounds or default_id_order_and_one_sided_bounds or unknown_count_stops_at_first_active_filter' --tb=short
```

샌드박스 밖 실행: **41 failed, 2 passed, 236 deselected (11.45s)**. 수집기의 범위 밖 Rated `SourceAccessError`, 순수 필터의 범위 재비교·미확인 제외 수, 서비스/CLI의 적격 0, 도움말 의미 누락으로 실패했다. 기존 정책에서도 다른 수치 조건이 같은 후보를 제외하는 2개 사례는 이미 통과했다. 새 실패를 숨기는 skip/xfail은 추가하지 않았다.

- DOM: list/recommend × 최초/번호/추가 목록 × 양쪽/하한만/상한만의 18개 조합. 기존 완료 신호를 제공해 US3와 분리한다.
- 순수 필터: 실제 티어 보존·정답률/정답 제출 수 조건·실제 난이도 양방향 정렬. 앞 필터 탈락과 정상 미정/미확인 정책은 기존 회귀를 유지한다.
- 서비스: 모든 Rated가 범위 밖인 양쪽/한쪽 경계에서 실제 전체 모집단과 limit/count=1, 고유 최초 관측·개수·티어를 검증한다.
- CLI: 요청 경계와 표시 티어 8, 경고 부재·공급자 정리, 사이트 검색 조건 도움말을 검증한다.

### T008~T010: US1 제품 변경

- jungol.py의 `_collect`에서 정상 Rated와 요청 티어 범위를 비교해 실패시키던 분기만 제거했다. URL/UI·사용자 조건 확인과 배지/행/통계 파싱, 기존 로드·종료 대기는 유지했다.
- selection.py에서 Rated의 로컬 티어 범위 비교만 제거했다. 정상 미정·미확인 티어 정책과 정답률→정답 제출 수 필터, 미확인 제외 수·정렬·추첨은 유지했다.
- cli.py의 TierOption과 list/recommend 도움말에 사이트 검색 조건 의미와 표시 티어가 범위 밖일 수 있음을 반영했다. 요청 경계·표시 티어 출력, 기존 옵션·기본값·종료 코드와 출력 채널은 유지했다.

### T011: 변경 후 검증

아래 명령은 기존 가상환경으로 실행했다. DOM 테스트는 샌드박스 밖에서 설치된 Chromium을 사용하며 fixture의 로컬 route가 원격 요청을 차단한다. CLI 테스트는 고정 공급자를 사용하고 실제 기본 브라우저 호출을 차단한다.

```powershell
.venv/Scripts/python.exe -X utf8 -B -m pytest -q -p no:cacheprovider tests/test_selection.py tests/test_service.py tests/test_cli.py
.venv/Scripts/python.exe -X utf8 -B -m pytest -q -p no:cacheprovider tests/test_cli.py
.venv/Scripts/python.exe -X utf8 -B -m pytest -q -p no:cacheprovider tests/test_jungol_dom.py -k 'rated_site or tier or filters or filter_not_applied or actual_picker or next_page_and_duplicate_first_record or cleanup_on_failure_and_cancel or schema_change_not_unknown'
```

| 실행 | 결과 | 판정·후속 조치 |
| --- | --- | --- |
| 순수 필터·서비스·CLI 초기 검증 | 134 passed, 6 failed (1.53s) | 필터·서비스 84개와 기존/도움말 CLI 50개 통과. 새 CLI 6개는 정상 결과를 얻었으나 Rich 표의 앞쪽 공백을 고려하지 못한 테스트 행 탐색에서 실패했다. 테스트에서 lstrip으로 행을 찾도록 수정했으며 제품 표시 코드는 바꾸지 않았다. |
| CLI 재검증 | 56 passed (0.55s) | 수정한 6개를 포함해 모두 통과. 실제 티어 8·요청 조건·경고 부재·도움말과 기존 입력 오류/solver/open/실패·취소 회귀 확인. |
| US1 관련 DOM 및 보호 경계 | 68 passed, 71 deselected (45.67s) | 최초/번호/추가 목록의 조회·추천 18개 조합, 정상 미정·미확인, 요청 URL/UI/사용자 필터 손실, 배지/구조 오류, 고유 최초 관측·목록 전용 요청·브라우저 정리 확인. |

최종적으로 US1 관련 고유 **208개 사례**가 통과했다(순수 필터·서비스 84 + CLI 56 + DOM 68). 위 초기 검증에서 통과한 순수/서비스 코드는 이후 변경하지 않았다. `git diff --check`도 통과했다. 검증 revision은 시작 HEAD와 같고 작업 트리는 dirty다. 이번 제품 변경은 jungol.py·selection.py·cli.py이며 회귀 네 파일·새 site-listing.html과 이 기능의 tasks.md/quickstart.md를 갱신했다. 기존 사용자 변경·체크리스트·과거 실행 기록은 보존했다.

T001~T011을 완료 표시한다. **T012~T030은 미완료**이며 다음을 이번 통과 근거로 해석하지 않는다.

- US2의 명시적 빈 통계는 아직 미지원이다. 새 data-col-empty 준비/파싱 회귀와 제품 전환은 T012~T019에서 수행한다. 이번 정상 수치 fixture의 통과가 빈 통계 지원을 뜻하지 않는다.
- US3의 버튼 부재 현재 목록 완료는 아직 미구현이다. 기존 목록 관찰자·일반 재대기와 T041의 반대 기대는 T020~T026에서 함께 전환한다. 이번 DOM 검증의 71개 제외는 실행 범위를 나눈 것이며 테스트 skip/xfail 표시는 추가하지 않았다.
- README의 과거 티어·통계·종료 정책 설명은 T027에서 정리한다. CLI의 나머지 정책 안내 정합성, 최종 전체 회귀(T029)와 실사이트 세 명령(T030)은 미실행이다. SC-007 및 전체 기능 수용 완료를 주장하지 않는다.

## 2026-10-24: US2 구현 기록 (T012~T019)

이 기록은 앞선 US1 완료 시점의 US2 미구현 상태를 갱신한다. 실행 범위는 T019까지이며 US3 및 T027~T030은 후속 작업이다.

### 시작 상태와 유지할 범위

- 브랜치 `003-align-site-listing`, HEAD `0c1565b86bd44f546a2e1954c8653762c24428e4`, 기존 사용자 변경과 US1 구현이 있는 dirty 작업 트리에서 진행했다. 기존 변경을 보존하고 커밋하지 않았다.
- Python 3.12.13, Playwright 1.64.0, Typer 0.27.3, Rich 15.0.0, pytest 9.1.1의 기존 가상환경과 설치된 Chromium을 사용했다. 의존성·lock·ignore 파일의 변경은 필요하지 않았다.
- prerequisites가 현재 기능 경로와 tasks.md를 확인했고 requirements.md는 16/16 checked였다. 체크리스트는 수정하지 않았다.
- 이번 제품 변경은 jungol.py에 한정한다. 기존 모델·Protocol·순수 필터·정렬·서비스·CLI의 Unavailable 처리와 수집 종료 정책은 유지한다.

### T012~T016: 제품 변경 전 검증

```powershell
.venv/Scripts/python.exe -X utf8 -B -m pytest -q -p no:cacheprovider tests/test_selection.py tests/test_service.py tests/test_cli.py -k 'missing_statistic or missing_statistics or zero_and_missing or numeric_rejection'
.venv/Scripts/python.exe -X utf8 -B -m pytest -q -p no:cacheprovider tests/test_jungol_dom.py -k 'explicit_empty_statistics or empty_marker_keeps or rate_unavailable_tokens or unmarked_empty_statistic or invalid_marked_statistic' --tb=line
.venv/Scripts/python.exe -X utf8 -B -m pytest -q -p no:cacheprovider tests/test_jungol_dom.py -k 'empty_statistics_listing_reaches' --tb=line
```

| 범위 | 구현 전 결과 | 확인 내용 |
| --- | --- | --- |
| 필터·서비스·CLI 새 회귀 | 31 passed, 140 deselected (0.34s) | 기존 Unavailable 경계로 수치 최소/최대/0~0·미확인 표시·고유 제외 수·정상 0개/추천 부족을 처리할 수 있다. 해당 제품 계층은 수정하지 않는다. |
| 통계 DOM 새 회귀 | 18 failed, 25 passed, 139 deselected (29.95s) | 빈 정답/정답률의 명시적 표시를 무시해 실패했다. 임시 빈 정답률을 기다리지 않는 경로와 추가 목록의 셀 누락/중복 진단 부족도 확인했다. 정상 수치·기존 토큰·마커로 숨기면 안 되는 오류 경계는 이미 통과했다. |
| 실제 공급자→Picker 결합 | 2 failed, 182 deselected (2.40s) | 추가 목록의 빈 통계 때문에 준비가 끝나지 않아 로컬 수치 필터에 도달하지 못했다. |

테스트는 기존 site-listing.html을 필요한 셀만 변형해 재생한다. 첫 목록/추가 목록에서 정답만·정답률만·둘 모두의 빈 표시, 빈 속성값과 값이 "false"인 속성의 존재, 정상 0/정수/천 단위 구분/소수 정밀도와 기존 미제공 토큰을 확인한다. 마커 없는 임시 값의 채움은 기존 50ms 확인 루프의 세 번째 확인 시점에 명시적으로 수행해 실제 값 준비 전에 파싱하지 않는지 검증한다. 제품에 새 고정 대기를 추가하지 않는다.

추가 로드 fixture에는 기존 공개 완료 신호를 제공해 US3 종료 전환과 분리했다. 원격 요청·실제 기본 브라우저 호출은 차단하며 skip/xfail로 새 기대를 숨기지 않았다.

### T017~T018: 구현

- `_SNAPSHOT`에 rateEmpty/acceptedEmpty boolean 배열을 추가했다. 텍스트와 빈 표시는 동일한 셀 목록에서 같은 순서로 읽고 `hasAttribute('data-col-empty')`로 속성 존재를 판별한다. 비어 있지 않은 숫자/토큰을 빈 표시로 덮어쓰지 않는다.
- 비공개 `_empty_statistic`을 준비 판정과 `_problem`에서 공유한다. 셀 정확히 1개·trim 빈 텍스트·해당 셀의 빈 표시를 함께 요구하며, 기존 같은 문제의 빈 정답률 링크 예외만 유지한다. 정답의 빈 앵커로 예외를 확대하지 않는다.
- 마커 없는 임시 빈 정답/정답률은 기존 제한 안에서 기다린다. 준비 실패는 오류로 남기며 미제공이나 0으로 바꾸지 않는다. 기존 공개 로딩/pending/disabled·snapshot 안정성·추가 로드 완료 근거는 유지한다.
- 추가 목록의 준비 제한에 도달한 경우에도 통계 셀 누락/중복은 기존 행 파서로 문제 번호·지표를 담은 SourceSchemaError를 제공한다. 임시 빈 값의 추가 준비 실패는 SourceCompletenessError로 유지한다. 잘못된 비어 있지 않은 수치는 빈 표시가 있어도 실패한다.

### T019: 구현 후 회귀 결과

```powershell
.venv/Scripts/python.exe -X utf8 -B -m pytest -q -p no:cacheprovider tests/test_selection.py tests/test_service.py tests/test_cli.py
.venv/Scripts/python.exe -X utf8 -B -m pytest -q -p no:cacheprovider tests/test_jungol_dom.py -k 'statistic or accepted or rate or tier or filters or filter_not_applied or actual_picker or next_page_and_duplicate_first_record or cleanup_on_failure_and_cancel or schema_change_not_unknown or list_distinct_metrics or partial_hydration or missing_problem_cell or empty_vs_temporarily_empty'
```

| 실행 | 결과 |
| --- | --- |
| 순수 필터·서비스·CLI | **171 passed (0.64s)** |
| US1/US2 DOM 및 보호 경계 | **138 passed, 46 deselected (89.72s)** |
| `git diff --check` | PASS |

총 **309개**가 통과했다. DOM 실행은 기존과 같이 샌드박스 밖 Chromium·로컬 HTML을 사용했다. 새로운 45개 DOM 사례를 모두 포함하며 나머지는 기존 통계·미정/미확인 티어·조건 손실·배지/행 오류·고유 관측·상세 요청 0건·브라우저 정리 경계를 확인한다.

범위 밖 Rated 8의 추가 목록 문제에서 두 통계가 명시적 미제공일 때도 정상 수집 후 수치 필터까지 도달함을 실제 JungolSource→Picker의 list/recommend로 검증했다. 수집 6·적격 2·반환 1·미확인 제외 1이며 실제 0인 문제만 0 조건을 통과한다. 합성 자료의 개수이며 실사이트 기대값이 아니다.

**T012~T019 완료**. 검증 revision은 시작 HEAD와 같으며 dirty 상태다. 이번 변경 파일은 jungol.py·테스트 네 파일과 이 기능의 tasks.md/quickstart.md다. 새 의존성·모델·공개 API·진행 정보·제품 옵션은 추가하지 않았다.

**T020~T030은 미완료**다. US3의 버튼 부재 현재 목록 완료·목록 관찰자 제거·외부 일반 재대기 제거와 관련 T041 기대 전환은 아직 적용하지 않았다. 이번 DOM 실행의 46개 제외는 US3·사용자 검색 등 실행 범위 밖의 사례이며 테스트 skip/xfail 표시는 추가하지 않았다. 사용자 검색·번호 페이지 정책은 유지한다. README/나머지 도움말 정리, 최종 전체 회귀와 실사이트 세 명령 수용은 미실행이며 SC-007 완료를 주장하지 않는다.

## 2026-10-24: US3와 최종 검증 (T020~T030)

이 실행은 앞선 US2 시점의 미완료 상태를 갱신한다. 시작 브랜치·HEAD는 `003-align-site-listing`·`0c1565b86bd44f546a2e1954c8653762c24428e4`이며 기존 사용자 변경과 US1/US2가 있는 dirty 상태를 보존했다. Python 3.12.13·기존 uv 잠금 의존성과 설치된 Chromium을 사용한다. requirements.md는 16/16 checked이고 체크리스트·과거 실행 기록은 수정하지 않았다.

### T020~T023: 정책 전환과 보호 테스트

```powershell
.venv/Scripts/python.exe -X utf8 -B -m pytest -q -p no:cacheprovider tests/test_service.py tests/test_cli.py
.venv/Scripts/python.exe -X utf8 -B -m pytest -q -p no:cacheprovider tests/test_jungol_dom.py -k 'cursor or t041 or cancel_during_load or duplicate_controls or final_empty_current or invalid_current or retained_cursor or unrelated_loading' --tb=line
.venv/Scripts/python.exe -X utf8 -B -m pytest -q -p no:cacheprovider tests/test_jungol_dom.py -k 'one_current_snapshot' --tb=line
```

- 서비스·CLI는 **104 passed (0.61s)**. 정상 완료 Result 불변식과 접근/구조/진행 실패·취소의 stdout 무출력·브라우저 정리를 보강했다.
- DOM 초기 실행은 **22 failed, 7 passed, 167 deselected (23.91s)**. 기존 완료 알림·중복 일반 대기·목록 관찰자 때문에 새 기대가 실패했다. 이 중 보류 요청 테스트 하나는 Playwright가 내장 list.append 콜백을 직접 받을 수 없어 생긴 테스트 설정 오류였다. lambda로 수정 후 해당 사례를 다시 실행해 **1 failed, 195 deselected (1.09s)**의 실제 준비 시간 초과를 확인했다.
- 과거 지연 행/다음 버튼 테스트는 완료 후 `fixture-finish` 이벤트를 보내 미래 DOM을 반영하도록 바꿨다. 결과를 받기 전에 임의 sleep·실행 속도로 3/4/5개를 맞추지 않는다. 별도 완료 알림 유무와 무관한 현재 목록 성공을 검증하고 skip/xfail로 반대 기대를 숨기지 않았다.
- 버튼 유지·disabled/로딩·진행 없음, 최종 새 행 없음/빈 검색 결과·누적 후보 보존, 중복 컨트롤, 잘못된 현재 목록·접근 오류, 원래 KeyboardInterrupt 전파를 확인한다. 사용자 검색은 기존 지연·동일 핸들·장식 변경·관찰자 정리 검증을 유지한다.

### T024~T026: 구현과 스토리 회귀

- `_wait_listing(previous)`의 클릭 후 모드에서 접근/중복 컨트롤 검증 후 컨트롤 부재와 읽을 수 있는 현재 목록을 일반 guard보다 먼저 평가한다. 이 경로는 pending·목록 busy 해제·추가 알림·동일 스냅샷 두 번·새 ID를 완료 증거로 요구하지 않는다. 임시 빈 통계와 깨진 행은 정상 결과로 바꾸지 않는다.
- 버튼이 남아 있으면 기존 준비 조건·새 ID 진행·제한을 유지한다. 다음 번호 링크가 있으면 해당 페이지 분기로 이동하며 origin/경로·반복 URL·새 ID 검증은 유지한다.
- `_LIST_UPDATE`·목록 update 인수/관찰자 수명을 제거하고 `_load_more`를 클릭→대기로 단순화했다. `_collect`는 각 로드가 반환한 snapshot을 재사용하고 URL/UI·관측 접근 오류를 확인한다. `_USER_UPDATE`·JSHandle·사용자 관찰자와 브라우저 정리는 유지한다. CompletedListing 주석만 새 완료 의미에 맞췄다.
- 보류된 관련 요청과 busy 표시가 있어도 버튼 부재에서 현재 스냅샷을 한 번만 읽어 완료하는 사례를 추가했다. 버튼이 계속 남는 두 번의 로드에서는 limit/count=1이어도 고유 5개를 모두 수집하고 최초 관측·전체 정렬/추첨·문서 요청 1건(목록만)을 확인했다.

```powershell
.venv/Scripts/python.exe -X utf8 -B -m pytest -q -p no:cacheprovider tests/test_jungol_dom.py -k 'cursor or t041 or cancel_during_load or duplicate_controls or final_empty_current or invalid_current or retained_cursor or unrelated_loading or t042 or user_cancel or filters' --tb=short
```

스토리 회귀는 **62 passed, 134 deselected (42.85s)**. 이후 더 불러오기→번호 페이지의 정상/새 ID 없음/반복/다른 origin 4개 사례를 추가해 최종 전체 회귀에 포함한다. 테스트는 샌드박스 밖 Chromium과 로컬 route로 수행하며 원격 요청·실제 기본 브라우저 호출을 차단한다.

### T027~T029: 문서·도움말·도구 검토

README의 범위 밖 티어 실패·빈 셀 일괄 오류·목록의 별도 종료 알림 필수 설명을 새 정책으로 전환했다. 명시적 빈 통계와 실제 0·필터 유무·고유 제외 수, 버튼 부재 현재 목록 완료와 미래 지연 반영 한계, 사용자 검색의 기존 정책을 구분한다. 001/002는 과거 정책의 검증·성능 이력이며 이번 수용 근거로 재사용하지 않는다.

list/recommend 도움말은 티어 의미 외에 두 명령이 공유하는 안내로 빈 통계·0·필터·버튼 부재 종료를 설명한다. 새 옵션·경고·동의 흐름은 추가하지 않았다. 두 명령의 실제 `--help` 실행은 종료 코드 0이며 CLI 회귀에서도 안내 내용을 확인한다.

기존 validate_live.py·benchmark_selection.py·benchmark_collection.py의 모델·Protocol 사용과 문법을 검토했다. 공개 경계를 변경하지 않아 도구 수정은 필요하지 않았다. 별도 사용자 라이브 분할 검증·새 벤치 목표/성능 측정은 추가하지 않았다.

```powershell
uv run --locked pytest -q
uv run --locked jpick list --help
uv run --locked jpick recommend --help
git diff --check
```

최종 로컬 검증: **375 passed (127.55s)**, skip/xfail 없음. 실제 두 도움말 명령도 종료 코드 0, 변경 형식 검사 PASS다. 이전 단계에서 제외했던 US3·사용자 검색을 포함한 전체 회귀이며 새 제품 변경 없이 반복 실행하지 않았다. 실행은 동일 잠금 환경·dirty 작업 트리, Playwright 테스트는 샌드박스 밖에서 수행했다.

T020~T029를 완료했다. 원문 세 명령의 실제 상태는 아래 T030 기록으로 별도 판정한다.

### T030: 실사이트 수용

로컬 전체 회귀 통과 후 원문 세 명령을 실제 사이트에서 순차 실행했다. 각 실행의 정확한 명령·시작/종료 시각(Asia/Seoul)·환경·revision/dirty·제품 SHA-256·stdout/stderr 원문은 [실사이트 수용 기록](live-validation-2026-10-24.md)에 보존한다. 개발 검증 기록이며 다음 제품 실행용 캐시·HAR·브라우저 상태가 아니다.

| 명령 | 실행 시각(Asia/Seoul) | 종료 코드 | 수집 / 적격 / 반환 | 판정 |
| --- | --- | --- | --- | --- |
| `uv run --locked jpick recommend --min-tier 9 --max-tier 13 --count 2` | 2026-10-24 14:07:11~14:07:35 | 0 | 761 / 761 / 2 | PASS. 새 정책으로 정상 추천·부족 0. |
| `uv run --locked jpick recommend --min-tier 9 --max-tier 10 --count 2` | 2026-10-24 14:07:35~14:07:42 | 0 | 277 / 277 / 2 | PASS. 정상 추천·부족 0. 반환한 13736번에서 정답률 미확인과 정답 제출 수 0을 구분해 표시. |
| `uv run --locked jpick list --min-tier 1 --max-tier 1 --sort accepted --order desc --limit 5` | 2026-10-24 14:07:42~14:07:47 | 0 | 136 / 136 / 5 | PASS. 정답 제출 수 8917→7194→6542→6315→4793으로 내림차순 표시. |

세 실행 모두 정상 접근·Collecting→Processing→Complete이며 실패·취소·추가 경고 없이 최종 결과를 출력했다. 과거 550/200/100·250/134개를 기대값으로 사용하지 않았다. 무작위 추천에서 범위 밖 특정 문제가 반드시 뽑힐 것을 요구하지 않으며 티어 보존·양방향 미확인 마지막·동점 번호순 등 결정적 경계는 로컬 회귀로 검증했다.

이 실행에서 버튼 제거 뒤 늦게 반영되는 추가 결과의 재현을 새로 입증한 것은 아니다. 현재 종료 기준으로 정상 완료했으며 사이트 전체 누락·미래 반영 복구나 새 성능 개선율을 주장하지 않는다.

### 최종 완료 상태

**T001~T030 모두 완료**, 전체 회귀 **375 passed**, 실사이트 수용 **3/3 PASS**다. README·도움말·조건/관측값·수집 종료 의미와 요구사항을 대조했다. 실패·취소 시 최종 결과 금지, 공개 사용자 검색·번호 페이지 검증, 목록 전용 접근·브라우저 정리 경계는 유지한다.

이번 실행 범위에 ISSUE-003 진행 정보 재설계·누적 개수 보존, 영구 캐시·새 원격 경로·제품 옵션은 추가하지 않았다. 기존 사용자 변경과 과거 기록을 보존했고 선택 커밋 훅은 실행하지 않았다.
