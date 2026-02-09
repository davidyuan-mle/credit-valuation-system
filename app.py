"""Streamlit dashboard for the Credit Valuation System."""

from __future__ import annotations

import io
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from credit_valuation import (
    CohortInput,
    GlobalParameters,
    PeriodData,
    ValuationSummary,
    run_valuation,
)
from credit_valuation.io import EXPECTED_COLUMNS

SAMPLE_CSV = Path(__file__).resolve().parent / "examples" / "sample_input.csv"

DISPLAY_COLUMNS = [
    "period",
    "active_accounts_bop",
    "total_revenue",
    "total_cost",
    "net_income",
    "discount_factor",
    "pv_net_income",
    "cumulative_pv",
]


def _parse_csv(source: str | Path) -> list[PeriodData]:
    """Parse CSV from a path or string and return validated PeriodData list."""
    df = pd.read_csv(source)
    missing = EXPECTED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"CSV is missing required columns: {missing}")
    return [PeriodData(**row) for row in df.to_dict(orient="records")]


def _fmt_currency(value: float) -> str:
    return f"${value:,.2f}"


def _fmt_pct(value: float) -> str:
    return f"{value:.2%}"


# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Credit Valuation", layout="wide")
st.title("Credit Valuation Dashboard")

# ---------------------------------------------------------------------------
# Sidebar — inputs
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Inputs")

    uploaded_file = st.file_uploader("Upload Period CSV", type=["csv"])

    st.subheader("Global Parameters")
    interchange_rate = st.number_input(
        "Interchange Rate",
        min_value=0.0,
        max_value=1.0,
        value=0.02,
        step=0.005,
        format="%.4f",
    )
    discount_rate = st.number_input(
        "Annual Discount Rate",
        min_value=0.0,
        max_value=1.0,
        value=0.10,
        step=0.01,
        format="%.4f",
    )
    num_accounts = st.number_input(
        "Number of Accounts",
        min_value=1,
        value=10_000,
        step=1000,
    )

    run_clicked = st.button("Run Valuation", type="primary", use_container_width=True)

# ---------------------------------------------------------------------------
# Run valuation
# ---------------------------------------------------------------------------
if run_clicked:
    try:
        if uploaded_file is not None:
            csv_source = io.StringIO(uploaded_file.getvalue().decode("utf-8"))
        else:
            csv_source = SAMPLE_CSV

        periods = _parse_csv(csv_source)
        params = GlobalParameters(
            flat_interchange_rate=interchange_rate,
            discount_rate=discount_rate,
            num_accounts=num_accounts,
        )
        cohort = CohortInput(periods=periods, parameters=params)
        df, summary = run_valuation(cohort)
    except Exception as exc:
        st.error(f"Validation error: {exc}")
        st.stop()

    # Store results in session state so they persist across reruns
    st.session_state["df"] = df
    st.session_state["summary"] = summary

if "df" not in st.session_state:
    st.info("Configure parameters in the sidebar and click **Run Valuation** to begin.")
    st.stop()

df: pd.DataFrame = st.session_state["df"]
summary: ValuationSummary = st.session_state["summary"]

# ---------------------------------------------------------------------------
# Row 1 — Summary metrics
# ---------------------------------------------------------------------------
st.subheader("Summary Metrics")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total PV", _fmt_currency(summary.total_pv))
c2.metric("PV per Account", _fmt_currency(summary.pv_per_account))
c3.metric("Final Survival Rate", _fmt_pct(summary.final_survival_rate))
c4.metric("Total Net Income", _fmt_currency(summary.total_net_income))

# ---------------------------------------------------------------------------
# Row 2 — Account Survival & Cumulative PV
# ---------------------------------------------------------------------------
left, right = st.columns(2)

with left:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["period"], y=df["active_accounts_bop"],
        mode="lines", name="Active Accounts",
    ))
    fig.update_layout(
        title="Account Survival",
        xaxis_title="Period",
        yaxis_title="Active Accounts (BOP)",
        margin=dict(t=40, b=30),
    )
    st.plotly_chart(fig, use_container_width=True)

with right:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["period"], y=df["cumulative_pv"],
        mode="lines", name="Cumulative PV",
    ))
    fig.update_layout(
        title="Cumulative Present Value",
        xaxis_title="Period",
        yaxis_title="Cumulative PV ($)",
        margin=dict(t=40, b=30),
    )
    st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# Row 3 — Revenue Breakdown & Net Income vs Charge-Off
# ---------------------------------------------------------------------------
left2, right2 = st.columns(2)

with left2:
    fig = go.Figure()
    for col, name in [
        ("finance_charge", "Finance Charge"),
        ("interchange", "Interchange"),
        ("fee_income", "Fee Income"),
    ]:
        fig.add_trace(go.Scatter(
            x=df["period"], y=df[col],
            mode="lines", stackgroup="revenue", name=name,
        ))
    fig.update_layout(
        title="Revenue Breakdown",
        xaxis_title="Period",
        yaxis_title="Revenue ($)",
        margin=dict(t=40, b=30),
    )
    st.plotly_chart(fig, use_container_width=True)

with right2:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["period"], y=df["net_income"],
        mode="lines", name="Net Income",
    ))
    fig.add_trace(go.Scatter(
        x=df["period"], y=df["charge_off_loss"],
        mode="lines", name="Charge-Off Loss",
    ))
    fig.update_layout(
        title="Net Income vs Charge-Off Loss",
        xaxis_title="Period",
        yaxis_title="Amount ($)",
        margin=dict(t=40, b=30),
    )
    st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# Row 4 — Detailed results table + downloads
# ---------------------------------------------------------------------------
st.subheader("Detailed Results")
st.dataframe(df[DISPLAY_COLUMNS], use_container_width=True, hide_index=True)

dl1, dl2, _ = st.columns([1, 1, 3])

with dl1:
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download CSV",
        data=csv_bytes,
        file_name="valuation_results.csv",
        mime="text/csv",
    )

with dl2:
    excel_buf = io.BytesIO()
    df.to_excel(excel_buf, index=False, engine="openpyxl")
    st.download_button(
        "Download Excel",
        data=excel_buf.getvalue(),
        file_name="valuation_results.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
