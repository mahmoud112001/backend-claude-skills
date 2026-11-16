"""Arrange a design folder: move artifacts into phase folders, fix links, index, verify.

Usage (python3 -I, standard library only, no network):
  organize.py plan   <out>              print the moves, change nothing
  organize.py apply  <out> --vcs git|none
        move each artifact (git mv when tracked and --vcs git, else a plain move), then
        rewrite every relative markdown link under <out>; writes <out>/.organize-manifest.json
  organize.py readme <out>              write <out>/README.md: index + reading order (keeps an
                                        existing '## Summary' section and per-file summaries)
  organize.py check  <out>              links resolve, nothing lost, README lists every artifact
Exit 1 on any failure. Writes only inside <out>. Runs only `git ls-files` and `git mv`.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

LAYOUT = [(r"^00-project-brief", "brief"), (r"^01-", "strategic"), (r"^02-", "tactical"),
          (r"^0[34]-", "data"), (r"^05-", "diagrams"), (r"^06-", "api"), (r"^07-", "review")]
ROOT_FILES = {"project-profile.md", "00-state.md", "README.md"}
LINK = re.compile(r"(\[[^\]]*\]\()([^)\s]+)(\))")
MANIFEST = ".organize-manifest.json"


def target_dir(name: str) -> str | None:
    if name in ROOT_FILES or name.startswith("."):
        return None
    return next((d for pat, d in LAYOUT if re.match(pat, name)), None)


def artifacts(out: Path) -> list[Path]:
    return sorted(p for p in out.rglob("*") if p.is_file() and not any(
        s.startswith(".") for s in p.relative_to(out).parts))


def plan(out: Path) -> dict[Path, Path]:
    moves = {}
    for p in artifacts(out):
        d = target_dir(p.name)
        if d and p.parent != out / d:
            moves[p] = out / d / p.name
    return moves


def fingerprint(p: Path) -> str:
    if p.suffix != ".md":
        return hashlib.sha256(p.read_bytes()).hexdigest()
    text = p.read_text(encoding="utf-8").replace("\r\n", "\n")
    return hashlib.sha256(LINK.sub(lambda m: m.group(1) + m.group(3), text).encode("utf-8")).hexdigest()


def tracked(p: Path) -> bool:
    r = subprocess.run(["git", "ls-files", "--error-unmatch", p.name], cwd=p.parent, capture_output=True)
    return r.returncode == 0


def is_local(target: str) -> bool:
    return not re.match(r"^([a-z][a-z0-9+.-]*:|#|/)", target, re.I)


def rewrite_links(out: Path, old_of: dict[Path, Path], new_of: dict[Path, Path]) -> int:
    """old_of maps new path -> old path, new_of maps old path -> new path, for moved files."""
    changed = 0
    for p in artifacts(out):
        if p.suffix != ".md":
            continue
        old_dir = old_of.get(p, p).parent

        def fix(m: re.Match) -> str:
            target, frag = m.group(2), ""
            if not is_local(target):
                return m.group(0)
            if "#" in target:
                target, frag = target.split("#", 1)
                frag = "#" + frag
            old_abs = Path(os.path.normpath(old_dir / target))
            new_abs = new_of.get(old_abs, old_abs)
            return m.group(1) + Path(os.path.relpath(new_abs, p.parent)).as_posix() + frag + m.group(3)

        text = p.read_text(encoding="utf-8")
        new = LINK.sub(fix, text)
        if new != text:
            p.write_text(new, encoding="utf-8")
            changed += 1
    return changed


def apply(out: Path, vcs: str) -> int:
    moves = plan(out)
    manifest = {s.relative_to(out).as_posix(): {"new": d.relative_to(out).as_posix(), "sha256": fingerprint(s)}
                for s, d in moves.items()}
    for src, dst in moves.items():
        dst.parent.mkdir(parents=True, exist_ok=True)
        how = "plain move"
        if vcs == "git" and tracked(src):
            r = subprocess.run(["git", "mv", str(src), str(dst)], cwd=out, capture_output=True, text=True)
            if r.returncode != 0:
                print(f"git mv failed for {src.name}: {r.stderr.strip()}")
                return 1
            how = "git mv"
        else:
            shutil.move(str(src), str(dst))
            how += " (untracked)" if vcs == "git" else ""
        print(f"{how}: {src.relative_to(out).as_posix()} -> {dst.relative_to(out).as_posix()}")
    changed = rewrite_links(out, {d: s for s, d in moves.items()}, dict(moves))
    (out / MANIFEST).write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print(f"{len(moves)} moved, links rewritten in {changed} files")
    return 0


def title(p: Path) -> str:
    if p.suffix != ".md":
        return p.suffix[1:] + " contract"
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return p.stem


def readme(out: Path) -> int:
    old = (out / "README.md").read_text(encoding="utf-8") if (out / "README.md").is_file() else ""
    summary = re.search(r"## Summary\n(.*?)(?=\n## |\Z)", old, re.S)
    notes = dict(re.findall(r"^\| \d+ \| \[[^\]]*\]\(([^)]*)\) \| .*? \| (.*?) \|$", old, re.M))
    docs = [p for p in artifacts(out) if p.name != "README.md"]
    order = sorted(docs, key=lambda p: (p.name != "project-profile.md", p.name != "00-state.md", p.name))
    lines = ["# Backend design", "", "## Summary", "",
             summary.group(1).strip() if summary else "<one paragraph: what was designed, for whom, status>", "",
             "## Reading order", "", "| # | File | Title | What it gives you |", "|---|---|---|---|"]
    for i, p in enumerate(order, 1):
        rel = p.relative_to(out).as_posix()
        lines.append(f"| {i} | [{p.name}]({rel}) | {title(p)} | {notes.get(rel, '<one line>')} |")
    (out / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"README.md lists {len(order)} files")
    return 0


def check(out: Path) -> int:
    bad = []
    for p in artifacts(out):
        if p.suffix != ".md":
            continue
        for m in LINK.finditer(p.read_text(encoding="utf-8")):
            t = m.group(2).split("#", 1)[0]
            if t and is_local(t) and not (p.parent / t).exists():
                bad.append(f"broken link {p.relative_to(out).as_posix()} -> {m.group(2)}")
    mf = out / MANIFEST
    for old, rec in (json.loads(mf.read_text(encoding="utf-8")).items() if mf.is_file() else []):
        new = out / rec["new"]
        if not new.is_file():
            bad.append(f"lost: {old} (expected at {rec['new']})")
        elif fingerprint(new) != rec["sha256"]:
            bad.append(f"content changed beyond links: {rec['new']}")
    bad += [f"not in its final folder: {p.relative_to(out).as_posix()}" for p in plan(out)]
    index = (out / "README.md").read_text(encoding="utf-8") if (out / "README.md").is_file() else ""
    for p in artifacts(out):
        rel = p.relative_to(out).as_posix()
        if p.name != "README.md" and f"]({rel})" not in index:
            bad.append(f"README does not list {rel}")
    if "<one line>" in index or "<one paragraph" in index:
        bad.append("README still has placeholder summaries")
    print("\n".join(bad) if bad else "OK: links resolve, nothing lost, README complete")
    return 1 if bad else 0


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[0] not in {"plan", "apply", "readme", "check"}:
        print(__doc__)
        return 2
    out = Path(argv[1]).resolve()
    if argv[0] == "plan":
        for s, d in plan(out).items():
            print(f"{s.relative_to(out).as_posix()} -> {d.relative_to(out).as_posix()}")
        return 0
    if argv[0] == "apply":
        return apply(out, argv[argv.index("--vcs") + 1] if "--vcs" in argv else "none")
    return readme(out) if argv[0] == "readme" else check(out)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
