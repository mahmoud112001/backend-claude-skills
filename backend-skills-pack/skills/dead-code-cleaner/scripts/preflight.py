"""Preflight for cleanup: today's date, clean git tree, branch name cleanup/<date>.

Usage: python -I preflight.py ROOT [--create-branch]
Prints facts and exits 1 if the tree is dirty or ROOT is not a git repo.
--create-branch switches to cleanup/<date> (or cleanup/<date>-N if taken). It only runs
when the tree is clean. It never commits, stashes or resets. Standard library only.
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import subprocess
import sys
from pathlib import Path

# Untracked build/test caches never count as a dirty tree (and are never deleted).
CACHE_RE = re.compile(r"(^|/)(__pycache__|\.pytest_cache|\.mypy_cache|\.ruff_cache|\.tox|\.cache|"
                      r"coverage|\.coverage|htmlcov|\.next|bin|obj|target)(/|$)|\.pyc$")


def git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)


def free_branch(root: Path, base: str) -> str:
    name, n = base, 1
    while git(root, "rev-parse", "--verify", "--quiet", f"refs/heads/{name}").returncode == 0:
        n += 1
        name = f"{base}-{n}"
    return name


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--create-branch", action="store_true")
    a = ap.parse_args(argv)
    root = Path(a.root).resolve()
    today = dt.date.today().isoformat()
    print(f"date: {today}")
    if git(root, "rev-parse", "--is-inside-work-tree").returncode != 0:
        print("git: NOT a git repository -> apply mode impossible; report mode only")
        return 1
    branch = git(root, "branch", "--show-current").stdout.strip() or "(detached)"
    raw = git(root, "status", "--porcelain").stdout.splitlines()
    caches = [ln for ln in raw if ln.startswith("?? ") and CACHE_RE.search(ln[3:])]
    status = "\n".join(ln for ln in raw if ln not in caches)
    if caches:
        print(f"ignored untracked caches: {len(caches)} (e.g. {caches[0][3:]}); not deleted")
    print(f"branch: {branch}")
    print(f"head: {git(root, 'rev-parse', '--short', 'HEAD').stdout.strip()}")
    if status:
        print("tree: DIRTY -> stop; commit or stash first (the skill must not do it)")
        print("\n".join(f"  {ln}" for ln in status.splitlines()[:20]))
        return 1
    print("tree: clean")
    target = free_branch(root, f"cleanup/{today}")
    print(f"cleanup branch: {target}")
    if a.create_branch:
        res = git(root, "switch", "-c", target)
        if res.returncode != 0:
            print(f"could not create branch: {res.stderr.strip()}")
            return 1
        print(f"switched to {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
