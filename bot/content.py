"""Tar fram veckans inläggsidéer och captions med Claude."""
from __future__ import annotations

import json
import random
import re
from datetime import datetime

import requests

from .config import Persona, dry_run, secret

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"

LANG_NAMES = {"sv": "svenska", "en": "engelska"}


def _build_prompt(persona: Persona, slots: list[datetime], recent_captions: list[str]) -> str:
    lo, hi = persona.images_per_post
    slot_lines = "\n".join(f"- inlägg {i+1}: {s.strftime('%A %d %B %Y kl %H:%M')}" for i, s in enumerate(slots))
    recent = "\n".join(f"- {c[:140]}" for c in recent_captions[-12:]) or "(inga ännu)"
    return f"""Du planerar Instagram/TikTok-inlägg för en tydligt AI-märkt virtuell influencer.

KARAKTÄR
Namn: {persona.display_name}
Nisch: {persona.niche}
Personlighet och bakgrund: {persona.personality}
Scenidéer att variera och bygga vidare på: {"; ".join(persona.scene_ideas)}
Samarbetsvänliga teman: {"; ".join(persona.brand_friendly_topics)}

VECKANS PUBLICERINGSTIDER
{slot_lines}

SENASTE CAPTIONS (upprepa inte samma idéer)
{recent}

REGLER
- Allt ska vara SFW och passa en bred publik. Personen är vuxen.
- Inga riktiga varumärken, loggor, kända personer eller identifierbara privata personer.
- Ta hänsyn till årstid och veckodag/tid på dygnet för varje inlägg.
- Captions på {LANG_NAMES.get(persona.language, persona.language)} (gärna med ett enstaka svenskt ord som "fika" som charmig detalj), personliga, 1–4 meningar, gärna en fråga till följarna.
- Påstå aldrig att karaktären är en riktig människa. Skriv inte "jag är inte AI" eller liknande.
- Variera format: vissa inlägg 1 bild, vissa karusell ({lo}–{hi} bilder).

SVARA ENBART med en JSON-lista med exakt {len(slots)} objekt i tidsordning, varje objekt:
{{
  "scene": "engelsk bildbeskrivning av första bilden: plats, handling, kläder, ljus, kameravinkel (max 60 ord, nämn inte utseendet på ansiktet)",
  "extra_shots": ["engelska beskrivningar av ev. fler karusellbilder, samma tillfälle och kläder"],
  "caption": "caption utan hashtags",
  "hashtags": ["#exempel", "... 5-10 relevanta hashtags utan AI-taggar"],
  "tiktok_title": "kort titel max 80 tecken"
}}"""


def _parse_json_list(text: str) -> list[dict]:
    match = re.search(r"\[.*\]", text, re.S)
    if not match:
        raise ValueError(f"Kunde inte hitta JSON i svaret: {text[:300]}")
    data = json.loads(match.group(0))
    if not isinstance(data, list):
        raise ValueError("Svaret var inte en lista")
    return data


def _fake_ideas(persona: Persona, slots: list[datetime]) -> list[dict]:
    rng = random.Random(persona.id + slots[0].isoformat())
    ideas = []
    for i, _ in enumerate(slots):
        scene = rng.choice(persona.scene_ideas)
        n_extra = rng.randint(persona.images_per_post[0], persona.images_per_post[1]) - 1
        ideas.append({
            "scene": f"[TORRKÖRNING] {scene}",
            "extra_shots": [f"[TORRKÖRNING] variant {k+2} av: {scene}" for k in range(n_extra)],
            "caption": f"Testinlägg {i+1} för {persona.display_name}: {scene}. Vad gör ni i helgen?",
            "hashtags": ["#test", f"#{persona.id}"],
            "tiktok_title": f"{persona.display_name} – {scene}"[:80],
        })
    return ideas


def plan_week(persona: Persona, slots: list[datetime], recent_captions: list[str], cfg: dict) -> list[dict]:
    if dry_run():
        return _fake_ideas(persona, slots)

    prompt = _build_prompt(persona, slots, recent_captions)
    resp = requests.post(
        ANTHROPIC_URL,
        headers={
            "x-api-key": secret("ANTHROPIC_API_KEY"),
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": cfg["ai_text"]["model"],
            "max_tokens": 4000,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=120,
    )
    resp.raise_for_status()
    text = "".join(b.get("text", "") for b in resp.json()["content"])
    ideas = _parse_json_list(text)
    if len(ideas) < len(slots):
        raise ValueError(f"Fick {len(ideas)} idéer men behövde {len(slots)}")

    lo, hi = persona.images_per_post
    for idea in ideas:
        extra = idea.get("extra_shots") or []
        idea["extra_shots"] = extra[: max(0, hi - 1)]
        idea["hashtags"] = [h if h.startswith("#") else f"#{h}" for h in idea.get("hashtags", [])][:10]
    return ideas[: len(slots)]


def build_caption(idea: dict, cfg: dict) -> str:
    """Caption + obligatorisk AI-märkning + hashtags."""
    disclosure = cfg["disclosure"]
    tags = [t for t in idea.get("hashtags", []) if t.lower() not in {d.lower() for d in disclosure["hashtags"]}]
    all_tags = " ".join(disclosure["hashtags"] + tags)
    return f"{idea['caption'].strip()}\n\n{disclosure['caption_line']}\n\n{all_tags}"
