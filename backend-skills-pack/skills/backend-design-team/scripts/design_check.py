"""Deterministic gate and lint checks for a backend design folder.

Usage (python3 -I, standard library only, no network, read-only except --write):
  design_check.py gate <out> <phase>     phase 0..7: structure + scriptable rules for that phase
  design_check.py lint <out> [--write]   all cross-artifact checks; --write saves <out>/07-lint.md
Exit 1 when any High finding exists, else 0. Output: a markdown findings table.

Artifacts are found anywhere under <out> by name (so checks still work after phase 8 moves them):
  project-profile.md, 00-project-brief.md, 01-strategic*.md, 02-tactical-*.md, 03-db-design*.md,
  04-erd*.md, 05-diagrams*.md, 06-api*.md, 07-review.md.
Table formats are defined in the phase skills. Tables are read by heading keyword and column
keyword, case-insensitive, so extra columns are fine.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

MAX_LINES = 300
HEADER = ("## inputs", "## decisions", "## open questions")
PROFILE_FIELDS = ["project_name", "prototype", "language_framework", "database", "api_style",
                  "api_contract_file", "architecture_style", "events_messaging", "id_convention",
                  "naming_convention", "error_format", "diagram_format", "output_folder",
                  "project_rules_file", "version_control"]
IRREGULAR = {"held", "sent", "paid", "made", "built", "taken", "given", "lost", "found", "written",
             "done", "set", "put", "cut", "read", "left", "won", "begun", "chosen", "frozen", "spent",
             "sold", "bought", "brought", "kept", "lent", "met", "run", "shut", "split", "told",
             "withdrawn", "drawn", "shown", "known", "grown", "thrown", "overdue", "due", "become",
             "come", "gone", "seen", "out", "low", "full"}
REQ_RE = re.compile(r"\bREQ-\d+\b")
FIND: list[tuple] = []  # (severity, rule, path, line, message)
NORM = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())  # noqa: E731


def add(sev, rule, path, line, msg):
    FIND.append((sev, rule, path, line, msg))


# ---------------------------------------------------------------- parsing
def files(out: Path, pattern: str) -> list[Path]:
    return sorted(p for p in out.rglob(pattern)
                  if not any(s.startswith(".") for s in p.relative_to(out).parts))


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def tables(text: str):
    """Yield (heading, headers, [(lineno, cells)]) for every markdown table."""
    lines, heading, i = text.splitlines(), "", 0
    while i < len(lines):
        ln = lines[i]
        if ln.lstrip().startswith("#"):
            heading = ln.strip("# ").strip()
        if ln.strip().startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|?\s*:?-{2,}", lines[i + 1]):
            headers, rows, j = [h.lower() for h in cells(ln)], [], i + 2
            while j < len(lines) and lines[j].strip().startswith("|"):
                rows.append((j + 1, cells(lines[j])))
                j += 1
            yield heading, headers, rows
            i = j
            continue
        i += 1


def table(text, *keywords):
    for heading, headers, rows in tables(text):
        if any(k in heading.lower() for k in keywords):
            return headers, rows
    return None


def col(headers, row, *keywords):
    for k in keywords:
        for idx, h in enumerate(headers):
            if k in h and idx < len(row):
                return row[idx]
    return ""


def names(cell: str) -> list[str]:
    cell = re.sub(r"<br\s*/?>", ",", cell)
    parts = (re.sub(r"\(.*?\)", "", p).strip(" `*_") for p in re.split(r"[,;]", cell))
    return [p for p in parts if p and p.lower() not in {"-", "—", "none", "n/a"}]


def ident(cell: str) -> str:
    m = re.search(r"([A-Za-z][A-Za-z0-9_]*)", (cell or "").replace("`", ""))
    return m.group(1) if m else ""


def last_word(name: str) -> str:
    words = re.findall(r"[A-Z][a-z0-9]*|[a-z0-9]+", name)
    return words[-1].lower() if words else ""


def is_policy(trigger: str) -> bool:
    return trigger.replace(" ", "").replace("`", "").lower().startswith("policy:")


# ---------------------------------------------------------------- model
class Design:
    def __init__(self, out: Path):
        self.out, self.profile = out, {}
        prof = files(out, "project-profile.md")
        if prof:
            for _, headers, rows in tables(read(prof[0])):
                if headers and "field" in headers[0]:
                    for _, row in rows:
                        self.profile[row[0].strip("` *").lower()] = (
                            row[1] if len(row) > 1 else "", row[2] if len(row) > 2 else "")
                    break
        self.reqs, self.out_of_scope = {}, set()
        for p in files(out, "00-project-brief.md"):
            t = table(read(p), "requirement")
            for ln, row in (t[1] if t else []):
                for r in REQ_RE.findall(row[0]):
                    self.reqs[r] = (p, ln)
        self.aggs, self.cmds, self.events, self.policies, self.queries = {}, {}, {}, {}, {}
        for p in files(out, "02-tactical-*.md"):
            self._tactical(p)
        for p in files(out, "*.md"):
            for heading, _, rows in tables(read(p)):
                if "out of scope" in heading.lower():
                    for _, row in rows:
                        self.out_of_scope |= set(REQ_RE.findall(" ".join(row)))

    def _tactical(self, p):
        text, ctx = read(p), p.stem.replace("02-tactical-", "")
        specs = (("agg", self.aggs, ("aggregate",)), ("cmd", self.cmds, ("command",)),
                 ("evt", self.events, ("event",)), ("pol", self.policies, ("polic",)),
                 ("qry", self.queries, ("quer", "read model")))
        for key, store, kws in specs:
            t = table(text, *kws)
            if not t:
                if key != "pol":
                    add("High", "DOC-01", p, 1, f"no table under a heading containing '{kws[0]}'")
                continue
            headers, rows = t
            for ln, row in rows:
                name = ident(row[0])
                if name and name.lower() not in {"none", "n", "na"}:
                    store[name] = dict(ctx=ctx, file=p, line=ln, headers=headers, row=row)


def get(rec, *kw):
    return col(rec["headers"], rec["row"], *kw)


# ---------------------------------------------------------------- checks
def check_header(p: Path):
    text = read(p)
    for h in HEADER:
        if h not in text.lower():
            add("High", "DOC-01", p, 1, f"missing section '{h[3:]}'")
    n = len(text.splitlines())
    if n > MAX_LINES:
        add("High", "DOC-01", p, n, f"{n} lines > {MAX_LINES}: split by context or module")


def check_profile(d: Design):
    prof = files(d.out, "project-profile.md")
    if not prof:
        return add("High", "PROFILE", d.out, 0, "project-profile.md not found")
    for f in PROFILE_FIELDS:
        val, src = d.profile.get(f, ("", ""))
        if not val.strip() or val.strip() in {"?", "-", "TBD"} or "missing" in src.lower():
            add("High", "PROFILE", prof[0], 0, f"field '{f}' has no confirmed value")
    briefs = files(d.out, "00-project-brief.md")
    if not briefs:
        return add("High", "PROFILE", d.out, 0, "00-project-brief.md not found")
    check_header(briefs[0])
    if not d.reqs:
        add("High", "REV-03", briefs[0], 1, "no REQ-n rows in a Requirements table")


def check_strategic(d: Design):
    fs = files(d.out, "01-strategic*.md")
    if not fs:
        add("High", "DOC-01", d.out, 0, "01-strategic.md not found")
        return ""
    text = "\n".join(read(p) for p in fs)
    for p in fs:
        check_header(p)
    sub = table(text, "subdomain")
    if not sub:
        add("High", "STR-01", fs[0], 1, "no Subdomains table")
    for ln, row in (sub[1] if sub else []):
        if col(sub[0], row, "type").lower().strip("* ") not in {"core", "supporting", "generic"}:
            add("High", "STR-01", fs[0], ln, f"subdomain '{row[0]}' type is not core/supporting/generic")
    ctx = table(text, "bounded context")
    if not ctx:
        add("High", "STR-02", fs[0], 1, "no Bounded contexts table")
        return text
    owner: dict[str, list] = {}
    for _, row in ctx[1]:
        for r in REQ_RE.findall(col(ctx[0], row, "req")):
            owner.setdefault(r, []).append(row[0])
    for r in d.reqs:
        if len(owner.get(r, [])) != 1:
            add("High", "STR-02", fs[0], 1, f"{r} owned by {owner.get(r) or 'no context'} (needs exactly one)")
    if not table(text, "ubiquitous", "language", "glossary"):
        add("High", "STR-04", fs[0], 1, "no ubiquitous-language table")
    if len(ctx[1]) > 1 and not table(text, "context map"):
        add("High", "STR-03", fs[0], 1, "several contexts but no Context map table")
    return text


def mapped(text, a, b) -> bool:
    t = table(text, "context map")
    return any(NORM(a) in NORM(" ".join(row)) and NORM(b) in NORM(" ".join(row)) for _, row in (t[1] if t else []))


def check_tactical(d: Design, strategic: str):
    fs = files(d.out, "02-tactical-*.md")
    if not fs:
        return add("High", "DOC-01", d.out, 0, "no 02-tactical-<context>.md files")
    for p in fs:
        check_header(p)
    for a, rec in d.aggs.items():
        for part in names(get(rec, "contain")):
            if ident(part) in d.aggs and ident(part) != a:
                add("High", "TAC-01", rec["file"], rec["line"], f"aggregate {a} contains aggregate {ident(part)}")
        creator = get(rec, "created by").replace(" ", "").replace("`", "")
        if not re.match(r"(actor|policy):", creator, re.I):
            add("High", "TAC-06", rec["file"], rec["line"], f"{a}: 'Created by' must be actor:<A> or policy:<P>")
        elif is_policy(creator) and ident(creator[7:]) not in d.policies:
            add("Medium", "TAC-06", rec["file"], rec["line"], f"{a} created by unknown policy {creator[7:]}")
    for c, rec in d.cmds.items():
        if not re.match(r"^(actor|policy):[A-Za-z]", get(rec, "trigger").replace(" ", "").replace("`", ""), re.I):
            add("High", "TAC-05", rec["file"], rec["line"], f"command {c}: trigger must be actor:<A> or policy:<P>")
        if ident(get(rec, "aggregate")) not in d.aggs:
            add("Medium", "DOC-04", rec["file"], rec["line"], f"command {c} targets an unknown aggregate")
    for e, rec in d.events.items():
        if e in d.cmds:
            add("High", "TAC-04", rec["file"], rec["line"], f"event {e} has the same name as a command")
        elif not (last_word(e).endswith("ed") or last_word(e) in IRREGULAR):
            add("Medium", "TAC-04", rec["file"], rec["line"], f"event {e} does not read as a past-tense fact")
    for pname, rec in d.policies.items():
        when, then = ident(get(rec, "when", "event")), ident(get(rec, "then", "command"))
        ev = d.events.get(when)
        if not ev:
            add("High", "TAC-10", rec["file"], rec["line"], f"policy {pname} reacts to unknown event {when}")
        elif ev["ctx"] != rec["ctx"]:
            if "integration" not in get(ev, "kind").lower():
                add("High", "TAC-10", rec["file"], rec["line"], f"policy {pname} consumes internal event {when} of {ev['ctx']}")
            if strategic and not mapped(strategic, ev["ctx"], rec["ctx"]):
                add("High", "STR-03", rec["file"], rec["line"], f"no context-map row for {ev['ctx']} -> {rec['ctx']}")
        if then not in d.cmds:
            add("High", "TAC-12", rec["file"], rec["line"], f"policy {pname} issues unknown command {then}")
        elif not is_policy(get(d.cmds[then], "trigger")):
            add("Medium", "TAC-05", rec["file"], rec["line"], f"{then} is issued by policy {pname} but its trigger is not policy")
    for q, rec in d.queries.items():
        kind = get(rec, "kind").lower()
        if ("read model" in kind or "cache" in kind) and not get(rec, "source").strip(" -"):
            add("High", "TAC-09", rec["file"], rec["line"], f"{q}: read model or cache without a source")
    covered = set()
    for rec in list(d.cmds.values()) + list(d.queries.values()):
        covered |= set(REQ_RE.findall(get(rec, "req")))
    for r, (bp, bl) in d.reqs.items():
        if r not in covered and r not in d.out_of_scope:
            add("High", "TAC-07", bp, bl, f"MISSING: {r} has no command or query in 02 and is not out of scope")


TABLE_RE = re.compile(r"^###\s+(?:Table|Collection|Item|Node|Entity)\s*:?\s*`?([\w.\-]+)`?.*?\(module:\s*`?([^)`]+?)`?\)", re.I)
FK_RE = re.compile(r"^\s*[-*]\s*FK\s+`?([\w.]+)`?\s*->\s*`?([\w.\-]+)", re.I)


def check_db(d: Design) -> dict:
    fs = files(d.out, "03-db-design*.md")
    if not fs:
        add("High", "DOC-01", d.out, 0, "03-db-design.md not found")
        return {}
    tbl, fks = {}, []
    for p in fs:
        check_header(p)
        current = None
        for ln, line in enumerate(read(p).splitlines(), 1):
            m = TABLE_RE.match(line)
            if m:
                current = m.group(1)
                tbl[current] = dict(module=m.group(2).strip(), file=p, line=ln, text="")
                continue
            if line.startswith("## "):
                current = None
            if current:
                tbl[current]["text"] += line + "\n"
                f = FK_RE.match(line)
                if f:
                    fks.append((current, f.group(2), p, ln))
    if not tbl:
        add("High", "DB-03", fs[0], 1, "no '### Table: <name> (module: <Context>)' blocks")
    for src, dst, p, ln in fks:
        if dst in tbl and NORM(tbl[dst]["module"]) != NORM(tbl[src]["module"]):
            add("High", "DB-01", p, ln, f"FK {src} -> {dst} crosses modules {tbl[src]['module']} -> {tbl[dst]['module']}")
    homes = NORM(" ".join(t["text"] for t in tbl.values()) + " ".join(tbl))
    for a in d.aggs:
        if NORM(a) not in homes:
            add("High", "DB-03", fs[0], 1, f"aggregate {a} has no table (no 'Aggregate: {a}' line)")
    for q, rec in d.queries.items():
        if "read model" in get(rec, "kind").lower() and NORM(q) not in homes:
            add("Medium", "DB-06", fs[0], 1, f"read model {q} has no table marked as its home")
    if "outbox" in d.profile.get("events_messaging", ("", ""))[0].lower():
        emitting = {NORM(e["ctx"]) for e in d.events.values() if "integration" in get(e, "kind").lower()}
        boxed = {NORM(t["module"]) for n, t in tbl.items() if "outbox" in (n + t["text"]).lower()}
        for ctx in sorted(emitting - boxed):
            add("High", "DB-05", fs[0], 1, f"context {ctx} emits integration events but has no outbox table")
    return tbl


def check_diagrams(d: Design, tbl: dict, which: tuple):
    fmt = (d.profile.get("diagram_format", ("mermaid", ""))[0] or "mermaid").lower()
    want, other = ("@startuml", "```mermaid") if "plantuml" in fmt else ("```mermaid", "@startuml")
    for pat, rule in which:
        fs = files(d.out, pat)
        if not fs:
            add("High", "DOC-01", d.out, 0, f"{pat} not found")
            continue
        text = "\n".join(read(p) for p in fs)
        for p in fs:
            check_header(p)
        if want not in text or other in text:
            add("High", rule, fs[0], 1, f"diagrams must use only the profile format '{fmt}'")
        if pat.startswith("04"):
            for t in tbl:
                if t.split(".")[-1] not in text:
                    add("High", "ERD-01", fs[0], 1, f"table {t} from 03 is not in the ERD")


def check_api(d: Design):
    fs = files(d.out, "06-api*.md")
    if not fs:
        return add("High", "DOC-01", d.out, 0, "06-api.md not found")
    covered = set()
    for p in fs:
        check_header(p)
        t = table(read(p), "operation")
        if not t:
            add("High", "API-01", p, 1, "no Operations table")
            continue
        headers, rows = t
        for ln, row in rows:
            target = ident(col(headers, row, "maps to"))
            covered |= set(REQ_RE.findall(col(headers, row, "req")))
            if target not in d.cmds and target not in d.queries:
                add("High", "API-01", p, ln, f"operation '{row[0]}' maps to unknown command/query '{target}'")
                continue
            if target in d.cmds:
                if is_policy(get(d.cmds[target], "trigger")):
                    add("High", "API-02", p, ln, f"operation '{row[0]}' invokes policy-triggered command {target}")
                if not col(headers, row, "idempot").strip(" -"):
                    add("High", "API-03", p, ln, f"command operation '{row[0]}' states no idempotency")
                if not col(headers, row, "error").strip(" -"):
                    add("High", "API-04", p, ln, f"command operation '{row[0]}' lists no errors")
            if not col(headers, row, "actor", "role", "auth").strip(" -"):
                add("Medium", "API-08", p, ln, f"operation '{row[0]}' names no actor")
    for r in sorted(set(d.reqs) - covered - d.out_of_scope):
        recs = [c for c in d.cmds.values() if r in get(c, "req")] + [q for q in d.queries.values() if r in get(q, "req")]
        if not recs or any(not is_policy(get(c, "trigger")) for c in recs):
            bp, bl = d.reqs[r]
            add("High", "REV-03", bp, bl, f"MISSING: {r} has no API operation")


def check_review(d: Design):
    fs = files(d.out, "07-review.md")
    if not fs:
        return add("High", "DOC-01", d.out, 0, "07-review.md not found")
    check_header(fs[0])
    t = table(read(fs[0]), "finding")
    for ln, row in (t[1] if t else []):
        for kw in ("sever", "rule", "location", "case", "fix"):
            if not col(t[0], row, kw).strip(" -"):
                add("High", "REV-02", fs[0], ln, f"finding '{row[0]}' has no {kw}")


# ---------------------------------------------------------------- main
def report(out: Path) -> str:
    order = {"High": 0, "Medium": 1, "Low": 2}
    rows = ["| # | Severity | Rule | Location | Problem |", "|---|---|---|---|---|"]
    for i, (sev, rule, p, ln, msg) in enumerate(sorted(FIND, key=lambda f: order[f[0]]), 1):
        p = Path(p)
        loc = p.relative_to(out).as_posix() if p.is_relative_to(out) else p.name
        rows.append(f"| L{i} | {sev} | {rule} | {loc}:{ln} | {msg.replace('|', '/')} |")
    high = sum(f[0] == "High" for f in FIND)
    return f"{len(FIND)} findings, {high} High\n\n" + "\n".join(rows)


def run(out: Path, phase: int):
    d = Design(out)
    if phase in (0, 99):
        check_profile(d)
    strategic = ""
    if phase == 1 or phase == 99:
        strategic = check_strategic(d)
    elif phase >= 2:
        strategic = "\n".join(read(p) for p in files(out, "01-strategic*.md"))
    if phase in (2, 99):
        check_tactical(d, strategic)
    tbl = {}
    if phase in (3, 4, 99):
        keep = len(FIND)
        tbl = check_db(d)
        if phase == 4:
            del FIND[keep:]
    if phase in (4, 99):
        check_diagrams(d, tbl, (("04-erd*.md", "ERD-01"),))
    if phase in (5, 99):
        check_diagrams(d, tbl, (("05-diagrams*.md", "DOC-04"),))
    if phase in (6, 99):
        check_api(d)
    if phase == 7:
        check_review(d)


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[0] not in {"gate", "lint"} or (argv[0] == "gate" and len(argv) < 3):
        print(__doc__)
        return 2
    out = Path(argv[1]).resolve()
    run(out, int(argv[2]) if argv[0] == "gate" else 99)
    text = report(out)
    print(text)
    if argv[0] == "lint" and "--write" in argv:
        (out / "07-lint.md").write_text(
            "# 07 Lint\n\n## Inputs\nAll artifacts in this folder, checked by design_check.py.\n\n"
            "## Decisions\nNone. These are machine findings for the reviewer to confirm or reject.\n\n"
            "## Open questions\nNone.\n\n## Findings\n\n" + text + "\n", encoding="utf-8")
    return 1 if any(f[0] == "High" for f in FIND) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
