#!/usr/bin/env python3
"""Example: load sample data, run valuation, print summary, export results."""

from pathlib import Path

from credit_valuation import load_cohort_input, run_valuation, export_results

HERE = Path(__file__).parent


def main() -> None:
    # Load the 60-period sample input
    cohort = load_cohort_input(
        csv_path=HERE / "sample_input.csv",
        flat_interchange_rate=0.02,
        discount_rate=0.10,
        num_accounts=10_000,
    )

    # Run the valuation
    df, summary = run_valuation(cohort)

    # Print summary
    print("=" * 60)
    print("  Credit Valuation Summary")
    print("=" * 60)
    print(f"  Accounts:            {summary.num_accounts:>12,}")
    print(f"  Periods:             {summary.num_periods:>12}")
    print(f"  Total Revenue:       ${summary.total_revenue:>14,.2f}")
    print(f"  Total Cost:          ${summary.total_cost:>14,.2f}")
    print(f"  Total Net Income:    ${summary.total_net_income:>14,.2f}")
    print(f"  Total PV:            ${summary.total_pv:>14,.2f}")
    print(f"  PV per Account:      ${summary.pv_per_account:>14,.2f}")
    print(f"  Final Survival Rate: {summary.final_survival_rate:>13.2%}")
    print("=" * 60)

    # Show first 5 periods
    print("\nFirst 5 periods:")
    cols = [
        "period",
        "active_accounts_bop",
        "total_revenue",
        "total_cost",
        "net_income",
        "pv_net_income",
        "cumulative_pv",
    ]
    print(df[cols].head().to_string(index=False))

    # Export results
    out_path = export_results(df, HERE / "valuation_results.csv", fmt="csv")
    print(f"\nResults exported to: {out_path}")


if __name__ == "__main__":
    main()
