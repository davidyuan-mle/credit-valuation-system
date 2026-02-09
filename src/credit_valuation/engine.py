"""Core calculation engine — pure function pipeline."""

from __future__ import annotations

import pandas as pd

from credit_valuation.models import CohortInput, ValuationSummary


def build_period_table(cohort: CohortInput) -> pd.DataFrame:
    """Convert validated CohortInput into a base DataFrame."""
    rows = [p.model_dump() for p in cohort.periods]
    df = pd.DataFrame(rows)
    df["flat_interchange_rate"] = cohort.parameters.flat_interchange_rate
    df["discount_rate"] = cohort.parameters.discount_rate
    df["num_accounts"] = cohort.parameters.num_accounts
    return df


def compute_survival(df: pd.DataFrame) -> pd.DataFrame:
    """Add survival cascade columns."""
    df = df.copy()
    df["survival_factor"] = 1.0 - df["prob_charge_off"] - df["prob_attrition"]
    df["cumulative_survival"] = df["survival_factor"].cumprod().shift(1, fill_value=1.0)
    df["active_accounts_bop"] = df["num_accounts"] * df["cumulative_survival"]
    df["charge_off_accounts"] = df["active_accounts_bop"] * df["prob_charge_off"]
    df["attrition_accounts"] = df["active_accounts_bop"] * df["prob_attrition"]
    return df


def compute_revenue(df: pd.DataFrame) -> pd.DataFrame:
    """Add revenue columns."""
    df = df.copy()
    df["finance_charge"] = (
        df["active_accounts_bop"] * df["revolving_balance"] * df["finance_charge_rate"]
    )
    df["interchange"] = (
        df["active_accounts_bop"] * df["purchase_amount"] * df["flat_interchange_rate"]
    )
    df["fee_income"] = df["active_accounts_bop"] * df["other_fees"]
    df["total_revenue"] = df["finance_charge"] + df["interchange"] + df["fee_income"]
    return df


def compute_costs(df: pd.DataFrame) -> pd.DataFrame:
    """Add cost columns."""
    df = df.copy()
    df["charge_off_loss"] = (
        df["active_accounts_bop"] * df["prob_charge_off"] * df["revolving_balance"]
    )
    df["total_cost"] = df["charge_off_loss"]
    return df


def compute_net_income_and_pv(df: pd.DataFrame) -> pd.DataFrame:
    """Add net income, discount factors, and PV columns."""
    df = df.copy()
    df["net_income"] = df["total_revenue"] - df["total_cost"]
    annual_rate = df["discount_rate"]
    df["discount_factor"] = 1.0 / (1.0 + annual_rate) ** (df["period"] / 12.0)
    df["pv_net_income"] = df["net_income"] * df["discount_factor"]
    df["cumulative_pv"] = df["pv_net_income"].cumsum()
    return df


def compute_summary(df: pd.DataFrame, num_accounts: int) -> ValuationSummary:
    """Extract summary metrics from the completed DataFrame."""
    total_pv = float(df["pv_net_income"].sum())
    return ValuationSummary(
        total_pv=total_pv,
        pv_per_account=total_pv / num_accounts,
        total_revenue=float(df["total_revenue"].sum()),
        total_cost=float(df["total_cost"].sum()),
        total_net_income=float(df["net_income"].sum()),
        final_survival_rate=float(df["cumulative_survival"].iloc[-1] * df["survival_factor"].iloc[-1]),
        num_periods=len(df),
        num_accounts=num_accounts,
    )


def run_valuation(cohort: CohortInput) -> tuple[pd.DataFrame, ValuationSummary]:
    """Run the full valuation pipeline.

    Returns the detailed period-by-period DataFrame and a ValuationSummary.
    """
    df = build_period_table(cohort)
    df = compute_survival(df)
    df = compute_revenue(df)
    df = compute_costs(df)
    df = compute_net_income_and_pv(df)
    summary = compute_summary(df, cohort.parameters.num_accounts)
    return df, summary
