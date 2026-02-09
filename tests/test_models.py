"""Tests for Pydantic validation in models.py."""

import pytest
from pydantic import ValidationError

from credit_valuation.models import CohortInput, GlobalParameters, PeriodData

from helpers import make_period


class TestPeriodData:
    def test_valid_period(self):
        p = make_period(1)
        assert p.period == 1

    def test_prob_charge_off_out_of_range(self):
        with pytest.raises(ValidationError):
            make_period(1, prob_charge_off=1.5)

    def test_prob_attrition_negative(self):
        with pytest.raises(ValidationError):
            make_period(1, prob_attrition=-0.1)

    def test_competing_risks_exceed_one(self):
        with pytest.raises(ValidationError, match="exceeds 1.0"):
            make_period(1, prob_charge_off=0.6, prob_attrition=0.5)

    def test_competing_risks_equal_one(self):
        # Edge case: exactly 1.0 is valid (all accounts exit)
        p = make_period(1, prob_charge_off=0.5, prob_attrition=0.5)
        assert p.prob_charge_off + p.prob_attrition == 1.0

    def test_negative_balance_rejected(self):
        with pytest.raises(ValidationError):
            make_period(1, revolving_balance=-100)

    def test_zero_balance_accepted(self):
        p = make_period(1, revolving_balance=0.0)
        assert p.revolving_balance == 0.0


class TestGlobalParameters:
    def test_valid_params(self):
        gp = GlobalParameters(
            flat_interchange_rate=0.02, discount_rate=0.10, num_accounts=1000
        )
        assert gp.num_accounts == 1000

    def test_zero_accounts_rejected(self):
        with pytest.raises(ValidationError):
            GlobalParameters(
                flat_interchange_rate=0.02, discount_rate=0.10, num_accounts=0
            )


class TestCohortInput:
    def test_sequential_periods_accepted(self):
        periods = [make_period(1), make_period(2), make_period(3)]
        params = GlobalParameters(
            flat_interchange_rate=0.02, discount_rate=0.10, num_accounts=100
        )
        ci = CohortInput(periods=periods, parameters=params)
        assert len(ci.periods) == 3

    def test_non_sequential_periods_rejected(self):
        periods = [make_period(1), make_period(3)]  # skip 2
        params = GlobalParameters(
            flat_interchange_rate=0.02, discount_rate=0.10, num_accounts=100
        )
        with pytest.raises(ValidationError, match="sequential"):
            CohortInput(periods=periods, parameters=params)

    def test_not_starting_at_one_rejected(self):
        periods = [make_period(2), make_period(3)]
        params = GlobalParameters(
            flat_interchange_rate=0.02, discount_rate=0.10, num_accounts=100
        )
        with pytest.raises(ValidationError, match="sequential"):
            CohortInput(periods=periods, parameters=params)
