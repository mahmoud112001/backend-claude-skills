"""No-loss proof for phase 8 (standard library only).

  noloss.py snapshot <out> <snapshot.json>   record every file: name, words, headings
  noloss.py compare  <out> <snapshot.json>   compare now vs snapshot; check relative links
Files are matched by base name, because phase 8 moves them into folders.
Exit 1 if a file, a word or a heading was lost, or a relative link does not resolve.
"""
import json
import re
import sys
from pathlib import Path

LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
HEADING = re.compile(r"^#{1,6} .+", re.M)
NEW_FILES_ALLOWED = {"README.md", ".organize-manifest.json"}


def scan(out: Path) -> dict:
    files = {}
    for p in sorted(out.rglob("*")):
        if not p.is_file():
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        if p.name in files:
            raise SystemExit(f"duplicate base name: {p.name}")
        files[p.name] = {
            "path": p.relative_to(out).as_posix(),
            "words": len(text.split()),
            "headings": HEADING.findall(text) if p.suffix == ".md" else [],
        }
    return files


def broken_links(out: Path) -> list:
    bad = []
    for p in sorted(out.rglob("*.md")):
        for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            for target in LINK.findall(line):
                if re.match(r"^[a-z]+:", target) or target.startswith("#"):
                    continue
                rel = target.split("#", 1)[0]
                if rel and not (p.parent / rel).exists():
                    bad.append(f"{p.relative_to(out).as_posix()}:{n} -> {target}")
    return bad


def compare(out: Path, snap_path: Path) -> int:
    before = json.loads(snap_path.read_text(encoding="utf-8"))
    after = scan(out)
    problems = []
    print("| File | Before path | After path | Words before | Words after | Headings |")
    print("|---|---|---|---|---|---|")
    for name, b in before.items():
        a = after.get(name)
        if a is None:
            problems.append(f"missing file: {name}")
            continue
        lost = [h for h in b["headings"] if h not in a["headings"]]
        if lost:
            problems.append(f"{name}: headings lost {lost}")
        if a["words"] < b["words"]:
            problems.append(f"{name}: words {b['words']} -> {a['words']}")
        print(f"| {name} | {b['path']} | {a['path']} | {b['words']} | {a['words']} | {len(b['headings'])} -> {len(a['headings'])} |")
    for name in sorted(set(after) - set(before)):
        if name not in NEW_FILES_ALLOWED:
            problems.append(f"unexpected new file: {name}")
        print(f"| {name} (new) | - | {after[name]['path']} | 0 | {after[name]['words']} | {len(after[name]['headings'])} |")
    bad = broken_links(out)
    problems += [f"broken link: {b}" for b in bad]
    print(f"\nFiles before {len(before)}, after {len(after)}. Relative links broken: {len(bad)}.")
    print("RESULT: " + ("OK" if not problems else "FAIL"))
    for pr in problems:
        print(f"- {pr}")
    return 1 if problems else 0


def main(argv: list) -> int:
    if len(argv) != 4 or argv[1] not in ("snapshot", "compare"):
        print(__doc__)
        return 2
    out, snap = Path(argv[2]), Path(argv[3])
    if argv[1] == "snapshot":
        files = scan(out)
        snap.write_text(json.dumps(files, indent=1), encoding="utf-8")
        print(f"snapshot: {len(files)} files, broken links now: {len(broken_links(out))}")
        return 0
    return compare(out, snap)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
