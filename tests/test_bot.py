from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from bot import content, post_queue
from bot.config import load_config, load_personas
from bot.schedule import next_week_start, parse_slot, week_slots

TZ = "Europe/Stockholm"


def test_personas_load():
    ids = {p.id for p in load_personas()}
    assert ids == {"maja"}
    assert {p.id for p in load_personas(only_active=False)} == {"maja", "ebba", "sara"}
    for p in load_personas(only_active=False):
        assert len(p.schedule) >= 1 and p.posts_per_week >= 1
        for s in p.schedule:
            parse_slot(s)


def test_next_week_start_is_monday_and_future():
    for d in range(2, 9):  # 2–8 nov 2026, mån–sön
        start = next_week_start(date(2026, 11, d))
        assert start.weekday() == 0 and start > date(2026, 11, d)


def test_week_slots_dst_and_order():
    slots = week_slots(["fri 17:00", "mon 07:15"], 2, date(2026, 11, 9), TZ)
    assert slots[0] == datetime(2026, 11, 9, 7, 15, tzinfo=ZoneInfo(TZ))
    assert slots[1].weekday() == 4
    # sommartid: offset +02:00
    summer = week_slots(["mon 07:15"], 1, date(2026, 6, 8), TZ)[0]
    assert summer.utcoffset().total_seconds() == 7200


def test_more_posts_than_slots():
    slots = week_slots(["mon 07:00"], 3, date(2026, 11, 9), TZ)
    assert [s.hour for s in slots] == [7, 10, 13]


def test_caption_always_has_ai_disclosure():
    cfg = load_config()
    cap = content.build_caption({"caption": "Hej!", "hashtags": ["#löpning", "#AI"]}, cfg)
    assert cfg["disclosure"]["caption_line"] in cap
    assert cap.count("#AI ") + cap.endswith("#AI") == 1  # ingen dubblett
    assert "#löpning" in cap


@pytest.mark.parametrize("state,expected", [(None, True), ("published", False), ("sent_to_inbox", False)])
def test_is_due(state, expected):
    post = {"scheduled_at": "2026-11-09T07:15:00+01:00", "status": {}}
    if state:
        post["status"]["instagram"] = {"state": state}
    now = datetime(2026, 11, 9, 8, 0, tzinfo=ZoneInfo(TZ))
    assert post_queue.is_due(post, now, "instagram") is expected
    early = datetime(2026, 11, 9, 7, 0, tzinfo=ZoneInfo(TZ))
    assert post_queue.is_due(post, early, "instagram") is False
