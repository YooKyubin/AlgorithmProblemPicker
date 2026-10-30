# 003 실사이트 수용 기록

원문 세 명령을 실제 공개 DOM으로 순차 실행했다. 합성 fixture와 과거 개수를 기대값으로 사용하지 않는다. 각 실행의 실제 상태는 아래 기록을 따른다.

- HEAD: 0c1565b86bd44f546a2e1954c8653762c24428e4
- 브랜치: 003-align-site-listing
- 실행 환경: Windows-11-10.0.26200-SP0, Python 3.12.13
- Python 실행 경로 (저장소 루트 기준): `./.venv/Scripts/python.exe`
- 의존성: {"playwright": "1.64.0", "typer": "0.27.3", "rich": "15.0.0", "pytest": "9.1.1"}
- 로컬 전체 회귀: uv run --locked pytest -q → 375 passed (127.55s)

## 시작 dirty 상태

~~~text
 M README.md
 M specs/001-jungol-problem-picker/quickstart.md
 M specs/001-jungol-problem-picker/tasks.md
 M specs/002-improve-list-collection/quickstart.md
 M src/algorithm_problem_picker/cli.py
 M src/algorithm_problem_picker/jungol.py
 M src/algorithm_problem_picker/models.py
 M src/algorithm_problem_picker/selection.py
 M tests/test_cli.py
 M tests/test_jungol_dom.py
 M tests/test_selection.py
 M tests/test_service.py
?? specs/002-improve-list-collection/post-implementation-issues.md
?? specs/003-align-site-listing/
?? tests/fixtures/jungol/site-listing.html
~~~

## 제품 파일 SHA-256

~~~json
{
  "src\\algorithm_problem_picker\\jungol.py": "022996176dcfb94ca2643d95444bda228fdfb21f32674f20b5f4553fc06c5cd7",
  "src\\algorithm_problem_picker\\cli.py": "0c9f2ed2d36186d5fdf372b6c5fcda8dd6c1b1f90c6cdee483d9a349beb669e2",
  "src\\algorithm_problem_picker\\models.py": "9c9324c3f47cefd77667a1a8a02d049d9908c578ddb1e280cc0d0a7f5ff44e61",
  "src\\algorithm_problem_picker\\selection.py": "50360c02f6cb19e955cb0de19dfcf2b8323b2042eafe792c109766d7356d661e"
}
~~~

## 실행 1

- 명령: uv run --locked jpick recommend --min-tier 9 --max-tier 13 --count 2
- 시작(Asia/Seoul): 2026-10-24T14:07:11.099339+09:00
- 종료(Asia/Seoul): 2026-10-24T14:07:35.819438+09:00
- 종료 코드: 0
- 결과 개수: {'fetched': 761, 'eligible': 761, 'requested': 2, 'returned': 2}

### stdout 원문

~~~text
                                  정답 제 …                                    
 번호  제목       난이도  정답률  수         링크                              
 2095  Aimu8      10      39.73%  29         https://jungol.co.kr/problem/2095 
 1457  영역       10      51.78%  2693       https://jungol.co.kr/problem/1457 
       구하기                                                                  
조건: min_tier=9, max_tier=13, status=all
조회 761 · 적격 761 · 요청 2 · 반환 2
부족 0개
조회 시각: 2026-10-24T14:07:11.755520+09:00 ~ 2026-10-24T14:07:35.707999+09:00
티어·정답률·정답 제출 수는 각 목록 관측 시점의 값입니다. 정답 제출 수는 동일 
사용자의 중복 정답 제출을 포함합니다.

~~~

### stderr 원문

~~~text
조회 시작 · Ctrl+C 취소
Collecting · 수집 0 · Ctrl+C 취소
Collecting · 수집 50개 · Ctrl+C 취소
Collecting · 수집 100개 · Ctrl+C 취소
Collecting · 수집 150개 · Ctrl+C 취소
Collecting · 수집 200개 · Ctrl+C 취소
Collecting · 수집 250개 · Ctrl+C 취소
Collecting · 수집 300개 · Ctrl+C 취소
Collecting · 수집 350개 · Ctrl+C 취소
Collecting · 수집 400개 · Ctrl+C 취소
Collecting · 수집 450개 · Ctrl+C 취소
Collecting · 수집 500개 · Ctrl+C 취소
Collecting · 수집 550개 · Ctrl+C 취소
Collecting · 수집 600개 · Ctrl+C 취소
Collecting · 수집 650개 · Ctrl+C 취소
Collecting · 수집 700개 · Ctrl+C 취소
Collecting · 수집 750개 · Ctrl+C 취소
Collecting · 수집 761개 · Ctrl+C 취소
Processing · 수집 761 · Ctrl+C 취소
Complete · 수집 761 · Ctrl+C 취소

~~~

## 실행 2

- 명령: uv run --locked jpick recommend --min-tier 9 --max-tier 10 --count 2
- 시작(Asia/Seoul): 2026-10-24T14:07:35.819438+09:00
- 종료(Asia/Seoul): 2026-10-24T14:07:42.764059+09:00
- 종료 코드: 0
- 결과 개수: {'fetched': 277, 'eligible': 277, 'requested': 2, 'returned': 2}

### stdout 원문

~~~text
                               정답 제출                                       
 번호   제목   난이도  정답률  수           링크                               
 13736  쇼핑   10      미확인  0            https://jungol.co.kr/problem/13736 
 2095   Aimu8  10      39.73%  29           https://jungol.co.kr/problem/2095  
조건: min_tier=9, max_tier=10, status=all
조회 277 · 적격 277 · 요청 2 · 반환 2
부족 0개
조회 시각: 2026-10-24T14:07:36.481030+09:00 ~ 2026-10-24T14:07:42.671471+09:00
티어·정답률·정답 제출 수는 각 목록 관측 시점의 값입니다. 정답 제출 수는 동일 
사용자의 중복 정답 제출을 포함합니다.

~~~

### stderr 원문

~~~text
조회 시작 · Ctrl+C 취소
Collecting · 수집 0 · Ctrl+C 취소
Collecting · 수집 50개 · Ctrl+C 취소
Collecting · 수집 100개 · Ctrl+C 취소
Collecting · 수집 150개 · Ctrl+C 취소
Collecting · 수집 200개 · Ctrl+C 취소
Collecting · 수집 250개 · Ctrl+C 취소
Collecting · 수집 277개 · Ctrl+C 취소
Processing · 수집 277 · Ctrl+C 취소
Complete · 수집 277 · Ctrl+C 취소

~~~

## 실행 3

- 명령: uv run --locked jpick list --min-tier 1 --max-tier 1 --sort accepted --order desc --limit 5
- 시작(Asia/Seoul): 2026-10-24T14:07:42.764059+09:00
- 종료(Asia/Seoul): 2026-10-24T14:07:47.458367+09:00
- 종료 코드: 0
- 결과 개수: {'fetched': 136, 'eligible': 136, 'requested': 5, 'returned': 5}

### stdout 원문

~~~text
                                  정답 제 …                                    
 번호  제목       난이도  정답률  수         링크                              
 1303  숫자사각   1       57.33%  8917       https://jungol.co.kr/problem/1303 
       형1                                                                     
 1291  구구단 4   1       20.76%  7194       https://jungol.co.kr/problem/1291 
 1000  두 정수    1       47.42%  6542       https://jungol.co.kr/problem/1000 
       더하기                                                                  
       (A+B)                                                                   
 1307  문자사각   1       39.94%  6315       https://jungol.co.kr/problem/1307 
       형1                                                                     
 1071  약수와     1       63.36%  4793       https://jungol.co.kr/problem/1071 
       배수                                                                    
조건: min_tier=1, max_tier=1, status=all
조회 136 · 적격 136 · 요청 5 · 표시 5
조회 시각: 2026-10-24T14:07:43.414205+09:00 ~ 2026-10-24T14:07:47.357064+09:00
티어·정답률·정답 제출 수는 각 목록 관측 시점의 값입니다. 정답 제출 수는 동일 
사용자의 중복 정답 제출을 포함합니다.

~~~

### stderr 원문

~~~text
조회 시작 · Ctrl+C 취소
Collecting · 수집 0 · Ctrl+C 취소
Collecting · 수집 50개 · Ctrl+C 취소
Collecting · 수집 100개 · Ctrl+C 취소
Collecting · 수집 136개 · Ctrl+C 취소
Processing · 수집 136 · Ctrl+C 취소
Complete · 수집 136 · Ctrl+C 취소

~~~

## 실행 완료 상태

종료 코드: [0, 0, 0]. 실패·미실행을 성공으로 기록하지 않는다. 이 기록은 사이트 전체 누락·미래 지연 반영의 복구나 새로운 성능 측정을 주장하지 않는다.
