#!/usr/bin/env python3
"""Unit tests for cutoff selection helpers."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.data_preparation.dataframe_preparer import DataFramePreparer
from backend.services.config import MAX_MISSING_DAYS_PER_MONTH


def test_select_full_months_by_day_accepts_complete_month():
    assert DataFramePreparer.select_full_months_by_day(
        "2025",
        "01",
        missing_days=[],
        warning_only=True,
    )


def test_select_full_months_by_day_respects_threshold():
    too_many_missing = list(range(1, MAX_MISSING_DAYS_PER_MONTH + 2))
    assert not DataFramePreparer.select_full_months_by_day(
        "2025",
        "01",
        missing_days=too_many_missing,
        warning_only=True,
    )


def test_select_full_months_by_day_requires_strict_when_warning_off():
    assert not DataFramePreparer.select_full_months_by_day(
        "2025",
        "01",
        missing_days=[1],
        warning_only=False,
    )


def test_select_full_months_requires_cutoff_column():
    preparer = DataFramePreparer()
    df = pd.DataFrame({"Date": ["2025-01-01"]})

    with pytest.raises(ValueError, match="Year-Month-cut-off"):
        preparer.select_full_months(df, warning_only=False)
