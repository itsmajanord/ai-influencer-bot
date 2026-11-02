"""Räknar ut publiceringstider för kommande vecka."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

DAYS = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}


def parse_slot(slot: str) -> tuple[int, time]:
    day, hhmm = slot.strip().lower().split()
    if day not in DAYS:
        raise ValueError(f"Okänd dag '{day}' i schemat (använd mon/tue/wed/thu/fri/sat/sun)")
    h, m = hhmm.split(":")
    return DAYS[day], time(int(h), int(m))


def next_week_start(today: date) -> date:
    """Närmaste kommande måndag (aldrig idag)."""
    days_ahead = 7 - today.weekday()
    return today + timedelta(days=days_ahead)


def week_slots(schedule: list[str], posts_per_week: int, week_start: date, tz: str) -> list[datetime]:
    """Returnerar posts_per_week tidpunkter (tz-medvetna) för veckan som börjar week_start."""
    zone = ZoneInfo(tz)
    parsed = sorted(parse_slot(s) for s in schedule)
    if not parsed:
        raise ValueError("Schemat är tomt")
    slots = []
    for i in range(posts_per_week):
        weekday, t = parsed[i % len(parsed)]
        # Fler inlägg än tider? Lägg extra inlägg samma dag 3 h senare.
        extra_shift = timedelta(hours=3 * (i // len(parsed)))
        dt = datetime.combine(week_start + timedelta(days=weekday), t, tzinfo=zone) + extra_shift
        slots.append(dt)
    return sorted(slots)
