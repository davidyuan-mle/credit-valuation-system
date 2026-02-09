"""Shared test helpers."""

from credit_valuation.models import PeriodData


def make_period(period: int, **overrides) -> PeriodData:
    """Create a PeriodData with sensible defaults, overridable per field."""
    defaults = dict(
        period=period,
        prob_charge_off=0.02,
        prob_attrition=0.03,
        revolving_balance=5000.0,
        purchase_amount=1000.0,
        finance_charge_rate=0.015,
        other_fees=25.0,
    )
    defaults.update(overrides)
    return PeriodData(**defaults)
