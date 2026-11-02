"""Publicering via officiella TikTok Content Posting API (fotoinlägg)."""
from __future__ import annotations

import requests

API = "https://open.tiktokapis.com/v2"


class TikTokError(RuntimeError):
    pass


def _check(r: requests.Response) -> dict:
    try:
        data = r.json()
    except ValueError:
        raise TikTokError(f"TikTok {r.status_code}: {r.text[:300]}")
    err = data.get("error") or {}
    if r.status_code >= 400 or (err.get("code") not in (None, "ok")):
        raise TikTokError(f"TikTok {r.status_code}: {err.get('code')} – {err.get('message')}")
    return data


def refresh(client_key: str, client_secret: str, refresh_token: str) -> dict:
    """Byter refresh token mot ny access token. Returnerar dict med access_token och refresh_token."""
    r = requests.post(
        f"{API}/oauth/token/",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "client_key": client_key,
            "client_secret": client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
        timeout=30,
    )
    data = r.json()
    if "access_token" not in data:
        raise TikTokError(f"Kunde inte förnya TikTok-token: {data}")
    return data


def exchange_code(client_key: str, client_secret: str, code: str, redirect_uri: str) -> dict:
    r = requests.post(
        f"{API}/oauth/token/",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "client_key": client_key,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        },
        timeout=30,
    )
    data = r.json()
    if "access_token" not in data:
        raise TikTokError(f"Kodbytet misslyckades: {data}")
    return data


def _privacy_level(access_token: str) -> str:
    r = requests.post(
        f"{API}/post/publish/creator_info/query/",
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json; charset=UTF-8"},
        timeout=30,
    )
    options = _check(r)["data"].get("privacy_level_options", [])
    # Ogranskade appar får bara SELF_ONLY – då blir inlägget privat tills appen är granskad.
    return "PUBLIC_TO_EVERYONE" if "PUBLIC_TO_EVERYONE" in options else (options[0] if options else "SELF_ONLY")


def publish_photos(access_token: str, image_urls: list[str], title: str, description: str,
                   mode: str = "inbox", auto_add_music: bool = True) -> str:
    """mode='direct' publicerar direkt, mode='inbox' skickar till appens inkorg för ett klick. Returnerar publish_id."""
    post_info = {"title": title[:89], "description": description[:4000]}
    if mode == "direct":
        post_info.update({
            "privacy_level": _privacy_level(access_token),
            "disable_comment": False,
            "auto_add_music": auto_add_music,
        })
    body = {
        "post_info": {**post_info, "is_aigc": True},
        "source_info": {"source": "PULL_FROM_URL", "photo_cover_index": 0, "photo_images": image_urls[:35]},
        "post_mode": "DIRECT_POST" if mode == "direct" else "MEDIA_UPLOAD",
        "media_type": "PHOTO",
    }
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json; charset=UTF-8"}
    r = requests.post(f"{API}/post/publish/content/init/", headers=headers, json=body, timeout=60)
    try:
        return _check(r)["data"]["publish_id"]
    except TikTokError as e:
        if "invalid_param" in str(e) and "is_aigc" in str(e):
            # Om fotoendpointen inte tar emot AI-flaggan: AI-märkningen finns ändå i texten.
            body["post_info"].pop("is_aigc")
            r = requests.post(f"{API}/post/publish/content/init/", headers=headers, json=body, timeout=60)
            return _check(r)["data"]["publish_id"]
        raise
