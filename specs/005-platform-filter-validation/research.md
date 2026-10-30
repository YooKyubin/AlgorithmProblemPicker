# Phase 0 Research: 플랫폼 선택과 지원 필터 검증

조사일: 2026-10-30. 기준 HEAD: `dca9659bc4fa196b043c67886d5c48e531bed52c`.
명세는 [spec.md](spec.md)를 따른다. 실제 사이트에는 접속하지 않았다.

## R1. 플랫폼 선택과 명시한 필터의 식별

**Decision**: 루트 Typer callback에서 문자열 `--platform`을 정적 레지스트리로 조회하고 `ctx.obj`에 선택한 바인딩을 보관한다. 기본값은 `jungol`이며 빈 값·미등록 값은 코드 2로 거부한다. 필터 명시 여부는 하위 명령의 `ctx.get_parameter_source(name)` 결과의 `name == 'COMMANDLINE'`으로 판정한다. 출처 누락은 내부 불변식 위반으로 다루며 기본값으로 추정하지 않는다.

**Rationale**: 생략된 `status=all`과 명시한 `--status all`은 값만 비교해서 구분할 수 없다. 출처 조회는 같은 기본값을 명시한 경우를 구분하는 공개 기능이다. [Typer Context reference](https://typer.tiangolo.com/reference/context/), [Context 사용법](https://typer.tiangolo.com/tutorial/commands/context/) 및 설치 소스를 대조했다.

**Alternatives considered**: `value != default`는 명시적 기본값을 놓친다. `sys.argv` 재해석은 등호·인자 경계 처리를 중복한다. 환경 변수나 설정 파일을 통한 플랫폼 선택은 이번 범위에서 추가하지 않는다.

## R2. 지원 검사 이후로 플랫폼 값 해석 이동

**Decision**: 필터는 `str | None`, 범위 옵션은 반복을 보존하는 `list[str]`로 받는다. 옵션 출처와 값으로 RawFilterInput을 만든 뒤 미지원 옵션을 모두 검사하고, 통과한 경우에만 플랫폼 정책이 파싱·범위·혼용·반복·legacy 입력을 검사한다. `limit/count/order` 같은 공통 비필터 검증은 CLI에 남긴다.

**Rationale**: 현재 `cli.py`의 `int(min=0)`, `Status` 변환, `_single_range`와 eager legacy callback은 명령 본문보다 먼저 실패한다. 그대로 두면 잘못된 미지원 값에 대해 플랫폼·미지원 옵션 안내를 보장할 수 없다. 값 누락·알 수 없는 옵션 같은 CLI 기본 문법 오류는 계속 Typer가 처리한다. [eager callback 공식 설명](https://typer.tiangolo.com/tutorial/options/version/)과 로컬 실행 순서를 확인했다.

**Alternatives considered**: eager 지원 검사와 별도 파서 서브클래스는 옵션 처리 순서 의존성을 늘린다. 본문 지원 검사만 추가하고 기존 자동 변환을 유지하면 FR-008을 충족하지 못한다.

정올의 폐기 solvers 옵션은 별도 retired_options 진단 선언으로 보존한다. 지원 필터로 승격하지 않고, 지원 검사 뒤 정올 전용 전환 안내와 코드 2를 반환한다. 이 구분이 없으면 공통 미지원 안내가 기존 지표 전환 설명을 가리게 된다.

## R3. 새 의존성 없이 현재 Typer 사용

**Decision**: Python 3.12 이상과 현재 잠금 의존성을 유지한다. 조사 환경은 Python 3.12.13, Typer 0.27.3, Rich 15.0.0, Playwright 1.64.0, pytest 9.1.1이다. 별도 Click 의존성이나 private enum import를 추가하지 않는다.

**Rationale**: 이 환경의 Typer는 `typer._click`을 내장하고 별도 `click` 배포판이 없다. `from click.core import ParameterSource`를 새 코드에 넣으면 실패한다. `typer.Context`의 공개 메서드로 충분하다. [Typer의 Click 내장 안내](https://typer.tiangolo.com/tutorial/click/)와 `.venv/Lib/site-packages/typer/_click/core.py`의 출처 조회·자동 help 처리, `typer/core.py`의 하위 context 생성을 확인했다.

**Alternatives considered**: 버전 업그레이드·추가 파서 도입은 현 요구에 필요하지 않다. enum 정수값 비교나 private 모듈 import는 불필요한 내부 결합을 만든다.

## R4. 플랫폼별 도움말

**Decision**: 정적 옵션 설명은 플랫폼 중립적으로 바꾸고 공통 eager `--help` callback에서 일반 `ctx.get_help()`와 선택 플랫폼의 지원 필터·허용 값·조합 규칙을 함께 출력한다. callback은 `expose_value=False`로 두고 본문 실행 전에 종료한다. 전역 command 객체의 help를 실행마다 수정하지 않는다.

**Rationale**: 로컬 CliRunner 실험에서 루트 callback의 `ctx.obj`가 하위 help callback까지 전달되고, 명시한 `--help`가 자동 help와 중복되지 않음을 확인했다. 지원하지 않는 옵션도 공통 문법에는 남아 있으므로 도움말은 해당 플랫폼에서 미지원임을 분명히 표시해야 한다.

**Alternatives considered**: 정올 설명을 그대로 공통 help에 노출하면 다른 플랫폼에 잘못된 규칙을 안내한다. TyperCommand 상속이나 command 객체 변이는 공개 callback으로 충족 가능한 범위를 넘어선다.

## R5. 정올 전용 타입과 공통 처리 경계

**Decision**: 기존 Problem·SearchCriteria·UserReference·Rated 및 관련 검증을 `jungol_models.py`로 소유권 이동한다. 공통 모델은 문제의 식별자·제목·URL·관측 시각 프로토콜과 제네릭 CompletedListing·Result, 진행 상태를 다룬다. 필터 값·속성 의미·행 구성·URL 규칙을 정올 정책에 둔다.

**Rationale**: 현재 `models.py`의 Problem은 정올 URL 일치, Rated는 1~30, SearchCriteria는 정올 통계·사용자 조합, UserReference는 숫자 계정 ID를 강제한다. 지원 여부 플래그만 추가하면 다른 플랫폼의 유효한 데이터가 이 규칙에서 실패한다. 기존 검증을 제거하는 대신 소유권을 분리해야 한다.

**Alternatives considered**: 모든 플랫폼 속성을 담는 공통 레코드·`dict[str, Any]` 속성 엔진·전역 티어 수치는 채택하지 않는다. 플랫폼마다 CLI나 Picker를 복제하는 방식도 FR-016과 충돌한다. 실제 신규 플랫폼 구현은 하지 않는다.

## R6. 수집·사용자 조회·추천의 조합

**Decision**: `ProblemSource[P,C,U]`는 `prepare_user(criteria) -> U | None`과 `collect(criteria, user)`를 제공한다. 정올의 prepare_user는 필요할 때 기존 resolve_user를 호출한다. Picker는 정올 조건 필드를 읽지 않고 완전 수집·진행·집계·추천 흐름을 한 번만 수행한다. 플랫폼 정책의 순수 filter/sort를 주입하고 공통 recommend의 고유 문제 추출·random.sample은 유지한다.

**Rationale**: 현 `service.py`는 `criteria.user_handle`을 직접 읽고 정올 필터·정렬을 import한다. 이 의존만 포트로 바꾸면 서비스 흐름을 보존할 수 있다. 수집기는 검증 완료 뒤 공통 `with`에서만 생성·진입한다. `open`은 플랫폼의 순수 번호 검증과 URL 생성만 사용하며 소스 팩터리도 호출하지 않는다.

**Alternatives considered**: 수집기가 추천까지 수행하면 수집과 로컬 처리 경계가 사라진다. 준비 단계 없이 수집기에 사용자 조회를 숨기면 기존 UserResolved 진행 단계와 실패 관측을 잃는다.

## R7. 속성 미지원과 미제공·제외 집계

**Decision**: 속성 미지원은 PlatformInfo의 지원 정보에만 표현한다. 해당 플랫폼 문제에 가짜 `Unavailable` 필드를 만들지 않는다. 지원 속성의 개별 미제공은 기존 `Unavailable`, 실제 0은 `Known(0)`을 유지한다. 정올 filter_listing은 `tier → rate → accepted`의 첫 실패 순서와 고유 문제당 한 번 집계를 그대로 이동한다.

**Rationale**: `test_numeric_rejection_does_not_count_later_missing_statistic`와 `test_unknown_count_stops_at_first_active_filter`는 모든 미제공 값을 미리 세는 방식과 다르다. Unrated는 티어 필터에서 제외되지만 미제공 제외 수에는 넣지 않는다. 확정 티어는 검색 경계 밖이어도 보존한다.

**Alternatives considered**: 전역 결측 개수 사전 집계, 미지원 속성을 전 문제의 미확인 값으로 채우기, 정올 티어를 단순 수치 범위로 재필터링하기는 모두 기존 동작을 바꾼다.

## R8. 기존 입력 문법과 이름 변경 범위

**Decision**: 정올 파서를 옮기면서 새 범위 문법과 기존 경계 문법의 차이를 보존한다. 기존 정답 제출 수 경계는 `int(text)` 변환 뒤 0 이상을 검사하고, 새 `--accepted` 범위는 기존 ASCII 문법을 유지한다. `[project.scripts]`의 키만 `algo-pick`으로 바꾸며 배포 패키지·내부 모듈 이름은 유지한다. 현재 README·두 가이드·VS Code 예제·내보내기 도움말을 함께 갱신한다.

**Rationale**: 메모리 내 Typer `int(min=0)` 실험에서 `+1`, 앞뒤 공백, 전각 숫자, `1_000`은 유효하고 `-1`, `1.0`은 무효였다. 새 범위의 엄격한 문법을 기존 경계에 확대하면 회귀다. export_tool은 src 전체를 복사하므로 새 모듈을 자동 포함하지만, 내보내는 문서와 실행 예제는 현재 `jpick`을 명시한다.

**Alternatives considered**: 패키지까지 개명하면 요구와 무관한 import·잠금 변경이 생긴다. 과거 specs·검증 기록의 일괄 개명과 기존 외부 복사본의 자동 변경도 하지 않는다.

## R9. 확장 검증과 헌장 게이트

**Decision**: 프로덕션 레지스트리는 정올 하나만 제공한다. 테스트는 실제 구성 경계에 합성 플랫폼을 주입해 다른 난이도·지원 속성·URL과 미지원 기본값을 검증한다. 이번 플랫폼 선택 요구와 헌장 I의 충돌은 범위가 제한된 명시적 예외로 정당화하고, III의 비영구 수집 예외는 선행 계획을 승계한다. 헌장 원문 개정은 이번 계획 산출물에 넣지 않는다.

**Rationale**: 사용자의 이번 지시가 과거 플랫폼 통합 제외보다 우선한다. 실지원은 여전히 정올뿐이며 신규 수집 허가·속성을 추측하지 않는다. 일반 레지스트리·정책 경계를 테스트에서 교체하므로 테스트만을 위한 공개 등록 API가 필요 없다.

**Alternatives considered**: 게이트 충돌을 숨겨 PASS로 표시하지 않는다. 테스트용 플랫폼을 제품에 노출하거나 프로그래머스 실제 지원을 구현하는 방식은 범위를 넘는다. 헌장 개정으로 현재 요구보다 넓은 다중 플랫폼 운영을 승인하지 않는다.

## 조사 검증 상태

- 두 연구 에이전트가 로컬 코드·잠금 환경·정책 경계를 검토했고, 부모 에이전트가 공식 문서와 기존 경계 변환 실험을 대조했다.
- 출처 DEFAULT/COMMANDLINE 구분, 복수 미지원+무효·반복 값의 사전 거부, 선택 플랫폼 help 상속을 메모리 내 CliRunner로 확인했다.
- 제품 코드·테스트·설정은 변경하지 않았다. 제품 전체 테스트, 신규 설계 구현 검증, 실사이트 수용을 완료했다고 주장하지 않는다.
- 미결정 기술 항목은 없다. 후속 설계는 [data-model.md](data-model.md), [contracts/platform.md](contracts/platform.md)를 따른다.
