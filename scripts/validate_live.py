"""Opt-in live partition check; all source data stays in memory."""

import argparse
from decimal import Decimal

from algorithm_problem_picker.jungol import JungolSource
from algorithm_problem_picker.models import SearchCriteria
from algorithm_problem_picker.selection import filter_listing, filter_solvers


def main() -> None:
    parser = argparse.ArgumentParser(description="공개 사용자 기준의 작은 라이브 집합 분할 검증")
    parser.add_argument("--user", required=True, help="정확한 공개 핸들")
    args = parser.parse_args()
    handle = SearchCriteria(status="solved", user_handle=args.user).user_handle
    results: dict[str, set[int]] = {}
    with JungolSource(report=print) as source:
        user = source.resolve_user(handle)
        print(f"기준 사용자 @{user.handle}, ID {user.account_id}")
        for status in ("all", "solved", "unsolved"):
            criteria = SearchCriteria(min_tier=1, max_tier=1, min_rate=Decimal("80"), status=status,
                                      user_handle="" if status == "all" else handle)
            listing = source.collect(criteria, None if status == "all" else user)
            cheap, _ = filter_listing(listing.candidates, criteria)
            eligible, _ = filter_solvers([source.read_details(problem) for problem in cheap], criteria)
            results[status] = {problem.id for problem in eligible}
            print(f"{status}: 조회 {len(listing.candidates)}, 적격 {len(eligible)}, 번호 {sorted(results[status])}")
        assert not results["solved"] & results["unsolved"]
        assert results["all"] == results["solved"] | results["unsolved"]
        print("PASS: solved와 unsolved는 겹치지 않고 합집합이 all과 같습니다.")


if __name__ == "__main__":
    main()
