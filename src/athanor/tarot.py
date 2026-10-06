import hashlib
import json
import random
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date
from pathlib import Path

MAJORS = (
    ("0", "The Fool", "Fool", "beginnings, a leap, innocence", "recklessness, hesitation"),
    ("I", "The Magician", "Magician", "will, skill, making it happen", "trickery, untapped talent"),
    (
        "II",
        "The High Priestess",
        "High Priestess",
        "intuition, the hidden, silence",
        "secrets kept, surface reading",
    ),
    ("III", "The Empress", "Empress", "abundance, growth, care", "smothering, stalled work"),
    ("IV", "The Emperor", "Emperor", "structure, authority, order", "rigidity, control slipping"),
    (
        "V",
        "The Hierophant",
        "Hierophant",
        "tradition, teaching, convention",
        "dogma, breaking the rules",
    ),
    ("VI", "The Lovers", "Lovers", "union, choice, alignment", "discord, a choice avoided"),
    (
        "VII",
        "The Chariot",
        "Chariot",
        "drive, victory through control",
        "scattered will, losing the road",
    ),
    (
        "VIII",
        "Strength",
        "Strength",
        "patience, quiet courage",
        "self-doubt, force over gentleness",
    ),
    ("IX", "The Hermit", "Hermit", "solitude, searching, an inner light", "isolation, withdrawal"),
    (
        "X",
        "Wheel of Fortune",
        "Wheel of Fortune",
        "cycles, turning luck",
        "bad timing, resisting change",
    ),
    ("XI", "Justice", "Justice", "fairness, cause and effect", "imbalance, dodging accountability"),
    (
        "XII",
        "The Hanged Man",
        "Hanged Man",
        "pause, surrender, a new view",
        "stalling, needless sacrifice",
    ),
    ("XIII", "Death", "Death", "endings, transformation", "clinging, slow decay"),
    ("XIV", "Temperance", "Temperance", "balance, moderation, mixing well", "excess, impatience"),
    ("XV", "The Devil", "Devil", "bondage, appetite, attachment", "release, breaking chains"),
    ("XVI", "The Tower", "Tower", "upheaval, sudden truth", "disaster averted, fear of change"),
    ("XVII", "The Star", "Star", "hope, renewal, calm", "discouragement, faith wavering"),
    ("XVIII", "The Moon", "Moon", "illusion, dreams, unease", "confusion lifting, fear released"),
    ("XIX", "The Sun", "Sun", "clarity, success, warmth", "clouded joy, delay"),
    (
        "XX",
        "Judgement",
        "Judgement",
        "reckoning, awakening, a call",
        "self-doubt, ignoring the call",
    ),
    ("XXI", "The World", "World", "completion, integration, arrival", "loose ends, a near finish"),
)

SUITS = (
    (
        "Wands",
        "Wands",
        (
            ("spark, inspiration", "delays, a false start"),
            ("planning, looking ahead", "fear of the unknown"),
            ("expansion, foresight", "obstacles at a distance"),
            ("celebration, homecoming", "shaky foundations"),
            ("conflict, competition", "avoidance, an uneasy truce"),
            ("victory, recognition", "pride before a fall"),
            ("holding your ground", "overwhelmed, giving way"),
            ("speed, news in motion", "delays, frustration"),
            ("resilience, the last stand", "exhaustion"),
            ("burden, overcommitment", "setting the load down"),
            ("curiosity, a message", "scattered energy"),
            ("action, adventure", "haste"),
            ("confidence, warmth", "jealousy"),
            ("vision, leadership", "impulsiveness"),
        ),
    ),
    (
        "Cups",
        "Cups",
        (
            ("new feeling, overflow", "emotional block"),
            ("partnership, mutual pull", "imbalance between two"),
            ("friendship, celebration", "overindulgence"),
            ("apathy, contemplation", "renewed interest"),
            ("loss, regret", "acceptance"),
            ("nostalgia, kindness", "stuck in the past"),
            ("choices, fantasy", "clarity arrives"),
            ("walking away", "fear of leaving"),
            ("contentment, a wish granted", "smugness"),
            ("harmony, family", "a broken home"),
            ("tender news, intuition", "emotional immaturity"),
            ("romance, an invitation", "moodiness"),
            ("compassion, calm", "martyrdom"),
            ("emotional balance", "manipulation"),
        ),
    ),
    (
        "Swords",
        "Swords",
        (
            ("clarity, breakthrough", "confusion"),
            ("stalemate, a hard choice", "too much information"),
            ("heartbreak, grief", "recovery"),
            ("rest, recovery", "restlessness"),
            ("a hollow victory", "reconciliation"),
            ("transition, passage", "an unfinished move"),
            ("deception, stealth", "coming clean"),
            ("restriction, self-made traps", "release"),
            ("anxiety, sleeplessness", "hope returning"),
            ("rock bottom, an ending", "recovery begins"),
            ("vigilance, curiosity", "gossip"),
            ("a charge, ambition", "recklessness"),
            ("perception, honesty", "coldness"),
            ("intellect, judgment", "tyranny"),
        ),
    ),
    (
        "Pentacles",
        "Pents",
        (
            ("opportunity, prosperity", "a missed chance"),
            ("juggling, adaptability", "overwhelm"),
            ("craft, teamwork", "poor workmanship"),
            ("holding on, security", "greed"),
            ("hardship, left out in the cold", "recovery"),
            ("generosity, fair exchange", "strings attached"),
            ("patience, the long view", "impatience"),
            ("diligence, practice", "perfectionism"),
            ("self-sufficiency, comfort", "overwork"),
            ("legacy, wealth", "family trouble"),
            ("study, a plan", "procrastination"),
            ("steady work", "boredom"),
            ("nurture, practicality", "self-neglect"),
            ("abundance, security", "stubbornness"),
        ),
    ),
)

RANKS = (
    "Ace",
    "Two",
    "Three",
    "Four",
    "Five",
    "Six",
    "Seven",
    "Eight",
    "Nine",
    "Ten",
    "Page",
    "Knight",
    "Queen",
    "King",
)

PLANET_TRUMP = {
    "Mercury": 1,
    "Moon": 2,
    "Venus": 3,
    "Jupiter": 10,
    "Mars": 16,
    "Sun": 19,
    "Saturn": 21,
}


@dataclass(frozen=True)
class Card:
    index: int
    numeral: str
    name: str
    upright: str
    reversed: str
    commons: str

    @property
    def title(self) -> str:
        return f"{self.numeral} {self.name}" if self.numeral else self.name


@dataclass(frozen=True)
class Draw:
    card: Card
    reversed: bool

    @property
    def title(self) -> str:
        return self.card.title + (", reversed" if self.reversed else "")

    @property
    def meaning(self) -> str:
        return self.card.reversed if self.reversed else self.card.upright


def _build() -> tuple[Card, ...]:
    cards = [
        Card(i, numeral, name, up, rev, f"RWS Tarot {i:02d} {file}.jpg")
        for i, (numeral, name, file, up, rev) in enumerate(MAJORS)
    ]
    for suit, file, meanings in SUITS:
        for rank, (up, rev) in enumerate(meanings, start=1):
            cards.append(
                Card(
                    len(cards), "", f"{RANKS[rank - 1]} of {suit}", up, rev, f"{file}{rank:02d}.jpg"
                )
            )
    return tuple(cards)


DECK = _build()


def by_name(query: str) -> Card | None:
    q = query.lower().removeprefix("the ").strip()
    for card in DECK:
        name = card.name.lower().removeprefix("the ")
        if q in (name, card.numeral.lower()) or q == card.title.lower():
            return card
    return None


def draw_by_name(query: str) -> Draw | None:
    name, comma, rest = query.rpartition(",")
    if comma and rest.strip().lower() == "reversed":
        card = by_name(name)
        return Draw(card, True) if card else None
    card = by_name(query)
    return Draw(card, False) if card else None


def trump_for(planet: str) -> Card:
    return DECK[PLANET_TRUMP[planet]]


def card_of_day(day: date, seed: bytes) -> Draw:
    h = hashlib.sha256(day.isoformat().encode() + seed).digest()
    return Draw(DECK[int.from_bytes(h[:4]) % len(DECK)], bool(h[4] & 1))


def spread(n: int, rng: random.Random | None = None) -> list[Draw]:
    rng = rng or random.SystemRandom()
    return [Draw(card, rng.random() < 0.5) for card in rng.sample(DECK, n)]


SPREAD_POSITIONS = {
    1: ("",),
    3: ("past", "present", "future"),
    5: ("present", "challenge", "root", "recent past", "near future"),
}


API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "athanor/0.1 (https://github.com/script-wizards/athanor)"


def art_path(card: Card, art_dir: Path) -> Path:
    return art_dir / card.commons.replace(" ", "_")


def _thumb_urls(titles: list[str], width: int) -> dict[str, str]:
    params = {
        "action": "query",
        "prop": "imageinfo",
        "iiprop": "url",
        "iiurlwidth": str(width),
        "format": "json",
        "titles": "|".join(f"File:{t}" for t in titles),
    }
    req = urllib.request.Request(
        f"{API}?{urllib.parse.urlencode(params)}", headers={"User-Agent": USER_AGENT}
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        pages = json.load(r)["query"]["pages"].values()
    urls = {}
    for page in pages:
        info = page.get("imageinfo")
        if info:
            urls[page["title"].removeprefix("File:")] = info[0].get("thumburl") or info[0]["url"]
    return urls


def fetch_art(art_dir: Path, width: int = 320, log=print) -> int:
    art_dir.mkdir(parents=True, exist_ok=True)
    missing = [c for c in DECK if not art_path(c, art_dir).exists()]
    fetched = 0
    for start in range(0, len(missing), 40):
        batch = missing[start : start + 40]
        urls = _thumb_urls([c.commons for c in batch], width)
        for card in batch:
            url = urls.get(card.commons)
            if url is None:
                log(f"no scan of {card.name} on Commons")
                continue
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=60) as r:
                art_path(card, art_dir).write_bytes(r.read())
            fetched += 1
            log(f"fetched {card.name}")
    return fetched
