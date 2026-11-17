"""Genericity check for the pack's skills and agents (S4).

  python3 -I tests/genericity-check.py [--allow tests/genericity-allow.tsv]
Scans <pack>/skills and <pack>/agents (skipping any examples/ or tests/ folder) for:
  project   names of the owner's own projects
  domain    domain words from the owner's own docs
  path      absolute paths (drive letters, /home/, /Users/)
  user      the owner's usernames
Prints file:line [category] match for every hit. A hit listed in the allow file
(path<TAB>line<TAB>match<TAB>reason) is printed as ALLOWED with its reason.
Exit 1 if any hit is not allowed. Standard library only, read-only, no network.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

PACK = Path(__file__).resolve().parent.parent
SCAN_DIRS = ("skills", "agents")
SKIP_PARTS = {"examples", "tests", "__pycache__"}
TEXT_SUFFIXES = {".md", ".py", ".txt", ".json", ".yaml", ".yml", ".sh", ".ps1", ".tsv", ".html", ""}

TERMS: list[tuple[str, re.Pattern[str]]] = [
    ("project", re.compile(r"i-?fikra|\bfikra\b|node-playground", re.I)),
    ("domain", re.compile(
        r"\b(Orders?|Billing|Enrollments?|Subscriptions?|Offers?|LiveSessions?|Marketplace|Wallets?)\b")),
    ("path", re.compile(r"\b[A-Za-z]:[\\/][^\s`'\")]*|/home/[^\s`'\")]*|/Users/[^\s`'\")]*")),
    ("user", re.compile(r"mahmoud\w*|\bawad\b|Users[\\/]HP\b", re.I)),
]


def load_allow(path: Path | None) -> dict[tuple[str, int, str], str]:
    if path is None or not path.exists():
        return {}
    allowed = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        rel, number, match, reason = line.split("\t", 3)
        allowed[(rel, int(number), match)] = reason
    return allowed


def iter_files(root: Path):
    for path in sorted(root.rglob("*")):
        rel_parts = path.relative_to(PACK).parts
        if path.is_file() and path.suffix in TEXT_SUFFIXES and not SKIP_PARTS & set(rel_parts):
            yield path


def scan() -> list[tuple[str, int, str, str]]:
    hits = []
    for name in SCAN_DIRS:
        for path in iter_files(PACK / name):
            rel = path.relative_to(PACK).as_posix()
            text = path.read_text(encoding="utf-8", errors="replace")
            for number, line in enumerate(text.splitlines(), start=1):
                for category, pattern in TERMS:
                    for match in pattern.finditer(line):
                        hits.append((rel, number, category, match.group(0)))
    return hits


def main(argv: list[str]) -> int:
    allow_path = None
    if len(argv) == 2 and argv[0] == "--allow":
        allow_path = PACK / argv[1]
    elif argv:
        print(__doc__)
        return 2
    allowed = load_allow(allow_path)
    unexplained = 0
    hits = scan()
    for rel, number, category, match in hits:
        reason = allowed.get((rel, number, match))
        if reason:
            print(f"ALLOWED {rel}:{number} [{category}] {match!r}: {reason}")
        else:
            unexplained += 1
            print(f"HIT     {rel}:{number} [{category}] {match!r}")
    print(f"total hits: {len(hits)}, allowed: {len(hits) - unexplained}, unexplained: {unexplained}")
    return 1 if unexplained else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
