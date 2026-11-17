## Manual-only skills: are they really free?

Manual-only (`disable-model-invocation: true`): **backend-design-team, dead-code-cleaner, skill-creator, skill-security-audit**.

**Confirmed: their descriptions stay out of the always-loaded listing.**
- **Docs.** code.claude.com/docs/en/skills (read 2026-11-16, through a fetch summary, not verbatim) gives `disable-model-invocation: true` as "Description not in context, full skill loads when invoked." The same page says a subagent cannot preload such a skill, which is why the 8 phase skills stay auto.
- **Test, 2026-11-16.** In a project holding only this pack, a session started with `claude -p --setting-sources project` was asked to copy its Skill listing verbatim. It listed the 14 auto pack skills and none of the 4 manual-only ones, plus 13 built-in skills that every session has, with or without the pack.

Caveats:
- The docs page was read through a summary. The live test is the stronger evidence.
- Built-in skills and the system prompt cost the same with or without the pack, so they are not counted on either side.
- The docs (summary) also state a listing budget of about 1% of the context window, and a cap of 1,536 characters per description. With 415 skills the baseline overruns that budget, so Claude Code shortens or drops descriptions. The real cost of the baseline is therefore capped, but triggering gets worse. This was not measured here.
- Things outside skills also cost tokens in every session and are not in these numbers: the superpowers plugin's SessionStart hook (about 1.5k tokens, AUDIT.md), the `~/.claude/rules/` files, and your other agents' descriptions.

## Proposal: use only this pack (not done; your decision)

**Option A, recommended to try first: nothing moves.** Install the pack into one project, then start Claude Code there with `--setting-sources project`:
```
bash backend-skills-pack/scripts/install.sh --project /path/to/project --apply
cd /path/to/project && claude --setting-sources project
```
Verified on 2026-11-16: such a session loads the pack's skills and agents plus the built-ins, and none of the 319 skills in `~/.claude/skills/` and none of your plugins. Trade-off: it also skips your user settings (`~/.claude/settings.json`: permissions, hooks, enabled plugins, default model). Not verified: whether `~/.claude/CLAUDE.md` and `~/.claude/rules/` still load. **Undo:** start `claude` without the flag.

**Option B: permanent, archive your other skills.** Close every Claude Code session first. In Git Bash:
```
cd ~/.claude
mkdir -p skills-archive
ls skills > skills-archive/MOVED.txt                      # record of what moved
for d in skills/*; do
  [ "$(basename "$d")" = synced ] || mv "$d" skills-archive/
done
```
- `skills/synced/` stays, because the claude.ai account sync manages it (12 skills, about 2,064 tokens). Removing synced skills is done in claude.ai, not on disk.
- Then disable the plugins you don't need in `/plugin` (Installed tab). That also removes the superpowers SessionStart hook. Check that `claude plugin disable <name>` works on your version before scripting it.
- Install the pack per project with `scripts/install.sh --project <dir> --apply`, or once with `--user`.

**Undo B:**
```
cd ~/.claude
for d in skills-archive/*; do
  [ "$(basename "$d")" = MOVED.txt ] || mv "$d" skills/
done
```
Then re-enable the plugins in `/plugin`. Nothing is deleted at any step, so B is fully reversible.

**Not recommended: `skillOverrides`.** Setting each unwanted skill to `"off"` in settings works without moving files, but it needs one entry per skill (300+), and the docs say plugin skills are not affected.
