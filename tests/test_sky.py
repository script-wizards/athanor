from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from athanor import sky

NYC = (40.7128, -74.0060)
TOKYO = (35.6762, 139.6503)
NY = ZoneInfo("America/New_York")


def close(a: datetime, b: datetime, minutes: int = 4) -> bool:
    return abs(a - b) <= timedelta(minutes=minutes)


def test_new_york_sun_times():
    # Published times for 2026-10-04: sunrise 06:57, sunset 18:35 EDT.
    rise, set_ = sky.sun_times(date(2026, 10, 4), *NYC, NY)
    assert close(rise, datetime(2026, 10, 4, 6, 57, tzinfo=NY))
    assert close(set_, datetime(2026, 10, 4, 18, 35, tzinfo=NY))


def test_tokyo_sunrise_lands_on_the_local_date():
    tz = ZoneInfo("Asia/Tokyo")
    rise, set_ = sky.sun_times(date(2026, 6, 21), *TOKYO, tz)
    assert rise.astimezone(tz).date() == date(2026, 6, 21)
    assert close(rise, datetime(2026, 6, 21, 4, 26, tzinfo=tz), 5)
    assert close(set_, datetime(2026, 6, 21, 19, 0, tzinfo=tz), 5)


def test_polar_night_has_no_sun_times():
    assert sky.sun_times(date(2026, 12, 21), 78.2, 15.6, UTC) is None


def test_first_hour_after_sunrise_belongs_to_the_day_ruler():
    rise, _ = sky.sun_times(date(2026, 10, 4), *NYC, NY)
    ph = sky.planetary_hour(rise + timedelta(minutes=5), NYC)
    assert (ph.day_ruler, ph.planet, ph.index, ph.is_day) == ("Sun", "Sun", 0, True)


def test_hours_follow_the_chaldean_order():
    start = datetime(2026, 10, 4, 6, 0, tzinfo=NY)
    planets = [sky.planetary_hour(start + timedelta(hours=h, minutes=30)).planet for h in range(5)]
    assert planets == ["Sun", "Venus", "Mercury", "Moon", "Saturn"]


def test_before_dawn_belongs_to_the_previous_day():
    ph = sky.planetary_hour(datetime(2026, 10, 5, 3, 0, tzinfo=NY))
    assert ph.day == date(2026, 10, 4)
    assert ph.day_ruler == "Sun"
    assert ph.index == 21
    assert not ph.is_day
    assert ph.planet == sky.CHALDEAN[(3 + 21) % 7]


def test_monday_belongs_to_the_moon():
    ph = sky.planetary_hour(datetime(2026, 10, 5, 6, 30, tzinfo=NY))
    assert (ph.day_ruler, ph.planet) == ("Moon", "Moon")
    assert ph.approximate


@pytest.mark.parametrize(
    ("when", "phase"),
    [
        (datetime(2024, 4, 8, 18, 21, tzinfo=UTC), "new"),  # total solar eclipse
        (datetime(2024, 4, 23, 23, 49, tzinfo=UTC), "full"),
        (datetime(2025, 9, 7, 18, 9, tzinfo=UTC), "full"),  # total lunar eclipse
    ],
)
def test_moon_phase(when, phase):
    assert sky.moon_phase(when) == phase


def test_ordinals():
    assert [sky.ordinal(n) for n in (1, 2, 3, 4, 11, 12, 13, 21, 22, 23, 31)] == [
        "1st",
        "2nd",
        "3rd",
        "4th",
        "11th",
        "12th",
        "13th",
        "21st",
        "22nd",
        "23rd",
        "31st",
    ]
