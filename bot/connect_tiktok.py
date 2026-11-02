"""Byter en TikTok-inloggningskod mot en refresh token och sparar den som hemlighet.

Körs av arbetsflödet 'Koppla TikTok-konto':  python -m bot.connect_tiktok <persona> <kod>
"""
from __future__ import annotations

import sys
import urllib.parse

from . import tiktok
from .config import get_persona, load_config, persona_secret_name, secret
from .secrets_store import update_secret


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if len(argv) != 2:
        print("Användning: python -m bot.connect_tiktok <persona> <kod>")
        return 1
    persona = get_persona(argv[0])
    code = urllib.parse.unquote(argv[1].strip())
    redirect = load_config()["public_base_url"].rstrip("/") + "/callback.html"
    data = tiktok.exchange_code(secret("TIKTOK_CLIENT_KEY"), secret("TIKTOK_CLIENT_SECRET"), code, redirect)
    name = persona_secret_name("TIKTOK_REFRESH", persona.id)
    if not update_secret(name, data["refresh_token"]):
        return 1
    print(f"TikTok kopplat för {persona.display_name} (sparat som {name}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
