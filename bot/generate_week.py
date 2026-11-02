"""Genererar nästa veckas inlägg för alla aktiva personas.

Användning:  python -m bot.generate_week [--persona lina] [--week-start 2026-11-09] [--pr-body pr_body.md]
"""
from __future__ import annotations

import argparse
import os
import sys
import traceback
from datetime import date, datetime
from zoneinfo import ZoneInfo

from . import content, images, post_queue
from .config import load_config, load_personas
from .schedule import next_week_start, week_slots


SV_DAYS = ["Mån", "Tis", "Ons", "Tor", "Fre", "Lör", "Sön"]


def _preview_url(rel_path: str) -> str:
    repo = os.environ.get("GITHUB_REPOSITORY")
    branch = os.environ.get("PREVIEW_BRANCH", "main")
    if not repo:
        return rel_path
    return f"https://github.com/{repo}/blob/{branch}/{rel_path}?raw=true"


def generate_for_persona(persona, week_start: date, cfg: dict) -> list[dict]:
    slots = week_slots(persona.schedule, persona.posts_per_week, week_start, cfg["timezone"])
    todo = [s for s in slots if not post_queue.post_path(persona.id, s.strftime("%Y-%m-%d-%H%M")).exists()]
    if not todo:
        print(f"[{persona.id}] veckan finns redan, hoppar över")
        return []

    ideas = content.plan_week(persona, todo, post_queue.recent_captions(persona.id), cfg)
    created = []
    for slot, idea in zip(todo, ideas):
        post_id = slot.strftime("%Y-%m-%d-%H%M")
        shots = [idea["scene"]] + list(idea.get("extra_shots", []))
        files = []
        for n, scene in enumerate(shots, start=1):
            dest = post_queue.media_dir(persona.id, post_id) / f"{n}.jpg"
            try:
                images.generate_post_image(persona, scene, dest, cfg)
                files.append(dest.name)
            except Exception as e:  # en misslyckad karusellbild ska inte fälla hela inlägget
                if n == 1:
                    raise
                print(f"[{persona.id}] extrabild {n} misslyckades: {e}")
        post = {
            "id": post_id,
            "persona": persona.id,
            "scheduled_at": slot.isoformat(),
            "platforms": persona.platforms,
            "images": files,
            "scenes": shots[: len(files)],
            "caption_raw": idea["caption"],
            "caption": content.build_caption(idea, cfg),
            "tiktok_title": idea.get("tiktok_title", "")[:89],
            "status": {},
        }
        post_queue.save(post)
        created.append(post)
        print(f"[{persona.id}] skapade {post_id} ({len(files)} bild(er))")
    return created


def pr_body(created: dict[str, list[dict]], errors: dict[str, str], personas) -> str:
    names = {p.id: p.display_name for p in personas}
    lines = [
        "## Veckans inlägg att godkänna",
        "",
        "**Godkänn:** tryck *Merge*. Bara inlägg som finns på `main` publiceras.",
        "**Ta bort ett inlägg:** öppna *Files changed* och radera inläggets json-fil i `queue/` (eller be mig ändra), sedan Merge.",
        "**Ändra en caption:** redigera json-filens `caption` direkt i PR:en.",
        "",
    ]
    for pid, posts in created.items():
        lines.append(f"### {names.get(pid, pid)}")
        for post in posts:
            dt = datetime.fromisoformat(post["scheduled_at"])
            when = f"{SV_DAYS[dt.weekday()]} {dt.strftime('%d/%m %H:%M')}"
            lines.append(f"**{when}** – `queue/{pid}/{post['id']}.json`")
            imgs = " ".join(
                f'<img src="{_preview_url(f"docs/media/{pid}/{post["id"]}/{f}")}" width="180">' for f in post["images"]
            )
            lines.append(imgs)
            lines.append("")
            lines.append("> " + post["caption"].replace("\n", "\n> "))
            lines.append("")
    if errors:
        lines.append("### ⚠️ Fel")
        for pid, err in errors.items():
            lines.append(f"- **{names.get(pid, pid)}**: {err}")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--persona")
    ap.add_argument("--week-start", help="YYYY-MM-DD (måndag). Standard: nästa måndag.")
    ap.add_argument("--pr-body", default="pr_body.md")
    args = ap.parse_args(argv)

    cfg = load_config()
    personas = [p for p in load_personas() if not args.persona or p.id == args.persona]
    today = datetime.now(ZoneInfo(cfg["timezone"])).date()
    week_start = date.fromisoformat(args.week_start) if args.week_start else next_week_start(today)

    created, errors = {}, {}
    for persona in personas:
        try:
            posts = generate_for_persona(persona, week_start, cfg)
            if posts:
                created[persona.id] = posts
        except Exception as e:
            traceback.print_exc()
            errors[persona.id] = str(e)

    with open(args.pr_body, "w", encoding="utf-8") as f:
        f.write(pr_body(created, errors, personas))

    total = sum(len(v) for v in created.values())
    print(f"Klart: {total} inlägg skapade, {len(errors)} fel. Vecka från {week_start}.")
    return 1 if errors and not created else 0


if __name__ == "__main__":
    sys.exit(main())
