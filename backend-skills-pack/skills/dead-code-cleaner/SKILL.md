---
name: dead-code-cleaner
description: Finds unused and duplicated code with the repo's own tools, classifies each candidate SAFE-TO-DELETE, NEEDS-HUMAN or KEEP, and writes docs/reviews/cleanup-<date>.md. Apply mode deletes only SAFE-TO-DELETE items, one tested commit per batch. Manual only.
disable-model-invocation: true
model: sonnet
argument-hint: "[report|apply] [path]"
allowed-tools: Read Grep Glob Bash(python *dead-code-cleaner/scripts/*) Bash(python3 *dead-code-cleaner/scripts/*) Bash(git status*) Bash(git diff*) Bash(git log*) Edit(docs/reviews/**)
---

# dead-code-cleaner

Model: sonnet, because the detection is tool- and script-driven and the deletions are mechanical. Ambiguous candidates go to NEEDS-HUMAN rather than to a bigger model.

Arguments: `$ARGUMENTS`. The first word `apply` selects apply mode; anything else means **report** mode, the default. An optional path limits the scope (default: repo root).
Scripts: `S="${CLAUDE_SKILL_DIR}/scripts"`. Run them with `python -I` (or `python3 -I`).

Deleting the wrong thing costs far more than leaving dead code in place. When in doubt, choose NEEDS-HUMAN.

## 1. Detect (both modes)

1. `python -I "$S/detect_stack.py" <root>` prints the stacks, the tools the repo **already** has (with the command to run each), the missing ones, and the build/test commands.
2. Run only the tools listed as available. Typical ones: knip, ts-prune, depcheck, eslint `no-unused-vars`, jscpd, vulture, ruff `F401,F841`, .NET analyzers (IDE0051/IDE0052), staticcheck `U1000`.
3. **Never install a tool.** If a useful one is missing, name it in the report under "Tools not installed" and ask the user whether to add it. Meanwhile use the stdlib fallbacks:
   - `python -I "$S/find_unused.py" <root>` lists definitions with zero production code references, with counts of test, string and doc/config references, plus hints (decorated, protected path, member, dynamic-lookup match, package export).
   - `python -I "$S/find_dupes.py" <root>` lists duplicate groups: AST-identical Python function bodies, or identical line runs for other languages.
4. Read the architecture docs and config (`ARCHITECTURE.md`, `CLAUDE.md`, `docs/`, DI/route/handler config, `pyproject.toml`, `package.json`) so you can spot names they mention.

## 2. Preflight (before anything runs the code)

1. `python -I "$S/preflight.py" <root>` prints the date, branch, and whether the tree is clean. It ignores untracked caches (`__pycache__`, `.pytest_cache`, `node_modules/.cache`, …), so build and test runs never make the tree look dirty. **Never delete, stash or commit anything to make preflight pass.** A dirty tree is the user's to fix.
2. Only then run the build and the tests with the detected commands (for Python, set `PYTHONDONTWRITEBYTECODE=1`), and record the result.

- **Report mode:** a dirty tree or failing tests are allowed, but write them at the top of the report.
- **Apply mode:** all three must hold: a clean tree, a passing build, and passing tests. If any fails, stop, write the report with `Applied: no (reason)`, and tell the user. If they all pass, run `python -I "$S/preflight.py" <root> --create-branch` to switch to `cleanup/<date>`.

## 3. Classify every candidate

**KEEP.** Never treat these as unused, whatever a tool says:
- dynamic imports and lazy loading (`import()`, `importlib`, `require(variable)`)
- string-based or reflection use (`getattr`, `globals()`, `Activator`, `Class.forName`, names built from parts: check the dynamic-lookup sites the script prints)
- DI registrations, decorators and attributes, route, handler, CLI and plugin registration
- ORM entities, models, mappings, and migrations
- public exports of a published package (`__all__`, `index.ts`, `exports` in package.json, public API of a library)
- generated or vendored code
- anything named in architecture docs, config, or infra files (YAML, TOML, JSON, SQL)
- test fixtures and framework hooks (setUp, conftest, lifecycle methods), overrides and interface implementations

**SAFE-TO-DELETE.** Every point must hold:
- zero references of any kind: code, tests, strings, docs, config (find_unused shows `0 | 0 | 0 | 0`), confirmed with a whole-word Grep
- no hint and no KEEP category applies
- private: a `_`-prefixed or non-exported name, or a public name in a feature module. A **public** function or class in a shared module (`shared/`, `common/`, `lib/`, `utils/`, `core/`) is never SAFE-TO-DELETE, because it exists to be reused, so it goes to NEEDS-HUMAN.

**NEEDS-HUMAN.** Everything else, for example: only tests reference it; it's mentioned in a string or a doc; a dynamic-lookup fragment matches; it's a public member of a shared module; tools disagree; it's a member that might override something. Give the reason in one line. The same candidate must get the same class in report and apply mode.

## 4. Duplicates

- Merge only code that **behaves identically**: same inputs, outputs, edge cases and side effects. An AST-identical body is strong evidence. A textual match needs a read of both copies.
- Merge into an **existing** shared helper (in `shared/`, `common/`, `lib/` or similar): replace the copy's call sites with the helper, then delete the copy. That merge is SAFE-TO-DELETE only if the copy is private and the existing tests cover the call sites.
- If no shared helper exists: for 3 or more copies, propose a new one (NEEDS-HUMAN, with the target path). For 2 copies, leave them and list them only.

## 5. Apply mode only

Work on `cleanup/<date>`. Handle only SAFE-TO-DELETE items, in batches of up to 10 that belong together (one module or one duplicate group).

For each batch:
1. Delete the code, plus the imports that become unused because of it.
2. Run the build and the tests.
3. If they pass: `git add <files>` and `git commit -m "refactor: remove unused <scope> (cleanup <date>)"`, then record the SHA.
4. If they fail: `git restore --staged --worktree -- <files>`, move the batch's items to NEEDS-HUMAN with the failing test name, and continue with the next batch.

Never touch NEEDS-HUMAN or KEEP items. Never push, rebase, amend, or delete branches.

## 6. Report: `docs/reviews/cleanup-<date>.md`

```markdown
# Cleanup <date> — <repo> (<mode>)
Scope: <path> · Branch: <branch> · Base: <sha> · Tools: <ran> · Tools not installed: <list or none>
Preflight: tree <clean|dirty> · build <pass|fail|n/a> · tests <pass|fail> (<command>)

## Counts
SAFE-TO-DELETE <n> · NEEDS-HUMAN <n> · KEEP <n> · Duplicate groups <n>

## Candidates
| # | Symbol | Location | Class | Evidence (refs: code/test/string/doc) | Reason |

## Duplicates
| Group | Copies (file:line) | Identical? | Proposal |

## Applied (apply mode)
| Batch | Items | Commit | Build/tests after |
Final test result: <command> → <pass/fail, counts>
```

Write only this file. Create `docs/reviews/` if it's missing.

## 7. Chat reply (at most 15 lines)

Give the mode, the counts per class, the deleted items and commits (apply mode), the test result, the top NEEDS-HUMAN items with their reasons, the missing tools you are asking to add, and the report path.
