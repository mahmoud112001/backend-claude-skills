# Fixture B results (Stockroom)

Design folder: tests/fixture-b/docs/design/ · Date: 2026-11-17 · Result: **phase 8 passed**

## Phases
| Phase | Status | Gate | Ran as (model, self-reported) |
|---|---|---|---|
| 0 | passed | script 0 High after 1 user answer (architecture_style = microservices, asked) | project-reader (Sonnet 5.5) |
| 1 | passed | 0 High | strategic-designer (Opus 5.5) |
| 2 | passed | 0 High; 3 contexts in parallel (cat, stk, pur) | tactical-designer x3 (Opus 5.5) |
| 3 | passed | 0 High; split in 4 files (DOC-01) | db-designer (Opus 5.5) |
| 4 | passed | 0 High | diagram-writer (Sonnet 5.5) |
| 5 | passed | retry 1: DOC-01 High (321 lines) -> split in 3 files, 0 High | diagram-writer (Sonnet 5.5) |
| 6 | passed | 0 High; 13 gRPC operations + 06-api.proto | api-designer (Opus 5.5) |
| 7 | passed | loop 2: no High | design-reviewer x2, each new (Fable 5.2); fixers below |
| 8 | passed | organize.py check OK; lint 0 High; noloss.py OK (21 -> 23 files, 0 broken links, fixture-b-noloss.md) | doc-librarian (Haiku 5.5) |

No general-purpose subagent was used for any role.

## Review loops
| Loop | High | Medium | Low | Fixed by |
|---|---|---|---|---|
| 1 | 1 | 6 | 7 | F1-F7 by project-reader, strategic-designer, tactical-designer x2, db-designer, diagram-writer, api-designer (in parallel); log review/07-fixes-loop1.md |
| 2 | 0 | 3 | 11 | none (gate met). Medium carried forward in 00-state.md: 03 still describes two AvailabilityChanged consumers, FLOW-6 lacks a projection step, SKU case normalisation (business rule -> open question) |

## Check a: the override
- ARCHITECTURE.md:5 (R1) names DB-02 as the only default rule it overrides (sentence added in S1).
- project-profile.md:38 Rule overrides row R1 -> DB-02; data/03-db-design.md:14 D3-1 "Override of DB-02 by R1": one schema `stockroom`, prefixed tables `cat_`/`stk_`/`pur_`.
- review/07-review-loop1.md:6 and review/07-review.md:6: "R1 overrides DB-02, so the own-schema part of DB-02 was not checked; R1 was checked instead". No finding reports the shared schema as a violation. **PASS**

## Check b: no leakage (tests/leakage_check.py, output tests/results/fixture-b-leakage.txt)
Words from fixture A (Shelfmark library; TypeScript/NestJS, PostgreSQL, REST, Mermaid, modular monolith). 10 hits, all explained: 3x "rest" = English "the rest"; 6x "modular monolith" = the architecture-style question and its alternatives (fixture B's own Q8/Q1-8, user chose microservices); 1x "Member of the configured set". Zero leaks. **PASS**
Fixture B's profile names its own stack: Go 1.22 + gRPC (project-profile.md:20), MariaDB 11.4 (:21), gRPC API (:22), PlantUML (:29), rules file ARCHITECTURE.md (:32).

## Bugs found in skills or agents (not fixed; none is a small mechanical fix)
- Worker self-reported line counts are estimates: diagram-writer reported ~290 lines for a 321-line file. Only the script gate caught it. Proposal: worker template asks for measured counts.
- project-reader has no Edit tool, so a phase-7 fix rewrote the whole brief with Write (checked by git diff: nothing lost). Proposal: give project-reader Edit, or route brief fixes to the orchestrator.
- Parallel fixers in phase 7 drift apart: stk_inbox key mismatch between 03 and 04 (caught by the orchestrator, sent back), and loop-1 F1 left a 02/03 contradiction (loop 2 Medium F1). Proposal: run fixers in phase order (02 -> 03 -> 04/05 -> 06).
- Orchestration slip in this run (main session, not a skill bug): phase 5 was committed before its failed gate was seen; the state was corrected and the retry committed as 5cd6405.
