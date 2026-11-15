"""Score every inventoried skill against each need from name + description only.

Usage: python -I scripts/score_needs.py [--inventory _work/inventory.csv] [--out _work/need_scores.csv] [--top 8]
Keyword lists are PROPOSED heuristics (not sourced); scores only rank candidates for human reading.
Name hits weigh 3, description hits 1. Standard library only. No network.
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

PACK = Path(__file__).resolve().parent.parent

NEEDS: dict[str, list[str]] = {
    "reuse-first/library-search": ["search-first", "reuse", "existing implementation", "library", "package registr", "before writing", "prior art", "skill-scout", "find-skills", "documentation-lookup"],
    "model-routing": ["model rout", "model-route", "model selection", "haiku", "sonnet", "opus", "cost-aware", "token budget", "route"],
    "dead/duplicate-code-cleanup": ["dead code", "unused", "duplicate", "refactor-clean", "cleanup", "knip", "prune", "simplif", "consolidat"],
    "architecture-conformance-review": ["architecture", "conformance", "layer", "dependency rule", "hexagonal", "clean architecture", "module-governance", "boundar", "drift"],
    "project-understanding-from-prototype": ["onboarding", "codebase", "understand", "prototype", "brownfield", "spec-min", "codemap", "explore", "map the"],
    "ddd-strategic": ["domain-driven", "ddd", "bounded context", "context map", "ubiquitous language", "subdomain", "strategic design"],
    "ddd-tactical": ["aggregate", "entity", "entities", "value object", "domain event", "repository", "ddd", "invariant"],
    "database-design/erd": ["database", "schema", "erd", "data model", "data-model", "normaliz", "postgres", "migration", "table"],
    "uml-usecase/db-diagrams": ["diagram", "mermaid", "plantuml", "uml", "use case", "use-case", "sequence diagram", "erd"],
    "rest/openapi-design": ["rest", "openapi", "endpoint", "api design", "api-design", "contract-first", "swagger", "status code"],
    "design-review/bug-finding": ["design review", "bug", "find bugs", "defect", "incident", "failure", "audit", "edge case", "silent fail"],
    "requirements-gap-analysis": ["requirement", "gap", "prd", "spec", "acceptance criteria", "user stor", "missing feature", "product-capability"],
    "docs/file-organisation": ["documentation", "docs", "readme", "file organi", "codemap", "living-docs", "docs-governance", "adr"],
    "skill-authoring": ["skill-creator", "create skill", "writing skill", "skill author", "new skill", "skill-create", "description for better trigger", "skill"],
    "multi-agent-orchestration": ["multi-agent", "orchestrat", "subagent", "parallel agent", "dispatch", "team", "fleet", "agents"],
    "testing/verification": ["test", "tdd", "verification", "verify", "coverage", "e2e", "regression"],
    "code-review": ["code review", "code-review", "review the", "pull request", "pr review", "reviewer", "diff"],
}


def score(text_name: str, text_desc: str, kws: list[str]) -> int:
    s = 0
    for kw in kws:
        k = kw.lower()
        if k in text_name:
            s += 3
        s += len(re.findall(re.escape(k), text_desc))
    return s


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--inventory", default=str(PACK / "_work" / "inventory.csv"))
    ap.add_argument("--out", default=str(PACK / "_work" / "need_scores.csv"))
    ap.add_argument("--top", type=int, default=8)
    a = ap.parse_args(argv)
    rows = list(csv.DictReader(open(a.inventory, encoding="utf-8")))
    out = []
    for need, kws in NEEDS.items():
        scored = []
        for r in rows:
            s = score(r["name"].lower(), r["description"].lower(), kws)
            if s:
                scored.append((s, r))
        scored.sort(key=lambda x: (-x[0], int(x[1]["description_chars"])))
        for rank, (s, r) in enumerate(scored[: a.top], 1):
            out.append([need, rank, s, r["name"], r["source"], r["group"], r["description_chars"], r["path"]])
    with open(a.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["need", "rank", "score", "name", "source", "group", "description_chars", "path"])
        w.writerows(out)
    for row in out:
        print(*row[:7], sep=" | ")
    return 0


if __name__ == "__main__":
    sys.exit(main())
