"""Publicering via officiella Instagram API (Instagram Login, graph.instagram.com)."""
from __future__ import annotations

import time

import requests

HOST = "https://graph.facebook.com"


class InstagramError(RuntimeError):
    pass


def _call(method: str, url: str, token: str, **params) -> dict:
    params["access_token"] = token
    r = requests.request(method, url, params=params, timeout=60)
    data = r.json() if r.content else {}
    if r.status_code >= 400 or "error" in data:
        raise InstagramError(f"Instagram {r.status_code}: {data.get('error', data)}")
    return data


def _wait_ready(container_id: str, token: str, version: str, timeout_s: int = 120) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        data = _call("GET", f"{HOST}/{version}/{container_id}", token, fields="status_code")
        status = data.get("status_code")
        if status == "FINISHED":
            return
        if status in ("ERROR", "EXPIRED"):
            raise InstagramError(f"Container {container_id} fick status {status}")
        time.sleep(4)
    raise InstagramError(f"Container {container_id} blev aldrig klar")


def publish(ig_user_id: str, token: str, image_urls: list[str], caption: str, version: str) -> str:
    """Publicerar en bild eller karusell. Returnerar Instagram-mediets id."""
    base = f"{HOST}/{version}/{ig_user_id}"
    if len(image_urls) == 1:
        container = _call("POST", f"{base}/media", token, image_url=image_urls[0], caption=caption)["id"]
    else:
        children = []
        for url in image_urls[:10]:
            cid = _call("POST", f"{base}/media", token, image_url=url, is_carousel_item="true")["id"]
            children.append(cid)
        for cid in children:
            _wait_ready(cid, token, version)
        container = _call(
            "POST", f"{base}/media", token, media_type="CAROUSEL", children=",".join(children), caption=caption
        )["id"]
    _wait_ready(container, token, version)
    return _call("POST", f"{base}/media_publish", token, creation_id=container)["id"]


def refresh_token(token: str) -> tuple[str, int]:
    """Förlänger en långlivad token (60 dagar). Returnerar (ny_token, sekunder_kvar)."""
    data = _call("GET", f"{HOST}/refresh_access_token", token, grant_type="ig_refresh_token")
    return data["access_token"], int(data.get("expires_in", 0))
