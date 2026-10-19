# Quickstart & Validation

설치·자동 검증과 명시적으로 선택하는 라이브 검증 가이드다.
애플리케이션·테스트·pyproject.toml·uv.lock을 구현했으며 실제 검증 기록은 아래에 구분한다.

## 준비

Windows 10/11, Python 3.12와 uv, 기본 브라우저가 필요하다.
실제 정올 조회는 네트워크가 필요하며 기본 자동 테스트는 오프라인으로 실행한다.
의존성과 Chromium 설치 방법은 [uv](https://docs.astral.sh/uv/guides/install-python/)와
[Playwright](https://playwright.dev/python/docs/library)를 따른다.

저장소 루트에서 다음을 실행한다.

```powershell
uv sync --locked
uv run playwright install chromium
uv run jpick --help
uv run pytest
```

uv.lock을 생성했으며 재현 검증은 잠금된 버전을 사용한다.
Chromium 설치 파일은 도구 의존성이다. 문제 목록 저장이나 로그인 프로필 생성은 하지 않는다.

## 기본 자동 검증

`uv run pytest`는 다음 고정 시나리오를 네트워크 없이 확인한다.

1. 경계가 포함된 복합 필터, 미정·미확인과 실제 0의 구분.
2. 양방향 지표 정렬·동점 ID 순서·미확인 마지막·표시 제한의 후적용.
3. 서로 다른 두 페이지의 후보가 추천에 전달되고 ID가 먼저 중복 제거되는지.
4. 추천 개수·부족·0개·균등 비복원 추출에 전체 후보를 전달하는지.
5. 정답 제출 수와 맞힌 사람 수가 다른 로컬 DOM, 페이지 종료·중단·구조 변경.
6. 사용자 누락 등 입력 오류가 브라우저 시작 전에 종료되는지.
7. 명시적인 open만 시스템 브라우저를 호출하고 중복 번호는 한 번만 전달하는지.
8. 실패·Ctrl+C에서 최종 결과가 출력되지 않고 조회용 브라우저가 정리되는지.

테스트 경로는 plan.md의 구조를 따르고, 로컬 HTML fixture는 최소 공개 레이아웃을 재구성한다.
전체 사이트 복사본이나 실제 계정 목록을 fixture로 저장하지 않는다.

## 라이브 조회 표본

사이트가 정상 접근 가능한 환경에서 순서대로 실행한다.
조회 결과의 정확한 숫자는 고정하지 말고 같은 시점의 정올 화면과 비교한다.
403·429·챌린지나 로그인 요구를 만나면 중단한다.

```powershell
uv run jpick list --min-tier 1 --max-tier 1 --min-rate 80 --limit 2
uv run jpick list --min-tier 1 --max-tier 1 --min-rate 80 --sort rate --order desc --limit 5
uv run jpick recommend --min-tier 1 --max-tier 1 --min-rate 80 --min-solvers 10 --count 3
```

기대 결과: 범위를 만족하는 일반 문제, 정확한 정답률과 푼 사람 수, 전체 적격/표시 개수.
추천은 후보가 충분하면 서로 다른 3개, 부족하면 가능한 전부와 부족 안내를 표시한다.
후보 개수가 작아 보이더라도 표시 제한 때문에 조회를 일찍 끝내서는 안 된다.
네트워크 시간이 길어질 수 있으며 진행 정보와 Ctrl+C 안내가 보여야 한다.

## 풀이 여부 비교

비로그인 상태에서 공개 사용자 표본을 지정한다.

```powershell
uv run jpick list --user JUNGOL --status solved --limit 5
uv run jpick list --user JUNGOL --status unsolved --min-tier 1 --max-tier 1 --limit 5
```

사용자 핸들이 정확히 @JUNGOL로 해석되는지, 화면의 기준 사용자·필터와 결과가 일치하는지 확인한다.
기존 표본의 풀이 내역은 변할 수 있으므로 2356·2799를 영구적인 기대값으로 고정하지 않는다.
작은 동일 후보 범위에서 all·solved·unsolved를 비교해 두 분할이 겹치지 않고 합집합이
all과 일치하는지 확인한다. 오답만 있는 문제는 unsolved에 포함되어야 한다.
기본 자동 테스트에서는 이 관계를 고정 공급자 데이터로 검증한다.

같은 사용자를 한 번 해석한 후 좁은 동일 조건(티어 1, 정답률 80% 이상)에서
공급자·필터의 분할을 검증하는 선택 실행 스크립트도 제공한다.

```powershell
uv run python scripts/validate_live.py --user JUNGOL
```

이 스크립트는 원격 조회를 수행하며 기본 pytest에는 포함되지 않는다.

## 열기·실패·취소

```powershell
uv run jpick open 1000 1000 1001
uv run jpick list --status unsolved
uv run jpick list --min-rate 80 --max-rate 20
```

첫 명령은 기본 브라우저에 1000·1001을 각각 한 번만 전달한다.
나머지 명령은 입력 오류로 종료하며 네트워크 조회를 시작하지 않는다.
기본 자동 테스트에서는 브라우저 호출을 대체해 실제 탭이 열리지 않도록 한다.

진행 중 Ctrl+C를 누르면 130으로 종료하고 최종 추천 표를 출력하지 않아야 한다.
공급자 테스트에서 접속 실패·사용자 없음·DOM 구조 변경을 주입하면 코드 1과 원인을 확인한다.
외부 사이트에 실패를 일으키는 요청을 보내 오류를 시험하지 않는다.

출력 형식·종료 코드는 [CLI 계약](contracts/cli.md),
지표·상태는 [데이터 모델](data-model.md)을 기준으로 판단한다.

## 구현 검증 기록 (2026-10-19, Asia/Seoul)

환경: Windows 11 10.0.26200, CPython 3.12.13, uv 0.11.2,
Playwright 1.64.0 / Chromium 156.0.8078.4, Typer 0.27.3, Rich 15.0.0.
`uv sync --locked --python 3.12` 및 `uv run playwright install chromium`을 실행했다.
`uv run jpick --help`, `uv run jpick --version`(0.1.0)을 원격 접근 없이 확인했다.

로컬 처리 측정 명령:

```powershell
uv run python scripts/benchmark_selection.py
```

실제 측정: 준비된 10,000개 중 적격 4,226개, 5개 추첨,
필터·정답률 내림차순 정렬·sample 총 **0.005200초**. 후보 생성과 네트워크는 측정에서 제외했다.
개발 PC 한 번의 측정이며 외부 사이트 조회 시간이나 모든 PC의 성능을 보장하지 않는다.

`src/algorithm_problem_picker/`를 검토해 문제/사용자/브라우저 상태를 파일에 저장하는 경로가
없음을 확인했다. 영구 프로필·storage_state·HAR·trace·DB·내부 API 직접 호출이 없다.

라이브에서 티어 1 목록 134개(추가 로드 50 → 100 → 134)를 끝까지 수집했다.
정답률 80% 이상 적격 9개의 상세를 모두 확인하고 list에서 2개를 표시했다(종료 0).
정답률 미제공 2개를 제외 개수로 안내했다. 목록과 상세 수치는 관측 시점 기준이다.
4964번은 83.79%·맞힌 사람 290, 5824번은 87.15%·236으로 표시됐다.

라이브 recommend는 같은 134개를 수집하고 9개의 상세를 확인한 뒤
8220·6296·6144번을 반환했다(요청 3 / 반환 3 / 부족 0, 종료 0).
이 번호와 지표는 실행 당시 표본이며 이후 실행의 고정 기대값이 아니다.

개발 중 확인한 DOM 차이는 fixture에 반영했다: 미정 문제의 배지 생략,
통계 앵커의 명시적 빈 값, 빈 alert 컨테이너, hydration 중 미완성 행,
상세 탭/URL의 cursor 쿼리, 사용자 검색의 지연된 결과 교체와 페이지 그룹 이동.

오프라인 전체 테스트: `uv run pytest -q`와 동일한 잠금 가상환경에서
**92 passed in 16.26s** (`uv run --locked pytest -q`). 모든 DOM 테스트는 원격 요청을 차단하고 로컬 HTML을 공급했다.
기본 브라우저 호출은 대체했고 정상/부분/전체 실패와 입력 오류를 검증했다.

공개 사용자 UI에서 대소문자를 보존한 @JUNGOL을 숫자 ID 146040으로 해석했다.
동일 조건(티어 1, 정답률 80% 이상)의 라이브 분할은 all=9, solved=0, unsolved=9로
서로소/합집합 검증을 통과했다. 이 표본에서는 solved가 비었으며,
양쪽이 모두 존재하는 분할 및 오답만 있는 문제는 고정 공급자 테스트로 검증했다.

정답률 내림차순 라이브 list의 상위 5개는 8220(89.47%), 6296(87.92%),
8305(87.70%), 5824(87.15%), 5844(86.55%)였다(종료 0).
공개 DOM의 1000번 헤더에서 제출 13,720·정답 6,510·맞힌 사람 5,171을
서로 다른 통계로 확인했으며, 제출 수를 푼 사람 수로 대체하지 않았다.

`uv run --locked jpick open 1000 1000 1001`은 1000·1001 링크만 각각 한 번 출력하고
기본 브라우저에 전달했다(종료 0). 페이지 로딩 성공까지 검증한 것은 아니다.

`jpick list --min-tier 1 --max-tier 1 --min-rate 50` 진행 중 실제 Ctrl+C를 전달했다.
Cancelled 단계·취소 안내 후 조회용 브라우저가 정리됐으며 최종 결과 표는 없었다.
자식 CLI의 `SystemExit=130`을 직접 관측했다. 검증 도구의 Windows PTY/PowerShell은
Ctrl+C 자체의 호스트 종료를 1로 보고하므로 이 값과 자식 CLI의 종료 코드를 구분했다.

403/429·챌린지·로그인 요구를 외부 사이트에 유발하지 않았다.
이 실패 경로는 로컬 DOM/응답 fixture로 검증했다. 전체 사이트·모든 공개 사용자·모든 배포의
DOM을 라이브 검증한 것은 아니며 수치/핸들 검색 결과는 실행 시점에 따라 달라진다.
