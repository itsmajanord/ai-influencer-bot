"""Skapa och välj referensansikte för en persona.

  python -m bot.reference create lina --count 6   # skapar personas/lina/candidates/1..6.jpg
  python -m bot.reference pick lina 3             # gör kandidat 3 till referensansiktet
"""
from __future__ import annotations

import argparse
import shutil
import sys

from .config import get_persona, load_config
from .images import generate_reference_candidates


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("create")
    c.add_argument("persona")
    c.add_argument("--count", type=int, default=6)
    p = sub.add_parser("pick")
    p.add_argument("persona")
    p.add_argument("number", type=int)
    args = ap.parse_args(argv)

    persona = get_persona(args.persona)
    cand_dir = persona.dir / "candidates"

    if args.cmd == "create":
        if cand_dir.exists():
            shutil.rmtree(cand_dir)
        paths = generate_reference_candidates(persona, cand_dir, args.count, load_config())
        print(f"Skapade {len(paths)} kandidater i {cand_dir}")
    else:
        src = cand_dir / f"{args.number}.jpg"
        if not src.exists():
            print(f"Hittar inte {src}", file=sys.stderr)
            return 1
        shutil.copy(src, persona.reference_image)
        shutil.rmtree(cand_dir)
        print(f"{persona.display_name} har nu kandidat {args.number} som referensansikte.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
