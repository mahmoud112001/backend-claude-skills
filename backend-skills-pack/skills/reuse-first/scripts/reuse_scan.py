"""List what already exists before writing code: matching definitions in the repo,
and the dependencies the repo already declares.

Usage: python -I reuse_scan.py ROOT KEYWORD [KEYWORD ...] [--max N]
Standard library only. No network. Reads files as text; never imports them.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tomllib
from pathlib import Path

SKIP_DIRS = {".git", "node_modules", "vendor", "dist", "build", "__pycache__", ".venv",
             "venv", "bin", "obj", "target", ".next", "coverage", ".claude"}
DEF_PATTERNS = {
    ".py": [r"^\s*(?:async\s+)?(def|class)\s+(\w+)"],
    ".js": [r"\b(function|class)\s+(\w+)", r"\b(const|let)\s+(\w+)\s*=\s*(?:async\s*)?\("],
    ".cs": [r"\b(class|record|interface)\s+(\w+)", r"\b(public|internal|static)\s+[\w<>\[\],?]+\s+(\w+)\s*\("],
    ".java": [r"\b(class|record|interface)\s+(\w+)", r"\b(public|static)\s+[\w<>\[\],]+\s+(\w+)\s*\("],
    ".go": [r"^(func)\s+(?:\([^)]*\)\s*)?(\w+)", r"^(type)\s+(\w+)"],
    ".rs": [r"\b(fn|struct|trait)\s+(\w+)"],
}
for ext in (".ts", ".tsx", ".jsx", ".mjs", ".cjs"):
    DEF_PATTERNS[ext] = DEF_PATTERNS[".js"]
DEF_PATTERNS[".kt"] = [r"\b(fun|class|object)\s+(\w+)"]
COMPILED = {e: [re.compile(p) for p in ps] for e, ps in DEF_PATTERNS.items()}
LOCKFILES = ("package-lock.json", "pnpm-lock.yaml", "yarn.lock", "poetry.lock", "uv.lock",
             "Pipfile.lock", "go.sum", "Cargo.lock", "packages.lock.json")


def words(name: str) -> set[str]:
    parts = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", name).replace("_", " ").lower().split()
    return {*parts, name.lower()}


def walk(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for f in filenames:
            yield Path(dirpath) / f


def find_defs(root: Path, keywords: list[str], limit: int) -> list[str]:
    kws = [k.lower() for k in keywords]
    out = []
    for path in walk(root):
        pats = COMPILED.get(path.suffix)
        if not pats:
            continue
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for n, line in enumerate(lines, 1):
            for rx in pats:
                m = rx.search(line)
                if not m:
                    continue
                name = m.group(m.lastindex)
                if any(k in w for k in kws for w in words(name)):
                    out.append(f"{path.relative_to(root).as_posix()}:{n}  {m.group(1)} {name}")
                break
            if len(out) >= limit:
                return out
    return out


def deps_from(path: Path) -> list[str]:
    name, text = path.name, path.read_text(encoding="utf-8", errors="replace")
    if name == "package.json":
        data = json.loads(text)
        return [f"{k} {v} ({sec})" for sec in ("dependencies", "devDependencies", "peerDependencies")
                for k, v in data.get(sec, {}).items()]
    if name.startswith("requirements") and name.endswith(".txt"):
        return [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.startswith(("#", "-"))]
    if name == "pyproject.toml":
        data = tomllib.loads(text)
        proj = data.get("project", {})
        out = list(proj.get("dependencies", []))
        for grp, items in proj.get("optional-dependencies", {}).items():
            out += [f"{i} (extra {grp})" for i in items]
        for grp, items in data.get("dependency-groups", {}).items():
            out += [f"{i} (group {grp})" for i in items if isinstance(i, str)]
        poetry = data.get("tool", {}).get("poetry", {})
        out += [f"{k} {v}" for k, v in poetry.get("dependencies", {}).items() if k != "python"]
        return out
    if name == "Cargo.toml":
        return [f"{k} {v}" for k, v in tomllib.loads(text).get("dependencies", {}).items()]
    if name == "go.mod":
        return re.findall(r"^\s*(?:require\s+)?([\w./-]+\.[\w./-]+\s+v[\w.+-]+)", text, re.M)
    if path.suffix in (".csproj", ".fsproj") or name == "Directory.Packages.props":
        return [" ".join(p for p in m if p) for m in
                re.findall(r'PackageReference\s+Include="([^"]+)"(?:\s+Version="([^"]+)")?', text)]
    if name == "pom.xml":
        return re.findall(r"<artifactId>([^<]+)</artifactId>", text)[1:]
    return []


def find_deps(root: Path) -> tuple[list[str], list[str]]:
    deps, locks = [], []
    for path in walk(root):
        rel = path.relative_to(root).as_posix()
        if path.name in LOCKFILES:
            locks.append(rel)
            continue
        try:
            items = deps_from(path)
        except (ValueError, OSError) as exc:  # TOMLDecodeError and JSONDecodeError are ValueErrors
            deps.append(f"{rel}: could not parse ({exc.__class__.__name__})")
            continue
        deps.extend(f"{rel}: {item}" for item in items)
    return deps, locks


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("keywords", nargs="+")
    ap.add_argument("--max", type=int, default=60)
    a = ap.parse_args(argv)
    root = Path(a.root).resolve()
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2
    defs = find_defs(root, a.keywords, a.max)
    print(f"## (a) repo definitions matching {a.keywords}: {len(defs)}")
    print("\n".join(defs) or "none")
    deps, locks = find_deps(root)
    print(f"\n## (c) declared dependencies: {len(deps)}")
    print("\n".join(deps) or "none")
    print("\n## lockfiles (transitive deps live here): " + (", ".join(locks) or "none"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
