"""Sparar förnyade tokens tillbaka som GitHub-hemligheter (kräver GH_PAT med rätt behörighet)."""
from __future__ import annotations

import os
import subprocess

from .config import dry_run, secret


def update_secret(name: str, value: str) -> bool:
    if dry_run():
        print(f"[torrkörning] skulle uppdatera hemligheten {name}")
        return True
    pat = secret("GH_PAT", required=False)
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not pat or not repo:
        print(f"VARNING: kan inte spara {name} (GH_PAT eller GITHUB_REPOSITORY saknas)")
        return False
    env = {**os.environ, "GH_TOKEN": pat}
    result = subprocess.run(
        ["gh", "secret", "set", name, "--repo", repo, "--body", value],
        env=env, capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"VARNING: kunde inte spara {name}: {result.stderr.strip()}")
        return False
    return True
