"""Grep every file under each TARGET (a skill, a plugin, a repo, or a whole skills root)
for risky patterns, plus SKILL.md frontmatter risks (hooks, broad allowed-tools,
missing disable-model-invocation next to side-effect words).

Usage: python -I scan.py TARGET [TARGET ...] [--hits hits.csv] [--summary summary.csv]
Without --hits, hits are printed grouped by owner (the nearest folder holding SKILL.md,
or <plugin> for files outside any skill). Also prints a sha256 tree hash per target, which
pins a target that is not a git checkout.
A hit is not a verdict: every hit needs human review. Standard library only. No network.
Reads files as text; never imports or executes them. (Moved here from
backend-skills-pack/scripts/scan.py in session 2. This is the only copy.)
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv"}
MAX_BYTES = 2_000_000
SNIPPET = 160

PATTERNS: dict[str, list[tuple[str, str]]] = {
    "exec": [
        ("bang-injection", r"!`[^`\n]+`"),
        ("eval", r"\beval\s*\("),
        ("exec", r"\bexec(Sync|File)?\s*\("),
        ("subprocess", r"\bsubprocess\.|\bos\.system\(|\bchild_process\b|\bspawn\s*\("),
        ("base64", r"base64\s+(-d|--decode)|b64decode|\batob\s*\(|Buffer\.from\([^)]*base64"),
        ("blob", r"[A-Za-z0-9+/]{160,}={0,2}"),
    ],
    "network": [
        ("curl/wget", r"\b(curl|wget|Invoke-WebRequest|iwr)\b"),
        ("fetch/http-lib", r"\bfetch\s*\(|\brequests\.(get|post|put)|urllib\.request|\bhttpx\.|axios"),
        ("netcat/ssh", r"\bnc\s+-|\bnetcat\b|\bssh\s+\S+@|\bscp\s"),
        ("git-push", r"\bgit\s+push\b"),
        ("gh-write", r"\bgh\s+(api|pr\s+comment|pr\s+create|issue\s+create|release)\b"),
    ],
    "secrets": [
        ("cred-paths", r"~/\.ssh|~/\.aws|\.ssh/id_|id_rsa|\.netrc|keychain|credential(s)?\.json"),
        ("dotenv", r"(^|[\s/'\"])\.env(\.|\b)"),
        ("token-keyword", r"\b(api[_-]?key|secret[_-]?key|access[_-]?token|auth[_-]?token|GITHUB_TOKEN|ANTHROPIC_API_KEY)\b"),
        ("history/transcripts", r"_history\b|history\.jsonl|\.claude/projects|transcript"),
    ],
    "permissions": [
        ("dangerous-flag", r"--dangerously|bypassPermissions|skip-permissions"),
        ("chmod/sudo", r"\bchmod\b|\bsudo\b"),
        ("rm-rf", r"\brm\s+-(rf|fr)\b|Remove-Item[^\n]*-Recurse[^\n]*-Force|shutil\.rmtree"),
    ],
    "hooks": [
        ("hook-event", r"\b(SessionStart|SessionEnd|PreToolUse|PostToolUse|UserPromptSubmit|Stop|SubagentStop|PreCompact|Notification)\b\"?\s*[:\]]"),
        ("telemetry", r"\b(telemetry|analytics|posthog|segment\.io|mixpanel|sentry)\b"),
    ],
    "injection": [
        ("ignore-rules", r"ignore\s+(all\s+|any\s+)?(previous|prior|above|other)\s+(instructions|rules)"),
        ("hide-from-user", r"(do\s+not|don'?t|never)\s+(tell|inform|mention\s+(this\s+)?to|show)\s+the\s+user|without\s+(telling|informing|asking)\s+the\s+user"),
        ("skip-review", r"skip\s+(the\s+)?(review|verification|tests|confirmation)|no\s+need\s+to\s+(ask|confirm)"),
        ("exfil", r"exfiltrat|send\s+(the\s+)?(data|contents|secrets|files)\s+to"),
    ],
}
COMPILED = {c: [(n, re.compile(p, re.IGNORECASE if c in ("injection", "secrets") else 0))
                for n, p in ps] for c, ps in PATTERNS.items()}

KEY_RE = re.compile(r"^([A-Za-z0-9_-]+)\s*:\s*(.*)$")
SIDE_EFFECT_RE = re.compile(r"\b(git (push|commit|reset)|rm -rf|delete|deploy|publish|install)\b", re.I)


def split_frontmatter(text: str) -> tuple[str, str]:
    text = text.lstrip("﻿")
    if not text.startswith("---"):
        return "", text
    lines = text.splitlines()
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "\n".join(lines[1:i]), "\n".join(lines[i + 1:])
    return "", text


def parse_frontmatter(fm: str) -> dict[str, str]:
    """Top-level keys only; a key with an indented block gets the block joined by spaces."""
    out: dict[str, str] = {}
    key = None
    for line in fm.splitlines():
        m = KEY_RE.match(line)
        if m:
            key = m.group(1)
            out[key] = m.group(2).strip().strip("\"'")
        elif key and line[:1] in (" ", "\t"):
            out[key] = (out[key] + " " + line.strip()).strip()
    return out


def iter_files(base: Path):
    if base.is_file():
        yield base
        return
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for f in sorted(filenames):
            yield Path(dirpath) / f


def read_text(p: Path) -> str | None:
    try:
        if p.stat().st_size > MAX_BYTES:
            return None
        data = p.read_bytes()
    except OSError:
        return None
    if b"\x00" in data[:4096]:
        return None
    return data.decode("utf-8", errors="replace")


def scan_text(text: str):
    for lineno, line in enumerate(text.splitlines(), 1):
        for cat, pats in COMPILED.items():
            for name, rx in pats:
                if rx.search(line):
                    yield lineno, cat, name, line.strip()[:SNIPPET]


def frontmatter_hits(text: str):
    """Yield (line, category, pattern, snippet) for SKILL.md frontmatter risks."""
    fm_text, body = split_frontmatter(text)
    fm = parse_frontmatter(fm_text)
    tools = fm.get("allowed-tools", "")
    items = [t.strip() for t in re.split(r",(?![^()]*\))|\s(?![^()]*\))", tools) if t.strip()]
    if "Bash" in items:
        yield 1, "permissions", "broad-bash", f"allowed-tools has bare Bash: {tools[:SNIPPET]}"
    for t in items:
        if t in ("Write", "Edit", "MultiEdit"):
            yield 1, "permissions", "broad-write", f"allowed-tools has unscoped {t}: {tools[:SNIPPET]}"
    if "hooks" in fm:
        yield 1, "hooks", "frontmatter-hooks", f"hooks registered when the skill runs, kept for the session: {fm['hooks'][:SNIPPET]}"
    if SIDE_EFFECT_RE.search(body) and fm.get("disable-model-invocation", "").lower() != "true":
        yield 1, "permissions", "auto-invocable-side-effects", "body mentions side effects; disable-model-invocation not true"


def owner_of(path: Path, target: Path) -> str:
    for d in [path.parent, *path.parent.parents]:
        if (d / "SKILL.md").is_file():
            try:
                return d.relative_to(target.parent).as_posix()
            except ValueError:
                return d.name
        if d == target:
            break
    return f"{target.name}:<plugin>"


def tree_hash(base: Path) -> str:
    h = hashlib.sha256()
    for f in iter_files(base):
        try:
            h.update(f.relative_to(base).as_posix().encode() + b"\0" + f.read_bytes())
        except (OSError, ValueError):
            continue
    return h.hexdigest()


NOISE = {"token-keyword", "dotenv", "blob"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("targets", nargs="+")
    ap.add_argument("--hits", help="write all hits to this CSV instead of printing them")
    ap.add_argument("--summary", help="write per-owner counts to this CSV")
    ap.add_argument("--noise", action="store_true", help="also print noise patterns: " + ", ".join(sorted(NOISE)))
    a = ap.parse_args(argv)
    hits, scanned = [], set()
    per_owner: dict[str, Counter] = defaultdict(Counter)
    for t in a.targets:
        target = Path(t).resolve()
        if not target.exists():
            print(f"not found: {target}", file=sys.stderr)
            return 2
        print(f"target: {target}  sha256-tree: {tree_hash(target)}")
        for f in iter_files(target):
            key = f.resolve()
            if key in scanned:
                continue
            scanned.add(key)
            text = read_text(f)
            if text is None:
                continue
            owner = owner_of(f, target)
            found = list(scan_text(text))
            if f.name == "SKILL.md":
                found += list(frontmatter_hits(text))
            for lineno, cat, name, snip in found:
                hits.append([owner, t, f.as_posix(), lineno, cat, name, snip])
                per_owner[owner][cat] += 1
    header = ["owner", "source", "path", "line", "category", "pattern", "snippet"]
    if a.hits:
        with open(a.hits, "w", newline="", encoding="utf-8") as fh:
            csv.writer(fh).writerows([header, *hits])
    else:
        shown = [h for h in hits if a.noise or h[5] not in NOISE]
        for h in shown:
            print(f"{h[2]}:{h[3]}  [{h[4]}/{h[5]}]  {h[6]}")
        print(f"({len(hits) - len(shown)} noise hits hidden; --noise shows them)")
    if a.summary:
        cats = [*PATTERNS, "permissions", "hooks"]
        cats = list(dict.fromkeys(cats))
        with open(a.summary, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["owner", *cats, "total"])
            for owner in sorted(per_owner):
                c = per_owner[owner]
                w.writerow([owner, *[c[k] for k in cats], sum(c.values())])
    print(f"files scanned: {len(scanned)}  owners: {len(per_owner)}  hits: {len(hits)}")
    print("by category:", dict(Counter(h[4] for h in hits)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
