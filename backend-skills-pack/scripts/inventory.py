"""Inventory every SKILL.md and compute the always-loaded baseline.

Usage: python -I scripts/inventory.py [--out _work/inventory.csv] [--baseline _work/baseline.txt] [ROOT ...]
Standard library only. No network. Reads files; never executes them.
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import skillmeta as sm  # noqa: E402

FIELDS = [
    "name", "path", "source", "group", "description", "description_chars",
    "skill_md_lines", "has_scripts", "has_hooks", "has_agents",
    "allowed_tools", "model", "disable_model_invocation", "sha256",
]


def row_for(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    fm_text, _ = sm.split_frontmatter(text)
    fm = sm.parse_frontmatter(fm_text)
    d = path.parent
    source = sm.classify(path)
    desc = " ".join(fm.get("description", "").split())
    has_hooks = "hooks" in fm or (d / "hooks").is_dir() or (d / "hooks.json").is_file()
    return {
        "name": fm.get("name", "") or d.name,
        "path": str(path),
        "source": source,
        "group": sm.group_of(path, source),
        "description": desc,
        "description_chars": len(desc),
        "skill_md_lines": len(text.splitlines()),
        "has_scripts": (d / "scripts").is_dir(),
        "has_hooks": has_hooks,
        "has_agents": (d / "agents").is_dir(),
        "allowed_tools": fm.get("allowed-tools", ""),
        "model": fm.get("model", ""),
        "disable_model_invocation": fm.get("disable-model-invocation", ""),
        "sha256": sm.sha256_file(path),
    }


def baseline_text(rows) -> str:
    def cost(rs):
        chars = sum(len(r["name"]) + int(r["description_chars"]) for r in rs)
        return len(rs), chars, chars // 4

    lines = ["ALWAYS-LOADED BASELINE (name + description chars; tokens ~= chars/4)", ""]
    by_src = Counter(r["source"] for r in rows)
    installed = [r for r in rows if r["source"] != "quarantine"]
    n, c, t = cost(installed)
    lines.append(f"Installed (mine + plugin): {n} skills, {c} chars, ~{t} tokens  <-- number to beat")
    n, c, t = cost(rows)
    lines.append(f"All incl. quarantine:      {n} skills, {c} chars, ~{t} tokens")
    lines.append("")
    lines.append("By source:")
    for src in sorted(by_src):
        n, c, t = cost([r for r in rows if r["source"] == src])
        lines.append(f"  {src:<11} {n:>4} skills {c:>7} chars ~{t:>6} tokens")
    lines.append("")
    lines.append("By group (installed only):")
    groups = Counter(r["group"] for r in installed)
    for g, _ in groups.most_common():
        n, c, t = cost([r for r in installed if r["group"] == g])
        lines.append(f"  {g:<40} {n:>4} skills ~{t:>6} tokens")
    lines.append("")
    lines.append("Caveat: plugins present in a marketplace folder but not enabled are not loaded")
    lines.append("by Claude Code; this baseline counts every SKILL.md found, as requested.")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(sm.PACK / "_work" / "inventory.csv"))
    ap.add_argument("--baseline", default=str(sm.PACK / "_work" / "baseline.txt"))
    ap.add_argument("roots", nargs="*")
    a = ap.parse_args(argv)
    roots = [Path(r) for r in a.roots] or sm.DEFAULT_ROOTS
    rows = []
    for p in sm.find_skill_files(roots):
        try:
            rows.append(row_for(p))
        except OSError as e:
            print(f"WARN cannot read {p}: {e}", file=sys.stderr)
    rows.sort(key=lambda r: (r["source"], r["group"], r["name"]))
    with open(a.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    text = baseline_text(rows)
    Path(a.baseline).write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
