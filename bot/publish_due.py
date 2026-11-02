"""Publicerar alla godkända inlägg vars tid har kommit. Körs var 30:e minut av GitHub Actions.

Användning: python -m bot.publish_due [--now 2026-11-09T08:00:00+01:00]
"""
from __future__ import annotations

import argparse
import sys
import traceback
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

from . import instagram, post_queue, tiktok
from .config import dry_run, load_config, persona_secret_name, secret
from .secrets_store import update_secret

MAX_LATE_HOURS = 12  # inlägg som missats mer än så hoppas över i stället för att postas mitt i natten


def _urls(cfg: dict, post: dict) -> list[str]:
    return [post_queue.media_url(cfg["public_base_url"], post["persona"], post["id"], f) for f in post["images"]]


def _media_live(urls: list[str]) -> bool:
    if dry_run():
        return True
    for u in urls:
        try:
            if requests.head(u, timeout=20, allow_redirects=True).status_code != 200:
                return False
        except requests.RequestException:
            return False
    return True


_tiktok_tokens: dict[str, str] = {}


def _tiktok_access(persona_id: str) -> str:
    if persona_id in _tiktok_tokens:
        return _tiktok_tokens[persona_id]
    name = persona_secret_name("TIKTOK_REFRESH", persona_id)
    data = tiktok.refresh(secret("TIKTOK_CLIENT_KEY"), secret("TIKTOK_CLIENT_SECRET"), secret(name))
    if data.get("refresh_token") and data["refresh_token"] != secret(name):
        update_secret(name, data["refresh_token"])
    _tiktok_tokens[persona_id] = data["access_token"]
    return data["access_token"]


def publish_one(post: dict, platform: str, cfg: dict) -> dict:
    urls = _urls(cfg, post)
    if dry_run():
        state = "sent_to_inbox" if platform == "tiktok" and cfg["tiktok"]["mode"] != "direct" else "published"
        return {"state": state, "id": f"dry-{platform}-{post['id']}"}
    pid = post["persona"]
    if platform == "instagram":
        media_id = instagram.publish(
            secret(persona_secret_name("IG_USER_ID", pid)),
            secret(persona_secret_name("IG_TOKEN", pid)),
            urls, post["caption"], cfg["instagram"]["api_version"],
        )
        return {"state": "published", "id": media_id}
    if platform == "tiktok":
        mode = cfg["tiktok"]["mode"]
        publish_id = tiktok.publish_photos(
            _tiktok_access(pid), urls, post.get("tiktok_title") or post["caption_raw"][:80],
            post["caption"], mode=mode, auto_add_music=cfg["tiktok"].get("auto_add_music", True),
        )
        return {"state": "published" if mode == "direct" else "sent_to_inbox", "id": publish_id}
    raise ValueError(f"Okänd plattform {platform}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--now", help="ISO-tid för test")
    args = ap.parse_args(argv)

    cfg = load_config()
    tz = ZoneInfo(cfg["timezone"])
    now = datetime.fromisoformat(args.now) if args.now else datetime.now(tz)

    n_ok = n_fail = 0
    for post in post_queue.load_all():
        changed = False
        for platform in post.get("platforms", []):
            if not post_queue.is_due(post, now, platform):
                continue
            status = post.setdefault("status", {}).setdefault(platform, {})
            late_h = (now - datetime.fromisoformat(post["scheduled_at"])).total_seconds() / 3600
            if late_h > MAX_LATE_HOURS:
                status.update({"state": "skipped", "reason": f"missat med {late_h:.0f} h"})
                changed = True
                continue
            urls = _urls(cfg, post)
            if not _media_live(urls):
                print(f"{post['persona']}/{post['id']}: bilderna är inte publika än, försöker igen senare")
                continue
            try:
                result = publish_one(post, platform, cfg)
                status.update(result, published_at=now.isoformat())
                n_ok += 1
                print(f"✓ {post['persona']}/{post['id']} → {platform} ({result['state']})")
            except Exception as e:
                traceback.print_exc()
                status["attempts"] = status.get("attempts", 0) + 1
                status["last_error"] = str(e)[:500]
                n_fail += 1
                print(f"✗ {post['persona']}/{post['id']} → {platform}: {e}")
            changed = True
        if changed:
            post_queue.save(post_queue.strip_internal(post))

    print(f"Publicering klar: {n_ok} lyckade, {n_fail} misslyckade.")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
