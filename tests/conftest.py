"""Shared test fixtures."""

import pytest

from credit_valuation.models import CohortInput, GlobalParameters
from helpers import make_period


@pytest.fixture()
def default_params() -> GlobalParameters:
    return GlobalParameters(
        flat_interchange_rate=0.02,
        discount_rate=0.10,
        num_accounts=1000,
    )


@pytest.fixture()
def single_period_cohort(default_params) -> CohortInput:
    return CohortInput(
        periods=[make_period(1)],
        parameters=default_params,
    )


@pytest.fixture()
def two_period_cohort(default_params) -> CohortInput:
    return CohortInput(
        periods=[make_period(1), make_period(2)],
        parameters=default_params,
    )


@pytest.fixture()
def sixty_period_cohort(default_params) -> CohortInput:
    periods = [make_period(t) for t in range(1, 61)]
    return CohortInput(periods=periods, parameters=default_params)
