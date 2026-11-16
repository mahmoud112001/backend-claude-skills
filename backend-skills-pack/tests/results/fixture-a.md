# Fixture A results (library lending prototype, no project rules file)

Design folder: tests/fixture-a/docs/design/ · Date: 2026-11-16 · Result: **phase 8 passed**

## Phases
| Phase | Status | Gate | Ran as (model) |
|---|---|---|---|
| 0-6 | passed | script gates 0 High (re-run 2026-11-16 on current files) | earlier session, in a scratchpad copy before the pack was installed in this repo; which agent types ran is not recorded |
| 1 self-check | passed | STR-01..06, DOC-01..03, DOC-06 PASS | strategic-designer (Opus 5.5, self-reported) |
| 7 loop 1 | 3 High, 7 Med, 3 Low; 13/13 fixed | lint 0 High | review: earlier session, agent type not recorded; fix completion: **general-purpose fork** (Opus 5.5), before the pack was installed |
| 7 loop 2 | 0 High, 5 Med, 7 Low; 11 fixed, F11 open | lint 0 High | design-reviewer (Fable 5.2, self-reported); fixes by tactical-designer x3, strategic-designer, db-designer, api-designer (opus per frontmatter), diagram-writer (sonnet per frontmatter); F12 by orchestrator |
| 8 | passed | organize.py check OK; lint 0 High; tests/noloss.py OK | doc-librarian (Haiku 5.5, self-reported) |

Gate: no High left after loop 2. Loop 2 fixes were not re-reviewed (2-loop cap).

## Findings that mattered (loop 1, all High)
- F1: Catalog needs the Librarian check, but 01 forbade every synchronous call -> ResolveCurrentMember open host (D1-10).
- F2: a delayed outbox row would re-notify every handler -> two targeted rows.
- F3: Idempotency-Key required on 7 operations with no storage -> idempotency_record tables.
- Loop 2 Mediums were follow-on drift from loop 1 fixes (hold uniqueness, RQ-4 deadline stated as fact, stale diagram labels, rebuild guard).

## Open questions
Q-1..Q-12 (brief), RQ-1..RQ-5 (review 1: hold-shelf pickup, copy matching, fine lag, 3-day period, name length). Loop 2 F11: Q-8 (renew an overdue loan?) has no proposed default. That is a business decision, left open.

## Cost (this session, from subagent usage)
Phase 1 self-check 33k tok / 25 s · loop 1 fix completion 114k / 110 s · review 2 160k / 267 s · loop 2 fixes 7 agents 199k / ~45 s wall (parallel) · phase 8 52k / 49 s. Phases 0-6: not measured.

## Bugs found in the pack
- Fixed: outputs went wherever the cwd was (relative `docs/design/`) -> root-anchored `<out>`, guard and per-phase commit (c714a5e).
- Fixed: loop 2 would overwrite 07-review.md and no fix log was kept -> per-loop review and fix files (backend-design-team phase 7 step 4).
- Fixed: worker replies did not state their model -> added to the worker prompt.
- Open: design_check.py TAC-04 flags `CopyPlacedOnHoldShelf` (noun + past verb + place suffix). It is a false positive in phase 2, loop 1 and loop 2.
- Open: no YAML or OpenAPI validator was available (no PyYAML), so contract validity was checked by eye only.
- Open: the fixture profile had version_control none, carried over from the scratchpad copy. It was corrected to git by hand.

No-loss proof: tests/results/fixture-a-noloss.md.
