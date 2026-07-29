from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from zenml.utils.time_utils import expires_in, iso8601_to_utc_naive, seconds_to_human_readable, to_utc_timezone


def test_iso8601_to_utc_naive_expected_behaviors() -> None:
    """Covers expected parsing and UTC-normalization behavior."""
    # Offset -> converted to UTC, returned naive
    assert iso8601_to_utc_naive("2026-02-18T10:15:30+02:00") == datetime(
        2026, 2, 18, 8, 15, 30
    )

    # Zulu -> treated as UTC, returned naive
    assert iso8601_to_utc_naive("2026-02-18T08:15:30Z") == datetime(
        2026, 2, 18, 8, 15, 30
    )

    # Naive -> returned as-is
    assert iso8601_to_utc_naive("2026-02-18T08:15:30") == datetime(
        2026, 2, 18, 8, 15, 30
    )

    # Whitespace tolerated
    assert iso8601_to_utc_naive(" 2026-02-18T08:15:30Z  ") == datetime(
        2026, 2, 18, 8, 15, 30
    )


def test_iso8601_to_utc_naive_unexpected_inputs_raise_value_error() -> None:
    """Covers invalid inputs that must raise ValueError."""
    with pytest.raises(ValueError):
        iso8601_to_utc_naive("")

    with pytest.raises(ValueError):
        iso8601_to_utc_naive("not-a-date")

    with pytest.raises(ValueError):
        iso8601_to_utc_naive("2026-02-30T08:15:30")  # invalid date

    with pytest.raises(ValueError):
        iso8601_to_utc_naive("2026-02-18T08:15:30+99:99")  # invalid offset


def test_seconds_to_human_readable_simple_minutes() -> None:
    """90 seconds should read as 1 minute 30 seconds."""
    assert seconds_to_human_readable(90) == "1m30s"


def test_seconds_to_human_readable_all_units() -> None:
    """A value spanning days, hours, minutes and seconds."""
    total = 86400 + 7200 + 180 + 4
    assert seconds_to_human_readable(total) == "1d2h3m4s"


def test_seconds_to_human_readable_zero() -> None:
    """Zero seconds should return an empty string, since no token applies."""
    assert seconds_to_human_readable(0) == ""


def test_seconds_to_human_readable_exact_minute() -> None:
    """Exactly 60 seconds should roll over to 1 minute, not '60s'."""
    assert seconds_to_human_readable(60) == "1m"


def test_expires_in_future() -> None:
    """When expiry is in the future, returns human-readable time left."""
    fixed_now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    future_time = fixed_now + timedelta(seconds=90)
    with patch("zenml.utils.time_utils.utc_now", return_value=fixed_now):
        result = expires_in(future_time, "expired")
    assert result == "1m30s"


def test_expires_in_expired() -> None:
    """When expiry is in the past, returns the expired string."""
    past_time = datetime.now(timezone.utc) - timedelta(seconds=90)
    result = expires_in(past_time, "expired")
    assert result == "expired"


def test_expires_in_skew_tolerance() -> None:
    """When skew_tolerance pushes an otherwise-future expiry into the past,
    returns the expired string."""
    near_future = datetime.now(timezone.utc) + timedelta(seconds=60)
    result = expires_in(near_future, "expired", skew_tolerance=120)
    assert result == "expired"


def test_expires_in_boundary_now() -> None:
    """When expiry is exactly now, treated as expired."""
    now_time = datetime.now(timezone.utc)
    result = expires_in(now_time, "expired")
    assert result == "expired"


def test_to_utc_timezone_naive_input() -> None:
    """A naive datetime is assumed to already be UTC and gets tagged as such."""
    naive_dt = datetime(2026, 1, 1, 10, 0, 0)
    result = to_utc_timezone(naive_dt)
    assert result == datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    assert result.tzinfo == timezone.utc


def test_to_utc_timezone_already_utc() -> None:
    """A datetime already in UTC should be returned unchanged in value."""
    utc_dt = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    result = to_utc_timezone(utc_dt)
    assert result == utc_dt
    assert result.tzinfo == timezone.utc


def test_to_utc_timezone_converts_other_timezone() -> None:
    """A datetime in IST (+5:30) should be converted to the correct UTC time."""
    ist = timezone(timedelta(hours=5, minutes=30))
    ist_dt = datetime(2026, 1, 1, 15, 30, 0, tzinfo=ist)
    result = to_utc_timezone(ist_dt)
    assert result == datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)


def test_to_utc_timezone_negative_offset() -> None:
    """A datetime in a negative-offset timezone (e.g. US Eastern, -5:00) converts correctly."""
    est = timezone(timedelta(hours=-5))
    est_dt = datetime(2026, 1, 1, 5, 0, 0, tzinfo=est)
    result = to_utc_timezone(est_dt)
    assert result == datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
