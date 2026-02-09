"""I/O utilities — CSV loading and result export."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from credit_valuation.models import CohortInput, GlobalParameters, PeriodData

EXPECTED_COLUMNS = {
    "period",
    "prob_charge_off",
    "prob_attrition",
    "revolving_balance",
    "purchase_amount",
    "finance_charge_rate",
    "other_fees",
}


def load_periods_from_csv(path: str | Path) -> list[PeriodData]:
    """Read a CSV file and return a list of validated PeriodData."""
    df = pd.read_csv(path)
    missing = EXPECTED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"CSV is missing required columns: {missing}")
    return [PeriodData(**row) for row in df.to_dict(orient="records")]


def load_cohort_input(
    csv_path: str | Path,
    flat_interchange_rate: float,
    discount_rate: float,
    num_accounts: int,
) -> CohortInput:
    """Convenience: load CSV periods and combine with global parameters."""
    periods = load_periods_from_csv(csv_path)
    params = GlobalParameters(
        flat_interchange_rate=flat_interchange_rate,
        discount_rate=discount_rate,
        num_accounts=num_accounts,
    )
    return CohortInput(periods=periods, parameters=params)


def export_results(
    df: pd.DataFrame,
    path: str | Path,
    fmt: str = "csv",
) -> Path:
    """Export the results DataFrame to CSV or Excel.

    Args:
        df: Results DataFrame from run_valuation.
        path: Output file path.
        fmt: 'csv' or 'excel'.

    Returns:
        The resolved output Path.
    """
    path = Path(path)
    if fmt == "csv":
        df.to_csv(path, index=False)
    elif fmt == "excel":
        df.to_excel(path, index=False, engine="openpyxl")
    else:
        raise ValueError(f"Unsupported format: {fmt!r}. Use 'csv' or 'excel'.")
    return path
