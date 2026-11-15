"""Fallback duplicate finder for repos without jscpd or similar.

Usage: python -I find_dupes.py ROOT [--min-lines N]
Python: functions whose bodies are identical after renaming arguments and dropping
docstrings (AST compare). This is strong evidence of identical behaviour.
Other languages: identical runs of N normalised lines (default 6). This is textual
evidence only, so check behaviour by reading.
Prints groups with their copy counts. Standard library only. Never imports scanned code.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

SKIP_DIRS = {".git", "node_modules", "vendor", "dist", "build", "__pycache__", ".venv", "venv",
             "bin", "obj", "target", "coverage", "migrations"}
OTHER_EXT = {".js", ".ts", ".tsx", ".jsx", ".cs", ".java", ".kt", ".go", ".rs"}


class _Rename(ast.NodeTransformer):
    def __init__(self, args: list[str]):
        self.map = {a: f"_a{i}" for i, a in enumerate(args)}

    def visit_Name(self, node: ast.Name) -> ast.AST:
        return ast.copy_location(ast.Name(id=self.map.get(node.id, node.id), ctx=node.ctx), node)


def py_key(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> str | None:
    body = fn.body
    if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant) \
            and isinstance(body[0].value.value, str):
        body = body[1:]
    if not body or (len(body) == 1 and isinstance(body[0], (ast.Pass, ast.Return)) and
                    getattr(body[0], "value", None) is None):
        return None
    args = [a.arg for a in fn.args.posonlyargs + fn.args.args + fn.args.kwonlyargs]
    mod = ast.Module(body=[_Rename(args).visit(ast.parse(ast.unparse(s))) for s in body], type_ignores=[])
    return hashlib.sha1(ast.dump(mod).encode()).hexdigest()


def walk(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for f in filenames:
            yield Path(dirpath) / f


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--min-lines", type=int, default=6)
    a = ap.parse_args(argv)
    root = Path(a.root).resolve()
    groups: dict[str, list[str]] = defaultdict(list)
    for path in walk(root):
        rel = path.relative_to(root).as_posix()
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if path.suffix == ".py":
            try:
                tree = ast.parse(text)
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    key = py_key(node)
                    if key:
                        groups["py:" + key].append(f"{rel}:{node.lineno} {node.name}()")
        elif path.suffix in OTHER_EXT:
            lines = [re.sub(r"\s+", " ", ln).strip() for ln in text.splitlines()]
            for i in range(len(lines) - a.min_lines + 1):
                win = lines[i:i + a.min_lines]
                if sum(len(w) > 3 for w in win) < a.min_lines - 1:
                    continue
                groups["tx:" + hashlib.sha1("\n".join(win).encode()).hexdigest()].append(f"{rel}:{i + 1}")
    dupes = [(k, v) for k, v in groups.items() if len({x.split(":")[0] for x in v}) > 1 or len(v) > 1]
    seen_files: set[tuple] = set()
    count = 0
    for key, locs in sorted(dupes, key=lambda kv: -len(kv[1])):
        sig = tuple(sorted(x.split(":")[0] for x in locs))
        if key.startswith("tx:") and sig in seen_files:
            continue  # overlapping windows of the same block
        seen_files.add(sig)
        kind = "identical function body (AST)" if key.startswith("py:") else f"{a.min_lines}+ identical lines (text)"
        print(f"{len(locs)} copies | {kind}")
        for loc in locs:
            print(f"   {loc}")
        count += 1
    print(f"\n{count} duplicate groups")
    return 0


if __name__ == "__main__":
    sys.exit(main())
