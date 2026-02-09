"""Tests for the calculation engine — hand-verified values."""

import math

import pytest

from credit_valuation.engine import (
    build_period_table,
    compute_costs,
    compute_net_income_and_pv,
    compute_revenue,
    compute_survival,
    run_valuation,
)
from credit_valuation.models import CohortInput, GlobalParameters, PeriodData

from helpers import make_period


class TestSinglePeriod:
    """Hand-computed single-period checks."""

    def test_period1_active_accounts(self, single_period_cohort):
        df, _ = run_valuation(single_period_cohort)
        # Period 1 starts with full cohort
        assert df["active_accounts_bop"].iloc[0] == 1000.0

    def test_period1_finance_charge(self, single_period_cohort):
        df, _ = run_valuation(single_period_cohort)
        # 1000 * 5000 * 0.015 = 75000
        assert df["finance_charge"].iloc[0] == pytest.approx(75_000.0)

    def test_period1_interchange(self, single_period_cohort):
        df, _ = run_valuation(single_period_cohort)
        # 1000 * 1000 * 0.02 = 20000
        assert df["interchange"].iloc[0] == pytest.approx(20_000.0)

    def test_period1_fee_income(self, single_period_cohort):
        df, _ = run_valuation(single_period_cohort)
        # 1000 * 25 = 25000
        assert df["fee_income"].iloc[0] == pytest.approx(25_000.0)

    def test_period1_charge_off_loss(self, single_period_cohort):
        df, _ = run_valuation(single_period_cohort)
        # 1000 * 0.02 * 5000 = 100000
        assert df["charge_off_loss"].iloc[0] == pytest.approx(100_000.0)

    def test_period1_net_income(self, single_period_cohort):
        df, _ = run_valuation(single_period_cohort)
        # revenue = 75000 + 20000 + 25000 = 120000
        # cost = 100000
        # net = 20000
        assert df["net_income"].iloc[0] == pytest.approx(20_000.0)

    def test_period1_discount_factor(self, single_period_cohort):
        df, _ = run_valuation(single_period_cohort)
        expected = 1.0 / (1.10 ** (1 / 12))
        assert df["discount_factor"].iloc[0] == pytest.approx(expected)


class TestTwoPeriodSurvival:
    """Verify the survival cascade across two periods."""

    def test_period2_active_accounts(self, two_period_cohort):
        df, _ = run_valuation(two_period_cohort)
        # survival_factor[1] = 1 - 0.02 - 0.03 = 0.95
        # active_accounts_bop[2] = 1000 * 0.95 = 950
        assert df["active_accounts_bop"].iloc[1] == pytest.approx(950.0)

    def test_charge_off_accounts_period1(self, two_period_cohort):
        df, _ = run_valuation(two_period_cohort)
        # 1000 * 0.02 = 20
        assert df["charge_off_accounts"].iloc[0] == pytest.approx(20.0)

    def test_attrition_accounts_period1(self, two_period_cohort):
        df, _ = run_valuation(two_period_cohort)
        # 1000 * 0.03 = 30
        assert df["attrition_accounts"].iloc[0] == pytest.approx(30.0)

    def test_account_conservation(self, two_period_cohort):
        """Sum of exits + remaining must equal original cohort."""
        df, _ = run_valuation(two_period_cohort)
        total_exits = df["charge_off_accounts"].sum() + df["attrition_accounts"].sum()
        remaining = df["active_accounts_bop"].iloc[-1] * df["survival_factor"].iloc[-1]
        assert total_exits + remaining == pytest.approx(1000.0)


class TestEdgeCases:
    def test_zero_attrition(self, default_params):
        periods = [
            make_period(t, prob_attrition=0.0) for t in range(1, 4)
        ]
        cohort = CohortInput(periods=periods, parameters=default_params)
        df, _ = run_valuation(cohort)
        assert all(df["attrition_accounts"] == 0.0)

    def test_full_charge_off_period1(self, default_params):
        """If 100% charge off in period 1, no one survives to period 2."""
        periods = [
            make_period(1, prob_charge_off=1.0, prob_attrition=0.0),
            make_period(2, prob_charge_off=0.0, prob_attrition=0.0),
        ]
        cohort = CohortInput(periods=periods, parameters=default_params)
        df, _ = run_valuation(cohort)
        assert df["active_accounts_bop"].iloc[1] == pytest.approx(0.0)
        assert df["total_revenue"].iloc[1] == pytest.approx(0.0)

    def test_zero_discount_rate(self):
        """With discount_rate=0, PV equals nominal net income."""
        params = GlobalParameters(
            flat_interchange_rate=0.02, discount_rate=0.0, num_accounts=1000
        )
        cohort = CohortInput(
            periods=[make_period(1), make_period(2)],
            parameters=params,
        )
        df, summary = run_valuation(cohort)
        assert df["discount_factor"].iloc[0] == pytest.approx(1.0)
        assert df["discount_factor"].iloc[1] == pytest.approx(1.0)
        assert summary.total_pv == pytest.approx(summary.total_net_income)


class TestSummary:
    def test_summary_pv_per_account(self, single_period_cohort):
        _, summary = run_valuation(single_period_cohort)
        assert summary.pv_per_account == pytest.approx(
            summary.total_pv / 1000
        )

    def test_summary_num_periods(self, sixty_period_cohort):
        _, summary = run_valuation(sixty_period_cohort)
        assert summary.num_periods == 60

    def test_final_survival_rate_decreases(self, sixty_period_cohort):
        _, summary = run_valuation(sixty_period_cohort)
        # With 5% exit rate per period over 60 periods, survival should be low
        assert 0.0 < summary.final_survival_rate < 1.0
