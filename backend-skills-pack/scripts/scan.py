"""Security gate for the pack: scan every file, fail on REJECT-class hits.

Usage: python -I scripts/scan.py [TARGET ...] [--waivers tests/scan-waivers.tsv]
Default targets: skills agents scripts tests examples README.md (relative to the pack).
The patterns and the walk come from skills/skill-security-audit/scripts/scan.py, the only
scanner implementation; this file adds the gate:
  REJECT-class  patterns that the audit skill calls "unacceptable" (hooks, network, credential
                paths, load-time shell injection, obfuscation, hide/exfil phrasing, bare Bash).
                Each one fails the gate unless a reviewed waiver (path glob + pattern + reason)
                covers it.
  WARN          every other non-noise hit. Listed, never fails.
Exit 1 if any unwaived REJECT-class hit remains. Standard library only. No network.
Reads files as text; never imports or executes them.
"""
from __future__ import annotations

import argparse
import fnmatch
import sys
from collections import Counter
from pathlib import Path

PACK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PACK / "skills" / "skill-security-audit" / "scripts"))
import scan as core  # noqa: E402

DEFAULT_TARGETS = ["skills", "agents", "scripts", "tests", "examples", "README.md"]
REJECT_CLASS = {
    "bang-injection", "base64", "curl/wget", "fetch/http-lib", "netcat/ssh", "git-push", "gh-write",
    "cred-paths", "dangerous-flag", "hook-event", "frontmatter-hooks", "telemetry",
    "ignore-rules", "hide-from-user", "exfil", "broad-bash",
}


def load_waivers(path: Path) -> list[tuple[str, str, str]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines() if path.is_file() else []:
        if line.strip() and not line.startswith("#"):
            glob, pattern, reason = (line.split("\t") + ["", ""])[:3]
            rows.append((glob.strip(), pattern.strip(), reason.strip()))
    return rows


def iter_hits(targets: list[Path], skip: Path):
    for target in targets:
        files = [target] if target.is_file() else core.iter_files(target)
        for f in files:
            if f.resolve() == skip.resolve():
                continue  # the waiver file names the patterns it waives
            text = core.read_text(f)
            if text is None:
                continue
            found = list(core.scan_text(text))
            if f.name == "SKILL.md":
                found += list(core.frontmatter_hits(text))
            rel = f.resolve().relative_to(PACK).as_posix()
            for lineno, cat, name, snip in found:
                yield rel, lineno, cat, name, snip


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("targets", nargs="*")
    ap.add_argument("--waivers", default=str(PACK / "tests" / "scan-waivers.tsv"))
    a = ap.parse_args(argv)
    targets = [Path(t) if Path(t).is_absolute() else PACK / t for t in (a.targets or DEFAULT_TARGETS)]
    missing = [t for t in targets if not t.exists()]
    if missing:
        print("not found: " + ", ".join(map(str, missing)), file=sys.stderr)
        return 2
    waivers = load_waivers(Path(a.waivers))
    rejects, waived, warns, used = [], [], [], set()
    for rel, lineno, cat, name, snip in iter_hits(targets, Path(a.waivers)):
        if name in core.NOISE:
            continue
        hit = f"{rel}:{lineno}  [{cat}/{name}]  {snip}"
        if name not in REJECT_CLASS:
            warns.append((name, hit))
            continue
        match = next((w for w in waivers if fnmatch.fnmatch(rel, w[0]) and w[1] == name), None)
        if match:
            used.add(match)
            waived.append(f"{hit}\n      waiver: {match[2]}")
        else:
            rejects.append(hit)
    print(f"REJECT-class, not waived: {len(rejects)}")
    print("\n".join(f"  {h}" for h in rejects))
    print(f"REJECT-class, waived after review: {len(waived)}")
    print("\n".join(f"  {h}" for h in waived))
    print(f"WARN (review, never fails): {len(warns)}  by pattern: {dict(Counter(n for n, _ in warns))}")
    print("\n".join(f"  {h}" for _, h in sorted(warns)))
    unused = [w for w in waivers if w not in used]
    if unused:
        print("unused waivers (remove them): " + "; ".join(f"{g} {p}" for g, p, _ in unused))
    print("GATE: " + ("FAIL" if rejects else "PASS"))
    return 1 if rejects else 0


if __name__ == "__main__":
    sys.exit(main())
