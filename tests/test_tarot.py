import random
from datetime import date

from athanor import sky, tarot


def test_deck():
    assert len(tarot.DECK) == 78
    assert len({c.name for c in tarot.DECK}) == 78
    assert len({c.commons for c in tarot.DECK}) == 78
    assert tarot.DECK[0].commons == "RWS Tarot 00 Fool.jpg"
    assert tarot.DECK[21].commons == "RWS Tarot 21 World.jpg"
    assert tarot.DECK[22].commons == "Wands01.jpg"
    assert tarot.DECK[77].name == "King of Pentacles"
    assert tarot.DECK[77].commons == "Pents14.jpg"


def test_every_planet_has_its_trump():
    assert set(tarot.PLANET_TRUMP) == set(sky.CHALDEAN)
    assert tarot.trump_for("Mercury").name == "The Magician"
    assert tarot.trump_for("Sun").title == "XIX The Sun"


def test_card_of_day_is_stable_per_day_and_host():
    a = tarot.card_of_day(date(2026, 10, 4), b"host-a")
    assert a == tarot.card_of_day(date(2026, 10, 4), b"host-a")
    days = {tarot.card_of_day(date(2026, 10, d), b"host-a").card.index for d in range(1, 29)}
    assert len(days) > 10


def test_spread_has_no_repeats():
    cards = tarot.spread(10, random.Random(7))
    assert len({d.card.index for d in cards}) == 10


def test_lookup_by_name():
    assert tarot.by_name("the tower").index == 16
    assert tarot.by_name("Tower").index == 16
    assert tarot.by_name("xvi").index == 16
    assert tarot.by_name("queen of cups").name == "Queen of Cups"
    assert tarot.by_name("nothing") is None


def test_reversed_meaning():
    draw = tarot.Draw(tarot.DECK[16], True)
    assert draw.title == "XVI The Tower, reversed"
    assert draw.meaning == tarot.DECK[16].reversed


def test_a_card_can_be_named_upright_or_reversed():
    upright = tarot.draw_by_name("the devil")
    assert (upright.card.name, upright.reversed) == ("The Devil", False)
    turned = tarot.draw_by_name("Eight of Cups, reversed")
    assert (turned.card.title, turned.reversed) == ("Eight of Cups", True)
    assert tarot.draw_by_name("the moon, sideways") is None
