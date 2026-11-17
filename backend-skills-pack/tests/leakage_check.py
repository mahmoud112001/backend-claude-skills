"""Leakage check: grep one fixture's design folder for the other fixture's words.

  leakage_check.py <design folder>
Words come from fixture A: the brief title (00-project-brief.md:1), the profile's
stack fields (project-profile.md:32-41) and the strategic contexts table.
Prints file:line:word for each hit (whole word, case-insensitive). Exit 1 on any hit.
Standard library only, read-only.
"""
import re
import sys
from pathlib import Path

DOMAIN_WORDS = [
    "Shelfmark", "library", "Circulation", "Catalogue", "Fines", "Fine",
    "Membership", "Member", "Loan", "Loans", "Renewal", "Hold shelf",
    "holds queue", "ISBN", "Book", "Books", "Borrower", "check in",
]
STACK_WORDS = [
    "TypeScript", "NestJS", "PostgreSQL", "Postgres", "REST", "Mermaid",
    "modular monolith",
]


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    root = Path(sys.argv[1])
    pattern = re.compile(
        r"\b(" + "|".join(re.escape(w) for w in DOMAIN_WORDS + STACK_WORDS) + r")\b",
        re.IGNORECASE,
    )
    hits = 0
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for number, line in enumerate(text.splitlines(), start=1):
            for match in pattern.finditer(line):
                hits += 1
                rel = path.relative_to(root).as_posix()
                print(f"{rel}:{number}: {match.group(0)!r}: {line.strip()[:140]}")
    print(f"hits: {hits}")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
