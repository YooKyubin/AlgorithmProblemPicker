# Local collection replay benchmark

고정 HTML 로컬 재생 결과다. 실사이트의 개선율로 일반화하지 않는다.

CLI import 후 명령 호출 직전부터 출력·브라우저 정리까지 전체 시간을 측정했다. 별도 프로세스 시작/import 시간은 제외한다. 제품의 기본 1초 시작 간격과 30초/15초 제한을 유지했다.

## Environment and source identity

```json
{
  "measured_at": "2026-10-20T16:20:21.320625+00:00",
  "platform": "Windows-11-10.0.26200-SP0",
  "python": "3.12.13 (main, Mar 24 2026, 22:57:53) [MSC v.1944 64 bit (AMD64)]",
  "executable": "./.venv/Scripts/python.exe",
  "runs": 3,
  "baseline_revision": "c37208f5a80628df5d7126972d31461b2517177d",
  "baseline_dirty": false,
  "current_revision": "c37208f5a80628df5d7126972d31461b2517177d",
  "current_dirty": true,
  "current_status": "M README.md\n M scripts/benchmark_selection.py\n M scripts/validate_live.py\n M src/algorithm_problem_picker/cli.py\n M src/algorithm_problem_picker/jungol.py\n M src/algorithm_problem_picker/models.py\n M src/algorithm_problem_picker/ports.py\n M src/algorithm_problem_picker/selection.py\n M src/algorithm_problem_picker/service.py\n M tests/conftest.py\n M tests/fixtures/jungol/list.html\n M tests/fixtures/jungol/pagination.html\n M tests/test_cli.py\n M tests/test_jungol_dom.py\n M tests/test_selection.py\n M tests/test_service.py\n?? scripts/benchmark_collection.py\n?? specs/002-improve-list-collection/\n?? tests/fixtures/jungol/benchmark/\n?? tests/fixtures/jungol/tier-pagination.html",
  "commands": {
    "list": [
      "list",
      "--sort",
      "id",
      "--order",
      "asc",
      "--limit",
      "1"
    ],
    "recommend": [
      "recommend",
      "--count",
      "1"
    ]
  },
  "fixture_root": "./tests/fixtures/jungol/benchmark",
  "fixture_sha256": {
    "detail-1000.html": "25a1046deab77a88541de9c36108f2cd27eaa18d5ffacc311a5b6bdf9aff7749",
    "detail-1001.html": "40b896536f2e48253c666ced697c16bc01818663f34dcfdd3d95db7dda24616a",
    "detail-1002.html": "b4b13a3d7e7116e1892b4b68e5276f935fb17d613a2d32b98c310421b78f8cfe",
    "detail-1003.html": "e79dc5710e80880afb4e9ba4f4993b923268c579b259652154e7617c9a590e7b",
    "page-1.html": "4db6757ddcc8ef3048c3cf61884c27f4463d39888934db509a0a6ad6cd831609",
    "page-2.html": "330fa87c976f0692e80d8b2131bcfc64797dc5402edd6f37ae40ecb4d174d6ff"
  },
  "harness_path": "./scripts/benchmark_collection.py",
  "harness_sha256": "21d7382e7128b6ddbc799e125c4ec8ec97cb37728c3eed9ccc08580feae13b9f",
  "lock_sha256": "8129099b0947f301987b7c988209a531bafbb65afc3206aa9fec7de237eff88f",
  "current_source_sha256": {
    "__init__.py": "1af78146d541b1bb1638ace221b8c4d32d47fa6d38b5c586b03d0b02c1cff3c7",
    "cli.py": "3f9d928fc29c533536ca1533030e362720e5f271da54d4ba06312440cf3bec6a",
    "jungol.py": "2f70de1702f09c29d052c9168c3f022f2769228b367732ae307787f587b699cc",
    "models.py": "c6b8449a85e6d3e4ae4b6b1c44807115faa5064d17f1ec45e585bfd3e203d28f",
    "ports.py": "a25e86108d05993b78bfec9d59fa361659bed22ae4a4be678641d12e3ea11567",
    "selection.py": "001422d95e48c3d665c94e09881daaa67c563b8b56239e08c80f91f7e0945944",
    "service.py": "7deaba19099c211c68be00938264c67736cfce697f7154082aae71b744c07ebc"
  },
  "dependencies": {
    "typer": "0.27.3",
    "rich": "15.0.0",
    "playwright": "1.64.0",
    "pytest": "9.1.1"
  }
}
```

## Raw timings

| Command | Version | Run | Fetched/eligible/returned | Detail requests | Total seconds | Collect seconds |
| --- | --- | ---: | --- | ---: | ---: | ---: |
| list | baseline | 1 | 4/4/1 | 4 | 5.491299 | 1.073797 |
| list | current | 1 | 4/4/1 | 0 | 1.575584 | 1.216903 |
| list | baseline | 2 | 4/4/1 | 4 | 5.464968 | 1.079420 |
| list | current | 2 | 4/4/1 | 0 | 1.572277 | 1.224385 |
| list | baseline | 3 | 4/4/1 | 4 | 5.488668 | 1.068255 |
| list | current | 3 | 4/4/1 | 0 | 1.580681 | 1.228032 |
| recommend | baseline | 1 | 4/4/1 | 4 | 5.454479 | 1.074818 |
| recommend | current | 1 | 4/4/1 | 0 | 1.563238 | 1.205162 |
| recommend | baseline | 2 | 4/4/1 | 4 | 5.474308 | 1.080322 |
| recommend | current | 2 | 4/4/1 | 0 | 1.558958 | 1.211870 |
| recommend | baseline | 3 | 4/4/1 | 4 | 5.474948 | 1.081357 |
| recommend | current | 3 | 4/4/1 | 0 | 1.605426 | 1.245700 |

## Medians

| Command | Version | Total seconds | Collect seconds |
| --- | --- | ---: | ---: |
| list | baseline | 5.488668 | 1.073797 |
| list | current | 1.575584 | 1.224385 |
| recommend | baseline | 5.474308 | 1.080322 |
| recommend | current | 1.563238 | 1.211870 |

## Verdict

PASS


## Full samples (import paths, output and diagnostics)

```json
[
  {
    "command": "list",
    "label": "baseline",
    "imports": {
      "algorithm_problem_picker.cli": "%TEMP%/jpick-benchmark-pbiatupe/baseline/src/algorithm_problem_picker/cli.py",
      "algorithm_problem_picker.jungol": "%TEMP%/jpick-benchmark-pbiatupe/baseline/src/algorithm_problem_picker/jungol.py",
      "algorithm_problem_picker.models": "%TEMP%/jpick-benchmark-pbiatupe/baseline/src/algorithm_problem_picker/models.py",
      "algorithm_problem_picker.service": "%TEMP%/jpick-benchmark-pbiatupe/baseline/src/algorithm_problem_picker/service.py"
    },
    "python": "3.12.13 (main, Mar 24 2026, 22:57:53) [MSC v.1944 64 bit (AMD64)]",
    "executable": "./.venv/Scripts/python.exe",
    "dependencies": {
      "typer": "0.27.3",
      "rich": "15.0.0",
      "playwright": "1.64.0",
      "pytest": "9.1.1"
    },
    "detail_requests": 4,
    "blocked_requests": [],
    "listing_seconds": 1.0737971999988076,
    "browser": "156.0.8078.4",
    "candidate_ids": [
      1000,
      1001,
      1002,
      1003
    ],
    "fetched": 4,
    "eligible": 4,
    "returned": 1,
    "shortage": 0,
    "selected_ids": [
      1000
    ],
    "eligible_ids": [
      1000,
      1001,
      1002,
      1003
    ],
    "total_seconds": 5.491298599998117,
    "exit_code": 0,
    "stdout": "                                  푼 사람                                      \n 번호  제목       난이도  정답률  수         링크                              \n 1000  두 정수    1       47.45%  5171       https://jungol.co.kr/problem/1000 \n       더하기                                                                  \n조건: status=all\n조회 4 · 적격 4 · 요청 1 · 표시 1\n조회 시각: 2026-10-21T01:20:22.319229+09:00 ~ 2026-10-21T01:20:27.418965+09:00\n티어·정답률은 목록 관측값, 푼 사람 수는 각 상세 조회 시점의 값입니다.\n",
    "stderr": "조회 시작 · Ctrl+C 취소\nCollecting · 수집 0 · 상세 0 · Ctrl+C 취소\nCollecting · 수집 3개 · Ctrl+C 취소\nCollecting · 수집 4개 · Ctrl+C 취소\nEnriching · 수집 4 · 상세 0 · Ctrl+C 취소\nEnriching · 수집 4 · 상세 1 · Ctrl+C 취소\nEnriching · 수집 4 · 상세 2 · Ctrl+C 취소\nEnriching · 수집 4 · 상세 3 · Ctrl+C 취소\nEnriching · 수집 4 · 상세 4 · Ctrl+C 취소\nComplete · 수집 4 · 상세 4 · Ctrl+C 취소\n",
    "run": 1
  },
  {
    "command": "list",
    "label": "current",
    "imports": {
      "algorithm_problem_picker.cli": "./src/algorithm_problem_picker/cli.py",
      "algorithm_problem_picker.jungol": "./src/algorithm_problem_picker/jungol.py",
      "algorithm_problem_picker.models": "./src/algorithm_problem_picker/models.py",
      "algorithm_problem_picker.service": "./src/algorithm_problem_picker/service.py"
    },
    "python": "3.12.13 (main, Mar 24 2026, 22:57:53) [MSC v.1944 64 bit (AMD64)]",
    "executable": "./.venv/Scripts/python.exe",
    "dependencies": {
      "typer": "0.27.3",
      "rich": "15.0.0",
      "playwright": "1.64.0",
      "pytest": "9.1.1"
    },
    "detail_requests": 0,
    "blocked_requests": [],
    "listing_seconds": 1.2169027000018104,
    "browser": "156.0.8078.4",
    "candidate_ids": [
      1000,
      1001,
      1002,
      1003
    ],
    "fetched": 4,
    "eligible": 4,
    "returned": 1,
    "shortage": 0,
    "selected_ids": [
      1000
    ],
    "eligible_ids": [
      1000,
      1001,
      1002,
      1003
    ],
    "total_seconds": 1.575584099999105,
    "exit_code": 0,
    "stdout": "                                  정답 제 …                                    \n 번호  제목       난이도  정답률  수         링크                              \n 1000  두 정수    1       47.45%  6510       https://jungol.co.kr/problem/1000 \n       더하기                                                                  \n조건: status=all\n조회 4 · 적격 4 · 요청 1 · 표시 1\n조회 시각: 2026-10-21T01:20:28.162897+09:00 ~ 2026-10-21T01:20:29.379285+09:00\n티어·정답률·정답 제출 수는 각 목록 관측 시점의 값입니다. 정답 제출 수는 동일 \n사용자의 중복 정답 제출을 포함합니다.\n",
    "stderr": "조회 시작 · Ctrl+C 취소\nCollecting · 수집 0 · Ctrl+C 취소\nCollecting · 수집 3개 · Ctrl+C 취소\nCollecting · 수집 4개 · Ctrl+C 취소\nProcessing · 수집 4 · Ctrl+C 취소\nComplete · 수집 4 · Ctrl+C 취소\n",
    "run": 1
  },
  {
    "command": "list",
    "label": "baseline",
    "imports": {
      "algorithm_problem_picker.cli": "%TEMP%/jpick-benchmark-pbiatupe/baseline/src/algorithm_problem_picker/cli.py",
      "algorithm_problem_picker.jungol": "%TEMP%/jpick-benchmark-pbiatupe/baseline/src/algorithm_problem_picker/jungol.py",
      "algorithm_problem_picker.models": "%TEMP%/jpick-benchmark-pbiatupe/baseline/src/algorithm_problem_picker/models.py",
      "algorithm_problem_picker.service": "%TEMP%/jpick-benchmark-pbiatupe/baseline/src/algorithm_problem_picker/service.py"
    },
    "python": "3.12.13 (main, Mar 24 2026, 22:57:53) [MSC v.1944 64 bit (AMD64)]",
    "executable": "./.venv/Scripts/python.exe",
    "dependencies": {
      "typer": "0.27.3",
      "rich": "15.0.0",
      "playwright": "1.64.0",
      "pytest": "9.1.1"
    },
    "detail_requests": 4,
    "blocked_requests": [],
    "listing_seconds": 1.0794198000003234,
    "browser": "156.0.8078.4",
    "candidate_ids": [
      1000,
      1001,
      1002,
      1003
    ],
    "fetched": 4,
    "eligible": 4,
    "returned": 1,
    "shortage": 0,
    "selected_ids": [
      1000
    ],
    "eligible_ids": [
      1000,
      1001,
      1002,
      1003
    ],
    "total_seconds": 5.464968200001749,
    "exit_code": 0,
    "stdout": "                                  푼 사람                                      \n 번호  제목       난이도  정답률  수         링크                              \n 1000  두 정수    1       47.45%  5171       https://jungol.co.kr/problem/1000 \n       더하기                                                                  \n조건: status=all\n조회 4 · 적격 4 · 요청 1 · 표시 1\n조회 시각: 2026-10-21T01:20:30.133981+09:00 ~ 2026-10-21T01:20:35.219861+09:00\n티어·정답률은 목록 관측값, 푼 사람 수는 각 상세 조회 시점의 값입니다.\n",
    "stderr": "조회 시작 · Ctrl+C 취소\nCollecting · 수집 0 · 상세 0 · Ctrl+C 취소\nCollecting · 수집 3개 · Ctrl+C 취소\nCollecting · 수집 4개 · Ctrl+C 취소\nEnriching · 수집 4 · 상세 0 · Ctrl+C 취소\nEnriching · 수집 4 · 상세 1 · Ctrl+C 취소\nEnriching · 수집 4 · 상세 2 · Ctrl+C 취소\nEnriching · 수집 4 · 상세 3 · Ctrl+C 취소\nEnriching · 수집 4 · 상세 4 · Ctrl+C 취소\nComplete · 수집 4 · 상세 4 · Ctrl+C 취소\n",
    "run": 2
  },
  {
    "command": "list",
    "label": "current",
    "imports": {
      "algorithm_problem_picker.cli": "./src/algorithm_problem_picker/cli.py",
      "algorithm_problem_picker.jungol": "./src/algorithm_problem_picker/jungol.py",
      "algorithm_problem_picker.models": "./src/algorithm_problem_picker/models.py",
      "algorithm_problem_picker.service": "./src/algorithm_problem_picker/service.py"
    },
    "python": "3.12.13 (main, Mar 24 2026, 22:57:53) [MSC v.1944 64 bit (AMD64)]",
    "executable": "./.venv/Scripts/python.exe",
    "dependencies": {
      "typer": "0.27.3",
      "rich": "15.0.0",
      "playwright": "1.64.0",
      "pytest": "9.1.1"
    },
    "detail_requests": 0,
    "blocked_requests": [],
    "listing_seconds": 1.2243852999999945,
    "browser": "156.0.8078.4",
    "candidate_ids": [
      1000,
      1001,
      1002,
      1003
    ],
    "fetched": 4,
    "eligible": 4,
    "returned": 1,
    "shortage": 0,
    "selected_ids": [
      1000
    ],
    "eligible_ids": [
      1000,
      1001,
      1002,
      1003
    ],
    "total_seconds": 1.5722774000023492,
    "exit_code": 0,
    "stdout": "                                  정답 제 …                                    \n 번호  제목       난이도  정답률  수         링크                              \n 1000  두 정수    1       47.45%  6510       https://jungol.co.kr/problem/1000 \n       더하기                                                                  \n조건: status=all\n조회 4 · 적격 4 · 요청 1 · 표시 1\n조회 시각: 2026-10-21T01:20:35.950782+09:00 ~ 2026-10-21T01:20:37.175767+09:00\n티어·정답률·정답 제출 수는 각 목록 관측 시점의 값입니다. 정답 제출 수는 동일 \n사용자의 중복 정답 제출을 포함합니다.\n",
    "stderr": "조회 시작 · Ctrl+C 취소\nCollecting · 수집 0 · Ctrl+C 취소\nCollecting · 수집 3개 · Ctrl+C 취소\nCollecting · 수집 4개 · Ctrl+C 취소\nProcessing · 수집 4 · Ctrl+C 취소\nComplete · 수집 4 · Ctrl+C 취소\n",
    "run": 2
  },
  {
    "command": "list",
    "label": "baseline",
    "imports": {
      "algorithm_problem_picker.cli": "%TEMP%/jpick-benchmark-pbiatupe/baseline/src/algorithm_problem_picker/cli.py",
      "algorithm_problem_picker.jungol": "%TEMP%/jpick-benchmark-pbiatupe/baseline/src/algorithm_problem_picker/jungol.py",
      "algorithm_problem_picker.models": "%TEMP%/jpick-benchmark-pbiatupe/baseline/src/algorithm_problem_picker/models.py",
      "algorithm_problem_picker.service": "%TEMP%/jpick-benchmark-pbiatupe/baseline/src/algorithm_problem_picker/service.py"
    },
    "python": "3.12.13 (main, Mar 24 2026, 22:57:53) [MSC v.1944 64 bit (AMD64)]",
    "executable": "./.venv/Scripts/python.exe",
    "dependencies": {
      "typer": "0.27.3",
      "rich": "15.0.0",
      "playwright": "1.64.0",
      "pytest": "9.1.1"
    },
    "detail_requests": 4,
    "blocked_requests": [],
    "listing_seconds": 1.0682550000019546,
    "browser": "156.0.8078.4",
    "candidate_ids": [
      1000,
      1001,
      1002,
      1003
    ],
    "fetched": 4,
    "eligible": 4,
    "returned": 1,
    "shortage": 0,
    "selected_ids": [
      1000
    ],
    "eligible_ids": [
      1000,
      1001,
      1002,
      1003
    ],
    "total_seconds": 5.488667800000258,
    "exit_code": 0,
    "stdout": "                                  푼 사람                                      \n 번호  제목       난이도  정답률  수         링크                              \n 1000  두 정수    1       47.45%  5171       https://jungol.co.kr/problem/1000 \n       더하기                                                                  \n조건: status=all\n조회 4 · 적격 4 · 요청 1 · 표시 1\n조회 시각: 2026-10-21T01:20:37.928199+09:00 ~ 2026-10-21T01:20:43.029116+09:00\n티어·정답률은 목록 관측값, 푼 사람 수는 각 상세 조회 시점의 값입니다.\n",
    "stderr": "조회 시작 · Ctrl+C 취소\nCollecting · 수집 0 · 상세 0 · Ctrl+C 취소\nCollecting · 수집 3개 · Ctrl+C 취소\nCollecting · 수집 4개 · Ctrl+C 취소\nEnriching · 수집 4 · 상세 0 · Ctrl+C 취소\nEnriching · 수집 4 · 상세 1 · Ctrl+C 취소\nEnriching · 수집 4 · 상세 2 · Ctrl+C 취소\nEnriching · 수집 4 · 상세 3 · Ctrl+C 취소\nEnriching · 수집 4 · 상세 4 · Ctrl+C 취소\nComplete · 수집 4 · 상세 4 · Ctrl+C 취소\n",
    "run": 3
  },
  {
    "command": "list",
    "label": "current",
    "imports": {
      "algorithm_problem_picker.cli": "./src/algorithm_problem_picker/cli.py",
      "algorithm_problem_picker.jungol": "./src/algorithm_problem_picker/jungol.py",
      "algorithm_problem_picker.models": "./src/algorithm_problem_picker/models.py",
      "algorithm_problem_picker.service": "./src/algorithm_problem_picker/service.py"
    },
    "python": "3.12.13 (main, Mar 24 2026, 22:57:53) [MSC v.1944 64 bit (AMD64)]",
    "executable": "./.venv/Scripts/python.exe",
    "dependencies": {
      "typer": "0.27.3",
      "rich": "15.0.0",
      "playwright": "1.64.0",
      "pytest": "9.1.1"
    },
    "detail_requests": 0,
    "blocked_requests": [],
    "listing_seconds": 1.2280323000013595,
    "browser": "156.0.8078.4",
    "candidate_ids": [
      1000,
      1001,
      1002,
      1003
    ],
    "fetched": 4,
    "eligible": 4,
    "returned": 1,
    "shortage": 0,
    "selected_ids": [
      1000
    ],
    "eligible_ids": [
      1000,
      1001,
      1002,
      1003
    ],
    "total_seconds": 1.5806808000015735,
    "exit_code": 0,
    "stdout": "                                  정답 제 …                                    \n 번호  제목       난이도  정답률  수         링크                              \n 1000  두 정수    1       47.45%  6510       https://jungol.co.kr/problem/1000 \n       더하기                                                                  \n조건: status=all\n조회 4 · 적격 4 · 요청 1 · 표시 1\n조회 시각: 2026-10-21T01:20:43.762850+09:00 ~ 2026-10-21T01:20:44.991965+09:00\n티어·정답률·정답 제출 수는 각 목록 관측 시점의 값입니다. 정답 제출 수는 동일 \n사용자의 중복 정답 제출을 포함합니다.\n",
    "stderr": "조회 시작 · Ctrl+C 취소\nCollecting · 수집 0 · Ctrl+C 취소\nCollecting · 수집 3개 · Ctrl+C 취소\nCollecting · 수집 4개 · Ctrl+C 취소\nProcessing · 수집 4 · Ctrl+C 취소\nComplete · 수집 4 · Ctrl+C 취소\n",
    "run": 3
  },
  {
    "command": "recommend",
    "label": "baseline",
    "imports": {
      "algorithm_problem_picker.cli": "%TEMP%/jpick-benchmark-pbiatupe/baseline/src/algorithm_problem_picker/cli.py",
      "algorithm_problem_picker.jungol": "%TEMP%/jpick-benchmark-pbiatupe/baseline/src/algorithm_problem_picker/jungol.py",
      "algorithm_problem_picker.models": "%TEMP%/jpick-benchmark-pbiatupe/baseline/src/algorithm_problem_picker/models.py",
      "algorithm_problem_picker.service": "%TEMP%/jpick-benchmark-pbiatupe/baseline/src/algorithm_problem_picker/service.py"
    },
    "python": "3.12.13 (main, Mar 24 2026, 22:57:53) [MSC v.1944 64 bit (AMD64)]",
    "executable": "./.venv/Scripts/python.exe",
    "dependencies": {
      "typer": "0.27.3",
      "rich": "15.0.0",
      "playwright": "1.64.0",
      "pytest": "9.1.1"
    },
    "detail_requests": 4,
    "blocked_requests": [],
    "listing_seconds": 1.0748177000023134,
    "browser": "156.0.8078.4",
    "candidate_ids": [
      1000,
      1001,
      1002,
      1003
    ],
    "fetched": 4,
    "eligible": 4,
    "returned": 1,
    "shortage": 0,
    "selected_ids": [
      1003
    ],
    "eligible_ids": [
      1000,
      1001,
      1002,
      1003
    ],
    "total_seconds": 5.454478999999992,
    "exit_code": 0,
    "stdout": "                                  푼 사람                                      \n 번호  제목       난이도  정답률  수         링크                              \n 1003  다음       2       50.00%  5171       https://jungol.co.kr/problem/1003 \n       페이지                                                                  \n조건: status=all\n조회 4 · 적격 4 · 요청 1 · 반환 1\n부족 0개\n조회 시각: 2026-10-21T01:20:45.748983+09:00 ~ 2026-10-21T01:20:50.831825+09:00\n티어·정답률은 목록 관측값, 푼 사람 수는 각 상세 조회 시점의 값입니다.\n",
    "stderr": "조회 시작 · Ctrl+C 취소\nCollecting · 수집 0 · 상세 0 · Ctrl+C 취소\nCollecting · 수집 3개 · Ctrl+C 취소\nCollecting · 수집 4개 · Ctrl+C 취소\nEnriching · 수집 4 · 상세 0 · Ctrl+C 취소\nEnriching · 수집 4 · 상세 1 · Ctrl+C 취소\nEnriching · 수집 4 · 상세 2 · Ctrl+C 취소\nEnriching · 수집 4 · 상세 3 · Ctrl+C 취소\nEnriching · 수집 4 · 상세 4 · Ctrl+C 취소\nComplete · 수집 4 · 상세 4 · Ctrl+C 취소\n",
    "run": 1
  },
  {
    "command": "recommend",
    "label": "current",
    "imports": {
      "algorithm_problem_picker.cli": "./src/algorithm_problem_picker/cli.py",
      "algorithm_problem_picker.jungol": "./src/algorithm_problem_picker/jungol.py",
      "algorithm_problem_picker.models": "./src/algorithm_problem_picker/models.py",
      "algorithm_problem_picker.service": "./src/algorithm_problem_picker/service.py"
    },
    "python": "3.12.13 (main, Mar 24 2026, 22:57:53) [MSC v.1944 64 bit (AMD64)]",
    "executable": "./.venv/Scripts/python.exe",
    "dependencies": {
      "typer": "0.27.3",
      "rich": "15.0.0",
      "playwright": "1.64.0",
      "pytest": "9.1.1"
    },
    "detail_requests": 0,
    "blocked_requests": [],
    "listing_seconds": 1.20516189999762,
    "browser": "156.0.8078.4",
    "candidate_ids": [
      1000,
      1001,
      1002,
      1003
    ],
    "fetched": 4,
    "eligible": 4,
    "returned": 1,
    "shortage": 0,
    "selected_ids": [
      1003
    ],
    "eligible_ids": [
      1000,
      1001,
      1002,
      1003
    ],
    "total_seconds": 1.5632377000001725,
    "exit_code": 0,
    "stdout": "                                  정답 제 …                                    \n 번호  제목       난이도  정답률  수         링크                              \n 1003  다음       2       50.00%  20         https://jungol.co.kr/problem/1003 \n       페이지                                                                  \n조건: status=all\n조회 4 · 적격 4 · 요청 1 · 반환 1\n부족 0개\n조회 시각: 2026-10-21T01:20:51.561803+09:00 ~ 2026-10-21T01:20:52.768183+09:00\n티어·정답률·정답 제출 수는 각 목록 관측 시점의 값입니다. 정답 제출 수는 동일 \n사용자의 중복 정답 제출을 포함합니다.\n",
    "stderr": "조회 시작 · Ctrl+C 취소\nCollecting · 수집 0 · Ctrl+C 취소\nCollecting · 수집 3개 · Ctrl+C 취소\nCollecting · 수집 4개 · Ctrl+C 취소\nProcessing · 수집 4 · Ctrl+C 취소\nComplete · 수집 4 · Ctrl+C 취소\n",
    "run": 1
  },
  {
    "command": "recommend",
    "label": "baseline",
    "imports": {
      "algorithm_problem_picker.cli": "%TEMP%/jpick-benchmark-pbiatupe/baseline/src/algorithm_problem_picker/cli.py",
      "algorithm_problem_picker.jungol": "%TEMP%/jpick-benchmark-pbiatupe/baseline/src/algorithm_problem_picker/jungol.py",
      "algorithm_problem_picker.models": "%TEMP%/jpick-benchmark-pbiatupe/baseline/src/algorithm_problem_picker/models.py",
      "algorithm_problem_picker.service": "%TEMP%/jpick-benchmark-pbiatupe/baseline/src/algorithm_problem_picker/service.py"
    },
    "python": "3.12.13 (main, Mar 24 2026, 22:57:53) [MSC v.1944 64 bit (AMD64)]",
    "executable": "./.venv/Scripts/python.exe",
    "dependencies": {
      "typer": "0.27.3",
      "rich": "15.0.0",
      "playwright": "1.64.0",
      "pytest": "9.1.1"
    },
    "detail_requests": 4,
    "blocked_requests": [],
    "listing_seconds": 1.0803223000002617,
    "browser": "156.0.8078.4",
    "candidate_ids": [
      1000,
      1001,
      1002,
      1003
    ],
    "fetched": 4,
    "eligible": 4,
    "returned": 1,
    "shortage": 0,
    "selected_ids": [
      1003
    ],
    "eligible_ids": [
      1000,
      1001,
      1002,
      1003
    ],
    "total_seconds": 5.4743077000021,
    "exit_code": 0,
    "stdout": "                                  푼 사람                                      \n 번호  제목       난이도  정답률  수         링크                              \n 1003  다음       2       50.00%  5171       https://jungol.co.kr/problem/1003 \n       페이지                                                                  \n조건: status=all\n조회 4 · 적격 4 · 요청 1 · 반환 1\n부족 0개\n조회 시각: 2026-10-21T01:20:53.533996+09:00 ~ 2026-10-21T01:20:58.627194+09:00\n티어·정답률은 목록 관측값, 푼 사람 수는 각 상세 조회 시점의 값입니다.\n",
    "stderr": "조회 시작 · Ctrl+C 취소\nCollecting · 수집 0 · 상세 0 · Ctrl+C 취소\nCollecting · 수집 3개 · Ctrl+C 취소\nCollecting · 수집 4개 · Ctrl+C 취소\nEnriching · 수집 4 · 상세 0 · Ctrl+C 취소\nEnriching · 수집 4 · 상세 1 · Ctrl+C 취소\nEnriching · 수집 4 · 상세 2 · Ctrl+C 취소\nEnriching · 수집 4 · 상세 3 · Ctrl+C 취소\nEnriching · 수집 4 · 상세 4 · Ctrl+C 취소\nComplete · 수집 4 · 상세 4 · Ctrl+C 취소\n",
    "run": 2
  },
  {
    "command": "recommend",
    "label": "current",
    "imports": {
      "algorithm_problem_picker.cli": "./src/algorithm_problem_picker/cli.py",
      "algorithm_problem_picker.jungol": "./src/algorithm_problem_picker/jungol.py",
      "algorithm_problem_picker.models": "./src/algorithm_problem_picker/models.py",
      "algorithm_problem_picker.service": "./src/algorithm_problem_picker/service.py"
    },
    "python": "3.12.13 (main, Mar 24 2026, 22:57:53) [MSC v.1944 64 bit (AMD64)]",
    "executable": "./.venv/Scripts/python.exe",
    "dependencies": {
      "typer": "0.27.3",
      "rich": "15.0.0",
      "playwright": "1.64.0",
      "pytest": "9.1.1"
    },
    "detail_requests": 0,
    "blocked_requests": [],
    "listing_seconds": 1.2118695000026491,
    "browser": "156.0.8078.4",
    "candidate_ids": [
      1000,
      1001,
      1002,
      1003
    ],
    "fetched": 4,
    "eligible": 4,
    "returned": 1,
    "shortage": 0,
    "selected_ids": [
      1003
    ],
    "eligible_ids": [
      1000,
      1001,
      1002,
      1003
    ],
    "total_seconds": 1.5589583000000857,
    "exit_code": 0,
    "stdout": "                                  정답 제 …                                    \n 번호  제목       난이도  정답률  수         링크                              \n 1003  다음       2       50.00%  20         https://jungol.co.kr/problem/1003 \n       페이지                                                                  \n조건: status=all\n조회 4 · 적격 4 · 요청 1 · 반환 1\n부족 0개\n조회 시각: 2026-10-21T01:20:59.349819+09:00 ~ 2026-10-21T01:21:00.563017+09:00\n티어·정답률·정답 제출 수는 각 목록 관측 시점의 값입니다. 정답 제출 수는 동일 \n사용자의 중복 정답 제출을 포함합니다.\n",
    "stderr": "조회 시작 · Ctrl+C 취소\nCollecting · 수집 0 · Ctrl+C 취소\nCollecting · 수집 3개 · Ctrl+C 취소\nCollecting · 수집 4개 · Ctrl+C 취소\nProcessing · 수집 4 · Ctrl+C 취소\nComplete · 수집 4 · Ctrl+C 취소\n",
    "run": 2
  },
  {
    "command": "recommend",
    "label": "baseline",
    "imports": {
      "algorithm_problem_picker.cli": "%TEMP%/jpick-benchmark-pbiatupe/baseline/src/algorithm_problem_picker/cli.py",
      "algorithm_problem_picker.jungol": "%TEMP%/jpick-benchmark-pbiatupe/baseline/src/algorithm_problem_picker/jungol.py",
      "algorithm_problem_picker.models": "%TEMP%/jpick-benchmark-pbiatupe/baseline/src/algorithm_problem_picker/models.py",
      "algorithm_problem_picker.service": "%TEMP%/jpick-benchmark-pbiatupe/baseline/src/algorithm_problem_picker/service.py"
    },
    "python": "3.12.13 (main, Mar 24 2026, 22:57:53) [MSC v.1944 64 bit (AMD64)]",
    "executable": "./.venv/Scripts/python.exe",
    "dependencies": {
      "typer": "0.27.3",
      "rich": "15.0.0",
      "playwright": "1.64.0",
      "pytest": "9.1.1"
    },
    "detail_requests": 4,
    "blocked_requests": [],
    "listing_seconds": 1.081357000002754,
    "browser": "156.0.8078.4",
    "candidate_ids": [
      1000,
      1001,
      1002,
      1003
    ],
    "fetched": 4,
    "eligible": 4,
    "returned": 1,
    "shortage": 0,
    "selected_ids": [
      1003
    ],
    "eligible_ids": [
      1000,
      1001,
      1002,
      1003
    ],
    "total_seconds": 5.474948400002177,
    "exit_code": 0,
    "stdout": "                                  푼 사람                                      \n 번호  제목       난이도  정답률  수         링크                              \n 1003  다음       2       50.00%  5171       https://jungol.co.kr/problem/1003 \n       페이지                                                                  \n조건: status=all\n조회 4 · 적격 4 · 요청 1 · 반환 1\n부족 0개\n조회 시각: 2026-10-21T01:21:01.339787+09:00 ~ 2026-10-21T01:21:06.437573+09:00\n티어·정답률은 목록 관측값, 푼 사람 수는 각 상세 조회 시점의 값입니다.\n",
    "stderr": "조회 시작 · Ctrl+C 취소\nCollecting · 수집 0 · 상세 0 · Ctrl+C 취소\nCollecting · 수집 3개 · Ctrl+C 취소\nCollecting · 수집 4개 · Ctrl+C 취소\nEnriching · 수집 4 · 상세 0 · Ctrl+C 취소\nEnriching · 수집 4 · 상세 1 · Ctrl+C 취소\nEnriching · 수집 4 · 상세 2 · Ctrl+C 취소\nEnriching · 수집 4 · 상세 3 · Ctrl+C 취소\nEnriching · 수집 4 · 상세 4 · Ctrl+C 취소\nComplete · 수집 4 · 상세 4 · Ctrl+C 취소\n",
    "run": 3
  },
  {
    "command": "recommend",
    "label": "current",
    "imports": {
      "algorithm_problem_picker.cli": "./src/algorithm_problem_picker/cli.py",
      "algorithm_problem_picker.jungol": "./src/algorithm_problem_picker/jungol.py",
      "algorithm_problem_picker.models": "./src/algorithm_problem_picker/models.py",
      "algorithm_problem_picker.service": "./src/algorithm_problem_picker/service.py"
    },
    "python": "3.12.13 (main, Mar 24 2026, 22:57:53) [MSC v.1944 64 bit (AMD64)]",
    "executable": "./.venv/Scripts/python.exe",
    "dependencies": {
      "typer": "0.27.3",
      "rich": "15.0.0",
      "playwright": "1.64.0",
      "pytest": "9.1.1"
    },
    "detail_requests": 0,
    "blocked_requests": [],
    "listing_seconds": 1.2457003999988956,
    "browser": "156.0.8078.4",
    "candidate_ids": [
      1000,
      1001,
      1002,
      1003
    ],
    "fetched": 4,
    "eligible": 4,
    "returned": 1,
    "shortage": 0,
    "selected_ids": [
      1003
    ],
    "eligible_ids": [
      1000,
      1001,
      1002,
      1003
    ],
    "total_seconds": 1.6054261999997834,
    "exit_code": 0,
    "stdout": "                                  정답 제 …                                    \n 번호  제목       난이도  정답률  수         링크                              \n 1003  다음       2       50.00%  20         https://jungol.co.kr/problem/1003 \n       페이지                                                                  \n조건: status=all\n조회 4 · 적격 4 · 요청 1 · 반환 1\n부족 0개\n조회 시각: 2026-10-21T01:21:07.174442+09:00 ~ 2026-10-21T01:21:08.421154+09:00\n티어·정답률·정답 제출 수는 각 목록 관측 시점의 값입니다. 정답 제출 수는 동일 \n사용자의 중복 정답 제출을 포함합니다.\n",
    "stderr": "조회 시작 · Ctrl+C 취소\nCollecting · 수집 0 · Ctrl+C 취소\nCollecting · 수집 3개 · Ctrl+C 취소\nCollecting · 수집 4개 · Ctrl+C 취소\nProcessing · 수집 4 · Ctrl+C 취소\nComplete · 수집 4 · Ctrl+C 취소\n",
    "run": 3
  }
]
```
