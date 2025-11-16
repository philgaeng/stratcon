#!/usr/bin/env python3
"""Timezone-aware cutoff handling tests."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.config import PHILIPPINES_TZ
from backend.services.data_preparation.cutoff_manager import CutoffManager


def _cutoff_month_label(date: datetime, cutoff) -> str:
    adjusted = CutoffManager.generate_cutoff_hourly_legacy(date, cutoff)
    return adjusted.astimezone(PHILIPPINES_TZ).strftime("%Y-%m")


def test_generate_cutoff_hourly_handles_pre_and_post_cutoff():
    cutoff = CutoffManager.create_cutoff_datetime(cutoff_day=14, hour=8, minute=0, second=0)

    before_cutoff = datetime(2024, 4, 14, 7, 59, 0)
    at_cutoff = datetime(2024, 4, 14, 8, 0, 0)
    after_cutoff = datetime(2024, 4, 14, 8, 1, 0)

    assert _cutoff_month_label(before_cutoff, cutoff) == "2024-04"
    assert _cutoff_month_label(at_cutoff, cutoff) == "2024-04"
    assert _cutoff_month_label(after_cutoff, cutoff) == "2024-04"


def test_create_cutoff_datetime_defaults_to_ph_timezone():
    cutoff = CutoffManager.create_cutoff_datetime(cutoff_day=14)
    assert cutoff.tzinfo is not None
    assert cutoff.utcoffset() == timedelta(hours=8)
    assert cutoff.day == 14
    assert (cutoff.hour, cutoff.minute, cutoff.second) == (23, 59, 59)


def test_cutoff_generation_with_timezone_conversion():
    cutoff = CutoffManager.create_cutoff_datetime(cutoff_day=14, hour=8, minute=0, second=0)
    utc_date = datetime(2024, 4, 14, 7, 59, 0, tzinfo=timezone.utc)

    label = _cutoff_month_label(utc_date, cutoff)
    assert label == "2024-04"
