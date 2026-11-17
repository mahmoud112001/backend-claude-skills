"""Independent verification of the backend skills pack (checks A to K).

Usage: python -I scripts/verify-pack.py [--install-target DIR]
  --install-target DIR  an existing empty folder OUTSIDE the repo; install.ps1 (or install.sh)
                        is run there in DRY-RUN mode only, so nothing is written.
Prints one line per check: PASS, WARN or FAIL, the check id, and evidence (file:line or counts).
Exit 0 only if there is no FAIL. Standard library only, no network, read-only: it never writes
a file. It runs only these programs: tests/genericity-check.py, scripts/scan.py (both read-only)
and the install script in dry-run mode.
Decisions that need human judgement (scan waivers, genericity hits) are recorded in the
REVIEWED_* tables below with their reason; a hit missing from them is a FAIL.
"""
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

PACK = Path(__file__).resolve().parent.parent
REPO = PACK.parent
ALIASES = {"haiku", "sonnet", "opus", "fable", "inherit"}
MAX_DESC_WORDS, MAX_BODY_LINES, MAX_REF_LINES, MAX_README_LINES = 45, 150, 200, 300
REQUIRED_CUSTOM = ["reuse-first", "model-router", "dead-code-cleaner", "architecture-conformance",
                   "skill-security-audit"]
PHASE_SKILLS = ["project-understanding", "ddd-strategic", "ddd-tactical", "db-design-erd", "design-diagrams",
                "api-endpoints", "design-review-fix", "design-docs-organizer"]
AGENTS = ["project-reader", "strategic-designer", "tactical-designer", "db-designer", "diagram-writer",
          "api-designer", "design-reviewer", "doc-librarian"]
SIX_SOURCES = {"ponytail": r"ponytail", "simplify/code-simplifier": r"simplify|code-simplifier",
               "code-review": r"code-review", "skill-creator": r"skill-creator",
               "superpowers": r"superpowers", "skills (anthropics/skills)": r"anthropics/skills"}
NETWORK_MODULES = {"socket", "http", "urllib", "ftplib", "smtplib", "telnetlib", "xmlrpc", "ssl",
                   "requests", "httpx", "aiohttp", "urllib3", "poplib", "imaplib"}
SEVERE_WAIVER_PATTERNS = {"curl/wget", "fetch/http-lib", "netcat/ssh", "git-push", "gh-write", "telemetry",
                          "hook-event", "frontmatter-hooks", "bang-injection", "cred-paths", "exec-eval"}
# (path, pattern) -> (decision, reason). Read by hand on 2026-11-17 at the cited lines.
REVIEWED_WAIVERS = {
    ("skills/api-endpoints/references/api-styles.md", "bang-injection"):
        ("JUSTIFIED", "GraphQL non-null '!' before a closing backtick; a references file, not preprocessed"),
    ("skills/skill-creator/SKILL.md", "exfil"): ("JUSTIFIED", "prose forbidding malware/exfiltration"),
    ("skills/skill-creator/eval-viewer/viewer.html", "fetch/http-lib"):
        ("FAIL", "real HTTP call (fetch /api/feedback) to the local viewer server; no written approval found"),
    ("skills/skill-creator/eval-viewer/viewer.html", "base64"):
        ("JUSTIFIED", "atob() decodes embedded output files for display; nothing is evaluated, no blob"),
    ("skills/skill-security-audit/SKILL.md", "git-push"):
        ("JUSTIFIED", "example text of a required change in an audit report; the skill runs no push"),
    ("scripts/check_skill.py", "fetch/http-lib"): ("JUSTIFIED", "set of forbidden module names"),
    ("scripts/scan.py", "curl/wget"): ("JUSTIFIED", "pattern name inside the REJECT_CLASS set"),
    ("scripts/scan.py", "netcat/ssh"): ("JUSTIFIED", "pattern name inside the REJECT_CLASS set"),
    ("scripts/scan.py", "telemetry"): ("JUSTIFIED", "pattern name inside the REJECT_CLASS set"),
}
for _p in ("bang-injection", "base64", "curl/wget", "fetch/http-lib", "netcat/ssh", "cred-paths",
           "dangerous-flag", "telemetry", "exfil"):
    REVIEWED_WAIVERS[("skills/skill-security-audit/scripts/scan.py", _p)] = (
        "JUSTIFIED", "the scanner's own regex definition; nothing runs")
# genericity hits judged by reading the line: (path, line, match) -> reason
REVIEWED_GENERICITY = {
    ("skills/backend-design-team/SKILL.md", "44", "Order"): "generic English 'Order matters', not a domain",
}

# Six-source decisions, judged by reading AUDIT.md and SELECTION.md (mentions alone are not decisions).
REVIEWED_SOURCE_DECISIONS = {
    "ponytail": ("PASS", "AUDIT: plugin REJECT, skills SAFE/SAFE-WITH-CHANGES; SELECTION: ponytail-audit ADAPT"),
    "code-review": ("FAIL", "SELECTION 'Code review' row: ponytail-review, 'decision 2 is still open'; AUDIT.md "
                            "has no verdict row for the official code-review plugin"),
    "skill-creator": ("PASS", "AUDIT SAFE-WITH-CHANGES; SELECTION ADOPT"),
    "superpowers": ("PASS", "AUDIT per-skill verdicts + plugin REJECT; SELECTION picks"),
    "skills (anthropics/skills)": ("PASS", "AUDIT 20 verdicts at a pinned SHA; SELECTION skill-creator ADOPT"),
}

RESULTS: list[tuple[str, str, str]] = []


def rec(status: str, cid: str, msg: str) -> None:
    RESULTS.append((status, cid, msg))


def rel(p: Path) -> str:
    try:
        return p.resolve().relative_to(PACK).as_posix()
    except ValueError:
        return p.as_posix()


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def split_fm(text: str) -> tuple[dict, list[str], int]:
    """Return (frontmatter dict, body lines, frontmatter end index)."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, lines, -1
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), -1)
    fm: dict = {}
    key = None
    for line in lines[1:end]:
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if m:
            key, val = m.group(1), m.group(2).strip().strip('"').strip("'")
            fm[key] = val
        elif key and re.match(r"^\s+-\s+", line):
            prev = fm.get(key)
            items = prev if isinstance(prev, list) else ([] if not prev else [prev])
            fm[key] = items + [line.strip()[2:].strip()]
    return fm, lines[end + 1:], end


def text_files(root: Path):
    for p in sorted(root.rglob("*")):
        if p.is_file() and "__pycache__" not in p.parts and p.suffix not in {".pyc", ".png", ".jpg"}:
            yield p


def grep(root: Path, pattern: str, flags: int = 0) -> list[tuple[Path, int, str]]:
    rx = re.compile(pattern, flags)
    hits = []
    for p in text_files(root):
        for i, line in enumerate(read(p).splitlines(), 1):
            if rx.search(line):
                hits.append((p, i, line.strip()))
    return hits


def skill_dirs() -> list[Path]:
    return sorted(p for p in (PACK / "skills").iterdir() if p.is_dir())


def agent_files() -> list[Path]:
    return sorted((PACK / "agents").glob("*.md"))


def manifest() -> dict:
    return json.loads(read(PACK / "MANIFEST.json"))


def cost(name: str, desc: str) -> int:
    return len(name) + len(" ".join(desc.split()))


# ---------------------------------------------------------------- A. structure
def check_a() -> None:
    need = ["README.md", "MANIFEST.json", "AUDIT.md", "SELECTION.md", "TOKEN-REPORT.md",
            "THIRD-PARTY-NOTICES.md", "skills", "agents", "scripts", "tests"]
    missing = [n for n in need if not (PACK / n).exists()]
    rec("FAIL" if missing else "PASS", "A1 structure", f"missing: {missing}" if missing else f"all {len(need)} present")
    gi = "\n".join(read(p) for p in (REPO / ".gitignore", PACK / ".gitignore") if p.is_file())
    lines = [l.strip() for l in gi.splitlines()]
    absent = [e for e in ("_quarantine/", "_work/tmp/", ".claude/") if not any(l.endswith(e) for l in lines)]
    rec("FAIL" if absent else "PASS", "A2 .gitignore", f"absent: {absent}" if absent else
        "has _quarantine/, _work/tmp/, .claude/ (.gitignore at repo root)")
    copies = [p for p in REPO.rglob("scan.py") if ".git" not in p.parts and "_quarantine" not in p.parts]
    hashes = {}
    for p in copies:
        hashes.setdefault(sha256(p)[:12], []).append(p.relative_to(REPO).as_posix())
    if len(hashes) > 1:
        rec("FAIL", "A3 scan.py copies", "; ".join(f"{h}: {', '.join(v)}" for h, v in hashes.items()))
    elif len(copies) > 1:
        rec("WARN", "A3 scan.py copies", f"Low finding: {len(copies)} identical copies {list(hashes.values())[0]}")
    else:
        rec("PASS", "A3 scan.py copies", f"{len(copies)} copy")


# ---------------------------------------------------------------- B. every skill
def check_b() -> None:
    origins = {s["name"]: s.get("origin", "") for s in manifest()["skills"]}
    report = read(PACK / "TOKEN-REPORT.md")
    for d in skill_dirs():
        n, sk = d.name, d / "SKILL.md"
        if not sk.is_file():
            rec("FAIL", f"B1 {n}", "no SKILL.md")
            continue
        fm, body, _ = split_fm(read(sk))
        if fm.get("name") != n:
            rec("FAIL", f"B1 {n}", f"frontmatter name {fm.get('name')!r} != folder")
        bad = [rel(p) for p in d.rglob("*") if re.match(r"(?i)(readme|changelog|install)", p.name)]
        hooks = [rel(p) for p in d.rglob("hooks") if p.is_dir()] + (["frontmatter hooks:"] if "hooks" in fm else [])
        if bad or hooks:
            rec("FAIL", f"B2 {n}", f"docs {bad} hooks {hooks}")
        if fm.get("model") not in ALIASES:
            rec("FAIL", f"B3 {n}", f"model {fm.get('model')!r} is not an alias")
        words = len(fm.get("description", "").split())
        refs = [(rel(p), len(read(p).splitlines())) for p in sorted((d / "references").glob("*"))] \
            if (d / "references").is_dir() else []
        if fm.get("name") == n and not bad and not hooks and fm.get("model") in ALIASES:
            rec("PASS", f"B1-3 {n}", f"SKILL.md, name = folder, model {fm['model']}, no README/CHANGELOG/hooks")
        over = [f"description {words} words" for _ in [0] if words > MAX_DESC_WORDS]
        over += [f"body {len(body)} lines" for _ in [0] if len(body) > MAX_BODY_LINES]
        over += [f"{p} {c} lines" for p, c in refs if c > MAX_REF_LINES]
        origin = origins.get(n, "?")
        if not over:
            rec("PASS", f"B4 budget {n}", f"{origin}: {words} words, body {len(body)} lines, refs max "
                f"{max([c for _, c in refs], default=0)}")
        elif origin == "adopted":
            listed = re.search(rf"^\| {re.escape(n)} \|.*\| {cost(n, fm.get('description', ''))} \|", report, re.M)
            rec("WARN" if listed else "FAIL", f"B4 budget {n}", f"adopted, over budget: {', '.join(over)}; "
                f"TOKEN-REPORT lists real description cost: {'yes' if listed else 'NO'}")
        else:
            rec("FAIL", f"B4 budget {n}", f"{origin}: {', '.join(over)}")
    ver = grep(PACK / "skills", r"(?i)claude-(opus|sonnet|haiku|fable|instant|[0-9])[-_ ]?[0-9]|"
               r"\b(opus|sonnet|haiku|fable)[ -][0-9]+(\.[0-9]+)?\b") + \
        grep(PACK / "agents", r"(?i)\b(opus|sonnet|haiku|fable)[ -][0-9]")
    rec("FAIL" if ver else "PASS", "B5 model versions",
        "; ".join(f"{rel(p)}:{i} {t[:60]}" for p, i, t in ver) if ver else "none in skills/ or agents/")


# ---------------------------------------------------------------- C. required parts
def check_c() -> None:
    have = {d.name for d in skill_dirs()}
    for group, names in (("custom", REQUIRED_CUSTOM), ("orchestrator", ["backend-design-team"]),
                         ("phase", PHASE_SKILLS)):
        miss = [x for x in names if x not in have]
        rec("FAIL" if miss else "PASS", f"C1 {group} skills", f"missing {miss}" if miss else f"{len(names)} present")
    agents = {p.stem for p in agent_files()}
    miss = [a for a in AGENTS if a not in agents]
    rec("FAIL" if miss else "PASS", "C2 agents", f"missing {miss}" if miss else f"8 present ({len(agents)} on disk)")
    for n in ("dead-code-cleaner", "skill-security-audit"):
        fm, _, _ = split_fm(read(PACK / "skills" / n / "SKILL.md"))
        ok = fm.get("disable-model-invocation", "").lower() == "true"
        rec("PASS" if ok else "FAIL", f"C3 {n} manual", f"disable-model-invocation: {fm.get('disable-model-invocation')}")


# ---------------------------------------------------------------- D. safety
def py_imports(p: Path) -> list[tuple[int, str]]:
    try:
        tree = ast.parse(read(p))
    except SyntaxError as exc:
        return [(exc.lineno or 0, "<syntax error>")]
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out += [(node.lineno, a.name) for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            out.append((node.lineno, node.module))
    return out


def py_eval_calls(p: Path) -> list[int]:
    try:
        tree = ast.parse(read(p))
    except SyntaxError:
        return []
    return [n.lineno for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
            and n.func.id in {"eval", "exec", "compile", "__import__"}]


def check_d_scripts() -> None:
    py = [p for root in ("skills", "scripts", "tests", "agents") for p in (PACK / root).rglob("*.py")
          if "__pycache__" not in p.parts]
    nonstd, net = [], []
    for p in py:
        local = {q.stem for q in p.parent.glob("*.py")} | {"scan", "skillmeta"}
        if (p.parent / "__init__.py").is_file():
            local.add(p.parent.name)  # package-relative import such as scripts.utils
        for line, mod in py_imports(p):
            top = mod.split(".")[0]
            if top in NETWORK_MODULES:
                net.append(f"{rel(p)}:{line} {mod}")
            elif top not in sys.stdlib_module_names and top not in local and top != "__future__":
                nonstd.append(f"{rel(p)}:{line} {mod}")
    rec("FAIL" if nonstd else "PASS", "D1 stdlib only", f"{len(py)} .py files; non-stdlib: {nonstd or 'none'}")
    rec("WARN" if net else "PASS", "D2 network imports",
        f"{net} (skill-creator eval viewer: HTTP server on 127.0.0.1, see D8 waiver)" if net else "none")
    claude_p = [f"{rel(p)}:{i}" for root in ("skills", "tests") for p, i, t in grep(PACK / root, r'"claude",\s*"-p"|\["claude"')]
    if claude_p:
        rec("WARN", "D2b nested claude -p", f"spawns billed Claude API runs: {claude_p}")
    ev = [f"{rel(p)}:{i}" for p in py for i in py_eval_calls(p)]
    ev += [f"{rel(p)}:{i}" for root in ("skills", "agents") for p, i, _ in
           grep(PACK / root, r"\beval\s*\(|new Function\s*\(") if p.suffix in {".js", ".html", ".cjs", ".mjs"}]
    rec("FAIL" if ev else "PASS", "D3 eval/exec", ", ".join(ev) if ev else "no eval/exec/compile calls")
    blobs = [f"{rel(p)}:{i}" for root in ("skills", "agents", "scripts") for p, i, _ in
             grep(PACK / root, r"[A-Za-z0-9+/]{120,}={0,2}")]
    rec("FAIL" if blobs else "PASS", "D4 base64 blobs", ", ".join(blobs) if blobs else "none (120+ char base64 runs)")


def check_d_skills() -> None:
    bang_md = [(p, i, t) for root in ("skills", "agents") for p, i, t in grep(PACK / root, r"!`[^`\n]+`")
               if p.suffix == ".md" and p.name != "scan.py"]
    load_time = [f"{rel(p)}:{i}" for p, i, _ in bang_md if p.name == "SKILL.md" or p.parent.name == "agents"]
    other = [f"{rel(p)}:{i}" for p, i, _ in bang_md if f"{rel(p)}:{i}" not in load_time]
    rec("FAIL" if load_time else "PASS", "D5 load-time shell", f"SKILL.md/agent hits: {load_time or 'none'}; "
        f"references (not preprocessed): {other or 'none'}")
    hook_files = [rel(p) for root in ("skills", "agents") for p in (PACK / root).rglob("*")
                  if p.name in {"hooks.json", "settings.json"} or (p.is_dir() and p.name == "hooks")]
    rec("FAIL" if hook_files else "PASS", "D6 hooks", f"{hook_files}" if hook_files else "no hook files or folders")
    bare, broad = [], []
    for sk in [d / "SKILL.md" for d in skill_dirs()]:
        fm, _, _ = split_fm(read(sk))
        tools = re.findall(r"\S+\([^)]*\)|\S+", fm.get("allowed-tools", ""))
        if "Bash" in tools:
            bare.append(rel(sk))
        broad += [f"{rel(sk)} {t}" for t in tools if re.fullmatch(r"Bash\((python3?|node|sh|bash|pwsh) \*\)", t)]
    for ag in agent_files():
        fm, _, _ = split_fm(read(ag))
        if "Bash" in [t.strip() for t in fm.get("tools", "").split(",")]:
            bare.append(f"{rel(ag)} (agent tools)")
    rec("FAIL" if bare else "PASS", "D7 no bare Bash", f"bare Bash: {bare}" if bare else "none")
    if broad:
        rec("WARN", "D7b broad Bash", f"any-script interpreter rules: {broad}")
    temp_rx = r"tempfile|gettempdir|mkdtemp|/tmp/|%TEMP%|\$TMPDIR|\$env:TEMP|AppData\\\\Local\\\\Temp"
    temp = [f"{rel(p)}:{i}" for p, i, _ in grep(PACK / "skills", temp_rx)
            if "skill-security-audit" not in p.parts and p.suffix != ".pyc"]
    rec("FAIL" if temp else "PASS", "D9 temp folders", f"outside skill-security-audit: {temp}" if temp else "none")
    audit = read(PACK / "AUDIT.md")
    rejected = set()
    for row in re.findall(r"^\|([^|]+)\|([^|]*REJECT[^|]*)\|", audit, re.M):
        for name in re.split(r",\s*", row[0].strip()):
            rejected.add(name.split(":")[-1].strip().strip("`"))
    present = sorted(rejected & {d.name for d in skill_dirs()})
    rec("FAIL" if present else "PASS", "D10 AUDIT REJECTs absent",
        f"present: {present}" if present else f"{len(rejected)} REJECT names, none in skills/")


def check_d_waivers() -> None:
    try:
        out = subprocess.run([sys.executable, "-I", str(PACK / "scripts" / "scan.py"), "--waivers",
                              str(PACK / "tests" / "scan-waivers.tsv")], capture_output=True, text=True,
                             cwd=PACK, timeout=300).stdout
    except (OSError, subprocess.TimeoutExpired) as exc:
        rec("FAIL", "D8 waivers", f"scan.py did not run: {exc}")
        return
    section = out.split("REJECT-class, waived after review", 1)[-1].split("WARN (review", 1)[0]
    hits = re.findall(r"^\s+(\S+):(\d+)\s+\[[^/\]]+/([^\]]+)\]", section, re.M)
    unwaived = re.search(r"REJECT-class, not waived: (\d+)", out)
    head = out.split("REJECT-class, waived after review", 1)[0]
    files = sorted(set(re.findall(r"^\s+(\S+):\d+\s+\[", head, re.M)))
    rec("PASS" if unwaived and unwaived.group(1) == "0" else "FAIL", "D8a scan gate",
        f"unwaived REJECT-class hits: {unwaived.group(1) if unwaived else '?'} in {files or 'none'}")
    for path, line, pat in hits:
        dec = REVIEWED_WAIVERS.get((path, pat))
        if dec is None:
            rec("FAIL", "D8 waiver", f"{path}:{line} [{pat}] not reviewed by the verifier")
        elif dec[0] == "FAIL" and pat in SEVERE_WAIVER_PATTERNS:
            rec("FAIL", "D8 waiver", f"{path}:{line} [{pat}] {dec[1]}")
        else:
            rec("PASS", "D8 waiver", f"{path}:{line} [{pat}] justified: {dec[1]}")


# ---------------------------------------------------------------- E. provenance
def check_e() -> None:
    man = manifest()
    notices = read(PACK / "THIRD-PARTY-NOTICES.md")
    audit = read(PACK / "AUDIT.md")
    for s in man["skills"]:
        if s.get("origin") not in {"adopted", "adapted"}:
            continue
        n, d = s["name"], PACK / "skills" / s["name"]
        body = read(d / "SKILL.md")
        src = re.search(r"^.*\b(Source|Adapted from)\b.*$", body, re.M | re.I)
        src_line = src.group(0) if src else ""
        has_repo = bool(re.search(r"github\.com/[\w.-]+/[\w.-]+", src_line))
        has_sha = bool(re.search(r"\b[0-9a-f]{40}\b", src_line))
        lic_file = [p.name for p in d.glob("LICENSE*")]
        holder = s.get("source", "").split()[0] if s.get("source") else ""
        lic_text = "Permission is hereby granted" in notices and any(
            k in notices.split("## ", 1)[-1] for k in (n,))
        lic_ok = bool(lic_file) or (n in notices and re.search(rf"## .*\({re.escape(s['licence'])}\)", notices)
                                    and _notice_has_text_for(notices, n))
        problems = []
        if not (has_repo and has_sha):
            problems.append(f"Source line lacks {'repo ' if not has_repo else ''}{'SHA' if not has_sha else ''}".strip())
        if not lic_ok:
            problems.append("no licence file and no licence text in THIRD-PARTY-NOTICES")
        ln = body[:src.start()].count("\n") + 1 if src else 0
        rec("FAIL" if problems else "PASS", f"E1 {n}", f"skills/{n}/SKILL.md:{ln} "
            + ("; ".join(problems) if problems else f"repo+SHA ok; licence {lic_file or 'in NOTICES'}"))
        _ = holder, lic_text
    q = PACK / "_quarantine"
    upstream = {"skill-creator": q / "anthropics-skills/skills/skill-creator",
                "verification-before-completion": q / "superpowers/skills/verification-before-completion"}
    for s in man["skills"]:
        if s.get("origin") != "adopted":
            continue
        n, up = s["name"], upstream.get(s["name"])
        if not q.is_dir() or up is None or not up.is_dir():
            rec("WARN", f"E2 {n}", "no quarantine copy to compare: unverified")
            continue
        mine = {p.relative_to(PACK / "skills" / n).as_posix(): sha256(p) for p in text_files(PACK / "skills" / n)}
        theirs = {p.relative_to(up).as_posix(): sha256(p) for p in text_files(up)}
        diff = sorted(k for k in mine.keys() | theirs.keys() if mine.get(k) != theirs.get(k)
                      and not (k.startswith("LICENSE") and k not in theirs))
        entry = re.search(rf"^- \*\*{re.escape(n)}\*\*.*$", audit, re.M)
        text = entry.group(0) if entry else ""
        unlisted = [k for k in diff if not (Path(k).name in text or (k == "SKILL.md" and re.search(
            r"frontmatter|description", text, re.I)))]
        rec("FAIL" if unlisted else "PASS", f"E2 {n} vs quarantine",
            f"{len(diff)} differing files {diff}; not listed in AUDIT.md: {unlisted or 'none'}")
    names = {d.name for d in skill_dirs()}
    listed = {s["name"] for s in man["skills"]}
    a_names, a_listed = {p.stem for p in agent_files()}, {a["name"] for a in man["agents"]}
    keys = ["source", "sha", "licence", "audit_verdict", "model", "description_tokens"]
    missing = [f"{e['name']}:{k}" for e in man["skills"] + man["agents"] for k in keys if k not in e]
    wrong = []
    for e in man["skills"]:
        fm, _, _ = split_fm(read(PACK / "skills" / e["name"] / "SKILL.md"))
        if e.get("model") != fm.get("model") or e.get("description_tokens") != cost(e["name"], fm["description"]) // 4:
            wrong.append(e["name"])
    for e in man["agents"]:
        fm, _, _ = split_fm(read(PACK / "agents" / f"{e['name']}.md"))
        if e.get("model") != fm.get("model") or e.get("description_tokens") != cost(e["name"], fm["description"]) // 4:
            wrong.append(e["name"])
    ok = names == listed and a_names == a_listed and not missing and not wrong
    rec("PASS" if ok else "FAIL", "E3 MANIFEST", f"skills {len(listed)}/{len(names)}, agents {len(a_listed)}/"
        f"{len(a_names)}; extra/missing {sorted(names ^ listed) + sorted(a_names ^ a_listed)}; missing keys "
        f"{missing[:6] or 'none'}; stale model/tokens {wrong or 'none'}")
    sel = read(PACK / "SELECTION.md")
    for label, rx in SIX_SOURCES.items():
        a = len(re.findall(rx, audit, re.I))
        s_ = len(re.findall(rx, sel, re.I))
        judged = REVIEWED_SOURCE_DECISIONS.get(label)
        status = "FAIL" if not (a and s_) else (judged[0] if judged else "PASS")
        rec(status, f"E4 decision {label}", f"mentions AUDIT.md {a}, SELECTION.md {s_}"
            + (f"; read: {judged[1]}" if judged else ""))


def _notice_has_text_for(notices: str, name: str) -> bool:
    """True if the NOTICES row for `name` points to a full text that exists (below or a file)."""
    row = next((l for l in notices.splitlines() if l.startswith("|") and name in l.split("|")[1]), "")
    if "not on disk" in row or "to add" in row:
        return False
    if "below" in row:
        return "Permission is hereby granted" in notices
    m = re.search(r"`([^`]+LICENSE[^`]*)`", row)
    return bool(m and (PACK / m.group(1).replace("<name>", name)).is_file())


# ---------------------------------------------------------------- F. tokens
def check_f() -> None:
    skills = []
    for d in skill_dirs():
        fm, _, _ = split_fm(read(d / "SKILL.md"))
        skills.append((d.name, cost(d.name, fm.get("description", "")),
                       fm.get("disable-model-invocation", "").lower() == "true"))
    agents = [cost(p.stem, split_fm(read(p))[0].get("description", "")) for p in agent_files()]
    auto = sum(c for _, c, m in skills if not m)
    allc = sum(c for _, c, _ in skills)
    tr = read(PACK / "TOKEN-REPORT.md")

    def row(label: str) -> tuple[int, int] | None:
        m = re.search(rf"^\|[^|\n]*{label}[^|\n]*\|[^|\n]*\| (\d+) \| \**(\d+)\**", tr, re.M)
        return (int(m.group(1)), int(m.group(2))) if m else None

    for label, chars in (("auto-invocable skills only", auto), ("all \\d+ skills", allc),
                         ("Pack agents", sum(agents)), ("auto skills \\+ agents", auto + sum(agents))):
        r = row(label)
        ok = r is not None and abs(r[1] - chars // 4) <= 0.02 * max(1, chars // 4)
        rec("PASS" if ok else "FAIL", f"F1 {label.replace(chr(92), '')}",
            f"recomputed {chars} chars ~{chars // 4} tok; TOKEN-REPORT {r}")
    with open(PACK / "_work" / "inventory.csv", encoding="utf-8") as fh:
        inv = list(csv.DictReader(fh))
    inst = [r for r in inv if r["source"] != "quarantine"]
    b_chars = sum(len(r["name"]) + len(r["description"]) for r in inst)
    b_col = sum(len(r["name"]) + int(r["description_chars"]) for r in inst)
    bt = read(PACK / "_work" / "baseline.txt")
    m = re.search(r"Installed \(mine \+ plugin\): (\d+) skills, (\d+) chars, ~(\d+) tokens", bt)
    b_ok = m and int(m.group(1)) == len(inst) and abs(int(m.group(2)) - b_col) <= 0.02 * b_col
    rec("PASS" if b_ok else "FAIL", "F2 baseline", f"inventory: {len(inst)} installed skills, {b_col} chars "
        f"(name+description_chars), {b_chars} from description text; baseline.txt {m.groups() if m else None}")
    r = row("Baseline: everything installed")
    rec("PASS" if r and abs(r[0] - b_col) <= 0.02 * b_col else "FAIL", "F3 baseline in TOKEN-REPORT",
        f"TOKEN-REPORT {r}; recomputed {b_col} chars ~{b_col // 4}")
    saved = 100 * (b_col - auto) / b_col
    saved2 = 100 * (b_col - auto - sum(agents)) / b_col
    rec("PASS", "F4 summary", f"{len(skills)} skills ({len(skills) - sum(m for *_, m in skills)} auto) + "
        f"{len(agents)} agents; always-loaded ~{auto // 4} tok vs baseline ~{b_col // 4}: {saved:.1f}% saved "
        f"({saved2:.1f}% incl. agents)")


# ---------------------------------------------------------------- G. README
def slug(h: str) -> str:
    return re.sub(r"[^\w\- ]", "", h.strip().lower()).replace(" ", "-")


def check_mermaid(block: str) -> str | None:
    lines = [l for l in block.splitlines() if l.strip() and not l.strip().startswith("%%")]
    kinds = ("flowchart", "graph", "sequenceDiagram", "erDiagram", "classDiagram", "stateDiagram", "gantt",
             "pie", "journey", "mindmap", "C4Context")
    if not lines or not lines[0].strip().startswith(kinds):
        return "unknown diagram type"
    body = "\n".join(lines[1:])
    for o, c in ("[]", "()", "{}"):
        if body.count(o) != body.count(c):
            return f"unbalanced {o}{c}"
    if body.count('"') % 2:
        return "odd number of quotes"
    if len(re.findall(r"^\s*subgraph\b", body, re.M)) != len(re.findall(r"^\s*end\s*$", body, re.M)):
        return "subgraph/end mismatch"
    return None


def readme_sections(text: str) -> dict[str, str]:
    region = text.split("## The skills", 1)[-1].split("## How the pieces fit", 1)[0]
    out: dict[str, str] = {}
    for m in re.finditer(r"^\*\*([a-z0-9-]+)\*\*[^:\n]*:(.*?)(?=^\*\*[a-z0-9-]+\*\*|^#|^The 8 phase|\Z)",
                         region, re.M | re.S):
        out[m.group(1)] = m.group(2)
    for m in re.finditer(r"^\| ([a-z0-9-]+) \|(.*)$", region, re.M):
        out[m.group(1)] = m.group(2)
    return out


def check_g() -> None:
    p = PACK / "README.md"
    text = read(p)
    n_lines = len(text.splitlines())
    rec("PASS" if n_lines <= MAX_README_LINES else "FAIL", "G1 README length", f"{n_lines} lines")
    man = {s["name"]: s for s in manifest()["skills"]}
    secs = readme_sections(text)
    phase_note = "They are auto skills" in text
    for n, s in man.items():
        sec = secs.get(n)
        if sec is None:
            rec("FAIL", f"G2 {n}", "no README section")
            continue
        is_row = sec.count("|") >= 4
        miss = []
        if not re.search(rf"\b{s['description_tokens']}\b", sec):
            miss.append(f"tokens {s['description_tokens']}")
        model_ok = re.search(rf"\b{s['model']}\b\s*(\(|:|for)", sec) if True else None
        if not model_ok:
            miss.append(f"model+why ({s['model']})")
        if not is_row and not re.search(r"\b(Auto|Manual)\b", sec):
            miss.append("when it runs")
        if is_row and not phase_note:
            miss.append("when it runs")
        if not is_row and sec.count("\n- ") < 1:
            miss.append("rules")
        if s["origin"] != "mine":
            if not re.search(r"(adapted|adopted) from", sec) or not re.search(r"SAFE", sec):
                miss.append("source/verdict")
        elif not re.search(r"\bmine\b", sec):
            miss.append("source")
        if miss:
            rec("FAIL", f"G2 {n}", f"README section lacks: {', '.join(miss)}")
        else:
            verdict = "own skill: source 'mine', no audit verdict shown" if s["origin"] == "mine" else "complete"
            rec("WARN" if s["origin"] == "mine" else "PASS", f"G2 {n}", verdict)
    extra = sorted(set(secs) - set(man))
    rec("FAIL" if extra else "PASS", "G3 no foreign sections", f"extra: {extra}" if extra else f"{len(secs)} sections")
    agents = [a.stem for a in agent_files()]
    miss = [a for a in agents if a not in text]
    tbl = re.findall(r"^\| \d+ \| ([a-z-]+)", text, re.M)
    foreign = sorted(set(tbl) - set(agents))
    rec("FAIL" if miss or foreign else "PASS", "G4 agents", f"missing {miss}, foreign {foreign}"
        if miss or foreign else f"all {len(agents)} named")
    bad = []
    for i, line in enumerate(text.splitlines(), 1):
        for target in re.findall(r"\]\(([^)\s]+)\)", line):
            if re.match(r"[a-z]+:", target):
                continue
            path, _, anchor = target.partition("#")
            f = (p.parent / path) if path else p
            if not f.exists():
                bad.append(f"README.md:{i} {target}")
            elif anchor and f.is_file() and anchor not in {slug(h) for h in re.findall(r"^#+ (.*)$", read(f), re.M)}:
                bad.append(f"README.md:{i} {target} (anchor)")
    rec("FAIL" if bad else "PASS", "G5 links", "; ".join(bad) if bad else "every relative link resolves")
    blocks = re.findall(r"```mermaid\n(.*?)```", text, re.S)
    errs = [e for e in (check_mermaid(b) for b in blocks) if e]
    tool = shutil.which("mmdc")
    rec("FAIL" if errs else "WARN", "G6 mermaid", f"{len(blocks)} block(s); structural check: {errs or 'ok'}; "
        f"mermaid-cli {'found but not run' if tool else 'not installed'}: not rendered (checked by heuristic and eye)")


# ---------------------------------------------------------------- H. design team
def check_h() -> None:
    sk = PACK / "skills" / "backend-design-team" / "SKILL.md"
    in_agents = (PACK / "agents" / "backend-design-team.md").exists()
    text = read(sk)
    n = len(text.splitlines())
    rec("PASS" if not in_agents and n <= MAX_BODY_LINES else "FAIL", "H1 orchestrator",
        f"skill (agent file: {in_agents}); {n} lines")
    rows = re.findall(r"^\| (\d) \| .*\| ([^|]+) \|$", text, re.M)
    expect = ["project-profile", "01-strategic", "02-tactical", "03-db-design", "04-erd", "05-diagrams",
              "06-api", "07-review", "README"]
    got = [w for _, w in rows]
    ok = len(got) == 9 and all(e in g for e, g in zip(expect, got))
    ln = text[:text.find("| 0 |")].count("\n") + 1
    rec("PASS" if ok else "FAIL", "H2 phase order", f"SKILL.md:{ln} {[r[0] for r in rows]} -> "
        "profile, strategic, tactical, database, ERD, diagrams, endpoints, review, document" if ok else f"{got}")
    for cid, rx, what in (("H3 guard", r"exists under `<out>` and is not empty", "guard"),
                          ("H4 checkpoint", r"Update `<out>/00-state\.md`[\s\S]{0,400}git commit", "state+commit"),
                          ("H5 <out> from root", r"resolved against `<root>`, never against the current", "root")):
        m = re.search(rx, text)
        rec("PASS" if m else "FAIL", cid, f"SKILL.md:{text[:m.start()].count(chr(10)) + 1} {what}" if m else "not found")
    readme = read(PACK / "README.md")
    for a in agent_files():
        fm, _, _ = split_fm(read(a))
        tools = [t.strip() for t in fm.get("tools", "").split(",") if t.strip()]
        ok = fm.get("model") in ALIASES and tools and "*" not in tools
        rec("PASS" if ok else "FAIL", f"H6 {a.stem}", f"model {fm.get('model')}, tools {tools}")
    fm, body, _ = split_fm(read(PACK / "agents" / "design-reviewer.md"))
    tools = [t.strip() for t in fm.get("tools", "").split(",")]
    row7 = re.search(r"^\| 7 \| design-reviewer.*$", readme, re.M)
    claims_only_review = bool(row7 and "07-review.md" in row7.group(0) and
                              ("only" in row7.group(0) or row7.group(0).count("`") <= 2))
    ok = "Edit" not in tools and "Write" in tools and claims_only_review and "Read-only" in readme
    rec("PASS" if ok else "FAIL", "H7 design-reviewer", f"tools {tools}; README row 7 says only 07-review.md: "
        f"{claims_only_review}; Write is not path-scoped (enforced by prompt only)")


# ---------------------------------------------------------------- I. genericity
def check_i() -> None:
    script = PACK / "tests" / "genericity-check.py"
    if not script.is_file():
        rec("FAIL", "I genericity", "tests/genericity-check.py missing")
        return
    base = [sys.executable, "-I", str(script)]
    with_allow = subprocess.run(base + ["--allow", str(PACK / "tests" / "genericity-allow.tsv")],
                                capture_output=True, text=True, cwd=PACK)
    rec("PASS" if with_allow.returncode == 0 else "FAIL", "I1 genericity --allow",
        f"exit {with_allow.returncode}: {with_allow.stdout.strip().splitlines()[-1:]}")
    raw = subprocess.run(base, capture_output=True, text=True, cwd=PACK).stdout
    hits = re.findall(r"^HIT\s+(\S+):(\d+) \[[^\]]+\] '([^']+)'", raw, re.M)
    unexplained = [h for h in hits if h not in REVIEWED_GENERICITY]
    rec("FAIL" if unexplained else "PASS", "I2 genericity raw",
        f"{len(hits)} hit(s), judged: {[f'{p}:{l} {m}: {REVIEWED_GENERICITY.get((p, l, m))}' for p, l, m in hits]}; "
        f"unexplained {unexplained or 0}")


# ---------------------------------------------------------------- J. tests on disk
def hml(text: str) -> list[tuple[int, int, int]]:
    return [tuple(map(int, m)) for m in re.findall(r"High:? (\d+),? Med\w*:? (\d+),? Low:? (\d+)", text)] + \
        [tuple(map(int, m)) for m in re.findall(r"(\d+) High, (\d+) Med\w*, (\d+) Low", text)]


def check_j() -> None:
    res = PACK / "tests" / "results"
    need = ["fixture-a.md", "fixture-b.md", "defect-test.md", "defect-key.md", "genericity.md"]
    miss = [n for n in need if not (res / n).is_file()] + ([] if (PACK / "tests/RESULTS.md").is_file() else ["RESULTS.md"])
    rec("FAIL" if miss else "PASS", "J1 result files", f"missing {miss}" if miss else "5 results files + RESULTS.md")
    if miss:
        return
    phases = [r"project-profile\.md", r"00-project-brief\.md", r"01-strategic.*\.md", r"02-tactical-.+\.md",
              r"03-db-design.*\.md", r"04-erd.*\.md", r"05-diagrams.*\.md", r"06-api.*", r"07-review\.md", r"README\.md"]
    for fx, folder in (("A", PACK / "tests/fixture-a/docs/design"), ("B", PACK / "tests/fixture-b/docs/design")):
        files = [p for p in folder.rglob("*") if p.is_file() and p.stat().st_size > 0]
        absent = [rx for rx in phases if not any(re.fullmatch(rx, f.name) for f in files)]
        rec("FAIL" if absent else "PASS", f"J2 fixture {fx} artifacts",
            f"missing {absent}" if absent else f"phases 0-8 present, {len(files)} non-empty files")
    results_md = read(PACK / "tests/RESULTS.md")
    rm = hml(results_md)
    fa, fb, dt = read(res / "fixture-a.md"), read(res / "fixture-b.md"), read(res / "defect-test.md")
    fb_loops = [tuple(map(int, m)) for m in re.findall(r"^\| [12] \| (\d+) \| (\d+) \| (\d+) \|", fb, re.M)]
    review = {
        "A": [hml(read(PACK / f"tests/fixture-a/docs/design/review/{f}"))[0] for f in ("07-review-loop1.md", "07-review.md")],
        "B": [hml(read(PACK / f"tests/fixture-b/docs/design/review/{f}"))[0] for f in ("07-review-loop1.md", "07-review.md")],
    }
    for fx, claimed in (("A", hml(fa)), ("B", fb_loops)):
        ok = claimed[:2] == review[fx] and all(t in rm for t in review[fx])
        rec("PASS" if ok else "FAIL", f"J3 fixture {fx} numbers", f"review files {review[fx]}; results file "
            f"{claimed[:2]}; in RESULTS.md: {[t in rm for t in review[fx]]}")
    dtot = hml(dt)
    rv = hml(read(PACK / "tests/defect-test/design/07-review.md"))
    found = re.findall(r"^\| (D\d) \|[^|]+\| found", dt, re.M)
    ok = dtot[:1] == rv[:1] and dtot[0] in rm and len(found) == 5 and "5/5" in results_md
    rec("PASS" if ok else "FAIL", "J4 defect test", f"found {found} ({len(found)}/5); totals {dtot[:1]} vs review "
        f"{rv[:1]}; RESULTS.md has 5/5: {'5/5' in results_md}")
    g = re.search(r"total hits: (\d+), allowed: (\d+), unexplained: (\d+)", read(res / "genericity.md"))
    ok = g and f"{g.group(1)} hit" in results_md
    rec("PASS" if ok else "FAIL", "J5 genericity numbers", f"genericity.md {g.groups() if g else None}")
    runs = sorted(res.glob("triggers-run*.md"), key=lambda p: int(re.sub(r"\D", "", p.stem) or 0))
    for r in runs:
        t = read(r)
        rows = re.findall(r"^\| [a-z-]+ \| (yes|no) \| (PASS|FAIL|ERROR) \| ([^|]*) \|", t, re.M)
        pas = [x for x in rows if x[1] == "PASS"]
        misgraded = [x for x in pas if not re.match(r"\s*(Skill\(|/|-\s*$)", x[2])]
        fails = sum(x[1] == "FAIL" for x in rows)
        errs = sum(x[1] == "ERROR" for x in rows)
        real = len(pas) - len(misgraded)
        verdicts = real + fails
        last = r == runs[-1]
        rec("WARN" if misgraded or errs else "PASS", f"J6 {r.name}{' (last)' if last else ''}",
            f"{len(rows)} cases: PASS {len(pas)} (of which {len(misgraded)} graded PASS on an error message), "
            f"FAIL {fails}, ERROR {errs}; real pass rate {real}/{len(rows)} = {100 * real / len(rows):.0f}%, "
            f"{real}/{verdicts} of cases with a verdict")
    m = re.search(r"(\d+) cases; (\d+) pass, (\d+) fail, (\d+) errors", results_md)
    rec("WARN" if m else "FAIL", "J7 RESULTS.md triggers", f"RESULTS.md claims {m.groups() if m else None}; "
        "see J6 for the regraded numbers")


# ---------------------------------------------------------------- K. install
def check_k(target: str | None) -> None:
    ps1 = PACK / "scripts" / "install.ps1"
    if not ps1.is_file():
        rec("FAIL", "K1 install.ps1", "missing")
        return
    t = read(ps1)
    probs = []
    if not re.search(r"\[switch\]\$Apply", t):
        probs.append("no -Apply switch")
    if re.search(r"(?i)SymbolicLink|HardLink|Junction|mklink", t):
        probs.append("creates links")
    if re.search(r"(?i)Invoke-WebRequest|Invoke-RestMethod|WebClient|BitsTransfer|curl|wget|http[s]?://", t):
        probs.append("network")
    if "Copy-Item" not in t or "DRY RUN" not in t:
        probs.append("no copy / no dry-run text")
    rec("FAIL" if probs else "PASS", "K1 install.ps1 static", f"{probs}" if probs else
        "dry run by default, -Apply to copy, Copy-Item (no links), no network")
    if not target:
        rec("WARN", "K2 install dry run", "not run (pass --install-target <empty dir outside the repo>)")
        return
    tgt = Path(target).resolve()
    if REPO in tgt.parents or tgt == REPO or not tgt.is_dir():
        rec("FAIL", "K2 install dry run", f"target {tgt} must be an existing folder outside the repo")
        return
    before = (tgt / ".claude").exists()
    ps = shutil.which("powershell") or shutil.which("pwsh")
    cmd = [ps, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps1), "-Project", str(tgt)] if ps else \
        ["bash", str(PACK / "scripts/install.sh"), "--project", str(tgt)]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=300).stdout
    listed = re.findall(r"^(NEW|SAME|CHANGED)\s+(skill|agent)\s+(\S+)", out, re.M)
    skills = {n for _, k, n in listed if k == "skill"}
    agents = {n.removesuffix(".md") for _, k, n in listed if k == "agent"}
    exp_s, exp_a = {d.name for d in skill_dirs()}, {a.stem for a in agent_files()}
    wrote = (tgt / ".claude").exists() and not before
    ok = skills == exp_s and agents == exp_a and not wrote
    rec("PASS" if ok else "FAIL", "K2 install dry run", f"{Path(cmd[0]).name}: {len(skills)} skills, {len(agents)} "
        f"agents listed; diff {sorted(skills ^ exp_s) + sorted(agents ^ exp_a) or 'none'}; wrote files: {wrote}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--install-target")
    args = ap.parse_args()
    steps = (check_a, check_b, check_c, check_d_scripts, check_d_skills, check_d_waivers, check_e, check_f,
             check_g, check_h, check_i, check_j)
    for step in steps:
        try:
            step()
        except Exception as exc:  # a crash in one group must not hide the others
            rec("FAIL", step.__name__, f"check crashed: {type(exc).__name__}: {exc}")
    try:
        check_k(args.install_target)
    except Exception as exc:
        rec("FAIL", "check_k", f"check crashed: {type(exc).__name__}: {exc}")
    for status, cid, msg in RESULTS:
        print(f"{status:4} {cid}: {msg}")
    counts = {s: sum(r[0] == s for r in RESULTS) for s in ("PASS", "WARN", "FAIL")}
    print(f"TOTAL PASS {counts['PASS']}  WARN {counts['WARN']}  FAIL {counts['FAIL']}")
    return 1 if counts["FAIL"] else 0


if __name__ == "__main__":
    sys.exit(main())
