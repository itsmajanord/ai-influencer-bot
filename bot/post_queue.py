"""Inläggskön: varje inlägg är en json-fil i queue/<persona>/ och bilder i docs/media/<persona>/<id>/."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .config import MEDIA_DIR, QUEUE_DIR


def post_path(persona_id: str, post_id: str) -> Path:
    return QUEUE_DIR / persona_id / f"{post_id}.json"


def media_dir(persona_id: str, post_id: str) -> Path:
    return MEDIA_DIR / persona_id / post_id


def media_url(base_url: str, persona_id: str, post_id: str, filename: str) -> str:
    return f"{base_url.rstrip('/')}/media/{persona_id}/{post_id}/{filename}"


def save(post: dict) -> Path:
    path = post_path(post["persona"], post["id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(post, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def load_all() -> list[dict]:
    posts = []
    for path in sorted(QUEUE_DIR.glob("*/*.json")):
        post = json.loads(path.read_text(encoding="utf-8"))
        post["_path"] = str(path)
        posts.append(post)
    return posts


def strip_internal(post: dict) -> dict:
    return {k: v for k, v in post.items() if not k.startswith("_")}


def recent_captions(persona_id: str, limit: int = 12) -> list[str]:
    posts = [p for p in load_all() if p["persona"] == persona_id]
    posts.sort(key=lambda p: p["scheduled_at"])
    return [p["caption_raw"] for p in posts[-limit:]]


def is_due(post: dict, now: datetime, platform: str) -> bool:
    status = post.get("status", {}).get(platform, {})
    if status.get("state") in ("published", "sent_to_inbox", "skipped"):
        return False
    if status.get("attempts", 0) >= 3:
        return False
    return datetime.fromisoformat(post["scheduled_at"]) <= now
