# Sunrise and sunset from the Almanac for Computers (1990). Off by a minute or
# two, and wrong past the polar circles.

import math
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta, tzinfo

CHALDEAN = ("Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon")

# Monday first, to match date.weekday().
DAY_RULER = (6, 2, 5, 1, 4, 0, 3)

SYNODIC_MONTH = 29.530588853
NEW_MOON_EPOCH = datetime(2000, 1, 6, 18, 14, tzinfo=UTC)
ZENITH = 90.833


@dataclass(frozen=True)
class PlanetaryHour:
    day: date
    day_ruler: str
    planet: str
    index: int
    is_day: bool
    approximate: bool
    sunrise: datetime
    sunset: datetime


def with_article(planet: str) -> str:
    return f"the {planet}" if planet in ("Sun", "Moon") else planet


def _sun_event(d: date, lat: float, lon: float, rising: bool) -> datetime | None:
    rad, deg = math.radians, math.degrees
    lng_hour = lon / 15
    t = d.timetuple().tm_yday + ((6 if rising else 18) - lng_hour) / 24
    m = 0.9856 * t - 3.289
    true_lon = (m + 1.916 * math.sin(rad(m)) + 0.020 * math.sin(rad(2 * m)) + 282.634) % 360
    ra = deg(math.atan(0.91764 * math.tan(rad(true_lon)))) % 360
    ra += (true_lon // 90) * 90 - (ra // 90) * 90
    ra /= 15
    sin_dec = 0.39782 * math.sin(rad(true_lon))
    cos_dec = math.cos(math.asin(sin_dec))
    cos_h = (math.cos(rad(ZENITH)) - sin_dec * math.sin(rad(lat))) / (cos_dec * math.cos(rad(lat)))
    if not -1 <= cos_h <= 1:
        return None
    h = (360 - deg(math.acos(cos_h)) if rising else deg(math.acos(cos_h))) / 15
    ut = (h + ra - 0.06571 * t - 6.622 - lng_hour) % 24
    return datetime.combine(d, time(), UTC) + timedelta(hours=ut)


def _onto(moment: datetime, d: date, tz: tzinfo) -> datetime:
    # The almanac's time is mod 24h, so in local time it can land on the wrong day.
    local = moment.astimezone(tz).date()
    if local < d:
        return moment + timedelta(days=1)
    if local > d:
        return moment - timedelta(days=1)
    return moment


def sun_times(d: date, lat: float, lon: float, tz: tzinfo) -> tuple[datetime, datetime] | None:
    rise, set_ = _sun_event(d, lat, lon, True), _sun_event(d, lat, lon, False)
    if rise is None or set_ is None:
        return None
    return _onto(rise, d, tz), _onto(set_, d, tz)


def _civil(d: date, tz: tzinfo) -> tuple[datetime, datetime]:
    return datetime.combine(d, time(6), tz), datetime.combine(d, time(18), tz)


def _day_bounds(d: date, place: tuple[float, float] | None, tz: tzinfo):
    if place is not None:
        times = sun_times(d, *place, tz)
        if times is not None:
            return times[0], times[1], False
    return *_civil(d, tz), True


def planetary_hour(now: datetime, place: tuple[float, float] | None = None) -> PlanetaryHour:
    tz = now.tzinfo
    today = now.date()
    rise, set_, approx = _day_bounds(today, place, tz)

    if now < rise:
        day = today - timedelta(days=1)
        prev_rise, prev_set, approx_prev = _day_bounds(day, place, tz)
        start, end, offset, is_day = prev_set, rise, 12, False
        rise, set_, approx = prev_rise, prev_set, approx or approx_prev
    elif now < set_:
        day, start, end, offset, is_day = today, rise, set_, 0, True
    else:
        day = today
        next_rise, _, approx_next = _day_bounds(today + timedelta(days=1), place, tz)
        start, end, offset, is_day = set_, next_rise, 12, False
        approx = approx or approx_next

    span = (end - start) / 12
    index = offset + min(11, int((now - start) / span))
    ruler = DAY_RULER[day.weekday()]
    return PlanetaryHour(
        day=day,
        day_ruler=CHALDEAN[ruler],
        planet=CHALDEAN[(ruler + index) % 7],
        index=index,
        is_day=is_day,
        approximate=approx,
        sunrise=rise,
        sunset=set_,
    )


PHASES = (
    "new",
    "waxing crescent",
    "first quarter",
    "waxing gibbous",
    "full",
    "waning gibbous",
    "last quarter",
    "waning crescent",
)


def moon_age(now: datetime) -> float:
    days = (now - NEW_MOON_EPOCH).total_seconds() / 86400
    return days % SYNODIC_MONTH


def moon_phase(now: datetime) -> str:
    fraction = moon_age(now) / SYNODIC_MONTH
    return PHASES[int(fraction * 8 + 0.5) % 8]


def moon_trend(now: datetime) -> str:
    phase = moon_phase(now)
    if phase in ("new", "full"):
        return phase
    return "waxing" if moon_age(now) < SYNODIC_MONTH / 2 else "waning"


def ordinal(n: int) -> str:
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"
