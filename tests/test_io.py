"""Tests for I/O: CSV loading, round-trip, and export."""

import tempfile
from pathlib import Path

import pandas as pd
import pytest

from credit_valuation.io import export_results, load_cohort_input, load_periods_from_csv
from credit_valuation.engine import run_valuation

from helpers import make_period


class TestLoadCSV:
    def test_round_trip(self, tmp_path):
        """Write periods to CSV, load them back, verify equality."""
        periods = [make_period(t) for t in range(1, 4)]
        df = pd.DataFrame([p.model_dump() for p in periods])
        csv_path = tmp_path / "test.csv"
        df.to_csv(csv_path, index=False)

        loaded = load_periods_from_csv(csv_path)
        assert len(loaded) == 3
        assert loaded[0].period == 1
        assert loaded[2].revolving_balance == pytest.approx(5000.0)

    def test_missing_column_raises(self, tmp_path):
        df = pd.DataFrame({"period": [1], "prob_charge_off": [0.01]})
        csv_path = tmp_path / "bad.csv"
        df.to_csv(csv_path, index=False)

        with pytest.raises(ValueError, match="missing required columns"):
            load_periods_from_csv(csv_path)


class TestLoadCohortInput:
    def test_load_cohort_input(self, tmp_path):
        periods = [make_period(t) for t in range(1, 4)]
        df = pd.DataFrame([p.model_dump() for p in periods])
        csv_path = tmp_path / "input.csv"
        df.to_csv(csv_path, index=False)

        cohort = load_cohort_input(csv_path, 0.02, 0.10, 500)
        assert cohort.parameters.num_accounts == 500
        assert len(cohort.periods) == 3


class TestExport:
    def test_export_csv(self, single_period_cohort, tmp_path):
        df, _ = run_valuation(single_period_cohort)
        out = export_results(df, tmp_path / "out.csv", fmt="csv")
        assert out.exists()
        loaded = pd.read_csv(out)
        assert len(loaded) == 1

    def test_export_excel(self, single_period_cohort, tmp_path):
        df, _ = run_valuation(single_period_cohort)
        out = export_results(df, tmp_path / "out.xlsx", fmt="excel")
        assert out.exists()
        loaded = pd.read_excel(out, engine="openpyxl")
        assert len(loaded) == 1

    def test_unsupported_format_raises(self, single_period_cohort, tmp_path):
        df, _ = run_valuation(single_period_cohort)
        with pytest.raises(ValueError, match="Unsupported format"):
            export_results(df, tmp_path / "out.json", fmt="json")
