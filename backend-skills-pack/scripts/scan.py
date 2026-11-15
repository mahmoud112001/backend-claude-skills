"""Grep every file of every skill (and plugin-level hooks/manifests) for risky patterns.

Usage: python -I scripts/scan.py [--hits _work/scan_hits.csv] [--summary _work/scan_summary.csv] [ROOT ...]
A hit is not a verdict: every hit needs human review. Standard library only. No network.
Reads files as text; never imports or executes them.
"""
from __future__ import annotations

import argparse
import csv
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import skillmeta as sm  # noqa: E402

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

ALLOWED_TOOLS_RE = re.compile(r"^allowed-tools\s*:\s*(.*)$", re.MULTILINE)
PLUGIN_EXTRA = ("hooks", "agents", "commands", "scripts", "bin")
PLUGIN_FILES = (".mcp.json", "plugin.json", "hooks.json", "package.json", "settings.json")


def iter_files(base: Path):
    if base.is_file():
        yield base
        return
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d not in sm.SKIP_DIRS]
        for f in filenames:
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


def allowed_tools_hits(skill_md: Path, text: str):
    fm, _ = sm.split_frontmatter(text)
    tools = sm.parse_frontmatter(fm).get("allowed-tools", "")
    if not tools:
        return
    items = [t.strip() for t in re.split(r",(?![^()]*\))|\s(?![^()]*\))", tools) if t.strip()]
    if "Bash" in items:
        yield "broad-bash", f"allowed-tools has bare Bash: {tools[:SNIPPET]}"
    for t in items:
        if t in ("Write", "Edit", "MultiEdit"):
            yield "broad-write", f"allowed-tools has unscoped {t}: {tools[:SNIPPET]}"


def targets(skill_files):
    """Yield (owner_label, source, path_to_scan). Skill folders plus plugin-level extras."""
    plugin_roots = {}
    for skill in skill_files:
        src = sm.classify(skill)
        label = f"{sm.group_of(skill, src)}:{skill.parent.name}"
        yield label, src, skill.parent
        stop = sm.QUARANTINE if src == "quarantine" else None
        root = sm.plugin_root(skill.parent, stop)
        if root is not None and root != skill.parent:
            plugin_roots[root] = (sm.group_of(skill, src), src)
    for q in sm.QUARANTINE.iterdir() if sm.QUARANTINE.is_dir() else []:
        if q.is_dir():
            plugin_roots.setdefault(q.resolve(), (q.name, "quarantine"))
    for root, (group, src) in plugin_roots.items():
        for extra in PLUGIN_EXTRA:
            if (root / extra).is_dir():
                yield f"{group}:<plugin>/{extra}", src, root / extra
        for f in PLUGIN_FILES:
            for cand in (root / f, root / ".claude-plugin" / f):
                if cand.is_file():
                    yield f"{group}:<plugin>/{f}", src, cand


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hits", default=str(sm.PACK / "_work" / "scan_hits.csv"))
    ap.add_argument("--summary", default=str(sm.PACK / "_work" / "scan_summary.csv"))
    ap.add_argument("roots", nargs="*")
    a = ap.parse_args(argv)
    roots = [Path(r) for r in a.roots] or sm.DEFAULT_ROOTS
    skills = list(sm.find_skill_files(roots))
    hits, scanned = [], set()
    per_owner: dict[str, Counter] = defaultdict(Counter)
    owner_src = {}
    for owner, src, base in targets(skills):
        owner_src[owner] = src
        per_owner[owner]  # ensure row exists
        for f in iter_files(base):
            key = f.resolve()
            if key in scanned:
                continue
            scanned.add(key)
            text = read_text(f)
            if text is None:
                continue
            for lineno, cat, name, snip in scan_text(text):
                hits.append([owner, src, str(f), lineno, cat, name, snip])
                per_owner[owner][cat] += 1
            if f.name == "SKILL.md":
                for name, snip in allowed_tools_hits(f, text):
                    hits.append([owner, src, str(f), 1, "permissions", name, snip])
                    per_owner[owner]["permissions"] += 1
    with open(a.hits, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["owner", "source", "path", "line", "category", "pattern", "snippet"])
        w.writerows(hits)
    cats = list(PATTERNS)
    with open(a.summary, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["owner", "source", *cats, "total"])
        for owner in sorted(per_owner):
            c = per_owner[owner]
            w.writerow([owner, owner_src[owner], *[c[k] for k in cats], sum(c.values())])
    tot = Counter(h[4] for h in hits)
    print(f"files scanned: {len(scanned)}  owners: {len(per_owner)}  hits: {len(hits)}")
    print("by category:", dict(tot))
    print("owners with hits:", sum(1 for c in per_owner.values() if c))
    return 0


if __name__ == "__main__":
    sys.exit(main())
