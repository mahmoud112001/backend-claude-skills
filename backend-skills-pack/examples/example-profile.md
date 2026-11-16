# Project profile: Quayside Lockers

> Example only. This profile belongs to a made-up project and shows how a project plugs into the backend design team. No skill or agent reads this file: each project's own profile lives in `<out>/project-profile.md`, and phase 0 writes it.

## Inputs
- `README.md`, `build.gradle.kts`, `src/main/resources/application.yaml`, `docker-compose.yml`, `docs/adr/0003-events.md`, `CONTRIBUTING.md`
- Prototype: `design/mockups/*.png` (6 screens), `docs/spec.md`

## Decisions
D0-P1 The admin console mockups count as prototype; the marketing site does not (it holds no backend behaviour).

## Open questions
None. All fields were detected or answered.

## Profile
| Field | Value | Source |
|---|---|---|
| project_name | Quayside Lockers | detected: README.md:1 |
| prototype | design/mockups/ (ui), docs/spec.md (spec) | detected: docs/spec.md:3 |
| language_framework | Kotlin 2 + Ktor 3 | detected: build.gradle.kts:4 |
| database | relational / an engine set in application.yaml | detected: application.yaml:12 |
| api_style | REST | default (confirmed) |
| api_contract_file | openapi | asked |
| architecture_style | modular monolith, one Gradle module per bounded context | detected: CONTRIBUTING.md:20 |
| events_messaging | in-process domain events + transactional outbox relayed to the message broker in docker-compose | detected: docs/adr/0003-events.md:8 |
| id_convention | time-ordered UUIDs generated in the application | asked |
| naming_convention | tables and columns snake_case; JSON camelCase; paths kebab-case plural | detected: CONTRIBUTING.md:31 |
| error_format | RFC 9457 problem+json with a `code` extension | asked |
| diagram_format | mermaid | default (confirmed) |
| output_folder | docs/design/ | default (confirmed) |
| project_rules_file | CONTRIBUTING.md | detected |
| version_control | git | detected: git rev-parse |

## Rule overrides
| Project rule (file:line) | Default rule overridden | Effect |
|---|---|---|
| CONTRIBUTING.md:44 "Locker sites may be soft-deleted for audit" | DB-11 (no soft delete by reflex) | The `site` table keeps `archived_at`, and every query on sites filters on it |
