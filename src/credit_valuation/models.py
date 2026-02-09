"""Pydantic models for credit valuation inputs and outputs."""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class PeriodData(BaseModel):
    """Input data for a single statement period."""

    period: int = Field(ge=1, le=60)
    prob_charge_off: float = Field(ge=0.0, le=1.0)
    prob_attrition: float = Field(ge=0.0, le=1.0)
    revolving_balance: float = Field(ge=0.0)
    purchase_amount: float = Field(ge=0.0)
    finance_charge_rate: float = Field(ge=0.0, le=1.0)
    other_fees: float = Field(ge=0.0)

    @model_validator(mode="after")
    def _competing_risks_valid(self) -> PeriodData:
        if self.prob_charge_off + self.prob_attrition > 1.0:
            raise ValueError(
                f"prob_charge_off ({self.prob_charge_off}) + "
                f"prob_attrition ({self.prob_attrition}) exceeds 1.0"
            )
        return self


class GlobalParameters(BaseModel):
    """Parameters that apply across all periods."""

    flat_interchange_rate: float = Field(ge=0.0, le=1.0)
    discount_rate: float = Field(ge=0.0, description="Annual discount rate")
    num_accounts: int = Field(gt=0)


class CohortInput(BaseModel):
    """Complete input: per-period data plus global parameters."""

    periods: list[PeriodData]
    parameters: GlobalParameters

    @model_validator(mode="after")
    def _periods_sequential(self) -> CohortInput:
        expected = list(range(1, len(self.periods) + 1))
        actual = [p.period for p in self.periods]
        if actual != expected:
            raise ValueError(
                f"Periods must be sequential starting at 1. Got: {actual[:5]}..."
            )
        return self


class ValuationSummary(BaseModel):
    """Summary metrics produced by the valuation engine."""

    total_pv: float
    pv_per_account: float
    total_revenue: float
    total_cost: float
    total_net_income: float
    final_survival_rate: float
    num_periods: int
    num_accounts: int
