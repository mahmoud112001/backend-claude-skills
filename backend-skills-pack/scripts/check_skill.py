"""Check skills against _work/CONVENTIONS.md (the measurable parts).

Usage: python -I scripts/check_skill.py [SKILL_DIR ...]   (default: every folder in skills/)
Checks: name == folder; description <= 45 words; body <= 150 lines; references/ one level,
each <= 200 lines; no README in the skill folder; model is an alias and a "Model:" reason
line exists; scripts import only the standard library and no network modules.
Exit 1 if any check fails. Standard library only.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import skillmeta as sm  # noqa: E402

MAX_DESC_WORDS, MAX_BODY, MAX_REF = 45, 150, 200
ALIASES = {"haiku", "sonnet", "opus", "fable", "inherit"}
NETWORK = {"socket", "http", "urllib.request", "requests", "httpx", "ftplib", "smtplib", "aiohttp"}


def script_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    mods = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            mods.add(node.module)
    return mods


def check(skill: Path) -> list[tuple[str, bool, str]]:
    text = (skill / "SKILL.md").read_text(encoding="utf-8")
    fm_text, body = sm.split_frontmatter(text)
    fm = sm.parse_frontmatter(fm_text)
    words = len(fm.get("description", "").split())
    body_lines = len(body.strip("\n").splitlines())
    res = [
        ("name == folder", fm.get("name") == skill.name, fm.get("name", "-")),
        (f"description <= {MAX_DESC_WORDS} words", 0 < words <= MAX_DESC_WORDS, f"{words} words"),
        (f"body <= {MAX_BODY} lines", body_lines <= MAX_BODY, f"{body_lines} lines"),
        ("model is an alias", fm.get("model") in ALIASES, fm.get("model", "-")),
        ("'Model:' reason line", any(ln.startswith("Model:") for ln in body.splitlines()), ""),
        ("no README", not any(skill.glob("README*")), ""),
    ]
    refs = skill / "references"
    if refs.is_dir():
        nested = [p for p in refs.rglob("*") if p.is_dir()]
        long = [f"{p.name}:{len(p.read_text(encoding='utf-8').splitlines())}" for p in refs.glob("*.md")
                if len(p.read_text(encoding="utf-8").splitlines()) > MAX_REF]
        res.append(("references one level, <= 200 lines", not nested and not long, ", ".join(long)))
    for script in sorted((skill / "scripts").glob("*.py")) if (skill / "scripts").is_dir() else []:
        mods = script_imports(script)
        local = {p.stem for p in script.parent.glob("*.py")}
        bad = sorted(m for m in mods if m.split(".")[0] not in sys.stdlib_module_names and m.split(".")[0] not in local)
        net = sorted(m for m in mods if m in NETWORK or m.split(".")[0] in NETWORK)
        res.append((f"{script.name}: stdlib only, no network", not bad and not net, ", ".join(bad + net)))
    return res


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    dirs = [Path(a) for a in args] or sorted(p for p in (sm.PACK / "skills").iterdir() if (p / "SKILL.md").is_file())
    failed = 0
    for d in dirs:
        results = check(d)
        bad = [r for r in results if not r[1]]
        failed += bool(bad)
        summary = "; ".join(f"{n}: {v}" for n, ok, v in results if v and n.startswith(("desc", "body")))
        print(f"{'PASS' if not bad else 'FAIL'} {d.name}  ({summary})")
        for name, _, detail in bad:
            print(f"   x {name} {detail}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
