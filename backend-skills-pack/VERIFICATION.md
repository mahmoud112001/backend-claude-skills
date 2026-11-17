# Verification (independent, 2026-11-17)

Command: `python3.15 -I scripts/verify-pack.py --install-target <empty temp dir>` → **exit 1: PASS 123, WARN 16, FAIL 16**. The full per-line output comes from that script; this file summarises it. Nothing was trusted from README, RESULTS or commit messages.

## Checks
| Group | Result | Evidence / FAILs |
|---|---|---|
| A structure | 2 PASS, 1 FAIL | A3: `scripts/scan.py` (62eff5a2) ≠ `skills/skill-security-audit/scripts/scan.py` (4486dc22, same as the `.claude/` copy). They are different programs (gate wrapper vs. core), but the rule says copies with one name must match. Fix: rename the wrapper (owner decision). |
| B skills | 17 budgets PASS; skill-creator WARN (body 484, schemas.md 430; cost listed in TOKEN-REPORT) | B5 FAIL: `skills/skill-creator/references/schemas.md:228` `claude-sonnet-4-20250514` (a model version). |
| C required parts | all PASS | 5 custom + orchestrator + 8 phase skills + 8 agents; dead-code-cleaner and skill-security-audit are manual-only. |
| D safety | 6 FAIL | D1 `skill-creator/scripts/quick_validate.py:9` imports `yaml` (not stdlib). D7 `agents/doc-librarian.md:4` `tools: … Bash` (bare). D9 skill-creator uses temp folders (`run_loop.py:13,274`, `SKILL.md:374,445,446`). D8 waiver ×3 (below). D8a: the scan gate now reports 13 unwaived hits, **all in `scripts/verify-pack.py`** (its own pattern names). The gate was 0 before this file existed; I did not add waivers (owner decision). WARN: `http.server` in the eval viewer; nested `claude -p` (billed); `backend-design-team` allows `Bash(python *)` (any Python). |
| E provenance | 9 FAIL | E1: api-endpoints, design-docs-organizer, project-understanding and reuse-first (ECC) have no SHA and no licence text; db-design-erd has no SHA. E4: AUDIT.md has no decision on simplify/code-simplifier; the code-review decision is "still open" (SELECTION decision 2), and AUDIT has no row for the official plugin. Adopted vs. quarantine: skill-creator (SKILL.md, generate_review.py) and verification-before-completion (SKILL.md) differ only as AUDIT.md lists. MANIFEST: 18/18 skills, 8/8 agents, models and tokens correct. |
| F tokens | all PASS | Pack: 18 skills (14 auto) cost ~1,018 tok; with 8 agents, ~1,553. Baseline: 415 skills, 145,889 chars, ~36,472 tok, which matches baseline.txt and TOKEN-REPORT exactly. **97.2% saved** (95.7% with agents). |
| G README | PASS; 9 WARN | 228 lines; every skill and agent has a section; no foreign sections; all links resolve. WARN: the 8 own skills show "mine" with no audit verdict. Mermaid: 1 block, structural check only (no mermaid-cli; checked by eye). |
| H design team | all PASS | Orchestrator is a skill, 96 lines. Phase order 0-8 (SKILL.md:34). Guard :65, checkpoint (00-state.md + per-phase commit) :66-67, `<out>` resolved against `<root>` :19. Every agent has an alias and an explicit tools list. design-reviewer has `Read, Glob, Grep, Write`, no Edit, which matches README row 7. Its Write is not path-scoped (only the prompt limits it). |
| I genericity | PASS | With and without `--allow`: 1 hit, `backend-design-team/SKILL.md:44` "Order matters" (generic English). The older `genericity_check.py` also flags `skill-creator/SKILL.md:31` "course" (English "of course"). |
| J tests | PASS; 3 WARN | All files present. Phase artifacts 0-8 exist in A (27 files) and B (23). Review totals in the 07-review files equal the results files and RESULTS.md (A 3/7/3 → 0/5/7; B 1/6/7 → 0/3/11). Defect test 5/5, 6H/1M/4L. **Triggers:** run2 (the last run) graded 4 rate-limit messages as PASS. Real result: 40 pass, 1 fail, 13 without a verdict = **74% (40/54)**, 40/41 of cases with a verdict. run1 also has 11 such PASS rows. The last run counts, but it is incomplete (rate limit), so the pass rate is unverified for 13 cases. |
| K install | PASS | `install.ps1` added: dry run by default, `-Apply`, Copy-Item, no links, no network. A dry run into a temp project listed exactly 18 skills and 8 agents and wrote nothing. Apply, re-run (all SAME) and change (CHANGED + backup) were tested. Temp project deleted. |

## Waiver decisions (tests/scan-waivers.tsv; I found no written approval anywhere in the repo)
- api-styles.md:17 bang-injection: **justified**. GraphQL `Payload!` before a backtick, in a references file (not preprocessed).
- skill-creator SKILL.md:118 exfil: **justified** (prose forbidding malware). viewer.html:832 base64 `atob`: **justified** (display decode, no blob).
- **viewer.html:666, :1012, :1044 fetch("/api/feedback"): FAIL.** Real HTTP calls to the local viewer server. A network-call waiver needs your written approval, and I found none.
- skill-security-audit SKILL.md:57 git-push: **justified** (example text in an audit template; nothing pushes).
- skill-security-audit/scripts/scan.py:30,34,38,39,40,45,51,57,63 (bang, base64, curl, fetch, netcat, cred-paths, dangerous-flag, telemetry, exfil): **justified**. The scanner's own regexes; nothing runs. Under a strict reading, a "network/load-time/credential" waiver still needs your approval: please confirm.
- scripts/check_skill.py:20 and scripts/scan.py:29,30: **justified** (lists of forbidden names).

## Fixes made (small, mechanical; re-ran the script after each)
- `scripts/install.ps1`: new (PowerShell 5.1 port of install.sh).
- `scripts/verify-pack.py`: new (this verifier).
- `scripts/pack_report.py` + regenerated `MANIFEST.json`: agents now carry origin/source/sha/licence/verdict. TOKEN-REPORT.md is unchanged byte for byte.
- `AUDIT.md`: the verification-before-completion entry now lists its reworded description (it was missing).
- `skills/design-review-fix/SKILL.md:12`: Source line now names repo @ SHA. Text only; no behaviour change.
- `README.md`: install.ps1 usage; model "why" for 4 skills; skill-creator body count 483 → 481 upstream / 484 now; row 7 says the reviewer writes only 07-review.md; verify-pack.py in the checks list.

## Open problems (not small: need your decision)
1. ECC and backend-design sources: no pinned SHA. ECC licence text is not on disk (no network to fetch it).
2. skill-creator (adopted): needs PyYAML, temp folders, a model version in schemas.md, and fetch to its 127.0.0.1 viewer. Approve in writing, or change it (that breaks the hash match).
3. doc-librarian has bare `Bash` (agent tools cannot be pattern-scoped). Remove Bash and let the orchestrator run organize.py, or approve.
4. scan.py name clash (A3), and the verify-pack.py pattern names failing the scan gate (approve waivers or restructure).
5. AUDIT/SELECTION: no decision on simplify/code-simplifier; code-review decision 2 is still open.
6. Triggers: grader counts error replies as PASS (`tests/grade_runs.py` / `run_triggers.py`); 13 cases need a re-run. RESULTS.md "44 pass" is overstated (40 real).
7. Skills call `python`/`python3` only (allowed-tools too). This machine has only `python3.15`, so the skill scripts may not run here.
8. reuse-first allows registry commands (`npm view`, `pip index versions`, `cargo search`). These are network calls, which README:188 forbids without approval. It also never says to ask the user before adding a dependency; it is read-only and only returns ADD.
9. Installed `.claude/skills` copies are stale: design-review-fix, reuse-first and skill-security-audit differ. The installed skill-security-audit SKILL.md:18,37 still holds the exclamation-backtick pattern that the pack removed. 4 skills are not installed. Re-install with `install.ps1 -Apply`.

## Judgement
(1) Custom skills: reuse-first searches repo → stdlib → installed → ≤2 libraries (yes; see 8 for "ask"). dead-code-cleaner has a KEEP never-delete list, a clean tree, build and tests, a `cleanup/<date>` branch, batches with rollback, and is manual-only (yes). architecture-conformance takes its rules only from a file and is read-only on code (yes). skill-security-audit pins, scans and never runs the skill (yes). model-router plus a per-skill `model:` covers model choice (yes).
(2) Design team: prototype → profile and brief → strategic → tactical (aggregates, entities, read models and caches as non-aggregates) → DB → ERD → use-case and DB-module diagrams → API → independent review (missing REQs, bugs) → fixes by authors → organise. Matches the request.
(3) README for a new person: usable. Unclear: what `opusplan` is and how to turn it on; that Python must be `python`/`python3` on PATH; how to undo an install on Windows (README has bash wording only); README does not say the installed copies go stale after pack edits.
(4) Random artifacts (seed 20261117): A `tactical/02-tactical-membership.md` has the template headings, RQ-5 and Fixed F13/F9, which match fixture-a.md (RQ-1..5, loop 1/2). B `brief/00-project-brief.md` has 21 REQ rows (REQ-21 from F5, as fixture-b.md says) and Q8 "Modular monolith", the stale default the loop-2 Low findings report.

## Unverified
Mermaid/PlantUML rendering; OpenAPI and proto validity; whether `!` injection fires in references or fences; the 13 trigger cases with no verdict; the models used in fixture A phases 0-6; ECC and backend-design upstream content.

## Privacy scan (tracked files + full history, 26 commits)
- Keys and tokens: none real. `_work/scan_hits.csv:1428,1489` hold doc placeholders `sk-ant-admin...` and `sk-ant-oat01-...`. No .env files, no file or blob over 5 MB.
- Email: `mahmoudawad112001@gmail.com` is the author and committer of all 26 commits (git metadata, not file content). Content holds only `@example.invalid`.
- Names: `tests/genericity-check.py:29` and `tests/genericity-terms.txt:5` (mahmoud, awad, ifikra); "fikra" is in 61 files.
- Paths `C:\Users\HP\…` and `D:\I-fikra\…`: `_work/scan_hits.csv` (1,927 lines), `_work/inventory.csv` (415), `_work/rejected.csv` (406), `_work/need_scores.csv` (106), `_work/evals/**/run.md`, `tests/fixture-a|b/docs/design/project-profile.md:42/:30`, `00-state.md:3`, `tests/defect-test/design/project-profile.md:42`. Timezone `Africa/Cairo`: `tests/results/triggers-run2.md` (13 lines).
- **Your installed-skills list (personal machine data):** `_work/inventory.csv`, `_work/scan_hits.csv`, `_work/scan_summary.csv`, `_work/rejected.csv`, `_work/reject_reasons.csv`, `_work/need_scores.csv`, `_work/selected.csv`, `_work/baseline.txt` (plugin groups). All are tracked and in history, so removing them needs a history rewrite.

## Verdict: **NO-GO**. 16 FAIL and 9 open problems.
