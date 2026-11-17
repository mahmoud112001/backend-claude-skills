# Design state

Profile: [project-profile.md](project-profile.md) · Rules: D:/I-fikra/backend-claude-skills/.claude/skills/backend-design-team/references/default-rulebook.md, D:/I-fikra/backend-claude-skills/backend-skills-pack/tests/fixture-b/ARCHITECTURE.md
Updated: 2026-11-17 · Current phase: 8 · Status: running

## Phases
| # | Phase | Status | Gate (script High / self-check MUST fails) | Retries | Files |
|---|---|---|---|---|---|
| 0 | Profile and brief | passed | 0 / 0 | 0 | [profile](project-profile.md), [brief](00-project-brief.md) |
| 1 | Strategic | passed | 0 / 0 | 0 | [01](01-strategic.md) |
| 2 | Tactical (cat, stk, pur) | passed | 0 / 0 | 0 | [cat](02-tactical-catalog.md), [stk](02-tactical-stock.md), [pur](02-tactical-purchasing.md) |
| 3 | Database | passed | 0 / 0 | 0 | [03](03-db-design.md) + catalog, stock, purchasing parts |
| 4 | ERD | passed | 0 / 0 | 0 | [04](04-erd.md) |
| 5 | Diagrams | passed | 0 / 0 | 1 | [05](05-diagrams.md) + use-cases, flows parts |
| 6 | API | passed | 0 / 0 | 0 | [06](06-api.md), [proto](06-api.proto) |
| 7 | Review and fix (loop 2/2) | passed | loop 2: H0 M3 L11 (gate: no High) | 0 | [review-loop1](07-review-loop1.md), [fixes-loop1](07-fixes-loop1.md), [review loop 2](07-review.md) |
| 8 | Arrange | running | | 0 | |

## Waiting for user

## Rule conflicts (the project rule overrides the default)
| Project rule | Default rule | Effect on the design | Reported to user |
|---|---|---|---|
| ARCHITECTURE.md R1 (one shared schema `stockroom`, module-prefixed tables) | DB-02 (schema or namespace per context) | All tables live in `stockroom`; ownership is shown by the 3-letter prefix; only the owner writes. | yes, 2026-11-17 |

## Open questions (business decisions; workers never resolve these)
| Id | Question | Raised in | Proposed default | Status |
|---|---|---|---|---|
| Q1-Q8 | See 00-project-brief.md Open questions (expiry duration, expiry behaviour, reason codes, reservation scope, roles, suggestion rules, accept effect, architecture style) | 00 | see brief | Q8 answered: microservices (asked) |

## Review loops
| Loop | High | Medium | Low | Fixed | Left open |
|---|---|---|---|---|---|
| 1 | 1 | 6 | 7 | F1-F7 | 7 Low; business questions to open questions (REQ-21 filters) |
| 2 | 0 | 3 | 11 | - | gate passed (no High); 3 Medium + 11 Low carried forward, see 07-review.md |

## Medium and Low gate findings carried forward
- Phase 7 loop 2 Medium F1: 03 still describes two AvailabilityChanged consumers vs 02 one handler (03-db-design.md:22, 03-db-design-purchasing.md:16, :146).
- Phase 7 loop 2 Medium F2: FLOW-6 lacks the KnownAvailability projection step (05-diagrams-flows.md:150-152).
- Phase 7 loop 2 Medium F3: SKU case normalisation across contexts (03-db-design-catalog.md:27); business rule is an open question.
- Phase 7 loop 2: 11 Low findings, see 07-review.md.
