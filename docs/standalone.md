# 다른 프로젝트에 포함된 algo-pick 사용법

이 폴더는 JUNGOL 문제 검색·추천 CLI의 독립 소스 복사본입니다. 원본 프로젝트 경로를 참조하지 않습니다.
Python 패키지는 이 폴더의 `.venv`에 설치하며, Chromium은 사용자별 Playwright 공용 경로에 설치합니다.

## 최초 설치: Windows / macOS

지원되는 운영체제에서 [uv](https://docs.astral.sh/uv/getting-started/installation/)를 설치하세요.
macOS에서 Homebrew를 사용한다면 `brew install uv`, Windows에서는 공식 설치 안내를 사용할 수 있습니다.
VS Code에서 `uv`를 찾지 못하면 설치 후 VS Code를 다시 실행하고 터미널에서 `uv --version`을 확인하세요.
Python 3.12는 `.python-version`에 지정되어 있으며 uv가 필요하면 다운로드합니다.
운영체제 지원 범위는 [Playwright 설치 문서](https://playwright.dev/python/docs/intro#system-requirements)를 확인하세요.

터미널에서 **이 README가 있는 폴더로 이동한 뒤** 아래 명령을 실행합니다. PowerShell과 macOS 셸에서 같습니다.

```sh
uv sync --locked --no-dev
uv run --locked --no-dev playwright install chromium
uv run --locked --no-dev algo-pick --version
uv run --locked --no-dev algo-pick --help
```

최초 설치에는 인터넷 연결이 필요합니다. 문제 조회에도 정올 접속이 필요합니다.
일반 Chrome과 별개로 Playwright 버전에 맞는 Chromium을 설치합니다.
운영체제·CPU가 다른 PC 사이에서 `.venv`나 Chromium을 복사하지 말고 각 PC에서 위 명령을 실행하세요.
같은 PC에서 복사본 폴더의 경로를 옮겼을 때도 기존 `.venv`를 제거하고 다시 설치하세요.

## 문제 추천·조회

```sh
uv run --locked --no-dev algo-pick --platform jungol recommend --tier S5..G1 --rate 50.. --accepted 500.. --count 3
uv run --locked --no-dev algo-pick list --tier S5..G1 --limit 20
uv run --locked --no-dev algo-pick open 1000
```

`--platform` 생략 시 정올을 사용하며 실제 지원 플랫폼은 소문자 `jungol` 하나입니다. 플랫폼은 위 추천 예시처럼 명령 앞에 지정합니다. 프로그래머스 수집기는 제공하지 않습니다.

선택 플랫폼의 지원 필터·의미·허용 값·조합과 미지원 옵션은 다음 도움말로 확인합니다.

```sh
uv run --locked --no-dev algo-pick --platform jungol list --help
uv run --locked --no-dev algo-pick --platform jungol recommend --help
```

정올은 티어(B5~R1 약칭, 대소문자 무관 또는 1~30), 정답률(0~100 정수·소수, % 없이), 정답 제출 수(0 이상 정수), 공개 사용자 풀이 조건을 지원합니다. 범위는 `MIN..MAX`, `MIN..`, `..MAX`로 양 끝을 포함하며 적어도 한 경계가 필요합니다. 같은 지표의 범위·기존 `--min-*`/`--max-*` 혼용, 범위 반복과 역전은 오류입니다. 정답 제출 수는 중복 정답 제출을 포함하며 푼 사람 수와 다릅니다. `--status solved/unsolved`에는 정확한 공개 핸들 `--user`가 필요하고 `all + user`는 오류입니다.

미등록 플랫폼은 가능한 값 안내 후 코드 2로 거부하며 정올로 대신 실행하지 않습니다. 명시한 미지원 필터는 플랫폼·해당 옵션 이름을 모두 안내하고 값 해석·접속 전에 거부합니다. 0이나 기본값과 같은 값을 명시해도 검사합니다. 지원 필터의 잘못된 값·조합도 플랫폼·옵션·이유를 알리고 접속 전에 코드 2로 중단합니다.

플랫폼 속성 미지원과 개별 문제의 값 미제공은 다릅니다. 정올의 지원 통계가 미제공이면 해당 필터가 없을 때 후보에 포함해 `미확인`으로 표시하고, 필터가 있을 때 제외합니다. 실제 0은 미제공과 구분합니다.

## VS Code 작업 연결

복사본이 `<사용할 프로젝트>/tools/algo-pick`에 있다면 `vscode-tasks.example.json`을 예제로 사용하세요.
프로젝트에 `.vscode/tasks.json`이 없으면 예제 파일을 해당 경로로 복사합니다.
기존 파일이 있으면 예제의 `tasks` 항목 세 개와 `inputs` 항목 다섯 개를 각각 기존 배열에 추가합니다.
`inputs`는 `tasks`와 같은 최상위 수준입니다. 같은 작업 이름이나 입력 `id`가 이미 있으면 중복 추가하지 말고 비교하세요.
기존 설정 전체를 예제로 덮어쓰지 마세요. 다른 위치에 복사했다면 세 작업의 `--directory` 다음 경로를 모두 수정합니다.
입력 참조 `${input:algoPickTier}` 등은 최상위 `inputs`의 같은 `id`와 연결하며, 조회·추천 작업은 명령 앞에 `--platform jungol`을 지정합니다.

이후 프로젝트 폴더를 VS Code로 열고 Windows는 `Ctrl+Shift+P`, macOS는 `Cmd+Shift+P`에서
`Tasks: Run Task` → `정올: 설치`를 한 번 실행합니다. 그 뒤 `정올: 문제 추천` 또는 `정올: 문제 목록`을 선택합니다.
설치 작업은 Python 환경과 Chromium을 준비하며, 사용 작업은 이미 설치한 환경을 사용합니다.
VS Code 없이 터미널 명령만으로도 사용할 수 있습니다.

## Git 공유·업데이트

소스, `pyproject.toml`, `uv.lock`, `.python-version`, `.gitignore`, 이 README와 예제·출처 파일을 함께 커밋하세요.
전용 `.gitignore`가 `.venv`, `__pycache__`, Python 캐시 파일을 제외합니다. 실제 제외 규칙은 아래 명령으로 확인할 수 있습니다.

```sh
git check-ignore -v tools/algo-pick/.venv/pyvenv.cfg
```

위 Git 명령은 사용할 프로젝트의 루트에서 실행합니다. 경로가 다르면 맞게 바꾸세요.
`.vscode`가 무시되고 있다면 `tasks.json`을 별도로 Git 공유해야 다른 PC에서도 작업 목록을 사용할 수 있습니다.
사용 대상 프로젝트 루트의 `.gitignore`에서 기존 `.vscode` 무시 규칙 뒤에 아래 예외를 추가하고 `tasks.json`을 커밋하세요.

```gitignore
!/.vscode/
/.vscode/*
!/.vscode/tasks.json
```

프로젝트가 `tools/`나 `.*`도 무시한다면 소스·`.python-version`·전용 `.gitignore`가 추적 대상인지 함께 확인하세요.

원본 프로젝트의 변경은 자동 반영되지 않습니다. 새 버전을 별도의 새 폴더로 내보내고 기존 복사본과 비교한 뒤 교체하세요.
소스와 `pyproject.toml`, `uv.lock`, `.python-version`을 한 버전으로 함께 교체하고 실행 환경과 Chromium을 다시 설치합니다.
직접 수정한 내용은 먼저 보관하고 병합하세요. 기존 `.venv`를 새 복사본으로 옮기지 마세요.
업데이트한 VS Code 예제는 자동 적용되지 않으므로 필요한 변경을 기존 작업 설정에 반영합니다.

실행 이름은 `jpick`에서 `algo-pick`으로 변경했으며 이전 이름의 호환 별칭은 제공하지 않습니다. 배포 패키지 `algorithm-problem-picker`와 내부 모듈 `algorithm_problem_picker`는 유지합니다. 기존 복사본 폴더는 자동 이동하지 않으므로 현재 경로를 유지하면 작업 예제의 `--directory` 경로를 맞추세요.

`export-manifest.json`에는 버전, 내보낸 UTC 시각, 원본 커밋, 미커밋 변경 여부와 파일별 SHA-256이 기록됩니다.
`source_dirty: true`는 해당 커밋 외의 변경도 있는 작업 폴더에서 복사했다는 뜻입니다.
Git 이력이 없는 소스 ZIP에서 내보냈다면 커밋과 변경 여부는 `null`이며 버전과 파일 해시로 구분합니다.
해시는 내보내기 시점의 비교용 기록이며 전자서명이나 자동 업데이트 기능은 아닙니다.
