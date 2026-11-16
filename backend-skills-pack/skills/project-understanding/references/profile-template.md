# project-profile.md template

This is the one file that holds everything that varies between projects. Phase 0 writes it, and every later phase reads it.
Keep the field keys exactly as written: `design_check.py` reads them.
Source values: `detected: <file>[:line]`, `asked`, `default (confirmed)`, `missing`. Only phase 0 may leave `missing`.

```markdown
# Project profile: <project name>

## Inputs
<files read to detect each field>

## Decisions
D0-P1 <only when a field needed interpretation, with why>

## Open questions
<fields still missing, each phrased as a question with a proposed default>

## Profile
| Field | Value | Source |
|---|---|---|
| project_name | <name> | |
| prototype | <path(s)> (<code / ui / spec / readme / text>) | |
| language_framework | <language + framework + version if known> | |
| database | <type: relational / document / key-value / graph / ...> / <engine> | |
| api_style | <REST / GraphQL / gRPC / async messaging / ...> | |
| api_contract_file | <none / openapi / graphql-sdl / proto / asyncapi> | |
| architecture_style | <modular monolith / microservices / serverless / ...> | |
| events_messaging | <none / in-process events / outbox + <broker> / event store / ...> | |
| id_convention | <e.g. time-ordered ids, string prefix, numeric; where generated> | |
| naming_convention | <casing for tables, columns, fields, paths, messages> | |
| error_format | <the envelope or standard used by the project> | |
| diagram_format | <mermaid (default) / plantuml / ...> | |
| output_folder | <docs/design/ (default)> | |
| project_rules_file | <path / none> | |
| version_control | <git / other / none> | |

## Rule overrides
| Project rule (file:line) | Default rule overridden | Effect |
|---|---|---|
```

Notes:
- `database`: when it is not relational, phase 3 maps aggregates to that store's unit (document, item, node) and says what replaces foreign keys and transactions.
- `api_contract_file`: `none` means phase 6 writes only `06-api.md`.
- `events_messaging = none`: there are no outbox tables, and cross-context policies call the other context's published operations synchronously, as the context map says.
- Add a row only for a fact every phase needs. Anything else belongs in the brief.
