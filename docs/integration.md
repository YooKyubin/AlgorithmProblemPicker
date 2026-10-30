# 다른 프로젝트 안에서 algo-pick 사용하기

`algo-pick`을 이 저장소에서 직접 실행할 수도 있고, 코딩테스트 프로젝트의 `tools/algo-pick` 같은 폴더에 독립 복사본으로 넣을 수도 있습니다.
후자는 원본 저장소를 계속 보관하거나 특정 절대 경로에 둘 필요가 없습니다. 업데이트는 명시적으로 복사본을 교체하여 진행합니다.

## 1. 독립 복사본 내보내기

이 저장소를 clone하거나 소스 ZIP을 풀고 [uv](https://docs.astral.sh/uv/getting-started/installation/)를 설치합니다.
**이 저장소 루트에서** 아래 명령을 실행합니다. Windows PowerShell과 macOS 셸에서 같은 명령입니다.
`../algorithm`은 이 저장소와 나란히 있는 사용 대상 프로젝트의 예시이므로 실제 경로로 바꾸세요.

```sh
uv run --no-project --python 3.12 python scripts/export_tool.py --target "../algorithm/tools/algo-pick"
```

내보내기 스크립트는 Python 표준 라이브러리만 사용하며 원본 프로젝트의 가상환경이나 개발 의존성을 설치하지 않습니다.
이미 Python 3.12 이상이 있다면 같은 스크립트를 직접 실행할 수도 있습니다.
상대 대상 경로는 명령을 실행한 현재 디렉터리를 기준으로 합니다. 공백이 있는 경로는 따옴표로 감싸세요.

```text
algorithm/
└─ tools/
   └─ algo-pick/
      ├─ src/algorithm_problem_picker/
      ├─ pyproject.toml
      ├─ uv.lock
      ├─ .python-version
      ├─ .gitignore
      ├─ README.md
      ├─ vscode-tasks.example.json
      └─ export-manifest.json
```

복사 대상은 소스·패키지 설정·Python 버전·사용 안내·VS Code 예제입니다.
원본의 `.venv`, Chromium, `.git`, 테스트, 벤치마크, 캐시와 빌드 산출물은 포함하지 않습니다.
예제는 [examples/vscode/tasks.json](../examples/vscode/tasks.json), 복사본 README는 [standalone.md](standalone.md)에서 관리합니다.

대상 경로가 이미 있으면 빈 폴더라도 종료 코드 1로 중단하며 내용을 수정하지 않습니다.
자동 덮어쓰기나 업데이트 옵션은 없습니다. 원본 저장소 안에서 시험하려면 `--target ./dist/algo-pick-preview`처럼 `dist/` 아래 새 경로를 사용하세요.
필수 파일 누락과 Git 이력 조회 오류도 복사 전에 중단합니다. Git 체크아웃에서는 `git` 명령이 필요합니다.
소스 ZIP처럼 `.git`이 없으면 커밋 정보 없이 내보낼 수 있습니다.
복사 도중 디스크 오류 등이 발생했다면 대상에 불완전한 파일이 남을 수 있으므로 확인 후 다른 새 경로에서 다시 실행하세요.

## 2. 각 PC에서 최초 설치

내보내기가 끝나면 **사용 대상 프로젝트 루트로 이동해서** 실행합니다.

```sh
uv --directory ./tools/algo-pick sync --locked --no-dev
uv --directory ./tools/algo-pick run --locked --no-dev playwright install chromium
uv --directory ./tools/algo-pick run --locked --no-dev algo-pick --version
uv --directory ./tools/algo-pick run --locked --no-dev algo-pick --platform jungol recommend --tier S5..G1 --rate 50.. --accepted 500.. --count 3
```

Windows·Mac에서 소스와 `uv.lock`을 공유하되 각 PC에서 `.venv`와 Playwright용 Chromium을 설치합니다.
Python 3.12는 uv가 필요하면 다운로드합니다. macOS에서도 지원되는 버전·CPU용 의존성을 선택합니다.
운영체제 지원 범위는 [Playwright 설치 문서](https://playwright.dev/python/docs/intro#system-requirements)를 확인하세요.
Windows에서 내보내기·복사본 CLI·로컬 Chromium·예제 작업 명령을 검증했습니다. macOS 실기기 실행은 아직 검증하지 않았습니다.
Windows용 EXE나 `.venv`를 Mac으로 가져가는 방식은 지원하지 않습니다.
같은 PC에서 도구 폴더 경로를 바꾼 경우에도 기존 `.venv`를 제거한 뒤 새 위치에서 다시 설치합니다.
패키지·Python·브라우저의 최초 설치 및 문제 조회에는 인터넷 연결이 필요합니다.

## 3. VS Code 연결

사용 대상 프로젝트에 `.vscode/tasks.json`이 없다면 `tools/algo-pick/vscode-tasks.example.json`을 해당 경로로 복사합니다.
기존 파일이 있으면 예제의 `tasks` 배열 항목 세 개와 `inputs` 배열 항목 다섯 개를 각각 추가하세요.
기존 항목은 유지하고, 같은 `label`이나 `id`가 있으면 비교하여 중복을 해결합니다. 스크립트는 이 파일을 자동 수정하지 않습니다.

프로젝트 루트를 VS Code로 열고 명령 팔레트(Windows `Ctrl+Shift+P`, macOS `Cmd+Shift+P`)에서 `Tasks: Run Task`를 선택합니다.

| 작업 | 동작 |
|---|---|
| `정올: 설치` | Python 환경과 Chromium 준비. 최초 또는 업데이트 후 실행 |
| `정올: 문제 추천` | 티어·정답률·정답 제출 수·추천 개수를 입력받아 실행 |
| `정올: 문제 목록` | 같은 조건과 표시 개수를 입력받아 목록 조회 |

경로는 `${workspaceFolder}/tools/algo-pick`이므로 OS별 절대 경로가 필요 없습니다.
다른 위치에 두었다면 세 작업의 `--directory` 다음 경로를 모두 수정하세요.
`command`는 `uv`, `type`은 `process`이므로 PowerShell이나 Bash 전용 구문에 의존하지 않습니다.
`options.env.PYTHONUTF8`은 한글 출력을 설정하며, 설치 작업의 `PLAYWRIGHT_SKIP_BROWSER_GC`는 기존 브라우저 설치본의 자동 정리를 막습니다.
입력 변수 `${input:algoPickTier}` 등은 최상위 `inputs`의 같은 `id`와 연결됩니다.
입력창의 범위·숫자는 `algo-pick`이 실행 전에 검사합니다. 전체 옵션은 CLI의 `--help`에서 확인하세요.

## 플랫폼과 지원 필터 확인

`--platform` 생략 시 정올을 사용하며 실제 지원 플랫폼은 소문자 `jungol` 하나입니다. `algo-pick --platform jungol recommend`처럼 명령 앞에 지정합니다. VS Code의 조회·추천 작업도 이 위치에 정올을 명시합니다. 프로그래머스 수집기는 제공하지 않습니다.

사용 대상 프로젝트 루트에서 다음 명령으로 선택 플랫폼의 필터·의미·허용 값·조합과 미지원 옵션을 확인합니다.

```sh
uv --directory ./tools/algo-pick run --locked --no-dev algo-pick --platform jungol list --help
uv --directory ./tools/algo-pick run --locked --no-dev algo-pick --platform jungol recommend --help
```

정올은 티어(B5~R1 또는 1~30), 정답률(0~100 정수·소수), 정답 제출 수(0 이상 정수), 공개 사용자 풀이 조건을 지원합니다. 정답 제출 수는 중복 정답 제출을 포함하며 푼 사람 수와 다릅니다. 범위는 양 끝을 포함하고 같은 지표의 범위·기존 경계 옵션 혼용과 범위 반복은 오류입니다. `solved/unsolved`에는 정확한 공개 핸들이 필요하고 `all + user`는 오류입니다.

미등록 플랫폼과 미지원 필터·잘못된 값은 접속 전에 코드 2로 거부합니다. 미지원 필터는 명시한 옵션을 모두 안내하며 0·명시적 기본값도 검사합니다. 플랫폼 미지원은 지원 속성의 개별 값 미제공과 다릅니다. 정올의 미제공 값은 해당 필터가 없으면 후보에 포함해 `미확인`으로 표시하고, 필터가 있으면 제외합니다.

## 4. Git으로 Windows·Mac 사이에 공유

`tools/algo-pick`의 소스, 패키지 설정, `.python-version`, 전용 `.gitignore`, README·예제·출처 파일을 커밋합니다.
`.venv`와 Python 캐시는 전용 `.gitignore`로 제외됩니다. `.gitignore`는 이미 추적 중인 파일의 추적을 해제하지는 않습니다.
Chromium은 사용자별 Playwright 공용 경로에 설치되므로 프로젝트에 들어가지 않습니다.
다른 PC에서 저장소를 받은 뒤 uv를 설치하고 `정올: 설치`를 실행하세요.

사용 대상 프로젝트가 `.vscode` 전체를 무시한다면 루트 `.gitignore`의 해당 규칙 **뒤에** 아래 예외를 추가합니다.
기존 무시 규칙이 없다면 이 예외를 추가할 필요는 없습니다.

```gitignore
# 기존 .vscode 무시 규칙 뒤에 배치
!/.vscode/
/.vscode/*
!/.vscode/tasks.json
```

`.vscode` 디렉터리를 다시 포함하고 그 안에서 `tasks.json`만 추적할 수 있게 합니다.
`tasks.json`을 실제로 커밋해야 작업 목록이 다른 PC로 전달됩니다.
프로젝트가 `tools/`나 `.*`를 추가로 무시한다면 소스·`.python-version`·전용 `.gitignore`가 빠지지 않는지도 확인하세요.

```sh
git check-ignore -v tools/algo-pick/.venv/pyvenv.cfg
git status --short --untracked-files=all -- tools/algo-pick .vscode/tasks.json
```

## 5. 업데이트와 출처 확인

원본 저장소를 원하는 버전으로 갱신한 뒤 기존 폴더가 아닌 `tools/algo-pick-next` 같은 **새 경로**로 내보냅니다.
기존 복사본의 직접 수정 사항을 비교·보관하고 새 복사본에 필요한 변경을 병합합니다.
도구 작업을 종료한 상태에서 프로젝트 내 복사본을 교체하고 최종 위치에서 실행 환경과 Chromium을 다시 설치하세요.
소스, `pyproject.toml`, `uv.lock`, `.python-version`을 서로 다른 버전에서 섞거나 기존 `.venv`를 옮기지 마세요.
업데이트 후 `algo-pick --version`과 `algo-pick --help`를 확인하고 새 VS Code 예제에서 필요한 변경을 기존 작업 설정에 반영합니다.

실행 이름은 `jpick`에서 `algo-pick`으로 바뀌었지만 배포 패키지 `algorithm-problem-picker`와 내부 모듈 `algorithm_problem_picker`는 유지합니다. 기존 외부 복사본 폴더는 자동 이동하지 않습니다. 기존 경로를 유지한다면 예제의 `--directory` 경로를 그 위치에 맞추세요. 새 input ID는 `algoPickTier` 등이며 참조와 정의를 함께 반영합니다.

`export-manifest.json`은 다음을 기록합니다.

| 항목 | 의미 |
|---|---|
| `version` | `pyproject.toml`의 프로젝트 버전 |
| `source_commit` | 내보낸 원본 체크아웃의 HEAD 커밋. Git 이력이 없으면 `null` |
| `source_dirty` | 원본 저장소에 미커밋·미추적 변경이 있었는지. Git 이력이 없으면 `null` |
| `exported_at` | 내보낸 UTC 시각 |
| `files` | 복사한 파일별 SHA-256. manifest 자체와 설치 후 생성한 파일은 제외 |

미커밋 변경이 있으면 커밋만으로 정확한 내용을 재현할 수 없으므로 이 상태와 파일 해시를 함께 확인하세요.
배포 기준을 명확히 하려면 변경을 커밋한 깨끗한 체크아웃에서 내보내면 됩니다.
원본 변경은 자동 반영되지 않으며, manifest는 출처 비교용 기록으로 전자서명을 제공하지 않습니다.
