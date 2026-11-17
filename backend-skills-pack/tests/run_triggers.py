"""Trigger tests: does each skill fire on its 2 'yes' prompts and stay quiet on its 'no' prompt?

Usage: python -I tests/run_triggers.py <project-dir> [--model sonnet] [--jobs 6] [--only a,b]
                                       [--out tests/results/triggers.md]
<project-dir> is a template holding ONLY this pack in .claude/ (scripts/install.sh --project <dir> --apply).
Each case runs in its own temporary copy of it, deleted afterwards.
Each case is a fresh headless session: claude -p <prompt> --setting-sources project, so user
skills, user plugins and user settings are not loaded. Only the Skill tool is pre-approved;
every other tool call is denied, except what an invoked skill's own allowed-tools pre-approve
(for example dead-code-cleaner may write docs/reviews/ inside the throwaway project). No network tool.
A session that ends in an API error (usage limit, overload) is reported as ERROR, not as a verdict.
Raw stream-json logs go to _work/tmp/trigger-logs/ (gitignored).
Triggered = a Skill tool call for that skill, an Agent call to an agent that preloads it, or
(for /name prompts) the slash command expanding to that skill.
Standard library only. Spawns the claude CLI, which is billed.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import tempfile
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

PACK = Path(__file__).resolve().parent.parent
CASES = PACK / "tests" / "triggers.json"
TIMEOUT_S = 300
MAX_TURNS = 4


def preloads() -> dict[str, set[str]]:
    """agent name -> skills it preloads (from agents/*.md frontmatter)."""
    out = {}
    for f in (PACK / "agents").glob("*.md"):
        fm = f.read_text(encoding="utf-8").split("---")[1]
        out[f.stem] = set(re.findall(r"^\s*-\s*([a-z0-9-]+)\s*$", fm, re.M))
    return out


LOGS = PACK / "_work" / "tmp" / "trigger-logs"


def run_case(template: Path, model: str, prompt: str, log_name: str) -> list[dict]:
    """Run one case in its own fresh copy of the template project, so no case sees another's writes."""
    with tempfile.TemporaryDirectory(prefix=f"trig-{log_name}-") as tmp:
        project = Path(tmp) / "proj"
        shutil.copytree(template, project, ignore=shutil.ignore_patterns(".backend-skills-pack-backup"))
        return run_in(project, model, prompt, log_name)


def run_in(project: Path, model: str, prompt: str, log_name: str) -> list[dict]:
    # stream-json input + --replay-user-messages makes a /name expansion visible as <command-name>.
    cmd = ["claude", "-p", "--input-format", "stream-json", "--output-format", "stream-json",
           "--verbose", "--replay-user-messages", "--model", model, "--setting-sources", "project",
           "--max-turns", str(MAX_TURNS), "--allowedTools", "Skill"]
    message = json.dumps({"type": "user", "message": {"role": "user", "content": prompt}})
    try:
        res = subprocess.run(cmd, cwd=project, input=message + chr(10), capture_output=True, text=True,
                             encoding="utf-8", timeout=TIMEOUT_S)
        lines = res.stdout.splitlines()
    except subprocess.TimeoutExpired as exc:
        lines = (exc.stdout or "").splitlines() if isinstance(exc.stdout, str) else []
    LOGS.mkdir(parents=True, exist_ok=True)
    (LOGS / f"{log_name}.jsonl").write_text(chr(10).join(lines), encoding="utf-8")
    events = []
    for ln in lines:
        try:
            events.append(json.loads(ln))
        except json.JSONDecodeError:
            continue
    return events


def api_error(events: list[dict]) -> str:
    """The error text when the session never got a model answer, else ''. Max turns is not an error."""
    for e in events:
        if e.get("type") == "result" and e.get("is_error") and e.get("subtype") != "error_max_turns":
            return str(e.get("result", "error"))[:60]
    return "" if any(e.get("type") == "result" for e in events) else "no result (timeout?)"


def fired(events: list[dict], skill: str, agent_skills: dict[str, set[str]]) -> tuple[bool, str]:
    seen = []
    for e in events:
        msg = e.get("message")
        content = msg.get("content") if isinstance(msg, dict) else msg
        content = content or []
        if isinstance(content, str):
            content = [{"type": "text", "text": content}]
        for c in content:
            if not isinstance(c, dict):
                continue
            if c.get("type") == "tool_use" and c.get("name") == "Skill":
                name = str((c.get("input") or {}).get("skill", "")).split(":")[-1]
                seen.append(f"Skill({name})")
            elif c.get("type") == "tool_use" and c.get("name") in ("Agent", "Task"):
                agent = str((c.get("input") or {}).get("subagent_type", ""))
                seen.append(f"Agent({agent})")
            elif e.get("type") == "user" and c.get("type") == "text":
                m = re.search(r"<command-name>/?([a-z0-9:-]+)</command-name>", c.get("text", ""))
                if m:
                    seen.append(f"/{m.group(1).split(':')[-1]}")
    hit = any(s in (f"Skill({skill})", f"/{skill}") or
              (s.startswith("Agent(") and skill in agent_skills.get(s[6:-1], set())) for s in seen)
    return hit, ", ".join(seen) or "-"


def judge(events: list[dict], skill: str, agent_skills: dict[str, set[str]]) -> tuple[bool, str, str]:
    hit, seen = fired(events, skill, agent_skills)
    return hit, seen, api_error(events)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--jobs", type=int, default=6)
    ap.add_argument("--only", default="")
    ap.add_argument("--out", default=str(PACK / "tests" / "results" / "triggers.md"))
    a = ap.parse_args(argv)
    project = Path(a.project).resolve()
    cases = {k: v for k, v in json.loads(CASES.read_text(encoding="utf-8")).items() if not k.startswith("_")}
    if a.only:
        cases = {k: v for k, v in cases.items() if k in a.only.split(",")}
    jobs = [(s, kind, p, f"{s}-{i}-{kind}") for s, c in cases.items() for i, (kind, p) in
            enumerate([("yes", c["yes"][0]), ("yes", c["yes"][1]), ("no", c["no"])], 1)]
    agent_skills = preloads()
    with ThreadPoolExecutor(max_workers=a.jobs) as pool:
        results = list(pool.map(lambda j: (j, judge(run_case(project, a.model, j[2], j[3]), j[0], agent_skills)), jobs))
    rows, fails, errors = [], 0, 0
    for (skill, kind, prompt, _), (hit, seen, err) in results:
        ok = hit == (kind == "yes")
        verdict = "ERROR" if err and not hit else ("PASS" if ok else "FAIL")
        fails += verdict == "FAIL"
        errors += verdict == "ERROR"
        short = prompt if len(prompt) <= 90 else prompt[:87] + "..."
        rows.append(f"| {skill} | {kind} | {verdict} | {err or seen} | {short.replace('|', '/')} |")
    head = [f"# Trigger tests ({a.model}, --setting-sources project, only the pack installed)", "",
            f"Cases: {len(results)}. Failures: {fails}. Errors (no verdict): {errors}.", "",
            "| Skill | Expect | Result | Invoked | Prompt |", "|---|---|---|---|---|"]
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text("\n".join(head + rows) + "\n", encoding="utf-8")
    print("\n".join(head + rows))
    return 1 if fails or errors else 0


if __name__ == "__main__":
    sys.exit(main())
