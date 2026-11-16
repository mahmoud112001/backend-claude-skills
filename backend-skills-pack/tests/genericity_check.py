"""Genericity check: no project-specific terms in skills/ or agents/ (test d).

Usage: python3 -I tests/genericity_check.py [DIR ...]   (default: <pack>/skills <pack>/agents)
Terms: tests/genericity-terms.txt (category | regex, case-insensitive). examples/ is never scanned.
Prints every hit as file:line [category] match, then a per-directory summary. Exit 1 on any hit.
Standard library only.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

PACK = Path(__file__).resolve().parent.parent
TERMS = Path(__file__).resolve().parent / "genericity-terms.txt"
TEXT = {".md", ".py", ".txt", ".json", ".yaml", ".yml", ".sh", ""}


def load_terms() -> list[tuple[str, re.Pattern]]:
    out = []
    for line in TERMS.read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.startswith("#"):
            cat, rx = (s.strip() for s in line.split("|", 1))
            out.append((cat, re.compile(rx, re.I)))
    return out


def scan(root: Path, terms) -> list[str]:
    hits = []
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.suffix not in TEXT or "examples" in p.relative_to(PACK).parts:
            continue
        for n, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            for cat, rx in terms:
                for m in rx.finditer(line):
                    hits.append(f"{p.relative_to(PACK).as_posix()}:{n} [{cat}] {m.group(0)!r}")
    return hits


def main(argv: list[str]) -> int:
    roots = [Path(a).resolve() for a in argv] or [PACK / "skills", PACK / "agents"]
    terms = load_terms()
    total = 0
    for root in roots:
        hits = scan(root, terms)
        total += len(hits)
        print("\n".join(hits))
        print(f"== {root.relative_to(PACK).as_posix()}: {len(hits)} hits")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
