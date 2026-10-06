from .sky import PlanetaryHour

STAGES = {
    "umber": "nigredo",
    "vellum": "albedo",
    "orpiment": "citrinitas",
    "cinnabar": "rubedo",
}

DAYLIGHT = ("vellum", "orpiment", "cinnabar")


def scheme_at(hour: PlanetaryHour) -> str:
    if not hour.is_day:
        return "umber"
    return DAYLIGHT[hour.index // 4]


def announcement(scheme: str) -> str:
    return f"The work passes into {STAGES[scheme]}."
