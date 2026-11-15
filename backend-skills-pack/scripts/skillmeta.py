"""Shared helpers: locate SKILL.md files, parse frontmatter, classify source.

Standard library only. No network. Never imports or executes scanned code.
"""
from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path

HOME = Path.home()
PACK = Path(__file__).resolve().parent.parent
QUARANTINE = PACK / "_quarantine"

DEFAULT_ROOTS = [
    HOME / ".claude" / "skills",
    Path.cwd() / ".claude" / "skills",
    HOME / ".claude" / "plugins",
    QUARANTINE,
]

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv"}


def find_skill_files(roots):
    seen = set()
    for root in roots:
        root = Path(root)
        if not root.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            if "SKILL.md" in filenames:
                p = (Path(dirpath) / "SKILL.md").resolve()
                if p not in seen:
                    seen.add(p)
                    yield p


def _is_under(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def classify(path: Path) -> str:
    if _is_under(path, QUARANTINE):
        return "quarantine"
    if _is_under(path, HOME / ".claude" / "plugins"):
        return "plugin"
    return "mine"


def plugin_root(skill_dir: Path, stop: Path | None = None) -> Path | None:
    """Nearest ancestor holding a plugin manifest, or None."""
    for d in [skill_dir, *skill_dir.parents]:
        if stop and d == stop:
            break
        if (d / ".claude-plugin" / "plugin.json").is_file() or (d / "plugin.json").is_file():
            return d
    return None


def read_plugin_name(root: Path) -> str | None:
    for cand in (root / ".claude-plugin" / "plugin.json", root / "plugin.json"):
        if cand.is_file():
            txt = cand.read_text(encoding="utf-8", errors="replace")
            m = re.search(r'"name"\s*:\s*"([^"]+)"', txt)
            if m:
                return m.group(1)
    return None


def group_of(path: Path, source: str) -> str:
    skill_dir = path.parent
    if source == "mine":
        return "synced-account" if "synced" in skill_dir.parts else "user-skills"
    if source == "quarantine":
        rel = skill_dir.resolve().relative_to(QUARANTINE.resolve()).parts
        repo = rel[0]
        for marker in ("plugins", "external_plugins"):
            if marker in rel:
                i = rel.index(marker)
                if i + 1 < len(rel):
                    return f"{repo}/{rel[i + 1]}"
        return repo
    root = plugin_root(skill_dir, HOME / ".claude" / "plugins")
    if root is not None:
        return read_plugin_name(root) or root.name
    return "plugin-unknown"


def split_frontmatter(text: str) -> tuple[str, str]:
    """Return (frontmatter_text, body_text). Empty frontmatter if none."""
    text = text.lstrip("﻿")
    if not text.startswith("---"):
        return "", text
    lines = text.splitlines()
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "\n".join(lines[1:i]), "\n".join(lines[i + 1:])
    return "", text


def _unquote(v: str) -> str:
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        inner = v[1:-1]
        return inner.replace('\\"', '"') if v[0] == '"' else inner.replace("''", "'")
    return v


_KEY_RE = re.compile(r"^([A-Za-z0-9_-]+)\s*:\s*(.*)$")
_BLOCK = ("|", ">", "|-", ">-", "|+", ">+")


def parse_frontmatter(fm: str) -> dict[str, str]:
    """Minimal YAML subset: top-level scalars, quoted strings, block scalars,
    folded continuation lines, and simple lists (joined with ', ')."""
    out: dict[str, str] = {}
    lines = fm.splitlines()
    i = 0
    while i < len(lines):
        m = _KEY_RE.match(lines[i])
        i += 1
        if not m:
            continue
        key, val = m.group(1), m.group(2).rstrip()
        cont = []
        while i < len(lines) and (lines[i][:1] in (" ", "\t") or not lines[i].strip()):
            cont.append(lines[i].strip())
            i += 1
        cont = [c for c in cont if c]
        if val in _BLOCK:
            out[key] = ("\n" if val.startswith("|") else " ").join(cont).strip()
        elif val == "" and cont and all(c.startswith("- ") for c in cont):
            out[key] = ", ".join(_unquote(c[2:]) for c in cont)
        else:
            out[key] = _unquote(" ".join([val, *cont]).strip())
    return out


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
