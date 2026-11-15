"""Write one line per non-selected skill with a reason.

Usage: python -I scripts/rejected.py [--work _work]
Inputs (in --work): inventory.csv, selected.csv (need,decision,name,group,source),
reject_reasons.csv (name,group,reason: hand-written, PROPOSED), need_scores.csv.
Output: rejected.csv (name,source,group,description_chars,words,reason,path).
Selected = exact (name, group, source) match; for quarantine ponytail, only skills/ (not .openclaw/).
Standard library only. No network.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import score_needs as sn  # noqa: E402

PACK = Path(__file__).resolve().parent.parent
MAX_WORDS = 45


def load(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def is_selected(row: dict, selected: set) -> bool:
    if ".openclaw" in row["path"]:
        return False
    return (row["name"], row["group"], row["source"]) in selected


def best_need(row: dict) -> tuple[str, int]:
    name, desc = row["name"].lower(), row["description"].lower()
    scores = [(sn.score(name, desc, kws), need) for need, kws in sn.NEEDS.items()]
    s, need = max(scores)
    return need, s


def reason_for(row, explicit, sel_names, sha_owner) -> str:
    key = (row["name"], row["group"])
    if key in explicit and explicit[key] != "n/a":
        base = explicit[key]
    elif row["name"] in sel_names:
        base = f"another copy of selected '{row['name']}' ({row['source']}/{row['group']}); pack uses the pinned/selected copy"
    elif ".openclaw" in row["path"]:
        base = "shorter .openclaw duplicate of ponytail skills/ copy"
    elif row["sha256"] in sha_owner and sha_owner[row["sha256"]] != row["path"]:
        base = "byte-identical duplicate of another inventoried copy"
    else:
        need, s = best_need(row)
        if s == 0:
            base = "no match to any of the 17 needs (name+description score 0)"
        else:
            base = f"weak or off-domain match to '{need}' (score {s}); a better candidate was chosen or the need is BUILD"
    flags = []
    if row["has_hooks"] == "True":
        flags.append("ships hooks")
    if len(row["description"].split()) > MAX_WORDS:
        flags.append(f"description {len(row['description'].split())} words > {MAX_WORDS}")
    if int(row["skill_md_lines"]) > 150:
        flags.append(f"SKILL.md {row['skill_md_lines']} lines > 150")
    return base + ("; " + ", ".join(flags) if flags else "")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default=str(PACK / "_work"))
    a = ap.parse_args(argv)
    work = Path(a.work)
    inv = load(work / "inventory.csv")
    sel_rows = load(work / "selected.csv")
    selected = {(r["name"], r["group"], r["source"]) for r in sel_rows}
    sel_names = {r["name"] for r in sel_rows}
    explicit = {(r["name"], r["group"]): r["reason"] for r in load(work / "reject_reasons.csv")}
    sha_owner = {}
    for r in inv:
        sha_owner.setdefault(r["sha256"], r["path"])
    out, kept = [], 0
    for r in inv:
        if is_selected(r, selected):
            kept += 1
            continue
        out.append([r["name"], r["source"], r["group"], r["description_chars"],
                    len(r["description"].split()), reason_for(r, explicit, sel_names, sha_owner), r["path"]])
    with open(work / "rejected.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["name", "source", "group", "description_chars", "words", "reason", "path"])
        w.writerows(out)
    print(f"selected rows matched: {kept} of {len(selected)}; rejected rows: {len(out)}; total: {len(inv)}")
    return 0 if kept == len(selected) else 1


if __name__ == "__main__":
    sys.exit(main())
