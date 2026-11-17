# Test results: backend skills pack

Date: 2026-11-17 · Branch: skills-pack · Sources: [fixture-a.md](results/fixture-a.md), [fixture-b.md](results/fixture-b.md), [defect-test.md](results/defect-test.md), [genericity.md](results/genericity.md), [triggers-run2.md](results/triggers-run2.md)

## Summary
| Test | Result | Key numbers |
|---|---|---|
| Fixture A (library lending: TypeScript/NestJS, PostgreSQL, REST, Mermaid, no rules file) | phase 8 passed | loop 1: 3 High, 7 Medium, 3 Low, 13/13 fixed; loop 2: 0 High, 5 Medium, 7 Low, 11 fixed, F11 left open |
| Fixture B (stockroom: Go/gRPC, MariaDB, PlantUML, rules file overrides DB-02) | phase 8 passed | loop 1: 1 High, 6 Medium, 7 Low, 7 fixed (all High and Medium); loop 2: 0 High, 3 Medium, 11 Low, carried forward |
| Fixture B check a: override | PASS | R1 overrides DB-02; design follows R1 (data/03-db-design.md:14); the reviewer did not report it as a violation |
| Fixture B check b: leakage of fixture A words | PASS | 10 hits, all explained (English "rest", architecture alternatives, "Member of"); 0 leaks |
| Planted-defect test (5 defects in a copy of fixture A) | 5/5 found | 6 High, 1 Medium, 4 Low; 4 extra Low, real leftovers; 0 false positives |
| Genericity (skills/ and agents/) | PASS | 1 hit ("Order matters"), judged generic; 0 leaks; 0 fixes |
| Trigger tests, run 2 (sonnet, only the pack installed) | 1 failure, 9 errors | 54 cases; 44 pass, 1 fail, 9 errors with no verdict |

## Agents that ran (self-reported models)
- Fixture B: project-reader (Sonnet 5.5), strategic-designer, tactical-designer x3, db-designer, api-designer (Opus 5.5), diagram-writer (Sonnet 5.5), design-reviewer x2 (Fable 5.2), doc-librarian (Haiku 5.5). No general-purpose agent was used.
- Fixture A: phases 0-6 and review loop 1 ran in an earlier session before the pack was installed. Their agent types are not recorded, and the loop-1 fix completion was a general-purpose fork. **This is a finding against the "no general-purpose for a role" rule.** Loop 2 and phase 8 used the role agents.
- Defect test: design-reviewer (Fable 5.2).

## Bugs found and status
Fixed earlier (fixture A): root-anchored `<out>` with guard and per-phase commit; per-loop review and fix files; the model stated in worker replies.
Open:
- design_check.py TAC-04 false positive on `CopyPlacedOnHoldShelf` (fixture A).
- No YAML or OpenAPI validator (no PyYAML), so the contracts were checked by eye (fixture A). The fixture B proto was not compiled.
- Worker line counts are estimates (fixture B phase 5 reported ~290 for 321 lines). Only the script gate catches this.
- project-reader has no Edit tool, so a fix rewrote the whole brief with Write; git diff showed nothing was lost.
- Parallel phase-7 fixers drift apart (fixture B: stk_inbox key mismatch; loop-2 Medium F1). Proposal: fix in phase order.
- Main-session slip in fixture B phase 5: committed before the failed gate was seen, then corrected (5cd6405).

## Platform facts (from the records)
| Fact | Record | Status |
|---|---|---|
| A skill with `disable-model-invocation: true` cannot be preloaded into an agent | tests/token-report-notes.md:6 (docs page read through a fetch summary, 2026-11-16) | kept; docs evidence only, not tested |
| A forked skill or subagent cannot start further subagents, so the orchestrator runs as a skill in the main session | not recorded. SKILL.md:14 records the main-session choice for a different reason (subagents cannot use AskUserQuestion). A third-party note (_quarantine/superpowers/.../claude-code-tools.md:14) says nested subagents are supported | not confirmed; dropped as a fact |
| Agent definitions resolve in the order managed settings, `--agents`, .claude/agents/, ~/.claude/agents/, plugin agents/ | not recorded | not recorded |
| Manual-only skills are not listed in a session | tests/token-report-notes.md:7 (live test, 2026-11-16) | recorded and tested |

## Unverified
- Fixture A phases 0-6: which agents ran, and their cost.
- Models are self-reported by the workers, not read from logs.
- Fixture B: the 3 loop-2 Medium and 11 Low findings are not fixed. Loop-2 fixes in both fixtures were not re-reviewed (2-loop cap).
- No PlantUML or Mermaid diagram was rendered. The OpenAPI files were not bundled. The proto was not compiled. No SQL was executed.
- Trigger tests: the 9 errors have no verdict, and triggers were not re-run after this session (see VERIFICATION.md).
- Defect test extras F9 to F11 were judged plausible, not checked line by line.
