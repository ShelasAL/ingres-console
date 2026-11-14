"""
Tests for NWIC Data Loader module.
"""
import sys
from pathlib import Path
from datetime import date
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ingres.data.nwic_loader import (
    NWIC_RESOURCES,
    _derive_season,
    _parse_date
)


def test_nwic_target_states_registered():
    expected = ["rajasthan", "punjab", "andhra", "delhi", "kerala", "tamil nadu", "uttar pradesh", "bihar"]
    for s in expected:
        assert s in NWIC_RESOURCES, f"State {s} missing from NWIC registry"
        assert "level_url" in NWIC_RESOURCES[s]
        assert "quality_url" in NWIC_RESOURCES[s]


def test_derive_season():
    # April = pre_monsoon
    assert _derive_season(date(2023, 4, 15)) == "pre_monsoon"
    # July = kharif
    assert _derive_season(date(2023, 7, 20)) == "kharif"
    # October = post_monsoon
    assert _derive_season(date(2023, 10, 30)) == "post_monsoon"
    # January = rabi
    assert _derive_season(date(2023, 1, 10)) == "rabi"


def test_parse_date():
    assert _parse_date("10-01-2022") == date(2022, 1, 10)
    assert _parse_date("2023-05-15 06:00") == date(2023, 5, 15)
    assert _parse_date(None) is None
    assert _parse_date("") is None

