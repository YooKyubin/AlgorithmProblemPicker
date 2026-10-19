from decimal import Decimal

import pytest

from algorithm_problem_picker.models import Known, Problem, Rated, now


@pytest.fixture
def problem():
    def make(id=1000, tier=Rated(1), rate=Known(Decimal("47.45")), solvers=Known(10)):
        return Problem(id=id, title=f"문제 {id}", url=f"https://jungol.co.kr/problem/{id}",
                       tier=tier, pass_rate=rate, solver_count=solvers,
                       listed_at=now(), details_observed_at=now())
    return make
