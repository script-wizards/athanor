from datetime import date, datetime
from zoneinfo import ZoneInfo

from athanor import palette, sky, stages

NY = ZoneInfo("America/New_York")


def hour(index: int, is_day: bool) -> sky.PlanetaryHour:
    t = datetime(2026, 10, 5, 12, tzinfo=NY)
    return sky.PlanetaryHour(date(2026, 10, 5), "Moon", "Moon", index, is_day, True, t, t)


def test_night_is_nigredo():
    assert stages.scheme_at(hour(12, False)) == "umber"
    assert stages.scheme_at(hour(23, False)) == "umber"


def test_daylight_runs_albedo_citrinitas_rubedo():
    assert [stages.scheme_at(hour(i, True)) for i in range(12)] == (
        ["vellum"] * 4 + ["orpiment"] * 4 + ["cinnabar"] * 4
    )


def test_on_civil_hours_noon_is_citrinitas():
    noon = datetime(2026, 10, 5, 12, 30, tzinfo=NY)
    assert stages.scheme_at(sky.planetary_hour(noon)) == "orpiment"


def test_every_scheme_is_a_stage_in_cycle_order():
    assert tuple(stages.STAGES) == palette.SCHEMES
