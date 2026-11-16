"""Grade the design-team test runs (tests a, b, c). Standard library only.

Usage (python3 -I):
  grade_runs.py fixture <out-dir> a|b      completeness, limits, lint, organize check, profile + rule
                                           adherence, and leak check against the other fixture
  grade_runs.py defects <07-review.md> <defects.json>   did the review find each planted defect?
Exit 1 if any check fails.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

PACK = Path(__file__).resolve().parent.parent
CHECK = PACK / "skills" / "backend-design-team" / "scripts" / "design_check.py"
ORGANIZE = PACK / "skills" / "design-docs-organizer" / "scripts" / "organize.py"
# Words that belong to one fixture's domain or stack and must not appear in the other's output.
LEAK = {
    "a": r"\blibrar(y|ian)s?\b|\bbooks?\b|\bloans?\b|\bborrow\w*|\bshelfmark\b|\bisbn\b|\bfines?\b|"
         r"\bpostgres(ql)?\b|\bnestjs\b|\btypescript\b|\buuidv7\b|problem\+json|rfc ?9457|```mermaid|\bopenapi\b",
    "b": r"\bskus?\b|\bwarehouses?\b|\bstockroom\b|\breorder\w*|\bbins?\b|\bgrpc\b|\bplantuml\b|@startuml|"
         r"\bulids?\b|\bnats\b|\bjetstream\b|\bmariadb\b|\bproto\b|errorinfo",
}
RESULTS: list[tuple[bool, str, str]] = []


def ok(cond: bool, name: str, detail: str = ""):
    RESULTS.append((bool(cond), name, detail))


def text_of(out: Path, pattern: str) -> str:
    return "\n".join(p.read_text(encoding="utf-8") for p in sorted(out.rglob(pattern)))


def run(*args) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-I", *map(str, args)], capture_output=True, text=True)


def grade_fixture(out: Path, which: str) -> None:
    need = {"README.md": "README.md", "project-profile.md": "project-profile.md", "00-state.md": "00-state.md",
            "brief": "brief/00-project-brief.md", "strategic": "strategic/01-strategic.md",
            "tactical": "tactical/02-tactical-*.md", "db": "data/03-db-design*.md", "erd": "data/04-erd*.md",
            "diagrams": "diagrams/05-diagrams*.md", "api": "api/06-api*.md", "review": "review/07-review.md"}
    for name, pat in need.items():
        ok(any(out.glob(pat)), f"present in final folder: {pat}")
    md = [p for p in out.rglob("*.md")]
    long = [f"{p.name}:{len(p.read_text(encoding='utf-8').splitlines())}" for p in md
            if len(p.read_text(encoding="utf-8").splitlines()) > 300]
    ok(not long, "every artifact <= 300 lines", ", ".join(long))
    lint = run(CHECK, "lint", out)
    first = lint.stdout.splitlines()[0] if lint.stdout else lint.stderr[:200]
    ok(lint.returncode == 0, "design_check lint: no High findings", first)
    org = run(ORGANIZE, "check", out)
    ok(org.returncode == 0, "organize check (links, nothing lost, README index)", org.stdout.strip()[:300])
    state = (out / "00-state.md").read_text(encoding="utf-8") if (out / "00-state.md").is_file() else ""
    rows = re.findall(r"^\| (\d)(?:\.\S*)? \| [^|]+\| (\w+)", state, re.M)
    ok(rows and all(s == "passed" for _, s in rows), "state: every phase passed", str(rows))
    erd, dia, api, db = (text_of(out, p) for p in ("04-erd*.md", "05-diagrams*.md", "06-api*.md", "03-db-design*.md"))
    prof = (out / "project-profile.md").read_text(encoding="utf-8")
    if which == "a":
        ok("```mermaid" in erd + dia and "@startuml" not in erd + dia, "profile: diagrams are Mermaid only")
        ok(re.search(r"\b(GET|POST|PUT|PATCH|DELETE) /", api), "profile: REST operations")
        ok(any(out.rglob("06-api*.y*ml")) or any(out.rglob("06-api*.json")), "profile: OpenAPI contract file written")
        ok(re.search(r"problem\+json|9457", api, re.I), "profile: error format problem+json")
        ok(re.search(r"uuid ?v?7", db, re.I), "profile: UUIDv7 ids")
        ok(re.search(r"outbox", db, re.I), "profile: outbox tables (events used)")
    else:
        ok("@startuml" in erd + dia and "```mermaid" not in erd + dia, "profile: diagrams are PlantUML only")
        ok(re.search(r"\brpc \w+", api), "profile: gRPC operations")
        ok(any(out.rglob("06-api*.proto")), "profile: .proto contract file written")
        ok(re.search(r"ErrorInfo", api) and re.search(r"\b[A-Z]+(_[A-Z]+)+\b", api), "profile/R3: ErrorInfo + UPPER_SNAKE reasons")
        ok(re.search(r"\bulid\b", db, re.I), "profile/R2: ULID ids")
        tables = re.findall(r"^###\s+Table:\s*`?([\w.]+)", db, re.M)
        bad = [t for t in tables if not re.match(r"^(\w+\.)?[a-z]{3}_\w+$", t)]
        ok(tables and not bad, "R1 override: every table has a 3-letter module prefix", f"{len(tables)} tables, bad={bad}")
        schemas = set(re.findall(r"^\|\s*\w+\s*\|\s*\w+\s*\|\s*`?(\w+)`?\s*\|", db.split("## Tables")[0], re.M)) - {"Module", "---"}
        ok(re.search(r"\bstockroom\b", db) and "R1" in db, "R1 override: one shared schema, R1 cited in 03", str(schemas))
        ok(re.search(r"DB-02", prof) and re.search(r"R1", prof), "R1 override recorded in profile Rule overrides")
        ok(re.search(r"stockroom\.\w+\.\w+", text_of(out, "*.md")), "R4: NATS subject format stockroom.<module>.<event>")
    other = "b" if which == "a" else "a"
    hits = []
    for p in out.rglob("*"):
        if p.is_file() and p.suffix in {".md", ".yaml", ".yml", ".json", ".proto", ".graphql"}:
            for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
                for m in re.finditer(LEAK[other], line, re.I):
                    hits.append(f"{p.relative_to(out).as_posix()}:{n} {m.group(0)!r}")
    ok(not hits, f"no fixture-{other.upper()} terms leak into fixture-{which.upper()} output", "; ".join(hits[:12]))


def grade_defects(review: Path, spec: Path) -> None:
    text = review.read_text(encoding="utf-8")
    rows = [ln for ln in text.splitlines() if re.match(r"^\|\s*F\d+\s*\|", ln)]
    for d in json.loads(spec.read_text(encoding="utf-8")):
        found = [r for r in rows if all(re.search(alt, r, re.I) for alt in d["match_all"])]
        ok(found, f"defect {d['id']} found: {d['what']}", found[0][:220] if found else "no matching finding row")


def main(argv: list[str]) -> int:
    if len(argv) == 3 and argv[0] == "fixture":
        grade_fixture(Path(argv[1]).resolve(), argv[2])
    elif len(argv) == 3 and argv[0] == "defects":
        grade_defects(Path(argv[1]), Path(argv[2]))
    else:
        print(__doc__)
        return 2
    for passed, name, detail in RESULTS:
        print(f"{'PASS' if passed else 'FAIL'}  {name}" + (f"  [{detail}]" if detail and not passed else ""))
    print(f"\n{sum(r[0] for r in RESULTS)}/{len(RESULTS)} checks passed")
    return 0 if all(r[0] for r in RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
