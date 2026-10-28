# Quickstart: 004 구현 후 범위 옵션 검증

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Contract**: [cli.md](contracts/cli.md)

구현 검증 절차와 실행 기록을 함께 관리한다. 아래 절차의 실제 수행 여부와 결과는 마지막 실행 기록에서 구분한다.

## 준비

Windows/PowerShell에서 저장소 루트와 `004-add-range-options` 브랜치를 확인한다. Python 3.12 이상, uv, 잠금 의존성과 전체 DOM 회귀용 Playwright Chromium이 필요하다. 이미 준비된 환경은 다시 설치하지 않는다.

```powershell
Set-Location '.'
git branch --show-current
uv sync --locked --python 3.12
uv run --locked playwright install chromium
```

새 의존성·잠금 파일 갱신은 필요하지 않다. uv 캐시나 브라우저 실행이 환경 권한 때문에 막히면 제품 실패와 구분해 기록한다. 동일 환경의 직접 실행 대안은 `.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider`다.

## 1. CLI 최소 회귀

구현 후 기존 고정 공급자 fixture를 활용해 다음 모듈을 실행한다. 이 검증은 실제 CLI 인자 해석과 Picker/selection·출력까지 연결하되 원격 요청과 실제 기본 브라우저 열기를 차단한다.

```powershell
uv run --locked pytest -q tests/test_cli.py
```

| 검증 집합 | 기대 결과 |
| --- | --- |
| 두 명령 × 세 지표 × 세 범위 형태, 18개 기본 조합 | 기존 min/max 표기와 같은 SearchCriteria·조건 안내·적격 후보·개수 |
| 같은 경계·0·티어 1/30·정답률 소수·세 지표 동시 입력 | 양 끝 포함과 정밀도 보존, 경계 전달 일치 |
| 다른 지표의 신·구 표기 혼용 | 모두 허용하고 모든 조건 적용 |
| 같은 지표 min/max 각각과 혼용, 양쪽 입력 순서 | 값이 같거나 기존 경계가 0이어도 종료 2 |
| 새 옵션 같은/다른 값 반복, 등호/일반 표기 반복 | 종료 2, 마지막 값 채택 없음 |
| 값 누락·빈 문자열·빈 범위·단일값·구분자 오류 | 종료 2와 옵션명·이유, 전달된 값의 문법 오류에는 예시 |
| 공백·부호·쉼표·%·지수·비ASCII·비유한 값·수치 제한·역전 | 계약대로 거부 |
| 생략·0/미제공·범위 밖 확정 티어·모두 제외 | 기존 기본값·미확인 집계·티어 의미·정상 빈 결과 유지 |
| 실제 목록으로 list 정렬·표시 제한과 recommend 중복·개수·부족 | 기존 후보 처리와 일치, 무작위 표본 일치는 요구하지 않음 |
| 기존 옵션만 사용·숨겨진 solver 입력·help/version | 기존 결과/진단 보존, 전환 경고 없음 |

오류 사례는 종료 2만 확인하지 않고 공급자의 호출 기록이 빈 목록인지, stdout 결과와 stderr 조회 시작 안내가 없는지도 확인한다. 혼용 진단에는 충돌 옵션 이름이 있어야 한다. 문법 파서 구현을 복제하는 테스트 대신 관측 가능한 결과를 확인한다.

## 2. 전체 회귀·도움말

CLI 관련 검증이 통과하면 전체 회귀와 도움말을 확인한다. 이후 새 변경·실패·미해결 우려가 없으면 같은 검증을 반복하지 않는다.

```powershell
uv run --locked pytest -q
uv run --locked jpick list --help
uv run --locked jpick recommend --help
```

기존 로컬 DOM 재생·필터·서비스·취소·공개 사용자·open 회귀가 통과해야 한다. 도움말과 README는 [CLI 계약](contracts/cli.md)을 따른다. 세 새 옵션과 여섯 기존 경계 옵션이 모두 보이고, 지원하지 않는 solver 옵션은 계속 숨겨져야 한다.

## 3. 브라우저 없는 오류 수동 확인

구현 후 아래 명령을 각각 실행하고 곧바로 `$LASTEXITCODE`가 2인지 확인한다. 모두 조회·브라우저 시작 없이 오류를 내야 한다.

```powershell
uv run --locked jpick list --accepted 1000..500
$LASTEXITCODE
uv run --locked jpick recommend --tier 0..5
$LASTEXITCODE
uv run --locked jpick list --rate 0..100.1
$LASTEXITCODE
uv run --locked jpick recommend --accepted 500..1000 --min-accepted 500
$LASTEXITCODE
uv run --locked jpick list --rate 40.5..80 --rate 40.5..80
$LASTEXITCODE
uv run --locked jpick list --accepted
$LASTEXITCODE
```

나머지 문법·순서·반복 조합은 고정 공급자 기반 자동 검증에서 다룬다.

## 4. 선택적 실사이트 통합 확인

로컬 회귀 후 실제 공개 사이트 접근을 확인할 필요가 있을 때만 실행한다. 네트워크/사이트 상태와 관측 시각을 기록하며, 변화하는 후보 수나 티어 표시를 고정 기대값으로 사용하지 않는다. 다음 명령은 조건 전달과 결과 의미를 확인하는 통합 확인이며 동등성 검증의 대체가 아니다.

```powershell
uv run --locked jpick list --tier 9..13 --rate 40.5..80 --accepted 500..1000 --sort accepted --order desc --limit 5
uv run --locked jpick recommend --tier 9.. --rate ..80 --accepted 500.. --count 3
```

두 명령은 종료 기준까지 전체 목록을 수집한다. 정상 빈 결과와 추천 부족은 성공이다. 조건 출력에서 정확한 경계와 생략 여부를 확인하며 범위 밖 표시 티어를 이번 기능의 오류로 판정하지 않는다. 실제 값과 미제공 처리는 기존 정책을 따른다.

## 기록할 근거

검증 시각·브랜치/리비전·사용한 환경과 명령·성공/실패/미실행·오류 메시지·자동 검증 결과를 기록한다. 문서 예시, Typer 최소 실험, 제품 회귀, 선택적 실사이트 관측을 구분한다. 이 안내에 실행 결과가 없다는 이유로 통과를 추정하지 않는다.


## 구현 실행 기록 — 2026-10-28

- 브랜치 `004-add-range-options`, 시작 HEAD `9bad679c0f441e284265e492ffc56a39fde69169`. Python 3.12.13, Typer 0.27.3, Rich 15.0.0, Playwright 1.64.0, pytest 9.1.1의 기존 잠금 환경을 사용했다.
- T001: `uv run --locked pytest -q tests/test_cli.py`는 uv 인터프리터 캐시 쓰기 권한 오류로 실패했다. 동일 `.venv`의 `.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests/test_cli.py`로 대체해 **70 passed (0.64s)**. 의존성·잠금 파일은 변경하지 않았다.
- 기존 `.gitignore`가 실제 `.venv/`, Python 산출물·테스트 캐시·빌드·비밀 설정과 일반 임시 파일을 포함함을 확인했다. 다른 도구의 ignore 파일은 필요하지 않다.
- T002~T003: 새 옵션의 출현 목록·반복 검사와 비공개 문법/경계 helper를 추가했다. 아직 명령에는 연결하지 않았다.
- T004: 닫힌 범위/복수 지표 테스트를 먼저 추가하고 `-k "closed_ranges or combined_ranges" --maxfail=1`로 새 `--tier` 미연결 오류를 확인했다(예상 실패 1건).
- T005~T007: 공통 수치 제한·범위 변환을 두 명령에 연결한 후 `-k "closed_ranges or combined_ranges or common_filters or site_tier_bounds"` 검증 **15 passed, 63 deselected (0.36s)**. 고정 공급자와 실제 Picker/selection·출력을 사용했다.
- T008~T010: 열린 범위 테스트를 추가하고 공통 해석기가 이미 열린 경계와 기존 값/0을 올바르게 보존함을 확인했다. 별도 제품 코드 수정이 필요하지 않았다. `-k "ranges or zero_range or equal_rate or missing_statistic_filter"` 검증 **44 passed, 62 deselected (0.54s)**. 기본 18개 조합과 같은 경계·미제공·Decimal 정밀도·등호/일반 표기·신/구 지표 혼합·생략을 확인했다.
- T011~T012: 두 명령의 문법/수치/혼용/반복/누락·도움말 계약을 먼저 추가했다. `-k "invalid_ranges or range_metric_limits or range_conflicts or repeated_ranges or missing_range_value or range_help" --maxfail=2`에서 **230 passed, 2 failed, 106 deselected**. 실패 두 건은 새 도움말 설명 미구현 때문이며 기본 오류 처리는 공통 기반으로 이미 통과했다.
- T013~T015: 정확한 옵션명·혼용 옵션·반복 진단과 Typer 기본 누락 오류를 확인했다. 도움말과 README에 세 범위 형태·허용 수치·최대 1회·신/구 혼용 제한·기존 옵션 유지와 두 명령 예시를 추가했다.
- T016: `.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests/test_cli.py`에서 **338 passed (1.46s)**. 실제 Python 프로세스에서 `from algorithm_problem_picker.cli import app; app()`로 두 도움말과 위 절차의 오류 명령 6개를 실행해 각각 종료 0/2, 조회 시작 없음과 오류 시 stdout 결과 없음을 확인했다. uv 캐시 오류를 피하기 위해 같은 환경의 진입점을 직접 실행했다.
- T017 환경 기록: 일반 샌드박스의 전체 회귀는 CLI 검증 후 Chromium 시작 구간에서 진행이 확인되지 않아 중단했다. 동일 명령을 권한 확장 환경에서 다시 실행했다. 결과는 아래에 별도 기록한다.

### 요구사항별 구현·검증 근거

| 요구사항 / 성공 기준 | 구현 및 확인 근거 |
| --- | --- |
| FR-001 / SC-001 | 두 CLI 명령의 세 범위 옵션, `test_combined_ranges_preserve_user_and_limit`, README의 세 옵션 조합. 여섯 경계 옵션을 세 옵션으로 표현한다. |
| FR-002~003 / SC-002 | `_parse_range`·`_range_bounds`, `test_ranges_match_legacy`의 기본 18개 조합과 티어 동일 경계, `test_equal_rate_preserves_decimal`·`test_zero_range_separates_zero_and_missing`. |
| FR-004~007 / SC-002~003 | 정수/Decimal 변환과 지표별 수치 검사, `test_invalid_ranges_before_source`·`test_range_metric_limits_before_source`, 정밀도/0 검증. |
| FR-005·FR-011~013 / SC-002~004 | 기존 SearchCriteria/Picker/selection 재사용. 닫힌/열린 범위 비교와 복수 지표·사용자 풀이·정렬·표시 제한·추천 부족/중복 검증. 범위 밖 Rated 보존과 미제공 고유 제외 수도 확인했다. |
| FR-008~010 / SC-003 | `_single_range`·`_range_bounds`, `test_range_conflicts_before_source`·`test_repeated_ranges_before_source`·`test_missing_range_value_before_source`와 문법 오류 검증. 모두 공급자 호출/결과/조회 시작이 없다. 실제 오류 명령 6개도 종료 2였다. |
| FR-014 / SC-005 | `test_range_help_preserves_legacy_options`, 두 실제 도움말 명령, README 옵션 표·닫힌/열린 범위·혼용/반복 규칙과 조회/추천 예시를 대조했다. |
| FR-015 / SC-004~005 | 기존 `_present`를 그대로 사용한다. `test_ranges_match_legacy`·`test_combined_ranges_preserve_user_and_limit`에서 조건 요약을 비교하고 `test_mixed_and_omitted_ranges_preserve_criteria`에서 생략 경계가 출력되지 않음을 확인했다. |

선택적 실사이트 통합 확인은 실행하지 않았다. 기본 회귀는 고정 공급자와 로컬 HTML을 사용하고 실사이트 후보 수·두 원격 실행 결과의 일치를 보장하지 않는다.

- T017 최종 결과: 권한 확장 환경에서 `.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider` 전체 회귀 **643 passed in 127.42s**. CLI 338개와 기존 로컬 Chromium DOM·선택·서비스 검증을 모두 통과했다. 원격 사이트 수용은 실행하지 않았다.
- T018: FR-001~015·SC-001~005의 구현/검증 근거를 위 표로 대조했다. `git diff --check` 통과, 제품 변경은 `cli.py`·`tests/test_cli.py`·`README.md`만이며 잠금/의존성·모델·포트·수집기·서비스·필터·헌장·품질 체크리스트는 변경하지 않았다. 문서 링크/코드 펜스와 기존 품질 체크리스트 16개 완료 상태도 확인했다. T001~T018을 완료 처리했다.
