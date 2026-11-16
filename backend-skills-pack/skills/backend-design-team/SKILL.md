---
name: backend-design-team
description: Runs a DDD backend design team on any project's prototype. Covers profile, strategic and tactical design, database, ERD, diagrams, API, independent review and docs, with gates and a resumable state file. Use to design a backend from a prototype or spec. Not for writing code.
model: sonnet
disable-model-invocation: true
argument-hint: "[start | resume | from <phase> | review-only] [prototype path] [--out <dir>]"
allowed-tools: Read Glob Grep Write Edit Agent AskUserQuestion Bash(python3 *) Bash(python *) Bash(git rev-parse*) Bash(git status*)
---

# backend-design-team

Model: sonnet. This skill routes work, runs gates and keeps the state file. All design and review judgement happens in workers on opus or fable.

It runs in the **main session** on purpose. Subagents cannot use AskUserQuestion, and only the main session can ask the user the Phase-0 questions and report rule conflicts. Workers never start other workers.
It is manual-only (`disable-model-invocation`) because one run starts about 10 or more paid subagents.

## Files (every hand-off is a file)

`<out>` is the profile's output folder, `docs/design/` by default, or `--out`.
- `<out>/project-profile.md` is the only source of project facts. Every worker reads it first. Never assume a stack, store, style or convention that is not in it.
- `<out>/00-state.md` holds the phase table, the gate results, the loop counts, open questions, rule conflicts and file paths. Format: [references/state-template.md](references/state-template.md). Update it after every step, so that a new session (after `/clear`) can resume from it alone.
- Rules: [references/default-rulebook.md](references/default-rulebook.md), plus the project rules file if the profile names one. Pass both paths to every worker as absolute paths, and the current state of the rule overrides with them.

## Start or resume

1. Parse `$ARGUMENTS`. If `<out>/00-state.md` exists, read it and the profile only, then continue at the first phase that is not `passed`. Never redo a passed phase unless the user said `from <n>`. If a phase's file exists but its worker's reply was lost (interrupted session), do not pass it on the script alone: send the same agent type a "self-check only" prompt for that file.
2. `review-only` runs phase 7 steps 1 to 2 once, with no fixes, and reports.
3. Optional pack skills: use `reuse-first`, `architecture-conformance` or `model-router` only if they appear in your skill list, and never depend on them.

## Phases

| # | Worker agent (preloaded skill) | Reads | Writes |
|---|---|---|---|
| 0 | project-reader (project-understanding) | prototype, repo | project-profile.md, 00-project-brief.md |
| 1 | strategic-designer (ddd-strategic) | 00: Requirements, Decisions, Open questions | 01-strategic.md |
| 2 | tactical-designer x N in parallel (ddd-tactical) | 01: its own context and the published contracts of the others | 02-tactical-<context>.md |
| 3 | db-designer (db-design-erd) | 02: Aggregates, Queries, Domain events | 03-db-design.md |
| 4 | diagram-writer (db-design-erd, ERD part) | 03 | 04-erd.md |
| 5 | diagram-writer (design-diagrams) | 00 actors, 01 context map, 02 commands and policies, 03 modules | 05-diagrams.md |
| 6 | api-designer (api-endpoints) | 02 Commands and Queries, 03 Decisions | 06-api.md [+ contract file if the profile asks] |
| 7 | design-reviewer (design-review-fix), then the authors fix | everything + 07-lint.md | 07-review.md |
| 8 | doc-librarian (design-docs-organizer) | `<out>` | README.md, final folders |

Order matters: aggregates decide the tables, so phase 2 comes before phase 3. A phase starts only after the previous gate passes.
Token rule: a worker reads only the Decisions and Open questions of the previous file, plus the sections named above, unless it needs more. If it reads more, it says what.

## Phase 0: understand and profile (questions happen here)

1. Check version control with `git rev-parse --is-inside-work-tree` (an error means `none`). If no prototype is given and none is detected, ask the user once where it is.
2. Spawn **project-reader**. It writes a draft profile in which each field has a value and a source (`detected: <file>`, or `missing`), and the brief.
3. Read the profile. Ask the user about every `missing` field in as few AskUserQuestion calls as possible (up to 4 questions each). If the profile is silent, propose these defaults as the first option, marked "(default)", and ask the user to confirm them: relational database, REST, Mermaid, `docs/design/`. Other stores and styles are accepted and passed on. Phases adapt to them; they are never refused.
4. **Can't ask** (non-interactive run, or AskUserQuestion unavailable): write the questions under `Waiting for user` in 00-state.md, set phase 0 to `waiting`, and stop. On resume, take the answers from the user's message.
5. Write each answer into the profile with source `asked` or `default (confirmed)`.
6. Rules: read the default rulebook. If the profile names a project rules file, read it and list every project rule that changes a default rule (same subject, different demand). The project rule wins. Record it in the profile's `Rule overrides` table and in the state's `Rule conflicts`, and **tell the user in your next message**. Ask only when the project rule is ambiguous.

## Gate (after phases 0 to 7)

1. `python3 -I "${CLAUDE_SKILL_DIR}/scripts/design_check.py" gate <out> <phase>` (if `python3` isn't on PATH, use `python`). Exit 0 means no script High findings.
2. The worker's reply holds a self-check of each applicable rule id, PASS or FAIL. This covers the default rules plus the project rules.
3. **Pass** = the script exits 0, and no MUST rule failed in the self-check. Medium and Low findings go in the state and do not block.
4. **Fail:** send the High findings to the same agent type, with the finding list and the file path. At most 2 retries per gate. If it still fails, set the phase to `blocked`, record why, and ask the user.

## Phase 2: one worker per bounded context, in parallel

Spawn every tactical-designer **in one message**, one per context in 01. Each prompt holds the profile path, the 01 path, the rule paths, its context name, and the file it writes. Wait for every reply before the gate. Never end your turn while workers are still running. At most 20 subagents run at once, so batch anything larger.

## Phase 7: independent review, then fix (at most 2 fix loops)

1. Run `design_check.py lint <out> --write`. It writes 07-lint.md.
2. Spawn a **new** design-reviewer every time, never a resumed one. It gets the paths of the profile, the brief, the prototype, the rules, every artifact and 07-lint.md, and writes 07-review.md.
3. For each High or Medium finding, send its id and fix to the **author** of its file (the phase table above), grouped by author. Authors fix in place and add `Fixed F<n>` to their Decisions. Anything that needs a business decision goes to Open questions in 07-review.md and the state, never into the design.
4. Re-run steps 1 and 2. Stop when there are no High findings or after 2 fix loops. High findings that remain go to the user, and the phase is set to `blocked`.

## Phase 8: arrange

Spawn **doc-librarian** with `<out>` and the profile's version_control. Its reply gives the absolute path of `organize.py`. Gate: run `organize.py check <out>` yourself and require `OK`, then run `design_check.py lint <out>`: the High count must not rise, because moving files never changes design content. After the move, update the file paths in the state.

## Worker prompt (all phases)

```
You are <agent>. Profile: <abs out>/project-profile.md. Rules: <abs rulebook>[, <abs project rules>].
Read: <paths + sections>. Write only: <paths>. [Context: <name>] [Fix findings: <ids + text>]
Reply in at most 300 words: files written, decisions (count), open questions (count + the top 3),
self-check table "rule id: PASS/FAIL (evidence)".
```

## Final message to the user

Give the phase table with the gate results, the rule conflicts, the open questions (all of them), the review totals per loop, and the README path. Report misses honestly.
