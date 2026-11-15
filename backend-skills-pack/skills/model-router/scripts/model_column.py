"""Print the README model column: one row per skill (SKILL.md) and agent (agents/*.md).

Usage: python -I model_column.py ROOT [ROOT ...] [--strict]
Reads frontmatter `name` and `model`, and the reason from the first body line that
starts with "Model:". Flags a missing model, a missing reason, a model that is not an
alias, and a version number in the model. --strict exits 1 when any row is flagged.
Standard library only. No network.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

ALIASES = {"haiku", "sonnet", "opus", "fable", "inherit", "opusplan", "sonnet[1m]", "opus[1m]"}
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "evals"}
KEY_RE = re.compile(r"^([A-Za-z0-9_-]+)\s*:\s*(.*)$")
WHY_RE = re.compile(r"^\s*Model:\s*(.+)$", re.MULTILINE)


def split_frontmatter(text: str) -> tuple[dict[str, str], str]:
    text = text.lstrip("﻿")
    if not text.startswith("---"):
        return {}, text
    lines = text.splitlines()
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            fm = {}
            for line in lines[1:i]:
                m = KEY_RE.match(line)
                if m:
                    fm[m.group(1)] = m.group(2).strip().strip("\"'")
            return fm, "\n".join(lines[i + 1:])
    return {}, text


def candidates(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        here = Path(dirpath)
        if "SKILL.md" in filenames:
            yield "skill", here / "SKILL.md"
        if here.name == "agents":
            for f in sorted(filenames):
                if f.endswith(".md"):
                    yield "agent", here / f


def row(kind: str, path: Path) -> tuple[list[str], list[str]]:
    fm, body = split_frontmatter(path.read_text(encoding="utf-8", errors="replace"))
    name = fm.get("name") or (path.parent.name if kind == "skill" else path.stem)
    model = fm.get("model", "")
    m = WHY_RE.search(body)
    why = m.group(1).strip() if m else ""
    flags = []
    if not model:
        flags.append("MISSING model")
    elif re.search(r"\d", model.replace("[1m]", "")):
        flags.append("VERSION in model")
    elif model not in ALIASES:
        flags.append("NOT an alias")
    if not why:
        flags.append("MISSING why")
    return [name, kind, model or "-", why or "-", ", ".join(flags) or "ok"], flags


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("roots", nargs="+")
    ap.add_argument("--strict", action="store_true")
    a = ap.parse_args(argv)
    rows, flagged = [], 0
    for root in a.roots:
        if not Path(root).is_dir():
            print(f"not a directory: {root}", file=sys.stderr)
            return 2
        for kind, path in candidates(Path(root)):
            r, flags = row(kind, path)
            rows.append(r)
            flagged += bool(flags)
    print("| Name | Kind | Model | Why | Check |")
    print("|---|---|---|---|---|")
    for r in sorted(rows):
        print("| " + " | ".join(c.replace("|", "\\|") for c in r) + " |")
    print(f"\n{len(rows)} rows, {flagged} flagged")
    return 1 if a.strict and flagged else 0


if __name__ == "__main__":
    sys.exit(main())
