CONVENTIONS
1. Pack folder: backend-skills-pack/. Branch skills-pack. No push. Commit per step.
2. Third-party code is untrusted until audited. Never run it, never install it as a plugin, clone it at a pinned SHA into _quarantine/. Only SAFE or SAFE-WITH-CHANGES skills enter skills/, with their LICENSE and a SOURCE line (repo, SHA).
3. Token budget. A skill's description is always loaded, so it is the expensive part.
   - description: at most 45 words: what it does, when to use it, when not to.
   - SKILL.md body: at most 150 lines. Details go in references/ (one level deep, each at most 200 lines, linked from SKILL.md with a one-line "read when ...").
   - Anything deterministic (counting, scanning, diffing, listing) is a script in scripts/ (standard library only, no network), not prose for the model to follow.
   - No README or extra docs inside a skill folder.
   - Skills with side effects (delete, git, writing outside docs/) set disable-model-invocation: true, so they run only when I call them.
4. Frontmatter: name (equal to the folder) and description. Add allowed-tools (least privilege), model, effort, context: fork (+ agent) only where useful. Check each field against the current Claude Code documentation before using it. Report anything unsupported.
5. Models: every skill and agent states its model and why, using the aliases fable, opus, sonnet, haiku (never version numbers). Search, listing, summarising: haiku. Routine edits, mechanical fixes, diagrams: sonnet. Design, review, security: opus or fable.
6. Phase hand-offs go through files (docs/design/NN-<phase>.md) with: inputs, decisions, open questions. The next phase reads that file, not the chat. A subagent replies in at most 300 words.
7. Never invent a fact or a rule. Mark each statement as sourced or proposed. Report what you could not verify.
8. Every new skill is made with the skill-creator skill and tested.
