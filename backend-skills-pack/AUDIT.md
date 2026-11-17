# AUDIT — session 1 (2026-11-15)

Read `_work/CONVENTIONS.md` first. The CSV files named here (`scan_hits.csv`, `scan_summary.csv`, `inventory.csv`, …) are in `_work/`. Every statement here is tagged **[sourced]** (seen in a file, with path:line) or **[proposed]** (my judgement). Nothing in `_quarantine/` was run, installed, enabled or sourced. Only my own stdlib scripts (`scripts/*.py`, run with `python -I`) read the files.

## Method

1. `scripts/scan.py` grepped 2,624 text files (session 2 moved it to `skills/skill-security-audit/scripts/scan.py`, the only copy, which now takes target folders as arguments): every file in each skill folder, plus plugin-level `hooks/`, `agents/`, `commands/`, `scripts/`, `bin/`, `plugin.json`, `.mcp.json`, `hooks.json`, `package.json` and `settings.json`. It produced 2,984 hits in `_work/scan_hits.csv`, with per-owner counts in `_work/scan_summary.csv`.
2. Noise patterns (`token-keyword`, `dotenv`, `blob`) were counted but not reviewed one by one. I reviewed every other hit for the quarantine skills and the shortlist. Most were documentation prose: words like "transcript" in "transcription", or curl examples in API docs. **[sourced: scan_hits.csv]**
3. Verdicts judge safety only. Fit for the pack is decided in `SELECTION.md`.
4. Limits: I read the full SKILL.md for every shortlisted skill. For the other quarantine skills, the verdict rests on the scan hits plus the frontmatter. Their scripts were not read line by line.

## Sources (pinned)

| Quarantine dir | Repo | SHA | Licence | Files |
|---|---|---|---|---|
| anthropics-skills | github.com/anthropics/skills | 1780c5e5a552fd4d1c9d6a7b0cab26b0c2bef064 | No root LICENSE. Per-skill `LICENSE.txt` (skill-creator: Apache-2.0) **[sourced]** | 448 |
| claude-plugins-official | github.com/anthropics/claude-plugins-official | b5b01ac4f889fec0c4c6bb89f27ca7c8574473f6 | Apache-2.0 (root and per-plugin LICENSE) **[sourced]** | 765 |
| superpowers | github.com/obra/superpowers | 22f0b463e7a5e579904dd6211a520321035526f7 | MIT, (c) 2025 Jesse Vincent **[sourced]** | 236 |
| ponytail | github.com/DietrichGebert/ponytail | 96608e078b2d5ea607c5c3b8b5a54d1c1fba6846 | MIT, (c) 2026 DietrichGebert **[sourced]** | 216 |

`git ls-files` in each clone gives the full file list.

Not cloned (installed already, not in the source list):
- backend-design (sheitabrk, MIT, v0.2.0, synced from the claude.ai account)
- ECC v2.2.3 (github.com/affaan-m/ECC, MIT), the origin of 229 of the 317 skills in `~/.claude/skills` (`metadata.origin: ECC`) **[sourced: ~/.claude/plugin.json]**

## Plugin-level findings (hooks, always-on)

| Plugin | Finding | Evidence | Verdict for install |
|---|---|---|---|
| ponytail | It registers **SessionStart, SubagentStart and UserPromptSubmit** hooks, all `node -e require(...)`, so it needs Node. On every prompt, `ponytail-mode-tracker.js:86` spawns the detached `ponytail-band-import.js`. That script reads **every session transcript** in `~/.claude/projects/*/*.jsonl` and the subagent transcripts (`ponytail-band-import.js:217-240`). It writes CSVs to `~/.config/ponytail/band/` (`:213,:263`) and writes flag files into `~/.claude` (`ponytail-activate.js:6`). A band module can POST each task row, including task names by default, to a user-set webhook with a Bearer token (`plugin.json` userConfig; `hooks/band/register.tsx:154-179`). It is off when the URL is empty. | `_quarantine/ponytail/.claude-plugin/plugin.json`, `hooks/claude-codex-hooks.json` | **REJECT** as a plugin. The skill files can be copied on their own, without hooks. |
| superpowers | A **SessionStart** hook injects the full `using-superpowers` text into every session. This session shows it costs about 1.5k tokens, and the description baseline doesn't count it. `scripts/sync-to-codex-plugin.sh:457-460` runs `git push` and `gh pr create` (a maintainer script). | `superpowers/hooks/hooks.json:3` | **REJECT** as a plugin. Copy the skills on their own. **The installed copy is the same SHA, so this hook runs today.** |
| backend-design (installed) | **PreToolUse** on `Write\|Edit` runs 3 standard-library Python checks. They give stderr advice only, with no network or exec. | `…/ef408ccc…/hooks/hooks.json`, `check_*.py` (imports json/os/re/sys only) | SAFE (advisory) **[proposed]** |
| claude-security | It has hooks on UserPromptExpansion and on PostToolUse for `Bash`, including a tip after `git push`. A metrics event goes out through the hook's stdout JSON, not straight to the network. | `claude-plugins-official/plugins/claude-security/hooks/hooks.json`, `hooks.py:270-300` | SAFE-WITH-CHANGES (drop the hooks) |
| hookify | It registers hooks for each rule (that is its whole purpose). | `plugins/hookify/hooks/` | not needed |
| own skills `ck`, `continuous-learning-v2`, `delivery-gate` | These ship hooks. The SessionStart brief is in `ck/hooks/session-start.mjs`. `instinct-cli.py:224` fetches a URL. `delivery-gate/hooks/quality-gate.py:124-137` reads the transcript. | inventory `has_hooks=True` | out of scope. Flagged as always-on cost. |

## Skill verdicts — quarantine (98 unique; ponytail's 6 `.openclaw/` copies duplicate `skills/`)

**SAFE** means text only, nothing runs at load, and the hits are prose or examples. **SAFE-WITH-CHANGES** means the changes are listed. **REJECT** means reasons are given.

### anthropics/skills (20)
| Skill | Verdict | Evidence / changes |
|---|---|---|
| skill-creator | SAFE-WITH-CHANGES | `scripts/run_eval.py:52-68` writes temp command files into `<project>/.claude/commands/` and deletes them at `:181`. `improve_description.py:26-35` and `run_eval.py` spawn nested `claude -p`, which is billable. `eval-viewer/generate_review.py:288-300` `_kill_port` sends SIGTERM to **any** process on port 3117: guard or remove it. The server binds 127.0.0.1 (`:443`). Copy LICENSE.txt. |
| docx, pptx, xlsx | SAFE-WITH-CHANGES | Scripts spawn LibreOffice through subprocess (`docx/scripts/accept_changes.py:68`, `pptx/scripts/thumbnail.py:200`, `xlsx/scripts/recalc.py:49`) and chmod helpers (`office/helpers/__init__.py:125`). Narrow allowed-tools to `Bash(python scripts/*)`. The xlsx `!` hit is a false positive (`xlsx/SKILL.md:77`, a formula). |
| webapp-testing | SAFE-WITH-CHANGES | `scripts/with_server.py:69` starts the server commands passed to it. Narrow allowed-tools. |
| web-artifacts-builder | SAFE-WITH-CHANGES | `scripts/bundle-artifact.sh:36` runs `rm -rf` on its build dir and installs npm packages (network). |
| pdf | SAFE | No non-noise hits. Scripts not read in full. |
| claude-api | SAFE | The 616-line docs hold curl, http and transcript examples (`SKILL.md:23,63`). It runs nothing itself. Bloated: 1,068-char description. |
| mcp-builder | SAFE | Hits are code samples in `reference/node_mcp_server.md:415,543`. |
| algorithmic-art | SAFE | `templates/generator_template.js:133` is a `regex.exec` call. |
| academy-guide, brand-guidelines, canvas-design, discernment-nudge, doc-coauthoring, frontend-design, internal-comms, slack-gif-creator, template, theme-factory | SAFE | No non-noise hits. |

### claude-plugins-official (57 skills)
| Skill | Verdict | Evidence / changes |
|---|---|---|
| plugin-dev:command-development | REJECT for this pack | `SKILL.md:471,492,525,581,591` holds `` !`git diff --name-only` ``, `` !`npm test $1` ``, `` !`gh pr view $1` `` and `` !`bash …/script.sh` `` inside fenced examples. **Unverified:** whether Claude Code expands `!` injection inside code fences when it loads the skill. If it does, loading the skill runs these commands. |
| claude-security | SAFE-WITH-CHANGES | Runs `` !`date -u …` `` and `` !`find . -maxdepth 1 …` `` at load (`SKILL.md:32,67`, read-only). allowed-tools has unscoped `Write` and `Edit` (`SKILL.md:3-8`). Plugin hooks: see above. |
| receipts | REJECT | Mines all session transcripts in `~/.claude/projects/**/*.jsonl` (`SKILL.md:11`, `scripts/mine-transcripts.mjs`). |
| session-report | REJECT | `analyze-sessions.mjs:6,54` reads session transcripts. |
| champion-kit:climb | SAFE-WITH-CHANGES | Reads transcripts only with consent (`SKILL.md:19-21,47`). Keep the consent gate. |
| champion-kit: faq, hackathon, maturity, office-hours, patterns, routines | SAFE | Hits are prose (`patterns/SKILL.md:26` mentions gh). |
| cwc-makers:m5-onboard | SAFE-WITH-CHANGES | Device setup with curl and chmod/sudo (`SKILL.md:133,139`). Set disable-model-invocation. |
| discord/telegram/imessage: access, configure | SAFE-WITH-CHANGES | Unscoped `Write` in allowed-tools (`access/SKILL.md:1` etc.). `telegram/configure/SKILL.md:11` uses chmod. These connect to external messaging. Narrow Write to the channel config path. |
| math-proof: siege, solo | SAFE-WITH-CHANGES | Unscoped `Write` (`SKILL.md:1`). |
| claude-md-management:claude-md-improver | SAFE-WITH-CHANGES | Edits CLAUDE.md, which is outside docs/. Set disable-model-invocation. |
| skill-creator (official copy) | SAFE-WITH-CHANGES | Byte-identical to the anthropics/skills copy (sha256 e030e768…). Same changes. |
| claude-code-setup:claude-automation-recommender | SAFE | The `!` hits are false positives. It's a read-only recommender. |
| hookify:writing-rules | SAFE | rm -rf and chmod appear inside example rules that block them (`SKILL.md:136,247`). |
| plugin-dev: agent-development, hook-development, mcp-integration, plugin-settings, plugin-structure, skill-development | SAFE | Documentation. Hook names and rm -rf appear in examples (`hook-development/SKILL.md:70`). |
| mcp-server-dev: build-mcp-app, build-mcp-server, build-mcpb | SAFE | Docs. `build-mcpb/SKILL.md:73` mentions credential paths as guidance. |
| math-olympiad, project-artifact, playground, frontend-design, example-plugin (2), cardputer-buddy | SAFE | Prose hits only. |
| claude-for-manufacturing (17 skills) | SAFE | Prose only ("meeting transcripts", e.g. `ncr-writeup/SKILL.md:341`). Off-domain for this pack. |

### superpowers (15)
| Skill | Verdict | Evidence / changes |
|---|---|---|
| dispatching-parallel-agents, test-driven-development, verification-before-completion, writing-plans, executing-plans, requesting-code-review, systematic-debugging, writing-skills | SAFE | Prose hits: `requesting-code-review/SKILL.md:85` "Skip review" appears in an anti-pattern list. `systematic-debugging/SKILL.md:98` keychain diagnostics are an example. `writing-skills/render-graphs.js:18` execFileSync calls `dot` (optional). |
| receiving-code-review | SAFE | `SKILL.md:205` uses `gh api` to reply only when the user is on GitHub. |
| finishing-a-development-branch, using-git-worktrees | SAFE-WITH-CHANGES | `SKILL.md:116` uses `git push -u`. These have git side effects, so set disable-model-invocation. |
| subagent-driven-development | SAFE-WITH-CHANGES | `references/final-review.md:45` runs `rm -rf <workspace>`, plus `scripts/sdd-*`. Bloated (339 lines + 9 refs). |
| brainstorming | SAFE-WITH-CHANGES | `scripts/server.cjs:540` passes the `BRAINSTORM_OPEN_CMD` env var to shell `cp.exec`. It starts a local server (`start-server.sh`). |
| using-superpowers | REJECT for this pack | Text is safe, but the plugin injects it into every session through SessionStart and forces skill checks before any reply (always-on). |
| diagnosing-superpowers | REJECT | Reads session transcripts (`SKILL.md:11,32`) and can file `gh issue create` (`references/github-issues.md:30`). |

### ponytail (6 skills; `.openclaw/skills/*` are shorter duplicates)
| Skill | Verdict | Evidence / changes |
|---|---|---|
| ponytail-review, ponytail-audit | SAFE-WITH-CHANGES | No hits, and the files are text only. Changes: copy `skills/<name>/SKILL.md` only, never the plugin. Cut the description to 45 words or fewer. Drop the `/ponytail-*` triggers and the `shortcut:` comment convention. Set allowed-tools `Read Grep Glob Bash(git diff:*) Bash(git log:*)`. |
| ponytail-debt, ponytail-gain, ponytail-help | SAFE | Text only. Off-need. |
| ponytail | SAFE (text) / REJECT for pack | "Use on any coding task" makes it an always-on mode. It's also installed as `~/.claude/skills/ponytail` (byte-identical to upstream, sha256 f1800847…) with no hooks in settings. |

## Shortlisted non-quarantine skills

| Skill | Source | Verdict | Evidence |
|---|---|---|---|
| search-first, codebase-onboarding, api-design, contract-first, intent-driven-development, living-docs-governance, architecture-decision-records, hexagonal-architecture, documentation-lookup, agentic-engineering | mine (ECC v2.2.3, MIT, except intent-driven-development, which has no origin tag) | SAFE | No non-noise hits, no scripts, no hooks, no allowed-tools. |
| data-modeling-discipline | plugin backend-design | SAFE | Text only (86 lines). Plugin hooks are advisory (see above). |

## Counts (unique quarantine skills + shortlist)

- Quarantine (98 unique: anthropics 20, official 57, superpowers 15, ponytail 6): **SAFE 68 · SAFE-WITH-CHANGES 25 · REJECT 5**. The rejects are command-development, receipts, session-report, using-superpowers and diagnosing-superpowers. Counting all 104 SKILL.md files, including ponytail's `.openclaw` copies, gives SAFE 72 · SAFE-WITH-CHANGES 27 · REJECT 5. Plugin installs rejected: ponytail and superpowers.
- Shortlist outside quarantine (11): SAFE 11.

## Not verified

- Whether `!` injection fires inside fenced code blocks of a SKILL.md (affects command-development).
- Whether the frontmatter field `model` accepts the aliases `haiku`/`sonnet`/`opus`/`fable`. The docs say "the same values as `/model`, or `inherit`" and don't list them (code.claude.com/docs/en/skills).
- The script bodies of non-shortlisted quarantine skills (pdf, docx, pptx, xlsx, sdd-* scripts): only grep-level coverage.
- backend-design and ECC have no pinned-SHA clone, so the installed copies were audited, not upstream.

## Session 3 (2026-11-16): changes applied when the pack was assembled

- **skill-creator** (SAFE-WITH-CHANGES): `eval-viewer/generate_review.py` no longer calls or defines `_kill_port` (it sent SIGTERM to any process on port 3117); the existing fallback picks a free port. Frontmatter: `disable-model-invocation: true` (its scripts write `.claude/commands/` and spawn billed `claude -p` runs) and `model: opus`. Remaining, accepted: a 127.0.0.1-only HTTP server for the viewer (`--static` avoids it), and `quick_validate.py` needs PyYAML.
- **verification-before-completion** (SAFE): copied as is plus `model: sonnet`, a reworded frontmatter description (trigger first) and two added body lines (Model, Source); SKILL.md is the only changed file. No `allowed-tools`, so test commands keep their permission prompts.
- **test-driven-development**, **dispatching-parallel-agents** (SAFE): adapted (see each SKILL.md Source line); no scripts.
- **ponytail-review**: not added; it overlaps the bundled `/code-review` (SELECTION decision 2 is still open).
- **skill-security-audit** (own): reworded `SKILL.md:18,37,44,45` so the body no longer contains an exclamation mark followed by a backticked command, because whether Claude Code expands that pattern inside inline code is unverified.
- The whole pack passes `scripts/scan.py` (0 unwaived REJECT-class hits; each waiver is in `tests/scan-waivers.tsv` with its reason).
