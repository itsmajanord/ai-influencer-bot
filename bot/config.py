"""Laddar config.yaml, persona-filer och hemligheter."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
PERSONAS_DIR = ROOT / "personas"
QUEUE_DIR = ROOT / "queue"          # inläggsbeskrivningar (json)
MEDIA_DIR = ROOT / "docs" / "media"  # bilder, publiceras via GitHub Pages


def dry_run() -> bool:
    """DRY_RUN=1 -> inga riktiga API-anrop, platshållarbilder och låtsas-publicering."""
    return os.environ.get("DRY_RUN", "").lower() in ("1", "true", "yes")


def load_config() -> dict:
    with open(ROOT / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


@dataclass
class Persona:
    id: str
    display_name: str
    niche: str
    appearance: str
    personality: str
    visual_style: str
    scene_ideas: list[str]
    schedule: list[str]
    posts_per_week: int
    platforms: list[str]
    language: str = "sv"
    active: bool = True
    brand_friendly_topics: list[str] = field(default_factory=list)
    images_per_post: list[int] = field(default_factory=lambda: [1, 3])

    @property
    def dir(self) -> Path:
        return PERSONAS_DIR / self.id

    @property
    def reference_image(self) -> Path:
        return self.dir / "reference.jpg"


def load_personas(only_active: bool = True) -> list[Persona]:
    personas = []
    for path in sorted(PERSONAS_DIR.glob("*/persona.yaml")):
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        p = Persona(**data)
        if p.id != path.parent.name:
            raise ValueError(f"id '{p.id}' matchar inte mappnamnet {path.parent.name}")
        if only_active and not p.active:
            continue
        personas.append(p)
    return personas


def get_persona(persona_id: str) -> Persona:
    for p in load_personas(only_active=False):
        if p.id == persona_id:
            return p
    raise KeyError(f"Ingen persona med id '{persona_id}'")


def _all_secrets() -> dict:
    raw = os.environ.get("ALL_SECRETS")
    if raw:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
    return {}


def secret(name: str, required: bool = True) -> str | None:
    """Hämtar en hemlighet från miljövariabel eller från ALL_SECRETS (GitHub Actions)."""
    value = os.environ.get(name) or _all_secrets().get(name)
    if required and not value:
        raise RuntimeError(f"Saknar hemligheten {name}. Lägg till den under Settings → Secrets → Actions.")
    return value


def persona_secret_name(prefix: str, persona_id: str) -> str:
    return f"{prefix}_{persona_id.upper()}"
