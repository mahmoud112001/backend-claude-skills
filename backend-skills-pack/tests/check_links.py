"""Check every Markdown link in the given files: relative paths must exist, #anchors must match a heading.

Usage: python -I tests/check_links.py [FILE.md ...]   (default: README.md of the pack)
External links (http, https, mailto) are listed but never fetched. Exit 1 on any broken link.
Standard library only. No network.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

PACK = Path(__file__).resolve().parent.parent
LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)\)")
FENCE = re.compile(r"^```.*?^```", re.M | re.S)


def anchors(md: str) -> set[str]:
    """GitHub-style heading slugs: lower case, drop punctuation, spaces to hyphens."""
    out = set()
    for h in re.findall(r"^#{1,6}\s+(.+?)\s*$", FENCE.sub("", md), re.M):
        out.add(re.sub(r"[^\w\- ]", "", h.lower()).replace(" ", "-"))
    return out


def check(path: Path) -> list[str]:
    md = path.read_text(encoding="utf-8")
    bad = []
    for target in LINK.findall(FENCE.sub("", md)):
        if re.match(r"^(https?|mailto):", target):
            print(f"  external (not fetched): {target}")
            continue
        file_part, _, anchor = target.partition("#")
        dest = (path.parent / file_part).resolve() if file_part else path
        if not dest.exists():
            bad.append(f"{path.name}: missing target {target}")
        elif anchor and dest.suffix == ".md" and anchor not in anchors(dest.read_text(encoding="utf-8")):
            bad.append(f"{path.name}: no heading for #{anchor} in {dest.name}")
        else:
            print(f"  ok {target}")
    return bad


def main(argv: list[str]) -> int:
    files = [Path(a) for a in argv] or [PACK / "README.md"]
    bad = [b for f in files for b in check(f)]
    print("\n".join(bad) if bad else "all links OK")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
