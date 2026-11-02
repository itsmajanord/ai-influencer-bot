"""Bildgenerering via Replicate (Flux). Samma ansikte hålls via en referensbild."""
from __future__ import annotations

import base64
import io
import time
from pathlib import Path

import requests
from PIL import Image, ImageDraw

from .config import Persona, dry_run, secret

API = "https://api.replicate.com/v1"


def _run_model(model: str, inputs: dict, timeout_s: int = 300) -> str:
    """Kör en Replicate-modell och returnerar URL till första utdatan."""
    headers = {
        "Authorization": f"Bearer {secret('REPLICATE_API_TOKEN')}",
        "Content-Type": "application/json",
        "Prefer": "wait=60",
    }
    resp = requests.post(f"{API}/models/{model}/predictions", headers=headers, json={"input": inputs}, timeout=90)
    resp.raise_for_status()
    pred = resp.json()
    deadline = time.time() + timeout_s
    while pred["status"] not in ("succeeded", "failed", "canceled"):
        if time.time() > deadline:
            raise TimeoutError(f"Replicate tog för lång tid ({model})")
        time.sleep(3)
        pred = requests.get(pred["urls"]["get"], headers=headers, timeout=30).json()
    if pred["status"] != "succeeded":
        raise RuntimeError(f"Bildgenerering misslyckades: {pred.get('error')}")
    out = pred["output"]
    return out[0] if isinstance(out, list) else out


def _download_jpg(url: str, dest: Path) -> Path:
    data = requests.get(url, timeout=120).content
    img = Image.open(io.BytesIO(data)).convert("RGB")
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest, "JPEG", quality=92)
    return dest


def _placeholder(dest: Path, text: str, size=(1080, 1350)) -> Path:
    img = Image.new("RGB", size, (220, 214, 205))
    d = ImageDraw.Draw(img)
    y = 80
    for chunk in [text[i:i + 38] for i in range(0, len(text), 38)][:20]:
        d.text((60, y), chunk, fill=(40, 40, 40))
        y += 40
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest, "JPEG", quality=85)
    return dest


def _data_uri(path: Path) -> str:
    return "data:image/jpeg;base64," + base64.b64encode(path.read_bytes()).decode()


def _full_prompt(persona: Persona, scene: str) -> str:
    return (
        f"Keep the exact same woman from the reference image (same face, same hair). "
        f"She is a {persona.appearance.strip()}. "
        f"New photo: {scene}. Style: {persona.visual_style.strip()}. "
        f"Photorealistic, natural anatomy, correct hands, no text, no logos, no watermark."
    )


def generate_post_image(persona: Persona, scene: str, dest: Path, cfg: dict) -> Path:
    if dry_run():
        return _placeholder(dest, f"{persona.display_name}: {scene}")
    if not persona.reference_image.exists():
        raise FileNotFoundError(
            f"{persona.display_name} saknar referensansikte ({persona.reference_image}). "
            "Kör arbetsflödet 'Skapa ansikte' först."
        )
    icfg = cfg["images"]
    url = _run_model(icfg["model"], {
        "prompt": _full_prompt(persona, scene),
        "input_image": _data_uri(persona.reference_image),
        "aspect_ratio": icfg["aspect_ratio"],
        "output_format": icfg["output_format"],
        "safety_tolerance": icfg["safety_tolerance"],
    })
    return _download_jpg(url, dest)


def generate_reference_candidates(persona: Persona, out_dir: Path, count: int, cfg: dict) -> list[Path]:
    """Skapar ansiktskandidater (porträtt) att välja referens från."""
    paths = []
    prompt = (
        f"Natural candid portrait photo of {persona.appearance}. Head and shoulders, looking at camera, "
        f"soft daylight, plain neutral background, realistic skin texture, shot on phone, "
        f"no makeup filter, no text, no watermark."
    )
    for i in range(1, count + 1):
        dest = out_dir / f"{i}.jpg"
        if dry_run():
            paths.append(_placeholder(dest, f"Kandidat {i}: {persona.appearance}"))
            continue
        url = _run_model(cfg["images"]["reference_model"], {
            "prompt": prompt,
            "aspect_ratio": "4:5",
            "output_format": "jpg",
            "raw": True,               # mer naturlig, mindre "AI-blank" look
            "safety_tolerance": 2,
            "seed": 1000 + i,
        })
        paths.append(_download_jpg(url, dest))
    return paths
