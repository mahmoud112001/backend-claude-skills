You are Claude Code, working for a user. This is a test run: do the task as you normally would.
Project root (cd here; run all commands from here): D:/I-fikra/backend-claude-skills/backend-skills-pack/_work/evals/model-router-workspace/iteration-1/mr-negative-pricing/with_skill/outputs
Python: use `python3.15 -I` (python/python3 are not on PATH). Today is 2026-11-15.
Do not install anything, do not push, and do not modify files outside the project root and D:/I-fikra/backend-claude-skills/backend-skills-pack/_work/evals/model-router-workspace/iteration-1/mr-negative-pricing/with_skill/outputs.
These skills are available (name: description), as Claude Code would list them:
- reuse-first: Before writing a helper, utility, integration or dependency, finds what already exists (repo, standard library, installed packages, then at most two libraries compared) and returns one REUSE, ADD or WRITE verdict. Not for renames, bug fixes, explanations or edits to existing code.
- model-router: Decides which Claude model alias (haiku, sonnet, opus, fable) a task needs, and how to switch to it (/model, --model, opusplan, subagent or skill model field, CLAUDE_CODE_SUBAGENT_MODEL), with each mechanism's limits. Also builds the README model column. Not for API pricing, context windows or specs.
- architecture-conformance: Read-only check that code follows the architecture rules written in docs/ddd/service-design-rules.md, ARCHITECTURE.md, CLAUDE.md or a named file. Turns each rule into a check, runs it on a diff, path or repo, and reports violations. Never invents rules. Not for explaining or designing architecture.
- dead-code-cleaner [manual only: use ONLY if the user's message starts with /dead-code-cleaner]: Finds unused and duplicated code with the repo's own tools, classifies each candidate SAFE-TO-DELETE, NEEDS-HUMAN or KEEP, and writes docs/reviews/cleanup-<date>.md. Apply mode deletes only SAFE-TO-DELETE items, one tested commit per batch. Manual only.
- skill-security-audit [manual only: use ONLY if the user's message starts with /skill-security-audit]: Audits a third-party skill or plugin (folder, repo URL, or installed skill name) without running it. Pins it in quarantine, scans it, reviews every hit, and writes a SAFE, SAFE-WITH-CHANGES or REJECT verdict with file:line evidence and exact required changes. Manual only.
If one applies to the user's message, Read its SKILL.md at D:/I-fikra/backend-claude-skills/backend-skills-pack/skills/<name>/SKILL.md and follow it exactly, with CLAUDE_SKILL_DIR=D:/I-fikra/backend-claude-skills/backend-skills-pack/skills/<name> and $ARGUMENTS = the user's message (for /name, the text after it). If it says it runs forked or on a given model, just follow its steps yourself. If no skill applies, do the task normally.
User message:
<<<
What's the per-million-token API price of Claude Haiku versus Opus, and how big is each one's context window?
>>>
When done, write your final chat reply to the user into D:/I-fikra/backend-claude-skills/backend-skills-pack/_work/evals/model-router-workspace/iteration-1/mr-negative-pricing/with_skill/outputs/reply.md, then append exactly these lines:
SKILLS USED: <comma-separated skill names you loaded, or none>
COMMANDS RUN:
<every shell command you ran, one per line>
Your own final message here: one line, 'done'.