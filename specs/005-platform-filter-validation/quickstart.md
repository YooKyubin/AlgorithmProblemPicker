# Quickstart Validation: algo-pick 플랫폼 선택

이 가이드는 **구현 후** 수행할 검증 절차다. 계획 작성 시점에는 새 실행 이름·플랫폼 경계·새 테스트가 구현되지 않았다. 아래 명령을 이미 통과한 결과로 해석하지 않는다.

**현재 구현 범위 (2026-10-30)**: T001~T012까지 완료했다. 설치 명령은 `algo-pick`이며 명령 앞의 `--platform` 선택과 정올 기본값을 제공한다. 미지원 필터의 값 해석 전 검사·선택 플랫폼별 help·합성 플랫폼 수용과 최종 배포/문서 정합성은 후속 범위다. 실제 실행 결과는 문서 끝의 검증 기록을 따른다.

## 전제와 설치

- Python >=3.12와 uv, 저장소 루트에서 실행하는 터미널.
- 기본 회귀는 고정 공급자·로컬 HTML을 사용하고 실제 원격 요청과 기본 브라우저 전달을 차단한다.
- CLI 계약: [contracts/cli.md](contracts/cli.md). 합성 플랫폼 계약: [contracts/platform.md](contracts/platform.md). 값/집계 불변식: [data-model.md](data-model.md).
- `jungol`만 실제 등록한다. 합성 플랫폼을 검증하려고 사용자 환경에 `programmers`나 테스트 플랫폼을 등록하지 않는다.

```powershell
uv sync --locked --python 3.12
uv run --locked playwright install chromium
uv run --locked algo-pick --version
uv run --locked algo-pick --help
```

Chromium은 기존 로컬 DOM 테스트와 선택적 실사이트 조회를 위해 필요하다. help/version과 open이 조회용 Chromium을 시작해서는 안 된다.

설치 메타데이터를 확인한다. 기존 환경에 남은 launcher 파일 유무만으로 새 배포 계약을 판단하지 않는다.

```powershell
uv run --locked python -c "from importlib.metadata import distribution; scripts={e.name for e in distribution('algorithm-problem-picker').entry_points if e.group=='console_scripts'}; assert scripts=={'algo-pick'}, scripts"
```

기대: 패키지 이름은 그대로이며 실행 키는 algo-pick 하나다. 변경된 실행 메타데이터가 반영되지 않았다면 해당 패키지를 재설치한 뒤 확인한다. 잠금 의존성 변경을 이유 없이 추가하지 않는다.

## 1. 관련 회귀

```powershell
uv run --locked pytest -q tests/test_platforms.py tests/test_cli.py tests/test_selection.py tests/test_service.py tests/test_export_tool.py
```

`test_platforms.py`는 이번 구현에서 추가할 계약 검증 파일이다. 기존 테스트는 타입 import·의존성 주입 지점만 변경하고 행동 기대를 유지한다.

| 확인 묶음 | 관측할 결과 |
| --- | --- |
| 기본/명시 정올 | 세 명령의 6개 기본 조합에서 같은 조건·후보·집계·정렬·정올 URL. 추천은 후보/개수/중복을 비교 |
| 입력 출처 | 생략된 status는 요청 아님. 명시한 all·빈 user·0 경계는 요청으로 식별 |
| 미지원 | 두 조회/추천 명령에서 범위·기존 하한/상한·사용자 옵션·복수 미지원 안내. 무효/반복 값이 섞여도 지원 검사 우선 |
| 사전 중단 | 코드 2, 플랫폼+옵션 안내, stdout 결과 없음. source factory·사용자 조회·수집·사이트 접속·브라우저 호출 0회 |
| 정올 값 회귀 | 티어 약칭/숫자, Decimal 정밀도, 기존 경계 문법과 새 범위 문법 차이, 혼용·반복·사용자 조건·legacy 전환 오류 |
| 결측·0·집계 | 미제공 필터 유무, 실제 0..0, 첫 실패 순서 고유 제외 수, Unrated 제외와 집계 차이, 정상 빈 결과/부족 코드 0 |
| 완료·실패·취소 | 완료 전 처리/추출 없음, 실패/취소 부분 출력 없음, 컨텍스트 정리와 기존 코드 1/130 |
| open | 전 번호 검증 후 고유 링크 전달, 잘못된 ID는 전달 0회, 일부 전달 실패 시 모든 링크·실패 ID와 코드 1, source factory 0회 |

위 항목은 필요한 행동을 한정한다. 동일한 파서 구현을 재작성하거나 기존 DOM 회귀에 새 입력 문법을 복제하는 테스트는 추가하지 않는다.

## 2. 합성 플랫폼을 통한 확장 수용

동일한 `test_platforms.py`에서 일반 구성 경계에만 test-platform을 주입한다. 공통 CLI·Picker·recommend를 그대로 사용한다.

1. 정올 1~30 밖의 합성 난도 점수 100~200과 다른 URL을 가진 고정 문제를 조회·추천한다. 자체 조건 검증이 적용되고 정올 규칙으로 거부되지 않아야 한다.
2. 지원하지 않는 accepted·사용자 옵션을 생략하면 정상 동작한다. 미지원 속성 때문에 후보가 제외되거나 미제공 집계가 늘거나 정올 통계 열이 출력되어서는 안 된다.
3. `--accepted 0..0`, 기존 min/max, 명시한 `--status all`, 복수 미지원과 무효 값/반복 조합을 거부한다. 합성 source도 생성하지 않아야 한다.
4. 선택 플랫폼의 도움말에서 합성 난도 의미·허용 값·미지원 옵션을 확인한다. 정올 전용 규칙을 합성 플랫폼 규칙으로 안내해서는 안 된다.
5. 정올과 같은 문제 ID로 open을 실행해 합성 URL만 전달한다. 정올 source 생성·사용자 조회·정올 링크 전달은 0회여야 한다.
6. 추천은 전체 적격 집합에 대한 동일한 공통 sample 경로를 사용하고 중복·부족 처리를 유지한다. 테스트가 끝난 일반 레지스트리에는 정올만 남아야 한다.

합성 결과를 프로그래머스의 실제 지원·속성·접근 허가 근거로 기록하지 않는다.

## 3. 접속 없는 CLI 오류와 도움말

아래 거부 명령은 각각 코드 2다. PowerShell에서는 각 명령 직후 `$LASTEXITCODE`로 확인한다.

```powershell
uv run --locked algo-pick --platform unknown list
uv run --locked algo-pick --platform programmers recommend
uv run --locked algo-pick --platform programmers open 1000
uv run --locked algo-pick --platform jungol list --accepted 1000..500
uv run --locked algo-pick --platform jungol recommend --tier B5..B1 --min-tier B5
```

기대: 플랫폼·문제 옵션·수정 이유를 안내하고 조회 시작/Processing/결과 집계를 출력하지 않는다. 실제 source 생성/접속 0회는 위 CliRunner 호출 기록으로 검증한다. 터미널 문구만으로 외부 호출 0회를 단정하지 않는다.

```powershell
uv run --locked algo-pick --platform jungol list --help
uv run --locked algo-pick --platform jungol recommend --help
uv run --locked algo-pick --platform jungol open --help
```

기대: 선택 플랫폼 이름과 필터별 의미·허용 값·조합 제약을 확인한다. 루트 help의 기본값/등록 목록은 jungol이며 신규 수집기 제공을 암시하지 않는다. help/version도 source 생성 0회를 고정 테스트로 확인한다.

## 4. 전체 회귀

관련 검증을 마친 뒤 한 번 실행한다.

```powershell
uv run --locked pytest -q
```

기대: 기존 로컬 정올 DOM·사용자 식별·사이트 검색 조건·완료 기준·실패 정리 회귀를 포함해 통과한다. 실패 테스트를 새 동작에 맞춘다는 이유로 정올 의미·제외 수·실패 기대를 약화하지 않는다. 이후 새로운 변경/실패가 없다면 같은 전체 검증을 반복하지 않는다.

## 5. 배포·사용 문서와 내보내기

현재 사용 자료만 검토한다.

```powershell
rg -n 'jpick|algo-pick|--platform' pyproject.toml README.md docs/integration.md docs/standalone.md examples/vscode/tasks.json scripts/export_tool.py
```

기대: 현재 실행 예시는 algo-pick, 새 예시 폴더는 tools/algo-pick으로 연결된다. VS Code task의 입력 참조가 inputs ID와 일치한다. 기존 외부 폴더를 자동 이동/덮어쓰지 않는다. 과거 명세와 검증 이력의 jpick 표기는 보존한다.

내보내기 동작은 기존 test_export_tool로 우선 검증한다. 독립 복사본 설치까지 수용하려면 저장소의 `dist/` 아래 **존재하지 않는 새 폴더**를 사용한다. 예시 대상이 이미 있으면 다른 새 이름을 고른다.

```powershell
uv run --no-project --python 3.12 python scripts/export_tool.py --target ./dist/algo-pick-005-validation
uv --directory ./dist/algo-pick-005-validation sync --locked --no-dev
uv --directory ./dist/algo-pick-005-validation run --locked --no-dev algo-pick --version
uv --directory ./dist/algo-pick-005-validation run --locked --no-dev algo-pick --platform jungol list --help
```

기대: 원본 경로에 의존하지 않는 복사본에 새 모듈·메타데이터·문서/예제가 포함되고 새 실행 이름과 정올 기본값을 확인할 수 있다. `.venv`·Chromium·원본 Git 상태를 복사하지 않는 기존 내보내기 정책을 유지한다. 이 절차는 삭제/이동 명령을 요구하지 않는다.

## 6. 선택적 실사이트 사용 예시

기본 수용은 고정 공급자로 완료한다. 허용된 기존 정올 접근 환경에서만 다음 사용 예시를 확인할 수 있다.

```powershell
uv run --locked algo-pick list --tier S2..G3 --rate 40.5..80 --accepted 500..1000 --limit 5
uv run --locked algo-pick --platform jungol recommend --tier S2..G3 --count 3
uv run --locked algo-pick --platform jungol open 1000 1000 1001
```

마지막 명령은 실제 기본 브라우저에 정올 링크 두 개를 전달한다. 앞의 두 명령은 실제 정올 목록에 접속한다. 사이트의 서로 다른 관측 시점이나 무작위 추출 결과를 비교해 기본/명시 플랫폼의 동등성을 판정하지 않는다. 접근 제한·챌린지에서는 기존 정책대로 중단하고 자동 재시도하지 않는다.

## 검증 기록

구현 단계에서 실행 명령·환경·실제 결과를 이 문서에 기록한다. 실패·환경 제약·선택적 미실행 항목도 구분한다. 2026-10-30 계획 단계에서는 문서 정합성 검증과 [research.md](research.md)의 로컬 실험만 수행했으며, 위 제품 수용 절차는 아직 실행하지 않았다.


### 2026-10-30 — T001 기존 회귀 기준

- 범위: T001~T007 중 구현 전 기준. 브랜치 `005-platform-filter-validation`, HEAD `dca9659bc4fa196b043c67886d5c48e531bed52c`. 시작 시 제품 변경은 없었고 005 설계 디렉터리만 미추적 상태였다.
- 환경: Windows/PowerShell, Python 3.12.13, uv 0.11.2, Typer 0.27.3, Rich 15.0.0, Playwright 1.64.0, pytest 9.1.1. 기존 잠금/가상환경과 Chromium을 사용했으며 설치·업그레이드하지 않았다.
- `.gitignore`는 Python 캐시·가상환경·dist/build·egg-info·환경 파일 패턴을 이미 포함해 수정하지 않았다. requirements 체크리스트 16/16 완료를 읽기 전용 확인했다.
- 원래 `uv run --locked pytest ...`는 샌드박스의 uv 캐시 쓰기 오류로 실행하지 못했다. `--cache-dir ./dist/uv-cache` 사용 시 pytest launcher의 trampoline 경로 오류가 발생했고, `python -m pytest`로 바꾼 샌드박스 실행은 DOM 단계에서 진행이 멈춰 중단했다. 이 실행들은 통과 결과로 계산하지 않는다.
- 하위 프로세스를 허용한 환경에서 아래 명령으로 기준을 확인했다. 로컬 HTML 라우팅과 브라우저 호출 대역을 사용하는 기존 테스트이며 실사이트 접근·기본 브라우저 전달은 하지 않았다.

```powershell
uv run --locked python -m pytest -q tests/test_cli.py tests/test_selection.py tests/test_service.py tests/test_jungol_dom.py tests/test_export_tool.py
```

결과: **744 passed in 128.88s**. `pyproject.toml`·`uv.lock`과 기존 실행 키 `jpick`은 유지한다. 이 기준은 005 전체 기능 수용 결과가 아니다.

### 2026-10-30 — T002~T007 구현 및 회귀 검증

| 완료 작업 | 변경과 확인 |
| --- | --- |
| T002 | 정올 Problem·Rated/Unrated·SearchCriteria·UserReference·Status·SortKey를 `src/algorithm_problem_picker/jungol_models.py`로 이동했다. 기존 7개 클래스의 AST를 HEAD와 비교해 필드·검증·enum 값이 동일함을 확인했다. |
| T003 | 공통 문제 프로토콜·지원 정보·불변 raw 입력·검증 요청·링크·제네릭 완료 목록/결과와 정책/소스 포트를 정의했다. raw 입력의 외부 변경 격리·빈 값/명시 기본값/반복 보존 검증 1개를 추가했다. |
| T004 | 정올 파싱·필터·정렬·행/조건/주의 문구·링크를 `src/algorithm_problem_picker/jungol_policy.py`로 옮기고 기존 CLI를 연결했다. 필터/정렬 함수 본문의 AST가 기존 selection과 동일함을 확인했다. |
| T005 | `src/algorithm_problem_picker/platforms.py`에서 jungol 하나의 지원 정보·정책·지연 소스 팩터리를 조립했다. 실제 선택 옵션과 구성 오류 검증은 후속 범위다. |
| T006 | 공통 Picker에 정책/소스를 명시적으로 주입하고 prepare_user·완료 수집·로컬 처리 흐름을 유지했다. 공통 service/selection에 정올 import·조건 필드 접근·티어 접근·resolve_user 호출이 없음을 확인했다. 정올 source에는 prepare_user만 추가했으며 기존 메서드 본문 AST는 동일하다. |
| T007 | 기존 테스트의 import·주입·monkeypatch 위치를 이동했다. opaque 조건·튜플 ID·None/실제 0 사용자 참조를 보존하고 0에서도 UserResolved를 보고하는 공통 흐름 검증 2개를 추가했다. 기존 행동 기대와 로컬 DOM/실패/취소/정리 회귀를 유지했다. |

타입/함수 이동의 기존 소비자인 `scripts/benchmark_selection.py`와 `scripts/validate_live.py`도 import·정책 호출 위치만 맞췄다. 배포 메타데이터·잠금 파일·헌장 원문·기존 export 테스트 내용은 HEAD와 동일하다. `tests/test_platforms.py`의 합성 CLI 수용은 아직 추가하지 않았다.

수행한 검증:

```powershell
# 정책/서비스/CLI 연결 후 빠른 관련 회귀
.\.venv\Scripts\python.exe -m pytest -q tests/test_cli.py tests/test_selection.py tests/test_service.py

# 로컬 DOM 하위 프로세스를 허용한 환경, T001과 같은 5개 파일
uv run --locked python -m pytest -q tests/test_cli.py tests/test_selection.py tests/test_service.py tests/test_jungol_dom.py tests/test_export_tool.py

# 최종 타입 표기·표시 문구·generic fixture 정리 후 영향받은 회귀
.\.venv\Scripts\python.exe -m pytest -q tests/test_selection.py tests/test_service.py

.\.venv\Scripts\python.exe -m compileall -q src tests scripts
.\.venv\Scripts\python.exe scripts/benchmark_selection.py
.\.venv\Scripts\python.exe scripts/validate_live.py --help
git diff --check
```

| 검증 | 실제 결과 |
| --- | --- |
| 빠른 CLI/정책/서비스 회귀 | **542 passed in 2.00s** |
| 기준과 같은 5개 파일 | **747 passed in 130.66s** (기존 744 + 신규 3) |
| 최종 정리 후 정책/서비스 회귀 | **108 passed in 0.12s** |
| Python 컴파일 | 통과 |
| 정올 모델·기존 source 본문·필터/정렬 본문 AST 비교 | 통과 |
| 로컬 선택 스크립트 | 10,000개 준비, 적격 6,039개, 중복 없는 추천 5개. 동작 확인이며 성능 개선 주장은 하지 않음 |
| live 검증 스크립트 | `--help`만 실행해 import/인자 처리를 확인. 실제 조회는 실행하지 않음 |
| diff 공백 검사 | 통과 |

T001~T007을 완료 표시했다. 이 범위에서 남은 테스트 실패는 없다. T008 이후의 새 실행 이름·플랫폼 선택·지원 검사 순서·플랫폼별 help·합성 CLI 확장·최종 배포/문서 수용은 미완료로 유지한다. 실제 사이트·기본 브라우저 호출·독립 복사본 설치·별도 전체 `pytest -q` 명령·커밋은 이번 범위에서 수행하지 않았다. 선택적 before/after implement 커밋 훅은 실행하지 않았다.

### 2026-10-30 — T008~T012 새 명령과 플랫폼 선택

기준은 기반 커밋 `d9df7cc`다. requirements 체크리스트 16/16 완료와 기존 Python ignore 패턴을 읽기 전용 확인했다. 이 구간은 설치 실행 키·루트 Context의 선택 바인딩·고정 정올의 기본/명시 세 명령만 다루며 T013 이후는 진행하지 않았다.

| 완료 작업 | 변경과 확인 |
| --- | --- |
| T008 | `tests/test_cli.py`에서 기본/명시 정올의 list/recommend/open 6개 흐름을 확인했다. 조회는 전체 25개 중 적격 24개를 정렬 후 기본 20개 표시, 추천은 동일 전체 적격 집합에서 중복 없는 24개/요청 30개·부족 6개를 관측했다. 사용자 조건·집계·스트림을 비교하고 기본 추천 1개도 양쪽 선택에서 확인했다. help/version/open의 팩터리 0회, 중간 무효 ID의 전달 0회, 고유 링크·일부 실패에도 모든 링크 시도·코드 1을 검증했다. |
| T009 | `[project.scripts]`는 `algo-pick` 하나로 변경했다. 배포 이름·내부 모듈·의존성 잠금은 유지했고 현재 로컬 패키지 1개만 재설치해 메타데이터를 반영했다. 옛 launcher 자동 삭제를 구현하지 않았다. |
| T010 | 루트 callback이 문자열 플랫폼을 정적 레지스트리로 선택해 Context에 보관하며 파싱·정렬·단일 소스 with·표시·open이 그 바인딩을 사용한다. 루트 help는 새 이름·옵션 위치·jungol 기본값/선택 가능 값을 안내한다. open은 raw ID 전체를 정책에서 검증한 후에만 고유 URL을 전달한다. |
| T011 | 기반 정올 정책의 행·조건·링크·주의 문구가 기존 티어 약칭/미정/미확인·Decimal 정밀도·중복 정답 제출 의미를 보존함을 기존 CLI 회귀와 새 흐름 검증으로 확인했다. 이미 충족한 순수 정책 구현을 불필요하게 다시 작성하지 않았다. |
| T012 | 관련 CLI/서비스 검증과 실제 설치 실행 파일의 version·루트/세 명령 help·console_scripts를 확인했다. |

테스트를 먼저 추가한 상태에서 아래 선택 실행은 **6 failed, 9 passed, 426 deselected in 1.52s**였다. 실패 원인은 새 루트 이름/플랫폼 옵션 미구현이며 기존 열기/무효 ID 동작은 통과했다. 구현 후 첫 전체 관련 실행은 477개가 통과했고, 기본 추천의 명시 정올 조합까지 보완한 최종 결과는 다음과 같다.

```powershell
uv run --locked python -m pytest -q tests/test_cli.py tests/test_service.py
uv run --locked algo-pick --version
uv run --locked algo-pick --help
uv run --locked algo-pick --platform jungol list --help
uv run --locked algo-pick --platform jungol recommend --help
uv run --locked algo-pick --platform jungol open --help
uv run --locked python -c "from importlib.metadata import distribution; scripts={e.name for e in distribution('algorithm-problem-picker').entry_points if e.group=='console_scripts'}; assert scripts=={'algo-pick'}, scripts"
git diff --check
```

- 최종 관련 회귀: **478 passed in 1.87s**.
- 실제 설치 실행: version은 **0.1.0**, 루트 및 명시 정올 세 명령 help는 모두 **exit 0**.
- 설치 메타데이터: **console_scripts = {'algo-pick'}**.
- `git diff --check`: 통과. `uv.lock`·정올 DOM/source·헌장은 변경하지 않았다.
- 환경 기록: 새 `dist/uv-cache`의 offline 빌드 시 hatchling 캐시가 없어 해당 시도는 실패했다. 기존 캐시를 사용할 수 있는 하위 프로세스 허용 환경에서 위 locked 명령으로 로컬 패키지만 재설치했고 검증을 완료했다. 새 의존성이나 버전 변경은 없다.
- 실제 사이트·기본 브라우저·전체 pytest·DOM 재실행·독립 내보내기 설치는 수행하지 않았다. before/after implement 선택적 커밋 훅은 부모가 구간 검토 후 커밋하므로 실행하지 않았다.

이 구간의 알려진 테스트 실패는 없다. 플랫폼별 지원 검사 순서·구성 오류 처리·고유 값 진단/동적 help·합성 수용과 현재 사용 문서 변경은 이후 작업에 남아 있다.
