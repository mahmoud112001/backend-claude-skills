# State file template: `<out>/00-state.md`

The orchestrator owns this file. On resume it is read first, and after `/clear` it must be enough on its own.
Keep it under 120 lines. When a gate is re-run, replace its details instead of appending new ones.

```markdown
# Design state

Profile: [project-profile.md](project-profile.md) · Rules: <default rulebook path>[, <project rules path>]
Updated: <date> · Current phase: <n> · Status: running | waiting | blocked | done

## Phases
| # | Phase | Status | Gate (script High / self-check MUST fails) | Retries | Files |
|---|---|---|---|---|---|
| 0 | Profile and brief | passed | 0 / 0 | 0 | [profile](project-profile.md), [brief](00-project-brief.md) |
| 1 | Strategic | running | - | 0 | |
| 2 | Tactical (one row per context: 2.<context>) | pending | | | |
| 3 | Database | pending | | | |
| 4 | ERD | pending | | | |
| 5 | Diagrams | pending | | | |
| 6 | API | pending | | | |
| 7 | Review and fix (loop <k>/2) | pending | | | |
| 8 | Arrange | pending | | | |

Status values: pending, running, waiting (on the user), passed, blocked (reason given below).

## Waiting for user
<questions not yet answered; empty when none>

## Rule conflicts (the project rule overrides the default)
| Project rule | Default rule | Effect on the design | Reported to user |
|---|---|---|---|

## Open questions (business decisions; workers never resolve these)
| Id | Question | Raised in | Proposed default | Status |
|---|---|---|---|---|

## Review loops
| Loop | High | Medium | Low | Fixed | Left open |
|---|---|---|---|---|---|

## Medium and Low gate findings carried forward
<one line each: phase, rule, file:line>
```
