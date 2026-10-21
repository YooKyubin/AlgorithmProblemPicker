# Local collection replay benchmark

고정 HTML 로컬 재생 결과다. 실사이트의 개선율로 일반화하지 않는다.

CLI import 후 명령 호출 직전부터 출력·브라우저 정리까지 전체 시간을 측정했다. 별도 프로세스 시작/import 시간은 제외한다. 제품의 기본 1초 시작 간격과 30초/15초 제한을 유지했다.

## Environment and source identity

```json
{
  "measured_at": "2026-10-20T16:12:38.225324+00:00",
  "platform": "Windows-11-10.0.26200-SP0",
  "python": "3.12.13 (main, Mar 24 2026, 22:57:53) [MSC v.1944 64 bit (AMD64)]",
  "executable": "./.venv/Scripts/python.exe",
  "runs": 1,
  "baseline_revision": "c37208f5a80628df5d7126972d31461b2517177d",
  "baseline_dirty": false,
  "current_revision": "c37208f5a80628df5d7126972d31461b2517177d",
  "current_dirty": true,
  "current_status": "M scripts/benchmark_selection.py\n M scripts/validate_live.py\n M src/algorithm_problem_picker/cli.py\n M src/algorithm_problem_picker/jungol.py\n M src/algorithm_problem_picker/models.py\n M src/algorithm_problem_picker/ports.py\n M src/algorithm_problem_picker/selection.py\n M src/algorithm_problem_picker/service.py\n M tests/conftest.py\n M tests/fixtures/jungol/list.html\n M tests/fixtures/jungol/pagination.html\n M tests/test_cli.py\n M tests/test_jungol_dom.py\n M tests/test_selection.py\n M tests/test_service.py\n?? scripts/benchmark_collection.py\n?? specs/002-improve-list-collection/\n?? tests/fixtures/jungol/benchmark/\n?? tests/fixtures/jungol/tier-pagination.html",
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
    "cli.py": "7b10701b8c5854efa8dfc4b29edcc9424ed5d3c48f12f870cf1a3bd76edb7098",
    "jungol.py": "e9486460a99b08e4414fb3c6a78ef14ec1b9e941d6146c67ebdcddbff3ca0dd6",
    "models.py": "c6b8449a85e6d3e4ae4b6b1c44807115faa5064d17f1ec45e585bfd3e203d28f",
    "ports.py": "a013a7e1673cf591c5c098663bea1e9985a0dce3266ae2146afba35b8ee5a1aa",
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
| list | baseline | 1 | 4/4/1 | 4 | 5.518629 | 1.084244 |
| list | current | 1 | 4/4/1 | 0 | 1.582606 | 1.230961 |
| recommend | baseline | 1 | 4/4/1 | 4 | 5.494317 | 1.069095 |
| recommend | current | 1 | 4/4/1 | 0 | 1.608004 | 1.242050 |

## Medians

| Command | Version | Total seconds | Collect seconds |
| --- | --- | ---: | ---: |
| list | baseline | 5.518629 | 1.084244 |
| list | current | 1.582606 | 1.230961 |
| recommend | baseline | 5.494317 | 1.069095 |
| recommend | current | 1.608004 | 1.242050 |

## Verdict

PASS

Smoke run only; SC-008 requires at least three runs per version and command.

## Full samples (import paths, output and diagnostics)

```json
[
  {
    "command": "list",
    "label": "baseline",
    "imports": {
      "algorithm_problem_picker.cli": "%TEMP%/jpick-benchmark-0dap23px/baseline/src/algorithm_problem_picker/cli.py",
      "algorithm_problem_picker.jungol": "%TEMP%/jpick-benchmark-0dap23px/baseline/src/algorithm_problem_picker/jungol.py",
      "algorithm_problem_picker.models": "%TEMP%/jpick-benchmark-0dap23px/baseline/src/algorithm_problem_picker/models.py",
      "algorithm_problem_picker.service": "%TEMP%/jpick-benchmark-0dap23px/baseline/src/algorithm_problem_picker/service.py"
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
    "listing_seconds": 1.0842441000022518,
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
    "total_seconds": 5.518628699999681,
    "exit_code": 0,
    "stdout": "                                  푼 사람                                      \n 번호  제목       난이도  정답률  수         링크                              \n 1000  두 정수    1       47.45%  5171       https://jungol.co.kr/problem/1000 \n       더하기                                                                  \n조건: status=all\n조회 4 · 적격 4 · 요청 1 · 표시 1\n조회 시각: 2026-10-21T01:12:39.267539+09:00 ~ 2026-10-21T01:12:44.364502+09:00\n티어·정답률은 목록 관측값, 푼 사람 수는 각 상세 조회 시점의 값입니다.\n",
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
    "listing_seconds": 1.2309606000017084,
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
    "total_seconds": 1.5826056000005337,
    "exit_code": 0,
    "stdout": "                                  정답 제 …                                    \n 번호  제목       난이도  정답률  수         링크                              \n 1000  두 정수    1       47.45%  6510       https://jungol.co.kr/problem/1000 \n       더하기                                                                  \n조건: status=all\n조회 4 · 적격 4 · 요청 1 · 표시 1\n조회 시각: 2026-10-21T01:12:45.130008+09:00 ~ 2026-10-21T01:12:46.360827+09:00\n티어·정답률·정답 제출 수는 각 목록 관측 시점의 값입니다. 정답 제출 수는 동일 \n사용자의 중복 정답 제출을 포함합니다.\n",
    "stderr": "조회 시작 · Ctrl+C 취소\nCollecting · 수집 0 · Ctrl+C 취소\nCollecting · 수집 3개 · Ctrl+C 취소\nCollecting · 수집 4개 · Ctrl+C 취소\nProcessing · 수집 4 · Ctrl+C 취소\nComplete · 수집 4 · Ctrl+C 취소\n",
    "run": 1
  },
  {
    "command": "recommend",
    "label": "baseline",
    "imports": {
      "algorithm_problem_picker.cli": "%TEMP%/jpick-benchmark-0dap23px/baseline/src/algorithm_problem_picker/cli.py",
      "algorithm_problem_picker.jungol": "%TEMP%/jpick-benchmark-0dap23px/baseline/src/algorithm_problem_picker/jungol.py",
      "algorithm_problem_picker.models": "%TEMP%/jpick-benchmark-0dap23px/baseline/src/algorithm_problem_picker/models.py",
      "algorithm_problem_picker.service": "%TEMP%/jpick-benchmark-0dap23px/baseline/src/algorithm_problem_picker/service.py"
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
    "listing_seconds": 1.0690950999996858,
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
    "total_seconds": 5.494316799999069,
    "exit_code": 0,
    "stdout": "                                  푼 사람                                      \n 번호  제목       난이도  정답률  수         링크                              \n 1003  다음       2       50.00%  5171       https://jungol.co.kr/problem/1003 \n       페이지                                                                  \n조건: status=all\n조회 4 · 적격 4 · 요청 1 · 반환 1\n부족 0개\n조회 시각: 2026-10-21T01:12:47.183736+09:00 ~ 2026-10-21T01:12:52.277578+09:00\n티어·정답률은 목록 관측값, 푼 사람 수는 각 상세 조회 시점의 값입니다.\n",
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
    "listing_seconds": 1.2420498999999836,
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
    "total_seconds": 1.60800449999806,
    "exit_code": 0,
    "stdout": "                                  정답 제 …                                    \n 번호  제목       난이도  정답률  수         링크                              \n 1003  다음       2       50.00%  20         https://jungol.co.kr/problem/1003 \n       페이지                                                                  \n조건: status=all\n조회 4 · 적격 4 · 요청 1 · 반환 1\n부족 0개\n조회 시각: 2026-10-21T01:12:53.037884+09:00 ~ 2026-10-21T01:12:54.279507+09:00\n티어·정답률·정답 제출 수는 각 목록 관측 시점의 값입니다. 정답 제출 수는 동일 \n사용자의 중복 정답 제출을 포함합니다.\n",
    "stderr": "조회 시작 · Ctrl+C 취소\nCollecting · 수집 0 · Ctrl+C 취소\nCollecting · 수집 3개 · Ctrl+C 취소\nCollecting · 수집 4개 · Ctrl+C 취소\nProcessing · 수집 4 · Ctrl+C 취소\nComplete · 수집 4 · Ctrl+C 취소\n",
    "run": 1
  }
]
```
