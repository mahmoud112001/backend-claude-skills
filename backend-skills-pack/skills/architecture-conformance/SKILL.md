---
name: architecture-conformance
description: Read-only check that code follows the architecture rules written in docs/ddd/service-design-rules.md, ARCHITECTURE.md, CLAUDE.md or a named file. Turns each rule into a check, runs it on a diff, path or repo, and reports violations. Never invents rules. Not for explaining or designing architecture.
model: sonnet
argument-hint: "[diff <base> | path <dir> | repo] [rules-file]"
allowed-tools: Read Grep Glob Bash(python *architecture-conformance/scripts/*) Bash(python3 *architecture-conformance/scripts/*) Bash(git diff*) Bash(git log*) Bash(git rev-parse*) Edit(docs/reviews/**)
---

# architecture-conformance

Model: sonnet, because most checks are tool- or script-driven. Judgement-only rules go to a forked opus subagent (step 3).

Arguments: `$ARGUMENTS`: the target (`diff <base>`, `path <dir>`, or `repo`, the default) and optionally a rules file.
Read-only for code. The only files you write are `docs/reviews/architecture-<date>.md` and `docs/reviews/architecture-checks.json`.

## 1. Find the rules (never from memory)

Use the first that exists: the file named in the arguments → `docs/ddd/service-design-rules.md` → `ARCHITECTURE.md` → `CLAUDE.md` (its architecture sections only).

- **None exists:** stop. Ask the user which file holds the rules, write no report, and do not proceed with "typical" rules.
- Use only rules written in that file. A typical DDD rule that the file doesn't state is not a rule. You may list it under "Not in the rulebook" at most, never as a violation.
- Keep the file's rule ids. If it has none, number the rules `R1…` in file order and quote each one.

Record the rules file path and its commit (`git log -1 --format=%h -- <file>`).

## 2. Turn each rule into a check

For each rule, pick the first method that works:

1. **The repo's own tool config**, if present: dependency-cruiser (`.dependency-cruiser.*`), eslint boundaries or `import/no-restricted-paths`, import-linter (`.importlinter`), ArchUnit or NetArchTest tests. Run it with its normal command and map its output to rule ids.
2. **Script:** an `import` or `grep` check in `docs/reviews/architecture-checks.json`, run by `check.py` (format in the script's docstring).
3. **Manual:** a rule that needs judgement, such as "refers by id", "same transaction", or naming that a regex can't decide.

Typical mappings, used only when the rulebook states the rule:

| Rule | Check |
|---|---|
| A module reaches another only through its public contract | `import` from `src/<a>/**` forbid `^<b>\.(domain|infrastructure|api)\b` (one check per module pair, or a regex excluding self) |
| Domain imports no infrastructure | `import` from `**/domain/**` forbid `infrastructure|<the persistence, HTTP and framework packages the rulebook names>` |
| Aggregates refer to others by id | manual. Grep helps: other modules' types in domain fields or annotations |
| Events go to the outbox in the same transaction | `grep` for `publish(` / `send(` in repositories and handlers, plus manual review of the save path |
| No FK or join across modules | `grep` `REFERENCES\s+<other-module-table>` and `JOIN\s+<other-table>` in migrations, SQL and ORM mappings |
| Endpoint paths and error codes follow the rulebook | `grep` route and error-code definitions, with the forbidden form expressed as a regex taken from the rulebook's own pattern |

Write the spec, then run it:

```
python -I "${CLAUDE_SKILL_DIR}/scripts/check.py" <root> --spec docs/reviews/architecture-checks.json [--diff <base> | --files <path>]
```

`--edges` dumps every import edge when you need to explore before writing a check. Read each hit before reporting it. Drop false positives, such as a module importing its own internals, and say how many you dropped.

## 3. Judgement rules → forked opus subagent

Don't judge manual rules yourself, even when the repo is small: the point is an independent check on a stronger model. Collect the manual rules and send them in **one** Agent call (`subagent_type: general-purpose`, `model: opus`). If the Agent tool isn't available, mark those rules `NOT CHECKED (no opus subagent)` instead. Its prompt holds: the exact rule texts with ids, the relevant file paths (not their contents), and this instruction: "Read-only. For each rule, report PASS or each violation as rule id | file:line | evidence (quoted code) | severity | smallest fix. Report only what the rule text says. Reply in at most 300 words." Verify each returned file:line exists before you use it.

## 4. Severity

- **high:** breaks a boundary or data integrity (cross-module internals, domain→infrastructure, a lost or duplicated event, a cross-module FK).
- **medium:** a contract or consistency break that is local and easy to fix (paths, error codes).
- **low:** style-level deviation from the rulebook.

## 5. Report: `docs/reviews/architecture-<date>.md`

```markdown
# Architecture conformance <date> — <repo>
Rules: <path>@<sha> · Target: <diff base | path | repo> · Methods: <tools/script/manual>

## Rules
| Rule | Summary (quoted or close paraphrase) | Method | Result | Violations |
|---|---|---|---|---|
| R1 | … | script import | FAIL | 2 |

## Violations (worst first)
| # | Rule | Location | Evidence | Severity | Suggested fix |
|---|---|---|---|---|---|

## Not checked
<rules or parts that could not be checked, and why>
```

Results are `PASS`, `FAIL`, or `NOT CHECKED (reason)`. Every rule in the file appears exactly once.

## 6. Chat reply

`<n> rules: <p> pass, <f> fail, <u> not checked · <v> violations (<h> high)`, then the 10 worst violations, one line each (`rule · file:line · problem · fix`), then the report path.
