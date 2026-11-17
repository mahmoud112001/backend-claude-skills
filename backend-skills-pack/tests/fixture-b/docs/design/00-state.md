# Design state

Profile: [project-profile.md](project-profile.md) · Rules: D:/I-fikra/backend-claude-skills/.claude/skills/backend-design-team/references/default-rulebook.md, D:/I-fikra/backend-claude-skills/backend-skills-pack/tests/fixture-b/ARCHITECTURE.md
Updated: 2026-11-17 · Current phase: 5 · Status: running

## Phases
| # | Phase | Status | Gate (script High / self-check MUST fails) | Retries | Files |
|---|---|---|---|---|---|
| 0 | Profile and brief | passed | 0 / 0 | 0 | [profile](project-profile.md), [brief](00-project-brief.md) |
| 1 | Strategic | passed | 0 / 0 | 0 | [01](01-strategic.md) |
| 2 | Tactical (cat, stk, pur) | passed | 0 / 0 | 0 | [cat](02-tactical-catalog.md), [stk](02-tactical-stock.md), [pur](02-tactical-purchasing.md) |
| 3 | Database | passed | 0 / 0 | 0 | [03](03-db-design.md) + catalog, stock, purchasing parts |
| 4 | ERD | passed | 0 / 0 | 0 | [04](04-erd.md) |
| 5 | Diagrams | running | | 0 | |
| 6 | API | pending | | | |
| 7 | Review and fix (loop 0/2) | pending | | | |
| 8 | Arrange | pending | | | |

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

## Medium and Low gate findings carried forward
