# 다른 프로젝트에서 Git submodule로 사용하기

외부 프로젝트도 Git으로 관리하면서 `algorithm/tools/algo-pick` 안에 소스 파일을 두고 업데이트하는 방법입니다. 태그 없이 원격 기본 브랜치를 기준으로 업데이트합니다. `.venv`는 도구 폴더 안에 생성하며 Chromium은 사용자별 Playwright 공용 경로에 설치합니다.

## 최초 설치

Git과 [uv](https://docs.astral.sh/uv/getting-started/installation/)를 설치하고 **외부 프로젝트 루트(`algorithm`)에서** 실행합니다.

```sh
git submodule add https://github.com/YooKyubin/AlgorithmProblemPicker.git tools/algo-pick
uv --directory tools/algo-pick sync --locked --no-dev
uv --directory tools/algo-pick run --locked --no-dev playwright install chromium
```

기존 `tools/algo-pick` 복사본이 있으면 직접 수정한 내용을 보관하고 기존 폴더와 Git 추적 관계를 정리한 뒤 submodule을 추가합니다. 이 명령은 기존 복사본을 자동으로 전환하지 않습니다. 소스 외에 문서·테스트·업데이트 스크립트도 함께 받습니다.

`.gitmodules`와 submodule의 커밋 참조를 외부 프로젝트에 커밋합니다.

```sh
git add .gitmodules tools/algo-pick
git commit -m "Add algo-pick submodule"
```

기존 [VS Code 작업 예제](../examples/vscode/tasks.json)의 `tasks`와 `inputs`를 외부 프로젝트의 `.vscode/tasks.json`에 병합하면 설치·추천·목록 작업을 사용할 수 있습니다. 경로는 기존 `tools/algo-pick`을 유지합니다.

## 스크립트로 업데이트

원본 프로젝트에서 수정사항을 커밋하고 GitHub에 push한 뒤, **외부 프로젝트 루트에서** 다음 명령 하나로 업데이트합니다. Windows PowerShell과 macOS 셸에서 같은 명령입니다.

```sh
uv run --no-project --python 3.12 python tools/algo-pick/scripts/update_tool.py
```

`--no-project`는 업데이트 대상의 `.venv` 밖에서 스크립트를 실행하기 위한 옵션입니다. 스크립트는 Python 표준 라이브러리만 사용하고 파일 위치로 도구 경로와 부모 프로젝트를 찾으므로 다른 위치에서 실행하려면 스크립트 경로만 맞추면 됩니다.

실행 순서는 다음과 같습니다.

```sh
git submodule update --init --remote -- tools/algo-pick
uv --directory tools/algo-pick sync --locked --no-dev
uv --directory tools/algo-pick run --locked --no-dev playwright install chromium
```

각 단계의 종료 코드를 검사하며 실패하거나 취소하면 다음 단계를 실행하지 않습니다. 이미 성공한 단계는 되돌리지 않습니다. Git이 로컬 수정 충돌을 보고하면 수정 내용을 먼저 보관하거나 커밋한 뒤 다시 실행합니다. 강제 덮어쓰기는 하지 않습니다. 업데이트 중에는 문제 조회 작업을 종료해 두세요.

소스는 원격 기본 브랜치를 기준으로 갱신합니다. `.gitmodules`에 추적 브랜치를 설정했다면 해당 브랜치를 사용합니다. `uv.lock`으로 실행 환경을 맞추고 해당 Playwright 버전의 Chromium을 준비합니다. 이 스크립트는 submodule 전용이며 독립 복사본과 일반 clone에서는 실행을 거부합니다.

업데이트한 버전과 실행 결과를 확인한 뒤 외부 프로젝트에도 변경된 커밋 참조를 커밋합니다.

```sh
uv --directory tools/algo-pick run --locked --no-dev algo-pick --version
git diff --submodule=log -- tools/algo-pick
git add tools/algo-pick
git commit -m "Update algo-pick submodule"
```

VS Code 작업으로 등록하려면 기존 `.vscode/tasks.json`의 `tasks` 배열에 다음 항목을 추가합니다. 기존 항목과 같은 이름이 있으면 비교하여 중복을 해결합니다.

```json
{
    "label": "정올: 업데이트",
    "type": "process",
    "command": "uv",
    "args": [
        "run", "--no-project", "--python", "3.12", "python",
        "${workspaceFolder}/tools/algo-pick/scripts/update_tool.py"
    ],
    "options": {
        "cwd": "${workspaceFolder}",
        "env": { "PYTHONUTF8": "1", "PLAYWRIGHT_SKIP_BROWSER_GC": "1" }
    },
    "problemMatcher": []
}
```

## 다른 PC에서 같은 버전 받기

외부 프로젝트를 clone하거나 pull한 뒤에는 기록된 submodule 버전을 준비합니다.

```sh
git submodule update --init --recursive -- tools/algo-pick
uv --directory tools/algo-pick sync --locked --no-dev
uv --directory tools/algo-pick run --locked --no-dev playwright install chromium
```

여기서는 `--remote`를 붙이지 않습니다. 최신 버전으로 올리는 작업과 외부 프로젝트에 기록된 버전을 받는 작업을 구분합니다. `.venv`와 Chromium은 PC마다 설치하며 Git으로 공유하지 않습니다.

`export_tool.py`로 내보낸 독립 복사본은 이 스크립트를 포함하지 않습니다. 해당 방식은 [복사본 업데이트 안내](integration.md#5-업데이트와-출처-확인)를 따릅니다.
