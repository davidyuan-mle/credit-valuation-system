# Credit Valuation System

This is a quick-and-dirty system built entirely by Claude from a few simple prompts.

A present-value calculation engine for credit card account cohorts. Given a portfolio of accounts and their expected behavior over time (charge-offs, attrition, balances, fees), the system computes period-by-period cash flows, discounts them to present value, and produces summary metrics that quantify the economic value of the cohort.

## How It Works

### The Problem

When a bank acquires or originates a cohort of credit card accounts, it needs to estimate the **present value** of the future net income those accounts will generate. This requires modeling:

- **Account attrition** — customers closing accounts or becoming inactive
- **Charge-offs** — accounts defaulting on their balances (a loss)
- **Revenue streams** — finance charges on revolving balances, interchange fees on purchases, and other fees
- **Time value of money** — future cash flows are worth less than present ones

### The Calculation Pipeline

The engine processes inputs through five sequential stages:

```
CohortInput → Period Table → Survival → Revenue → Costs → Net Income & PV
```

**1. Survival Cascade**

Each period, accounts can leave the cohort through charge-off or voluntary attrition. These are modeled as competing risks:

```
survival_factor = 1 - prob_charge_off - prob_attrition
cumulative_survival = product of all prior survival factors
active_accounts_bop = num_accounts * cumulative_survival
```

The "BOP" (beginning of period) active accounts drive all subsequent revenue and cost calculations.

**2. Revenue Calculation**

Three revenue streams are computed for each period based on the number of active accounts:

| Revenue Stream | Formula |
|---|---|
| Finance Charge | active_accounts * revolving_balance * finance_charge_rate |
| Interchange | active_accounts * purchase_amount * flat_interchange_rate |
| Fee Income | active_accounts * other_fees |

**3. Cost Calculation**

The primary cost is charge-off losses — the outstanding balance of accounts that default:

```
charge_off_loss = active_accounts * prob_charge_off * revolving_balance
```

**4. Net Income and Present Value**

Net income is discounted back to present value using the annual discount rate:

```
net_income = total_revenue - total_cost
discount_factor = 1 / (1 + annual_rate) ^ (period / 12)
pv_net_income = net_income * discount_factor
cumulative_pv = running sum of pv_net_income
```

The final `cumulative_pv` at the last period represents the total present value of the cohort.

## Input Format

### CSV File (per-period data)

| Column | Description | Range |
|---|---|---|
| period | Statement period number | 1-60 |
| prob_charge_off | Probability of charge-off | 0.0-1.0 |
| prob_attrition | Probability of voluntary attrition | 0.0-1.0 |
| revolving_balance | Average revolving balance per account ($) | >= 0 |
| purchase_amount | Average purchase amount per account ($) | >= 0 |
| finance_charge_rate | Monthly finance charge rate | 0.0-1.0 |
| other_fees | Other fees per account ($) | >= 0 |

Constraint: `prob_charge_off + prob_attrition <= 1.0` for each period.

### Global Parameters

| Parameter | Description |
|---|---|
| flat_interchange_rate | Interchange fee rate applied to purchase volume (e.g., 0.02 = 2%) |
| discount_rate | Annual discount rate for PV calculation (e.g., 0.10 = 10%) |
| num_accounts | Number of accounts in the cohort |

## Output

### Summary Metrics

- **Total PV** — present value of all future net income
- **PV per Account** — total PV divided by number of accounts
- **Final Survival Rate** — fraction of accounts remaining at the end
- **Total Revenue / Cost / Net Income** — undiscounted totals

### Detailed DataFrame

Period-by-period breakdown with all intermediate calculations: active accounts, revenue components, costs, discount factors, and cumulative PV.

## Project Structure

```
credit-valuation-system/
├── app.py                          # Streamlit dashboard
├── pyproject.toml                  # Project config and dependencies
├── src/credit_valuation/
│   ├── __init__.py                 # Public API exports
│   ├── models.py                   # Pydantic data models (input/output)
│   ├── engine.py                   # Calculation pipeline
│   └── io.py                       # CSV loading and result export
├── tests/                          # Test suite (pytest)
└── examples/
    ├── sample_input.csv            # 60-period sample dataset
    └── run_valuation.py            # CLI usage example
```

## Usage

### Installation

```bash
pip install -e ".[dev]"
```

### Streamlit Dashboard

```bash
streamlit run app.py
```

Opens an interactive dashboard where you can upload CSV data, adjust parameters, run the valuation, view charts, and download results.

### Python API

```python
from credit_valuation import load_cohort_input, run_valuation, export_results

cohort = load_cohort_input(
    csv_path="examples/sample_input.csv",
    flat_interchange_rate=0.02,
    discount_rate=0.10,
    num_accounts=10_000,
)

df, summary = run_valuation(cohort)

print(f"Total PV: ${summary.total_pv:,.2f}")
print(f"PV per Account: ${summary.pv_per_account:,.2f}")
print(f"Final Survival Rate: {summary.final_survival_rate:.2%}")

export_results(df, "results.csv")
```

### Running Tests

```bash
pytest
```
