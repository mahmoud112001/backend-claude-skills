"""Run architecture checks (import and grep rules) from a JSON spec.

Usage:
  python -I check.py ROOT --spec checks.json [--files F ...] [--diff BASE]
  python -I check.py ROOT --edges [--files ...]    # dump import edges only

Spec: a JSON list of checks, each one of
  {"id": "R3", "kind": "import", "from": "src/*/domain/**", "forbid": "infrastructure|^requests$",
   "severity": "high", "fix": "inject a port"}
  {"id": "R5", "kind": "grep", "files": "migrations/**/*.sql", "pattern": "REFERENCES\\s+orders",
   "severity": "high", "fix": "..."}
"from"/"files" are globs relative to ROOT (** = any depth). "forbid"/"pattern" are regexes,
matched against the imported module name or the line. An optional "unless" regex skips a
matching line. --diff BASE limits files to `git diff --name-only BASE`. Prints one block
per check: PASS/FAIL plus file:line and evidence. Exit 0 always (a report, not a gate).
Standard library only. Never imports scanned code.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path

SKIP_DIRS = {".git", "node_modules", "vendor", "dist", "build", "__pycache__", ".venv", "venv",
             "bin", "obj", "target", ".claude"}
IMPORT_RE = {
    ".py": [re.compile(r"^\s*from\s+([\w.]+)\s+import\s+([\w, ]+)"), re.compile(r"^\s*import\s+([\w.]+)")],
    ".js": [re.compile(r"""\bfrom\s+['"]([^'"]+)['"]"""), re.compile(r"""\b(?:require|import)\(\s*['"]([^'"]+)['"]""")],
    ".cs": [re.compile(r"^\s*using\s+(?:static\s+)?([\w.]+)\s*;")],
    ".java": [re.compile(r"^\s*import\s+(?:static\s+)?([\w.]+)")],
    ".go": [re.compile(r"""^\s*(?:import\s+)?(?:\w+\s+)?"([\w./-]+)"\s*$""")],
}
for e in (".ts", ".tsx", ".jsx", ".mjs", ".cjs"):
    IMPORT_RE[e] = IMPORT_RE[".js"]
IMPORT_RE[".kt"] = IMPORT_RE[".java"]


def glob_re(pattern: str) -> re.Pattern:
    out, i = "", 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out, i = out + "(?:.*/)?", i + 3
        elif pattern.startswith("**", i):
            out, i = out + ".*", i + 2
        elif pattern[i] == "*":
            out, i = out + "[^/]*", i + 1
        elif pattern[i] == "?":
            out, i = out + "[^/]", i + 1
        else:
            out, i = out + re.escape(pattern[i]), i + 1
    return re.compile(out + "$")


def all_files(root: Path) -> list[str]:
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        out += [(Path(dirpath) / f).relative_to(root).as_posix() for f in filenames]
    return sorted(out)


def lines_of(root: Path, rel: str) -> list[str]:
    try:
        return (root / rel).read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []


def imports(root: Path, rel: str):
    pats = IMPORT_RE.get(Path(rel).suffix)
    for n, line in enumerate(lines_of(root, rel) if pats else [], 1):
        for rx in pats:
            m = rx.search(line)
            if m:
                mod = m.group(1)
                yield n, mod, line.strip()
                if rx.groups > 1:  # python "from pkg import a, b": also yield pkg.a, pkg.b
                    for name in m.group(2).split(","):
                        if name.strip():
                            yield n, f"{mod}.{name.strip().split()[0]}", line.strip()
                break


def run_check(root: Path, files: list[str], chk: dict) -> list[str]:
    hits = []
    unless = re.compile(chk["unless"]) if chk.get("unless") else None
    if chk["kind"] == "import":
        src, forbid = glob_re(chk["from"]), re.compile(chk["forbid"])
        for rel in (f for f in files if src.match(f)):
            seen = set()
            for n, mod, line in imports(root, rel):
                if forbid.search(mod) and n not in seen and not (unless and unless.search(line)):
                    seen.add(n)
                    hits.append(f"{rel}:{n}  {line}")
    elif chk["kind"] == "grep":
        src, pat = glob_re(chk["files"]), re.compile(chk["pattern"], re.IGNORECASE if chk.get("ignore_case") else 0)
        for rel in (f for f in files if src.match(f)):
            for n, line in enumerate(lines_of(root, rel), 1):
                if pat.search(line) and not (unless and unless.search(line)):
                    hits.append(f"{rel}:{n}  {line.strip()[:160]}")
    else:
        hits.append(f"unknown kind {chk['kind']!r}: use import or grep, or mark the rule manual")
    return hits


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--spec")
    ap.add_argument("--files", nargs="*")
    ap.add_argument("--diff")
    ap.add_argument("--edges", action="store_true")
    a = ap.parse_args(argv)
    root = Path(a.root).resolve()
    files = all_files(root)
    if a.diff:
        res = subprocess.run(["git", "-C", str(root), "diff", "--name-only", a.diff], capture_output=True, text=True)
        if res.returncode:
            print(f"git diff failed: {res.stderr.strip()}", file=sys.stderr)
            return 2
        changed = set(res.stdout.split())
        files = [f for f in files if f in changed]
    if a.files:
        wanted = [glob_re(g.rstrip("/") + ("/**" if (root / g).is_dir() else "")) for g in a.files]
        files = [f for f in files if any(w.match(f) for w in wanted)]
    print(f"date: {dt.date.today().isoformat()}  files in scope: {len(files)}")
    if a.edges:
        for rel in files:
            for n, mod, _ in imports(root, rel):
                print(f"{rel}:{n} -> {mod}")
        return 0
    if not a.spec:
        print("need --spec or --edges", file=sys.stderr)
        return 2
    checks = json.loads(Path(a.spec).read_text(encoding="utf-8"))
    failed = 0
    for chk in checks:
        hits = run_check(root, files, chk)
        failed += bool(hits)
        status = "FAIL" if hits else "PASS"
        print(f"\n{status} {chk['id']} [{chk.get('severity', '?')}] {chk['kind']}: "
              f"{chk.get('from') or chk.get('files')} / {chk.get('forbid') or chk.get('pattern')}")
        for h in hits:
            print(f"  {h}")
    print(f"\n{len(checks)} checks, {failed} failing")
    return 0


if __name__ == "__main__":
    sys.exit(main())
