# algo-pick

알고리즘 사이트의 공개 문제를 조건으로 조회하고 무작위로 추천받는 CLI입니다. 현재 지원 플랫폼은 `jungol`이며, 앞으로 다른 플랫폼도 추가할 계획입니다.

## 설치

Python 3.12 이상과 [uv](https://docs.astral.sh/uv/getting-started/installation/)가 필요합니다. 저장소를 내려받고 프로젝트 루트에서 실행하세요.

```sh
uv sync --locked --python 3.12
uv run --locked playwright install chromium
```

## 문제 추천·조회

```sh
# 실버 5~골드 1, 정답률 50% 이상인 문제 3개 추천
uv run --locked algo-pick recommend --tier S5..G1 --rate 50.. --count 3

# 정답 제출 수가 500건 이상인 문제를 많은 순서로 20개 조회
uv run --locked algo-pick list --accepted 500.. --sort accepted --order desc --limit 20

# 지정한 공개 사용자가 아직 풀지 않은 문제 조회 (JUNGOL을 본인 핸들로 변경)
uv run --locked algo-pick list --user JUNGOL --status unsolved --tier S5..G1

# 문제 번호로 기본 브라우저에서 열기
uv run --locked algo-pick open 1000 1001
```

플랫폼을 직접 지정하려면 명령 앞에 붙입니다. 생략하면 정올을 사용합니다.

```sh
uv run --locked algo-pick --platform jungol recommend --count 3
```

조회 중에는 `Ctrl+C`로 취소할 수 있습니다.

## 조건 지정

| 옵션 | 사용 예시 |
|---|---|
| `--tier` | `S5..G1`: 실버 5~골드 1, `G5..`: 골드 5 이상 |
| `--rate` | `40.5..80`: 정답률 40.5~80%, `50..`: 50% 이상 |
| `--accepted` | `500..1000`: 정답 제출 500~1,000건 |
| `--user`, `--status` | 공개 핸들과 `solved` 또는 `unsolved`를 함께 지정 |
| `recommend --count` | 추천 개수, 기본 1개 |
| `list --limit` | 표시 개수, 기본 20개 |
| `list --sort` | `id`, `difficulty`, `rate`, `accepted`, `random` |
| `list --order` | `asc`(오름차순), `desc`(내림차순). 무작위 정렬에는 `asc` 사용 |

범위는 `최솟값..최댓값`, `최솟값..`, `..최댓값`으로 지정하며 양 끝을 포함합니다. 한 값만 지정하려면 `--tier B5..B5`처럼 입력하세요.

티어는 `B`, `S`, `G`, `P`, `D`, `R`에 `5`~`1`을 붙입니다. 각 티어 안에서는 5가 가장 쉽습니다. 티어는 사이트 검색 조건이므로 결과의 표시 티어가 요청 범위 밖일 수 있습니다.

정답 제출 수는 같은 사용자의 중복 제출을 포함하며, 푼 사람 수와 다릅니다.

전체 옵션과 지원 조건은 도움말에서 확인하세요.

```sh
uv run --locked algo-pick --help
uv run --locked algo-pick recommend --help
uv run --locked algo-pick list --help
uv run --locked algo-pick open --help
```

## 다른 프로젝트·VS Code에서 사용

이 저장소 루트에서 새 경로로 소스를 내보냅니다. 대상 경로는 사용할 프로젝트에 맞게 바꾸세요.

```sh
uv run --no-project --python 3.12 python scripts/export_tool.py --target "../algorithm/tools/algo-pick"
```

복사본 설치와 VS Code의 `정올: 설치`, `정올: 문제 추천`, `정올: 문제 목록` 작업 연결은 [통합 가이드](docs/integration.md)를 참고하세요. [작업 설정 예제](examples/vscode/tasks.json)도 제공합니다.
