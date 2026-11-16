# Design state

Profile: [project-profile.md](project-profile.md) · Rules: D:/I-fikra/backend-claude-skills/.claude/skills/backend-design-team/references/default-rulebook.md
eferences\default-rulebook.md
Updated: 2026-11-16 · Current phase: 7 · Status: running

## Phases
| # | Phase | Status | Gate (script High / self-check MUST fails) | Retries | Files |
|---|---|---|---|---|---|
| 0 | Profile and brief | passed | 0 High / n/a | 0 | [profile](project-profile.md), [brief](00-project-brief.md) |
| 1 | Strategic | passed | 0 High / 0 MUST fails (self-check re-run 2026-11-16 by installed strategic-designer, STR-01..06, DOC-01..03, DOC-06 PASS) | 0 | [strategic](01-strategic.md) |
| 2 | Tactical | passed | 0 High / 0 MUST fails (4 contexts) | 0 | [catalog](02-tactical-catalog.md), [lending](02-tactical-lending.md), [fines](02-tactical-fines.md), [membership](02-tactical-membership.md) |
| 3 | Database | passed | 0 High / 0 MUST fails | 0 | [db](03-db-design.md), [lending](03-db-design-lending.md), [fines](03-db-design-fines.md) |
| 4 | ERD | passed | 0 High / 0 MUST fails | 0 | [erd](04-erd.md) |
| 5 | Diagrams | passed | 0 High after 1 retry (DOC-01 line count, fixed by split) / 0 MUST fails | 1 | [diagrams](05-diagrams.md), [flows](05-diagrams-flows.md) |
| 6 | API | passed | 0 High / 0 MUST fails (API-01..08, DOC-01..04 PASS); no OpenAPI validator run | 0 | [api](06-api.md), [root](06-api.openapi.yaml), [common](06-api.openapi-common.yaml), [catalog](06-api.openapi-catalog.yaml), [lending](06-api.openapi-lending.yaml), [membership](06-api.openapi-membership.yaml), [fines](06-api.openapi-fines.yaml) |
| 7 | Review and fix (loop 1/2 done; review 2 next) | running | review 1: 3 High, 7 Medium, 3 Low; all 13 fixed; lint after fixes 0 High (L1 Medium rejected by review 1) | 0 | [lint](07-lint.md), [review 1](07-review-loop1.md), [fixes 1](07-fixes-loop1.md) |
| 8 | Arrange | pending | | | |

## Waiting for user
none (all profile answers received and written to the profile, 2026-11-15)

## Rule conflicts (the project rule overrides the default)
| Project rule | Default rule | Effect on the design | Reported to user |
|---|---|---|---|
| none (no project rules file) | | | n/a |

## Open questions (business decisions; workers never resolve these)
| Id | Question | Raised in | Proposed default | Status |
|---|---|---|---|---|
| Q-1..Q-12 | see [brief](00-project-brief.md) | 0 | see brief | open |
| RQ-1 | Who picks up a shelved hold (Borrow by holder or desk action)? REQ-30 | 7 (F9), [brief](00-project-brief.md) | holder uses Borrow | open |
| RQ-2 | How is the physical copy matched to the loan's assigned copy? | 7 (F7), [06](06-api.md) | loan shows assigned barcode | open |
| RQ-3 | Accept a few seconds where a member with a new fine can still borrow? | 7, [01](01-strategic.md) | yes | open |
| RQ-4 | Hold-shelf 3 days: 72 hours or end of third calendar day? | 7, [02 Lending](02-tactical-lending.md) | end of third calendar day | open |
| RQ-5 | Maximum member name length? | 7 (F13), [02 Membership](02-tactical-membership.md) | 200 characters | open |

## Review loops
| Loop | High | Medium | Low | Fixed | Left open |
|---|---|---|---|---|---|
| 1 | 3 | 7 | 3 | 13 of 13 (F1..F13; see [fixes 1](07-fixes-loop1.md)) | RQ-1..RQ-5 raised as business questions (see 07-review-loop1.md) |

## Medium and Low gate findings carried forward
- none. L1 TAC-04 rejected by review 1 (lint heuristic false positive); CQ-6 resolved (F11, 03 D3-9); CQ-7 resolved (F1).
