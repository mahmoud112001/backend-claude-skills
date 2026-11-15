"""Fallback unused-symbol finder for repos without a dead-code tool.

Usage: python -I find_unused.py ROOT [--all]
For each definition (py, js/ts, cs, java, kt, go) it counts whole-word mentions of the
name in EVERY text file of the repo, outside its own definition line, split into code,
string literal, and non-code (docs, config, SQL) mentions. It also prints protection hints:
decorators, exports, protected paths, and names matching a dynamic-lookup fragment.
By default only rows with zero code mentions are shown. A row is a CANDIDATE, not a verdict.
Standard library only. No network. Never imports the scanned code.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

SKIP_DIRS = {".git", "node_modules", "vendor", "dist", "build", "__pycache__", ".venv", "venv",
             "bin", "obj", "target", "coverage", ".next", ".claude"}
CODE_EXT = {".py", ".js", ".ts", ".tsx", ".jsx", ".mjs", ".cjs", ".cs", ".java", ".kt", ".go"}
DEF_RE = {
    ".py": re.compile(r"^(\s*)(?:async\s+)?(?:def|class)\s+(\w+)"),
    ".js": re.compile(r"^(\s*)(?:export\s+)?(?:default\s+)?(?:async\s+)?(?:function\*?|class|const|let)\s+(\w+)"),
    ".cs": re.compile(r"^(\s*)(?:\[.*\]\s*)?(?:public|private|protected|internal|static|\s)+[\w<>\[\],?]+\s+(\w+)\s*\("),
    ".go": re.compile(r"^()func\s+(?:\([^)]*\)\s*)?(\w+)"),
}
for e in (".ts", ".tsx", ".jsx", ".mjs", ".cjs"):
    DEF_RE[e] = DEF_RE[".js"]
DEF_RE[".java"] = DEF_RE[".kt"] = DEF_RE[".cs"]
PROTECTED_PATHS = re.compile(r"(^|/)(migrations?|alembic|generated|gen|vendor|third_party|__generated__)(/|$)|\.g\.cs$|_pb2\.py$")
DYNAMIC_RE = re.compile(r"getattr\(|globals\(\)|locals\(\)|importlib|__import__|import\(\s*[^'\"]|require\(\s*[^'\")]"
                        r"|Activator\.CreateInstance|GetType\(|Class\.forName|reflect\.|\[\s*\w+\s*\]\s*\(")
STRING_RE = re.compile(r"(?<![fF])(['\"])(?:\\.|(?!\1).)*\1")  # f-strings count as code
ANY_STRING_RE = re.compile(r"(['\"])(?:\\.|(?!\1).)*\1")
TEST_PATH = re.compile(r"(^|/)(tests?|__tests__|spec)(/|$)|(_test|\.test|\.spec|Tests?)\.\w+$")
KEEP_NAMES = {"main", "__init__", "setUp", "tearDown", "Main", "init"}


def text_files(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for f in filenames:
            p = Path(dirpath) / f
            try:
                data = p.read_bytes()
            except OSError:
                continue
            if b"\x00" not in data[:4096] and len(data) < 2_000_000:
                yield p, data.decode("utf-8", errors="replace").splitlines()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--all", action="store_true", help="show every definition, not only zero-code-ref ones")
    a = ap.parse_args(argv)
    root = Path(a.root).resolve()
    files = list(text_files(root))
    defs, dynamic_frags, dynamic_sites = [], set(), []
    for path, lines in files:
        rx = DEF_RE.get(path.suffix)
        rel = path.relative_to(root).as_posix()
        for n, line in enumerate(lines, 1):
            if path.suffix in CODE_EXT and DYNAMIC_RE.search(line):
                dynamic_sites.append(f"{rel}:{n}")
                for s in ANY_STRING_RE.finditer(line):
                    dynamic_frags.update(f for f in re.split(r"\{[^}]*\}|%s|\W", s.group(0)[1:-1]) if len(f) >= 4)
            m = rx.match(line) if rx and not TEST_PATH.search(rel) else None
            if m and m.group(2) not in KEEP_NAMES and not m.group(2).startswith("test"):
                prev = lines[n - 2].strip() if n > 1 else ""
                defs.append((m.group(2), rel, n, len(m.group(1)), prev.startswith(("@", "["))))
    counts = defaultdict(lambda: [0, 0, 0, 0])  # prod code, string, noncode, test code
    names = {d[0] for d in defs}
    word = re.compile(r"\b(" + "|".join(sorted(map(re.escape, names), key=len, reverse=True)) + r")\b") if names else None
    def_lines = {(d[1], d[2]) for d in defs}
    for path, lines in files if word else []:
        rel = path.relative_to(root).as_posix()
        is_code = path.suffix in CODE_EXT
        is_test = bool(TEST_PATH.search(rel))
        for n, line in enumerate(lines, 1):
            if (rel, n) in def_lines:
                continue
            spans = [s.span() for s in STRING_RE.finditer(line)] if is_code else []
            for m in word.finditer(line):
                c = counts[m.group(1)]
                if not is_code:
                    c[2] += 1
                elif any(a <= m.start() < b for a, b in spans):
                    c[1] += 1
                else:
                    c[3 if is_test else 0] += 1
    print("name | where | prod code refs | test refs | string refs | doc/config refs | hints")
    shown = 0
    for name, rel, n, indent, decorated in sorted(defs, key=lambda d: (d[1], d[2])):
        code, strs, noncode, tests = counts[name]
        if code and not a.all:
            continue
        hints = []
        if decorated:
            hints.append("decorated/attributed")
        if PROTECTED_PATHS.search(rel):
            hints.append("protected path")
        if indent:
            hints.append("member (check overrides/interfaces)")
        if any(f in name for f in dynamic_frags):
            hints.append("matches dynamic-lookup fragment")
        if not name.startswith("_") and rel.endswith(("__init__.py", "index.ts", "index.js")):
            hints.append("package entry export")
        print(f"{name} | {rel}:{n} | {code} | {tests} | {strs} | {noncode} | {', '.join(hints) or '-'}")
        shown += 1
    print(f"\n{shown} candidates of {len(defs)} definitions")
    print("dynamic lookup sites (names built at runtime; check before deleting):",
          ", ".join(dynamic_sites[:30]) or "none")
    return 0


if __name__ == "__main__":
    sys.exit(main())
