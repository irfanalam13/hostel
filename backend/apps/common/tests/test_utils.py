import datetime as dt

from apps.common.utils import month_key, parse_month_key


def test_month_key_zero_pads_month():
    assert month_key(dt.date(2026, 3, 5)) == "2026-03"


def test_parse_month_key_round_trips_month_key():
    key = month_key(dt.date(2026, 11, 20))
    assert parse_month_key(key) == dt.date(2026, 11, 1)
