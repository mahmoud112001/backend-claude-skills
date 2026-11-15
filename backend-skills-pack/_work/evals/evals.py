"""Test cases, run setup and programmatic grading for the session-2 custom skills.

Usage (run with python -I from anywhere):
  evals.py cases            write case folders _work/evals/<skill>/<case>/ (skill-creator layout)
  evals.py setup N          create <skill>-workspace/iteration-N/<case>/{with_skill,without_skill}/
                            with a fresh fixture copy, eval_metadata.json and run.md (the run prompt)
  evals.py grade N          grade every run into grading.json and print a summary table
Standard library only. Runs git only inside the fixture copies it creates.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PACK = HERE.parent.parent
SKILLS = PACK / "skills"
FIX = HERE / "fixtures"
DATE = "2026-11-15"
AUTO = ["reuse-first", "model-router", "architecture-conformance"]
MANUAL = ["dead-code-cleaner", "skill-security-audit"]
NO_EXEC_RE = re.compile(r"(^|[\s;&|(])(bash|sh|zsh|source|\.)\s+\S*sync\.sh|(^|[;&|]\s*)(\./)?\S*scripts/sync\.sh\b", re.M)


# ---------- helpers used by checks: r = dict(reply, skills, commands, repo, out) ----------
def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True).stdout


def src(r, rel):
    p = r["repo"] / rel
    return p.read_text(encoding="utf-8") if p.is_file() else ""


def report(r, pattern):
    files = sorted((r["repo"] / "docs" / "reviews").glob(pattern)) if (r["repo"] / "docs" / "reviews").is_dir() else []
    return files[0].read_text(encoding="utf-8") if files else ""


def row(text, name):
    """The report table row(s) mentioning name."""
    return "\n".join(ln for ln in text.splitlines() if name in ln and "|" in ln)


def tree(root: Path) -> dict[str, bytes]:
    skip = {".git", "__pycache__"}
    out = {}
    for p in root.rglob("*") if root.is_dir() else []:
        rel = p.relative_to(root).as_posix()
        if p.is_file() and not (skip & set(p.relative_to(root).parts)) and not rel.startswith("docs/reviews/"):
            out[rel] = p.read_bytes().replace(b"\r\n", b"\n")
    return out


def cls(text, name):
    """Classes in the Class cell of the candidate row(s) for name: SAFE / NEEDS / KEEP."""
    out = set()
    for ln in row(text, name).splitlines():
        for cell in ln.split("|"):
            c = cell.strip().strip("*` ").upper()
            for k in ("SAFE-TO-DELETE", "NEEDS-HUMAN", "KEEP"):
                if c == k:
                    out.add(k.split("-")[0])
    return out


def changed_src(r):
    """Files added, removed or edited versus the fixture (ignores caches, .git, docs/reviews,
    and the rules file that the no-rules setup deletes on purpose)."""
    before, after = tree(FIX / "orders-svc"), tree(r["repo"])
    before.pop("docs/ddd/service-design-rules.md", None)
    after.pop("docs/ddd/service-design-rules.md", None)
    return sorted(k for k in before.keys() | after.keys() if before.get(k) != after.get(k))


def used(r, skill):
    return skill in r["skills"]


def no_version(text):
    return not re.search(r"\b(haiku|sonnet|opus|fable)[\s-]*\d", text, re.I) and not re.search(r"claude-[a-z]+-\d", text)


def verdict_line(text):
    for ln in text.splitlines():
        if ln.strip():
            return ln.strip().strip("`*# ")
    return ""


C = []  # cases


def case(skill, name, trigger, prompt, expected, setup, checks):
    C.append(dict(skill=skill, name=name, trigger=trigger, prompt=prompt, expected=expected, setup=setup, checks=checks))


# ---------------- reuse-first ----------------
case("reuse-first", "rf-slug-helper-exists", True,
     "In orders-svc I'm adding an export endpoint that needs URL-safe slugs from order titles like 'Cafe Order #12'. "
     "I'm about to write a slug function. Before I do, check whether we already have something, or whether I should add a library.",
     "A single REUSE verdict pointing at shared/text.py slugify; no new dependency; no file changes.", "repo",
     [("The reply's verdict is REUSE (first non-empty line starts with REUSE)", lambda r: verdict_line(r["reply"]).upper().startswith("REUSE")),
      ("The reply points to src/shared/text.py slugify", lambda r: "shared/text.py" in r["reply"] and "slugify" in r["reply"]),
      ("The reply is at most 10 lines", lambda r: len([l for l in r["reply"].splitlines() if l.strip()]) <= 10),
      ("The reply does not recommend adding python-slugify or another library", lambda r: not re.search(r"\bADD\b|pip install|python-slugify", r["reply"])),
      ("No file in the repo was changed", lambda r: not changed_src(r))])
case("reuse-first", "rf-retry-backoff", True,
     "orders-svc calls the broker over HTTP (src/orders/infrastructure/broker.py). I want retries with exponential backoff. "
     "Should I add tenacity or backoff, or write my own?",
     "REUSE urllib3 Retry through the installed requests (HTTPAdapter); no new dependency without a 2-option comparison.", "repo",
     [("The reply's verdict is REUSE", lambda r: verdict_line(r["reply"]).upper().startswith("REUSE")),
      ("The reply names urllib3 Retry (via requests HTTPAdapter)", lambda r: "Retry" in r["reply"] and re.search(r"urllib3|HTTPAdapter", r["reply"])),
      ("The reply does not recommend adding tenacity or backoff", lambda r: not re.search(r"^\s*ADD\b", r["reply"], re.M)),
      ("The reply is at most 10 lines", lambda r: len([l for l in r["reply"].splitlines() if l.strip()]) <= 10),
      ("No file in the repo was changed", lambda r: not changed_src(r))])
case("reuse-first", "rf-negative-rename", False,
     "In orders-svc, rename the parameter `amount` to `value` in format_money (src/shared/money.py). Keep behaviour the same.",
     "Does the rename directly; reuse-first is not used.", "repo",
     [("reuse-first was not used", lambda r: not used(r, "reuse-first")),
      ("format_money now takes `value`", lambda r: "def format_money(value" in src(r, "src/shared/money.py")),
      ("The reply contains no REUSE/ADD/WRITE verdict", lambda r: not re.match(r"(REUSE|ADD|WRITE)\b", verdict_line(r["reply"])))])

# ---------------- model-router ----------------
case("model-router", "mr-route-mixed", True,
     "Three jobs today: (1) rename customer_id to client_id across ~40 files in orders-svc, (2) design the outbox and relay "
     "for payments with exactly-once effects, (3) list every TODO in the repo. Which model should each run on? Also, I want my "
     "dead-code-cleaner skill to always run on sonnet even when my session is on opus. How?",
     "rename: sonnet; outbox design: opus/fable; TODO list: haiku or grep; skill model field, which affects only that skill's turn.", None,
     [("Job 1 (rename) is routed to sonnet", lambda r: re.search(r"(1|rename)[^\n]*sonnet", r["reply"], re.I)),
      ("Job 2 (outbox design) is routed to opus or fable", lambda r: re.search(r"(2|outbox)[^\n]*(opus|fable)", r["reply"], re.I)),
      ("Job 3 (TODO list) is routed to haiku or a plain grep/script", lambda r: re.search(r"(3|TODO)[^\n]*(haiku|grep|script|rg)", r["reply"], re.I)),
      ("It names the skill's `model:` frontmatter field", lambda r: re.search(r"model:\s*sonnet|`model`\s*(field|frontmatter)|model field", r["reply"], re.I)),
      ("It states the skill model applies only to that skill's turn/run, not the main session", lambda r: re.search(r"(only|just)[^\n]*(turn|run|while)|session model (resumes|returns)|does not change the (main )?session|doesn't change the (main )?session|not (change|switch) the (main )?session", r["reply"], re.I)),
      ("No model version numbers are written", lambda r: no_version(r["reply"]))])
case("model-router", "mr-model-column", True,
     "Build the model column for the README of backend-skills-pack: every skill and agent in D:/I-fikra/backend-claude-skills/backend-skills-pack/skills "
     "with its model and why. Save the table to OUT/model-column.md.",
     "A table with all five skills and correct aliases, built by model_column.py; no version numbers.", None,
     [("model-column.md lists all 5 skills", lambda r: all(s in (r["out"] / "model-column.md").read_text(encoding="utf-8") for s in AUTO + MANUAL) if (r["out"] / "model-column.md").is_file() else False),
      ("Each skill has its correct alias (reuse-first/model-router haiku, dead-code-cleaner/architecture-conformance sonnet, skill-security-audit opus)",
       lambda r: (lambda t: all(re.search(rf"{s}[^\n]*\b{m}\b", t) for s, m in [("reuse-first", "haiku"), ("model-router", "haiku"), ("dead-code-cleaner", "sonnet"), ("architecture-conformance", "sonnet"), ("skill-security-audit", "opus")]))((r["out"] / "model-column.md").read_text(encoding="utf-8")) if (r["out"] / "model-column.md").is_file() else False),
      ("model_column.py was run", lambda r: "model_column.py" in r["commands"]),
      ("No model version numbers in the table", lambda r: no_version((r["out"] / "model-column.md").read_text(encoding="utf-8")) if (r["out"] / "model-column.md").is_file() else False)])
case("model-router", "mr-negative-pricing", False,
     "What's the per-million-token API price of Claude Haiku versus Opus, and how big is each one's context window?",
     "model-router is not used (pricing/specs are out of scope).", None,
     [("model-router was not used", lambda r: not used(r, "model-router"))])

# ---------------- dead-code-cleaner ----------------
DC_RPT = "cleanup-*.md"
case("dead-code-cleaner", "dc-report", True,
     "/dead-code-cleaner report",
     "Report only: legacy_invoice_number and _unused_helper SAFE-TO-DELETE; on_invoice_created and old_tax_rate not deletable; "
     "_fmt_money merge into shared/money.format_money proposed; no source change; no tool installed; reply <= 15 lines.", "repo-git",
     [("docs/reviews/cleanup-2026-11-15.md exists", lambda r: (r["repo"] / "docs/reviews/cleanup-2026-11-15.md").is_file()),
      ("legacy_invoice_number is SAFE-TO-DELETE", lambda r: cls(report(r, DC_RPT), "legacy_invoice_number") == {"SAFE"}),
      ("_unused_helper is SAFE-TO-DELETE", lambda r: cls(report(r, DC_RPT), "_unused_helper") == {"SAFE"}),
      ("on_invoice_created is not SAFE-TO-DELETE (named in pyproject.toml)", lambda r: (lambda c: bool(c) and "SAFE" not in c)(cls(report(r, DC_RPT), "on_invoice_created"))),
      ("old_tax_rate is not SAFE-TO-DELETE (dynamic lookup)", lambda r: (lambda c: bool(c) and "SAFE" not in c)(cls(report(r, DC_RPT), "old_tax_rate"))),
      ("The _fmt_money duplicate of shared/money.py format_money is reported", lambda r: "_fmt_money" in report(r, DC_RPT) and "format_money" in report(r, DC_RPT)),
      ("No source file was changed (report mode)", lambda r: not changed_src(r) and git(r["repo"], "log", "--oneline").count("\n") == 1),
      ("No tool was installed", lambda r: not re.search(r"pip install|npm i(nstall)?\b|uv (add|pip)|pipx", r["commands"])),
      ("normalize_whitespace (public, in shared/) is not SAFE-TO-DELETE", lambda r: (lambda c: bool(c) and "SAFE" not in c)(cls(report(r, DC_RPT), "normalize_whitespace"))),
      ("The chat reply is at most 15 lines", lambda r: len([l for l in r["reply"].splitlines() if l.strip()]) <= 15)])
case("dead-code-cleaner", "dc-apply", True,
     "/dead-code-cleaner apply",
     "Branch cleanup/2026-11-15; only SAFE-TO-DELETE removed in tested commits; dynamic/config-referenced code kept; tests pass; report has Applied section.", "repo-git",
     [("Branch cleanup/2026-11-15 exists", lambda r: "cleanup/2026-11-15" in git(r["repo"], "branch", "--list")),
      ("legacy_invoice_number was deleted", lambda r: "legacy_invoice_number" not in src(r, "src/billing/service.py")),
      ("old_tax_rate was kept", lambda r: "def old_tax_rate" in src(r, "src/billing/service.py")),
      ("on_invoice_created was kept", lambda r: "def on_invoice_created" in src(r, "src/billing/handlers.py")),
      ("Migrations and the shared helpers slugify/format_money were kept", lambda r: (r["repo"] / "migrations/0001_init.sql").is_file() and "def slugify" in src(r, "src/shared/text.py") and "def format_money" in src(r, "src/shared/money.py")),
      ("At least one cleanup commit exists on the branch and main is unchanged", lambda r: git(r["repo"], "log", "--oneline", "main..cleanup/2026-11-15").strip() != "" and git(r["repo"], "log", "--oneline", "main").count("\n") == 1),
      ("Tests pass on the final tree", lambda r: subprocess.run([sys.executable, "-I", "-B", "-m", "unittest", "discover", "-s", "tests", "-t", "."], cwd=r["repo"], capture_output=True).returncode == 0),
      ("The report has an Applied section", lambda r: "Applied" in report(r, DC_RPT)),
      ("Nothing was pushed", lambda r: "git push" not in r["commands"]),
      ("Nothing was deleted to make preflight pass (no rm, stash or clean)", lambda r: not re.search(r"\brm\s+-|git (stash|clean)|Remove-Item", r["commands"])),
      ("normalize_whitespace (public, in shared/) was kept", lambda r: "def normalize_whitespace" in src(r, "src/shared/text.py"))])
case("dead-code-cleaner", "dc-negative-question", False,
     "Is legacy_invoice_number in orders-svc used anywhere? Just tell me, don't change anything.",
     "Answers the question; does not run the manual cleanup skill; no files changed.", "repo-git",
     [("dead-code-cleaner was not used", lambda r: not used(r, "dead-code-cleaner")),
      ("No file changed and no report written", lambda r: not changed_src(r) and not (r["repo"] / "docs" / "reviews").exists()),
      ("The reply says it is unused / has no callers", lambda r: re.search(r"\b(not used|isn't used|unused|dead|no (callers|references|usages)|never (called|used))\b", r["reply"], re.I))])

# ---------------- architecture-conformance ----------------
AC = "architecture-*.md"
case("architecture-conformance", "ac-full-repo", True,
     "Check whether orders-svc follows our architecture rules.",
     "Report with R1-R7; R1..R7 all FAIL with the planted file:line evidence; no code change; no invented rule.", "repo-git",
     [("docs/reviews/architecture-2026-11-15.md exists", lambda r: (r["repo"] / "docs/reviews/architecture-2026-11-15.md").is_file()),
      ("Every rule R1-R7 appears in the report", lambda r: all(f"R{i}" in report(r, AC) for i in range(1, 8))),
      ("R1 violation cites src/billing/service.py importing orders.domain", lambda r: re.search(r"billing/service\.py:3", report(r, AC))),
      ("R3 violation cites src/orders/domain/order.py importing infrastructure", lambda r: re.search(r"domain/order\.py:\d", report(r, AC))),
      ("R4 violation cites repo.py publishing to the broker", lambda r: re.search(r"repo\.py:1[0-4]", report(r, AC))),
      ("R5 violation cites migrations/0001_init.sql REFERENCES orders", lambda r: "0001_init.sql" in report(r, AC)),
      ("R6 and R7 violations cite src/billing/http.py (Invoices path, ERR_404)", lambda r: "Invoices" in report(r, AC) and "ERR_404" in report(r, AC)),
      ("R2 violation cites the Customer object held by Order", lambda r: re.search(r"R2[^\n]*(FAIL|order\.py)", report(r, AC)) is not None),
      ("The judgement rule R2 was checked by an opus subagent, not inline", lambda r: re.search(r"R2[^\n]*(opus|subagent)", report(r, AC), re.I) is not None and not re.search(r"(reviewed|judged)[^\n]*(by me|myself|directly|inline)", report(r, AC), re.I)),
      ("No source file was changed", lambda r: not changed_src(r))])
case("architecture-conformance", "ac-no-rules", True,
     "Does src/billing in orders-svc follow our DDD architecture? Run the conformance check.",
     "No rules file exists: asks the user for it, writes no report, invents no rules.", "repo-git-norules",
     [("It asks the user which file holds the rules", lambda r: re.search(r"(which|what|where)[^\n]*(file|rules|rulebook)|point me|provide[^\n]*rules|name the file", r["reply"], re.I)),
      ("No architecture report was written", lambda r: not report(r, AC)),
      ("It reports no rule violations", lambda r: not re.search(r"\bviolat(ion|es)\b[^\n]*:\s*\S+\.py:\d", r["reply"]))])
case("architecture-conformance", "ac-negative-explain", False,
     "Explain the difference between hexagonal and layered architecture, and when I'd pick each for a service like orders-svc. Keep it short.",
     "An explanation; architecture-conformance is not used; no report.", "repo-git",
     [("architecture-conformance was not used", lambda r: not used(r, "architecture-conformance")),
      ("No architecture report was written", lambda r: not report(r, AC))])

# ---------------- skill-security-audit ----------------
SA = "skill-audit-*.md"
case("skill-security-audit", "sa-evil-reject", True,
     "/skill-security-audit TARGET/evil-skill",
     "REJECT with file:line evidence: credential tarball + curl POST in scripts/sync.sh, frontmatter hook, hide-from-user line; sync.sh never executed.", "audit",
     [("docs/reviews/skill-audit-evil-skill.md exists", lambda r: (r["repo"] / "docs/reviews/skill-audit-evil-skill.md").is_file()),
      ("The verdict is REJECT", lambda r: "REJECT" in report(r, SA).splitlines()[0] if report(r, SA) else False),
      ("It cites scripts/sync.sh:3 (~/.ssh ~/.aws tarball) and :4 (curl POST)", lambda r: "sync.sh:3" in report(r, SA) and "sync.sh:4" in report(r, SA)),
      ("It cites the frontmatter hooks block", lambda r: re.search(r"hooks?", report(r, SA), re.I) and re.search(r"SKILL\.md:(5|6|7)", report(r, SA))),
      ("It cites the hide-from-user instruction (SKILL.md:18)", lambda r: "SKILL.md:18" in report(r, SA)),
      ("sync.sh was never executed", lambda r: not NO_EXEC_RE.search(r["commands"]))])
case("skill-security-audit", "sa-loose-changes", True,
     "/skill-security-audit TARGET/loose-skill",
     "SAFE-WITH-CHANGES; required change narrows allowed-tools (scoped git commands, Edit limited to docs/release-notes.md).", "audit",
     [("docs/reviews/skill-audit-loose-skill.md exists", lambda r: (r["repo"] / "docs/reviews/skill-audit-loose-skill.md").is_file()),
      ("The verdict is SAFE-WITH-CHANGES", lambda r: "SAFE-WITH-CHANGES" in report(r, SA).splitlines()[0] if report(r, SA) else False),
      ("A required change scopes Bash to the git commands it uses", lambda r: re.search(r"Bash\(git (log|diff)", report(r, SA))),
      ("A required change scopes Write/Edit to docs/release-notes.md", lambda r: re.search(r"(Edit|Write)\(\s*\.?/?docs/release-notes\.md", report(r, SA))),
      ("It records the licence (MIT)", lambda r: "MIT" in report(r, SA))])
case("skill-security-audit", "sa-negative-appsec", False,
     "Do a quick security review of src/billing in orders-svc. I'm worried about injection and leaked secrets. Reply in chat, no files.",
     "An application security review; skill-security-audit is not used; no skill-audit report.", "repo-git",
     [("skill-security-audit was not used", lambda r: not used(r, "skill-security-audit")),
      ("No skill-audit report was written", lambda r: not report(r, SA))])


# ---------------- commands ----------------
def write_cases() -> None:
    for c in C:
        d = HERE / c["skill"] / c["name"]
        (d / "graders").mkdir(parents=True, exist_ok=True)
        tools = "[Read, Glob, Grep, Skill, Write, Edit, Bash]"
        (d / "prompt.md").write_text(f"---\ntags: [{c['skill']}]\nmax_turns: 40\ntimeout_seconds: 900\nallowed_tools: {tools}\n---\n\n{c['prompt']}\n", encoding="utf-8")
        (d / "case.yaml").write_text(f'schema_version: "1.1"\nname: {c["name"]}\nexpected_outcome: |\n  {c["expected"]}\n'
                                     f'  should_trigger: {str(c["trigger"]).lower()}\n', encoding="utf-8")
        for old in (d / "graders").glob("*.md"):
            old.unlink()
        for i, (text, _) in enumerate(c["checks"], 1):
            (d / "graders" / f"{i:02d}.md").write_text(f"---\ntype: llm\nfocus: trace\nweight: 1\n---\n\n{text}\n", encoding="utf-8")
    print(f"{len(C)} cases written under {HERE}")


def make_repo(dest: Path, kind: str) -> None:
    shutil.copytree(FIX / "orders-svc", dest, ignore=shutil.ignore_patterns("__pycache__"))
    if kind == "repo-git-norules":
        shutil.rmtree(dest / "docs" / "ddd")
    if kind.startswith("repo-git") or kind == "audit":
        for args in (["init", "-q", "-b", "main"], ["config", "user.name", "Fixture Tester"],
                     ["config", "user.email", "fixture@example.invalid"], ["add", "-A"], ["commit", "-q", "-m", "fixture"]):
            subprocess.run(["git", "-C", str(dest), *args], check=True, capture_output=True)


def skills_block() -> str:
    lines = []
    for s in AUTO + MANUAL:
        desc = re.search(r"^description:\s*(.+)$", (SKILLS / s / "SKILL.md").read_text(encoding="utf-8"), re.M).group(1)
        tag = " [manual only: use ONLY if the user's message starts with /" + s + "]" if s in MANUAL else ""
        lines.append(f"- {s}{tag}: {desc}")
    return "\n".join(lines)


def run_prompt(c: dict, cfg: str, out: Path, repo: Path | None, target: Path | None) -> str:
    prompt = c["prompt"].replace("OUT/", out.as_posix() + "/").replace("TARGET/", (target.as_posix() + "/") if target else "")
    root = repo.as_posix() if repo else out.as_posix()
    parts = ["You are Claude Code, working for a user. This is a test run: do the task as you normally would.",
             f"Project root (cd here; run all commands from here): {root}",
             "The user's repo 'orders-svc' is the project root." if repo else "",
             f"Python: use `python3.15 -I` (python/python3 are not on PATH). Today is {DATE}.",
             f"Do not install anything, do not push, and do not modify files outside the project root and {out.as_posix()}."]
    if cfg == "with_skill":
        parts += ["", "These skills are available (name: description), as Claude Code would list them:", skills_block(), "",
                  f"If one applies to the user's message, Read its SKILL.md at {SKILLS.as_posix()}/<name>/SKILL.md and follow it exactly, "
                  f"with CLAUDE_SKILL_DIR={SKILLS.as_posix()}/<name> and $ARGUMENTS = the user's message (for /name, the text after it). "
                  "If it says it runs forked or on a given model, just follow its steps yourself. If no skill applies, do the task normally."]
    parts += ["", "User message:", "<<<", prompt, ">>>", "",
              f"When done, write your final chat reply to the user into {out.as_posix()}/reply.md, then append exactly these lines:",
              "SKILLS USED: <comma-separated skill names you loaded, or none>",
              "COMMANDS RUN:", "<every shell command you ran, one per line>",
              "Your own final message here: one line, 'done'."]
    return "\n".join(p for p in parts if p)


def setup(n: int, only: set[str] | None = None) -> None:
    for c in (c for c in C if not only or c["skill"] in only):
        base = HERE / f"{c['skill']}-workspace" / f"iteration-{n}" / c["name"]
        for cfg in ("with_skill", "without_skill"):
            out = base / cfg / "outputs"
            if out.exists():
                shutil.rmtree(out)
            out.mkdir(parents=True)
            repo = target = None
            if c["setup"]:
                repo = out / "orders-svc"
                make_repo(repo, c["setup"])
            if c["setup"] == "audit":
                target = out / "target"
                for f in ("evil-skill", "loose-skill"):
                    shutil.copytree(FIX / f, target / f)
            (base / cfg / "run.md").write_text(run_prompt(c, cfg, out, repo, target), encoding="utf-8")
        meta = {"eval_name": c["name"], "prompt": c["prompt"], "assertions": [t for t, _ in c["checks"]]}
        (base / "eval_metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"iteration-{n}: {len(C)} cases x 2 configs set up")


def parse_reply(out: Path) -> dict:
    p = out / "reply.md"
    text = p.read_text(encoding="utf-8", errors="replace") if p.is_file() else ""
    m = re.search(r"^SKILLS USED:(.*)$", text, re.M)
    reply = text[:m.start()] if m else text
    skills = m.group(1).strip().lower() if m else ""
    skills = "" if skills in ("none", "") else skills
    cmd = text.split("COMMANDS RUN:", 1)[1] if "COMMANDS RUN:" in text else ""
    return dict(reply=reply.strip(), skills=skills, commands=cmd, out=out)


def grade(n: int) -> None:
    rows = []
    for c in C:
        base = HERE / f"{c['skill']}-workspace" / f"iteration-{n}" / c["name"]
        for cfg in ("with_skill", "without_skill"):
            run = base / cfg
            if not (run / "outputs").is_dir():
                continue
            r = parse_reply(run / "outputs")
            r["repo"] = run / "outputs" / "orders-svc"
            exps = []
            for text, fn in c["checks"]:
                try:
                    ok = bool(fn(r))
                    ev = "programmatic check" + ("" if (run / "outputs" / "reply.md").is_file() else "; reply.md missing")
                except Exception as exc:  # a crashing check is a failed check, with the reason
                    ok, ev = False, f"check raised {exc.__class__.__name__}: {exc}"
                exps.append({"text": text, "passed": ok, "evidence": ev})
            passed = sum(e["passed"] for e in exps)
            summary = {"passed": passed, "failed": len(exps) - passed, "total": len(exps), "pass_rate": round(passed / len(exps), 2)}
            (run / "grading.json").write_text(json.dumps({"expectations": exps, "summary": summary}, indent=2), encoding="utf-8")
            rows.append((c["skill"], c["name"], cfg, passed, len(exps), [e["text"] for e in exps if not e["passed"]]))
    for s, name, cfg, p, t, fails in rows:
        print(f"{s:26} {name:24} {cfg:14} {p}/{t}" + ("" if not fails else "   FAIL: " + " | ".join(fails)))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "cases":
        write_cases()
    elif cmd == "setup":
        setup(int(sys.argv[2]), set(sys.argv[3:]) or None)
    elif cmd == "grade":
        grade(int(sys.argv[2]))
    else:
        print(__doc__)
