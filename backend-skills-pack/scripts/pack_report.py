"""Write MANIFEST.json and TOKEN-REPORT.md for the pack.

Usage: python -I scripts/pack_report.py
Reads skills/*/SKILL.md and agents/*.md frontmatter, _work/inventory.csv (the baseline of every
installed SKILL.md, from scripts/inventory.py) and the PROVENANCE table below.
Cost of one skill = (len(name) + len(description)) / 4 tokens, the same rule as _work/baseline.txt.
Standard library only. No network.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import skillmeta as sm  # noqa: E402

PACK = sm.PACK
ECC = ("github.com/affaan-m/ECC v2.2.3 (installed copy)", "none: no pinned clone (AUDIT.md, Not verified)", "MIT")
SUPERPOWERS = "github.com/obra/superpowers", "22f0b463e7a5e579904dd6211a520321035526f7", "MIT"
# name: (origin, upstream skill(s), repo, sha, licence, audit verdict)
PROVENANCE = {
    "api-endpoints": ("adapted", "api-design + contract-first", *ECC, "SAFE"),
    "architecture-conformance": ("mine", "-", "-", "-", "yours (no licence file)", "own; pack gate"),
    "backend-design-team": ("mine", "-", "-", "-", "yours (no licence file)", "own; pack gate"),
    "db-design-erd": ("adapted", "data-modeling-discipline", "backend-design plugin v0.2.0 by sheitabrk (installed copy)",
                      "none: no pinned clone (SELECTION decision 1)", "MIT", "SAFE"),
    "ddd-strategic": ("mine", "-", "-", "-", "yours (no licence file)", "own; pack gate"),
    "ddd-tactical": ("mine", "-", "-", "-", "yours (no licence file)", "own; pack gate"),
    "dead-code-cleaner": ("mine", "-", "-", "-", "yours (no licence file)", "own; pack gate"),
    "design-diagrams": ("mine", "-", "-", "-", "yours (no licence file)", "own; pack gate"),
    "design-docs-organizer": ("adapted", "living-docs-governance", *ECC, "SAFE"),
    "design-review-fix": ("adapted", "ponytail-audit (+ intent-driven-development, yours)", "github.com/DietrichGebert/ponytail",
                          "96608e078b2d5ea607c5c3b8b5a54d1c1fba6846", "MIT", "SAFE-WITH-CHANGES"),
    "dispatching-parallel-agents": ("adapted", "dispatching-parallel-agents", *SUPERPOWERS, "SAFE"),
    "model-router": ("mine", "-", "-", "-", "yours (no licence file)", "own; pack gate"),
    "project-understanding": ("adapted", "codebase-onboarding (+ intent-driven-development, yours)", *ECC, "SAFE"),
    "reuse-first": ("adapted", "search-first", *ECC, "SAFE"),
    "skill-creator": ("adopted", "skill-creator", "github.com/anthropics/skills",
                      "1780c5e5a552fd4d1c9d6a7b0cab26b0c2bef064", "Apache-2.0", "SAFE-WITH-CHANGES"),
    "skill-security-audit": ("mine", "-", "-", "-", "yours (no licence file)", "own; pack gate"),
    "test-driven-development": ("adapted", "test-driven-development", *SUPERPOWERS, "SAFE"),
    "verification-before-completion": ("adopted", "verification-before-completion", *SUPERPOWERS, "SAFE"),
}


def meta(path: Path) -> dict[str, str]:
    fm_text, _ = sm.split_frontmatter(path.read_text(encoding="utf-8"))
    return sm.parse_frontmatter(fm_text)


def cost(name: str, desc: str) -> tuple[int, int]:
    chars = len(name) + len(" ".join(desc.split()))
    return chars, chars // 4


def pack_rows() -> list[dict]:
    rows = []
    for d in sorted(p for p in (PACK / "skills").iterdir() if (p / "SKILL.md").is_file()):
        fm = meta(d / "SKILL.md")
        chars, tokens = cost(fm["name"], fm.get("description", ""))
        origin, upstream, repo, sha, lic, verdict = PROVENANCE[d.name]
        rows.append({"name": fm["name"], "origin": origin, "upstream_skill": upstream, "source": repo, "sha": sha,
                     "licence": lic, "audit_verdict": verdict, "model": fm.get("model", ""),
                     "manual_only": fm.get("disable-model-invocation", "").lower() == "true",
                     "description_chars": chars, "description_tokens": tokens})
    return rows


def agent_rows() -> list[dict]:
    rows = []
    for f in sorted((PACK / "agents").glob("*.md")):
        fm = meta(f)
        chars, tokens = cost(fm["name"], fm.get("description", ""))
        rows.append({"name": fm["name"], "model": fm.get("model", ""), "preloads": fm.get("skills", ""),
                     "description_chars": chars, "description_tokens": tokens})
    return rows


def baseline() -> tuple[list[dict], list[dict]]:
    with open(PACK / "_work" / "inventory.csv", encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader(fh) if r["source"] != "quarantine"]
    manual = [r for r in rows if r["disable_model_invocation"].lower() == "true"]
    return rows, manual


def chars_of(rows: list[dict]) -> int:
    return sum(len(r["name"]) + int(r["description_chars"]) for r in rows)


def report(skills: list[dict], agents: list[dict]) -> str:
    base, base_manual = baseline()
    b_chars = chars_of(base)
    b_auto_chars = b_chars - chars_of(base_manual)
    p_chars = sum(r["description_chars"] for r in skills)
    p_auto = [r for r in skills if not r["manual_only"]]
    p_auto_chars = sum(r["description_chars"] for r in p_auto)
    a_chars = sum(r["description_chars"] for r in agents)

    def pct(new: int, old: int) -> str:
        return f"{100 * (old - new) / old:.1f}%"

    out = ["# Token report", "",
           "Always-loaded cost = the name and description of every skill, which Claude Code lists in the context of "
           "every session. Tokens are estimated as characters / 4, the same rule as `_work/baseline.txt`. "
           "Generated by `scripts/pack_report.py`; do not edit by hand.", "",
           "## Totals", "",
           "| Set | Skills | Chars | ~Tokens | Saved vs baseline |", "|---|---|---|---|---|",
           f"| Baseline: everything installed (yours + plugins), counted as in baseline.txt | {len(base)} | {b_chars} | {b_chars // 4} | - |",
           f"| Baseline without its {len(base_manual)} manual-only skills | {len(base) - len(base_manual)} | {b_auto_chars} | {b_auto_chars // 4} | - |",
           f"| Pack, all {len(skills)} skills (upper bound) | {len(skills)} | {p_chars} | {p_chars // 4} | {pct(p_chars, b_chars)} |",
           f"| **Pack, auto-invocable skills only (what is listed)** | {len(p_auto)} | {p_auto_chars} | **{p_auto_chars // 4}** | **{pct(p_auto_chars, b_chars)}** |",
           f"| Pack agents (subagent descriptions, listed separately) | {len(agents)} | {a_chars} | {a_chars // 4} | n/a |",
           f"| **Pack, auto skills + agents** | {len(p_auto)} + {len(agents)} | {p_auto_chars + a_chars} | **{(p_auto_chars + a_chars) // 4}** | **{pct(p_auto_chars + a_chars, b_chars)}** |",
           "", "## Per skill", "",
           "| Skill | Origin | Model | Manual only | Chars | ~Tokens | Listed every session |", "|---|---|---|---|---|---|---|"]
    for r in skills:
        out.append(f"| {r['name']} | {r['origin']} | {r['model']} | {'yes' if r['manual_only'] else 'no'} | "
                   f"{r['description_chars']} | {r['description_tokens']} | {'no' if r['manual_only'] else 'yes'} |")
    out += ["", "## Per agent", "", "| Agent | Model | Preloads | Chars | ~Tokens |", "|---|---|---|---|---|"]
    out += [f"| {r['name']} | {r['model']} | {r['preloads']} | {r['description_chars']} | {r['description_tokens']} |"
            for r in agents]
    return "\n".join(out) + "\n"


def main() -> int:
    skills, agents = pack_rows(), agent_rows()
    missing = sorted({p.name for p in (PACK / "skills").iterdir() if p.is_dir()} - set(PROVENANCE))
    if missing:
        print("no PROVENANCE entry for: " + ", ".join(missing), file=sys.stderr)
        return 1
    manifest = {"pack": "backend-skills-pack", "token_rule": "(len(name) + len(description)) / 4",
                "skills": skills, "agents": agents}
    (PACK / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    text = report(skills, agents)
    notes = PACK / "tests" / "token-report-notes.md"
    if notes.is_file():
        text += "\n" + notes.read_text(encoding="utf-8")
    (PACK / "TOKEN-REPORT.md").write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
