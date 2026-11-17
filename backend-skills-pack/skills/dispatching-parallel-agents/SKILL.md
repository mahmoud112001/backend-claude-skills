---
name: dispatching-parallel-agents
description: Use when given two or more independent tasks or failures (separate files, subsystems or bugs, no shared state). Splits them across parallel subagents with self-contained prompts, file hand-offs and short replies, then verifies the combined result. Not for related failures or shared files.
model: sonnet
---

# Dispatching Parallel Agents

Model: sonnet, because splitting work and checking the results is routine coordination (CONVENTIONS rule 5). Each subagent keeps its own model.
Source: adapted from github.com/obra/superpowers @ 22f0b463e7a5e579904dd6211a520321035526f7, `skills/dispatching-parallel-agents` (MIT, see LICENSE). The changes: the 300-word reply cap and file hand-offs from CONVENTIONS rule 6, the Graphviz chart replaced with a list, and the body cut from 167 lines.

**Core principle:** one agent per independent problem domain, each with exactly the context it needs. Agents never inherit your session's history; you write what they need. This also keeps your own context free for coordination.

## When to use

Ask these questions in order:
1. Are there several tasks or failures? If not, use one agent or do it yourself.
2. Are they independent, so that fixing one cannot fix or break another? If not, investigate them together first.
3. Can they run at the same time without sharing state (the same files, the same database, the same port)? If not, run the agents one after another.
4. If all three answers are yes, dispatch them in parallel.

Typical cases: several test files failing with different root causes, or several subsystems broken separately.

**Do not use** for related failures, for exploratory debugging (you don't know yet what is broken), when the task needs the whole system in view, or when the agents would edit the same files.

## The pattern

1. **Group by domain.** One domain is one test file, one subsystem or one bounded context. Write one line each on why it is independent of the others.
2. **Write one self-contained prompt per domain.** Each prompt has:
   - **Scope:** the files or subsystem, by path.
   - **Goal:** the exact outcome, such as "these 3 tests pass".
   - **Context:** the error messages, test names and facts the agent can't find alone. Paste them; don't refer to "the conversation".
   - **Constraints:** what it must not change (for example "production code only in `src/abort/`", or "do not raise timeouts").
   - **Hand-off:** where to write its full output (for example `docs/work/<domain>.md` with *inputs, decisions, open questions*), and that its reply is **at most 300 words**: what it found, what it changed, and what it could not verify.
3. **Dispatch every agent in one message.** Several Agent calls in one response run in parallel. One call per response runs them one after another.
4. **Collect.** Wait for every agent and read every reply and hand-off file. Never end your turn while agents are still running, and never report "waiting" as the result.

## Example prompt

```markdown
Fix the 3 failing tests in src/agents/agent-tool-abort.test.ts:
1. "aborts tool with partial output capture": expects 'interrupted at' in the message
2. "handles mixed completed and aborted tools": the fast tool is aborted instead of completed
3. "tracks pendingToolCount": expects 3 results, gets 0

Find the root cause: a timing issue or a real bug in the abort code. Replace arbitrary
timeouts with event-based waiting. Do not just raise timeouts. Change nothing outside
src/agents/abort/ and this test file.
Write your notes to docs/work/abort.md (inputs, decisions, open questions).
Reply in at most 300 words: root cause, files changed, anything not verified.
```

## Common mistakes

| Mistake | Better |
|---|---|
| "Fix all the tests": the agent gets lost | "Fix agent-tool-abort.test.ts" |
| "Fix the race condition": no context | Paste the error messages and test names |
| No constraints: the agent refactors everything | "Do not change production code" or "fix tests only" |
| "Fix it": you don't know what changed | "Reply with the root cause and the files changed" |
| A long reply pasted back into your context | 300-word reply, details in the hand-off file |

## Verify after the agents return

1. **Read each reply and hand-off file.** Understand what changed.
2. **Check for conflicts.** Did two agents edit the same file? Use the diff (for example `git diff --stat`), not the agents' word.
3. **Run the full suite.** Independent fixes can still break each other.
4. **Spot-check.** Agents can make the same mistake systematically. Read at least one change in full.
5. **Report the real state**, with the evidence (see verification-before-completion).
