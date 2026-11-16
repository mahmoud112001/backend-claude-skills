---
name: model-router
description: Decides which Claude model alias (haiku, sonnet, opus, fable) a task needs, and how to switch to it (/model, --model, opusplan, subagent or skill model field, CLAUDE_CODE_SUBAGENT_MODEL), with each mechanism's limits. Also builds the README model column. Not for API pricing, context windows or specs.
model: haiku
allowed-tools: Read Glob Grep Bash(python *model_column.py*) Bash(python3 *model_column.py*)
---

# model-router

Model: haiku, because routing is a table lookup and the model column is a script.

Use aliases only: `haiku`, `sonnet`, `opus`, `fable`. Never write a version number. Aliases resolve to the current model, while numbers go stale.

## 1. Route the task

| Task type | Alias | Why |
|---|---|---|
| Search, listing, cataloguing, summaries, triage, log reading | haiku | No judgement, so speed and cost matter most |
| Routine edits, mechanical fixes, renames, test scaffolding, diagrams, tool-driven checks | sonnet | Reliable code changes at moderate cost |
| Design, architecture, DDD modelling, security review, independent review of someone else's work | opus | Judgement-heavy, where a wrong call costs more than the tokens |
| The hardest and longest-running work: multi-day design, deep audits, problems sonnet and opus both failed | fable | Highest capability, highest cost. Use rarely |
| Plan with judgement, then implement | opusplan | opus in plan mode, sonnet for the implementation |

Rules:
- **De-escalate first.** If a script, grep or existing tool can answer it, write or run the script and use haiku or no model at all. Counting, scanning, diffing and listing are never opus work.
- **Escalate only for judgement**: trade-offs, ambiguity, security, or reviewing work you did not do. Mechanical work does not escalate because it is large.
- An ambiguous case inside a mechanical task (for example "is this code really unused?") goes to a human list, not to a bigger model, unless the skill says otherwise.
- Mixed task: split it. Run the mechanical part on haiku/sonnet and send only the judgement part to opus (a forked subagent with `model: opus`).

Reply: `<alias> — <one-line why>` plus the mechanism from section 2. Add more only if asked.

## 2. Switch mechanisms and their limits

Sourced from code.claude.com/docs/en/model-config, /sub-agents, /skills and /env-vars (read 2026-11-15). Re-check them if behaviour differs.

| Mechanism | Scope | Limits |
|---|---|---|
| `/model <alias>` | Current session, from now on | Also saves the default to user settings. In the picker, `s` applies it to this session only. It has the highest priority. |
| `claude --model <alias>` | The session it launches | Not saved. A later `/model` overrides it. |
| `opusplan` (via `/model` or `--model`) | Session | opus only while Plan Mode is active, sonnet otherwise. `ANTHROPIC_DEFAULT_OPUS_MODEL` and `ANTHROPIC_DEFAULT_SONNET_MODEL` change what it uses. |
| Agent tool `model` parameter | One subagent call | Highest precedence for that subagent. |
| Subagent frontmatter `model:` | Every run of that agent | Accepts `haiku`, `sonnet`, `opus`, `fable`, a full ID, or `inherit`. Beats `CLAUDE_CODE_SUBAGENT_MODEL` unless `CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1`, which ignores the field. |
| Skill frontmatter `model:` | Only the turn the skill runs in | **It cannot change the main session's model.** It isn't saved, and the session model resumes on the next prompt. With `context: fork` it sets the forked subagent's model. |
| `CLAUDE_CODE_SUBAGENT_MODEL` | Default for subagents that have no model set another way | On its own it does not change the built-in Explore and Plan subagents. |
| `ANTHROPIC_DEFAULT_{HAIKU,SONNET,OPUS,FABLE}_MODEL` | What each alias resolves to | Pins an alias. Use it to hold a model stable, not for routing. |

Precedence for the session: `/model` > `--model` > `ANTHROPIC_MODEL` > settings `model` > `ANTHROPIC_DEFAULT_MODEL`.
Precedence for a subagent: Agent-call `model` > frontmatter `model` > `CLAUDE_CODE_SUBAGENT_MODEL` > parent's model.

Choosing a mechanism:
- One skill should always use a model, without touching the session: set the skill's `model:` field. For long work, also set `context: fork` so the whole run stays on that model.
- An agent role should always use a model: set the agent's `model:` field.
- The whole session needs a different model: `/model`, or `--model` at launch.
- Design then build in one session: `opusplan`.

## 3. README model column

Every skill and agent states its model in frontmatter (`model:`) and its reason as the first body line `Model: <alias>, because <why>.` To build or check the column, run:

```
python -I "${CLAUDE_SKILL_DIR}/scripts/model_column.py" <pack-root>/skills [<pack-root>/agents] [--strict]
```

It prints a Markdown table (Name | Kind | Model | Why | Check) and flags missing models, missing reasons, non-alias values and version numbers. Paste the table into the README unchanged. Fix any flagged row in its own SKILL.md, never in the README. `--strict` exits 1 when a row is flagged, which suits CI.
