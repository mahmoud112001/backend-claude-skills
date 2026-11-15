---
name: reuse-first
description: Before writing a helper, utility, integration or dependency, finds what already exists (repo, standard library, installed packages, then at most two libraries compared) and returns one REUSE, ADD or WRITE verdict. Not for renames, bug fixes, explanations or edits to existing code.
context: fork
agent: Explore
model: haiku
allowed-tools: Read Grep Glob Bash(python *reuse_scan.py*) Bash(python3 *reuse_scan.py*) Bash(npm view *) Bash(npm ls *) Bash(pip show *) Bash(pip index versions *) Bash(dotnet list package*) Bash(go list *) Bash(cargo search *)
---

# reuse-first

Model: haiku, because this is search and listing only. It runs in a forked Explore subagent so the search does not fill the main conversation.
Adapted from `search-first` (ECC, MIT). Kept: search before building, and say which channel was skipped. Dropped: agent and planner hooks, web/MCP/skill catalogs.

**Need:** $ARGUMENTS

If the need is empty or unclear, reply `NEED MISSING: say what the code must do, in which repo` and stop.

## Rules

- Read-only. Never install, edit or write files. Only the package manager's *info* commands are allowed (`npm view`, `npm ls`, `pip show`, `pip index versions`, `dotnet list package`, `go list -m`, `cargo search`).
- Stop at the first level that fits. A fit means the behaviour matches the need, not only the name. Read the candidate's body and check inputs, edge cases and return type.
- Never recommend a new dependency without the comparison table in step (d).
- If a channel was not available (no network, no package manager), say so in the verdict. Don't claim coverage you didn't have.

## Search order

**(a) This repo.** Pick 2-5 keywords from the need (domain word plus verb, e.g. `slug url`, `retry backoff`). Run:

```
python -I "${CLAUDE_SKILL_DIR}/scripts/reuse_scan.py" <repo-root> <kw1> <kw2> ...
```

It lists matching function and class definitions (`file:line`) and every declared dependency. Then Grep for usages of the best hits and Read them. Prefer shared modules (`shared/`, `common/`, `lib/`, `utils/`) over a copy buried in one feature.

**(b) Standard library and platform.** Ask whether the language or framework already does this. Examples: `urllib.parse`, `itertools`, `dataclasses`, `Intl`, `AbortController`, `System.Text.Json`, `context.WithTimeout`. Name the exact module or API.

**(c) Already-installed dependencies.** Use the dependency list from the script, plus transitive packages from the lockfile or `pip show <pkg>` / `npm ls <pkg>` (look at "Requires"). For example, `requests` brings `urllib3`, whose `Retry` covers backoff. Using a transitive package directly is a REUSE, but say it should then be declared explicitly.

**(d) A maintained library**, only if (a)-(c) fail. Compare at most 2 options:

| | option 1 | option 2 |
|---|---|---|
| Maintenance (last release, open issues) | | |
| Licence | | |
| Size (install / transitive deps) | | |
| Known vulnerabilities | | |
| Fit with our architecture | | |

Fill cells from `npm view <pkg> time.modified license dist.unpackedSize dependencies`, `pip index versions <pkg>`, or the registry page. Write `unknown (not checked)` rather than guessing. "Fit" covers layer and licence policy: no framework types in the domain layer, and no copyleft in a closed service unless allowed.

## Output

Reply with at most 10 lines, starting with exactly one verdict:

```
REUSE <what> at <where: file:line | stdlib module | installed package>
  why: <one line on how it matches the need>
  how: <call or import to use>
  checked: a ✓ b ✓ c ✓ d skipped (reason)
```

```
ADD <library> <version range>
  why: <why a-c failed, one line>
  <the comparison table, 2 options max>
```

```
WRITE <one-line scope of the new code>
  why nothing fits: <a: …; b: …; c: …; d: …>
  put it in: <existing shared module path>
```

The comparison table for ADD may push the reply past 10 lines. Everything else must fit.
