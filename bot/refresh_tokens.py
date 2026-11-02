"""Förnyar Instagram-tokens (gäller 60 dagar) så de aldrig går ut. Körs varje vecka."""
from __future__ import annotations

import sys

from . import instagram
from .config import dry_run, load_personas, persona_secret_name, secret
from .secrets_store import update_secret


def main() -> int:
    failures = 0
    for p in load_personas():
        if "instagram" not in p.platforms:
            continue
        name = persona_secret_name("IG_TOKEN", p.id)
        token = secret(name, required=False)
        if not token:
            print(f"[{p.id}] ingen Instagram-token ännu, hoppar över")
            continue
        if dry_run():
            print(f"[{p.id}] torrkörning – skulle förnya {name}")
            continue
        try:
            new_token, expires = instagram.refresh_token(token)
            update_secret(name, new_token)
            print(f"[{p.id}] Instagram-token förnyad ({expires // 86400} dagar kvar)")
        except Exception as e:
            failures += 1
            print(f"[{p.id}] kunde inte förnya Instagram-token: {e}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
