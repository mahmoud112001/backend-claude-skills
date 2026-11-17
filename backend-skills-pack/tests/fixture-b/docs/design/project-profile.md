# Project profile: Stockroom

## Inputs
README.md, ARCHITECTURE.md, go.mod, docker-compose.yml, proto/stockroom/v1/stockroom.proto, internal/stock/stock.go, docs/context.puml. Default rulebook read for override detection.

## Decisions
D0-P1 database is relational / MariaDB: compose runs image `mariadb:11.4` and go.mod has the MySQL driver (compose names the engine, go.mod only confirms the driver).
D0-P2 architecture_style is `microservices`, asked from the user (no file stated it). R1 still binds: one shared `stockroom` schema, each service owns only its own prefixed tables.
D0-P3 version_control is `git` as told by the caller (root inside repo D:/I-fikra/backend-claude-skills), not detected from a file in the root.

## Open questions
- Q1 What is the architecture style (modular monolith with one deployable and modules per context, or separate services)? Proposed default: modular monolith, since R1 puts all modules in one schema.
- Q2 What are the three-letter module codes beyond the examples `cat_`, `stk_`, `pur_` in R1? Proposed: set in phase 1 from the contexts.

## Profile
| Field | Value | Source |
|---|---|---|
| project_name | Stockroom | detected: README.md:1 |
| prototype | README.md, proto/stockroom/v1/stockroom.proto, internal/stock/stock.go, docs/context.puml (readme + code stub + spec; no UI) | detected: README.md:3 |
| language_framework | Go 1.22, gRPC (google.golang.org/grpc v1.67.1, protobuf v1.35.1) | detected: go.mod:3, go.mod:9 |
| database | relational / MariaDB 11.4 | detected: docker-compose.yml:10 |
| api_style | gRPC | detected: README.md:3, proto/stockroom/v1/stockroom.proto:7 |
| api_contract_file | proto (proto/stockroom/v1/stockroom.proto) | detected: proto/stockroom/v1/stockroom.proto:1 |
| architecture_style | microservices (one service per bounded context; per R1 all services share the `stockroom` schema and each owns only its prefixed tables) | asked |
| events_messaging | outbox (per-module table, same transaction) + NATS JetStream; subjects `stockroom.<module>.<event_name>`; consumers deduplicate by event id | detected: ARCHITECTURE.md:8 |
| id_convention | ULID string, generated in the domain layer, never by the database | detected: ARCHITECTURE.md:6 |
| naming_convention | tables and columns snake_case; table name prefixed with module code + `_`; protobuf messages PascalCase, fields snake_case | detected: ARCHITECTURE.md:5, ARCHITECTURE.md:10 |
| error_format | gRPC canonical status code + `google.rpc.ErrorInfo` detail with UPPER_SNAKE_CASE `reason` (e.g. INSUFFICIENT_STOCK) | detected: ARCHITECTURE.md:7 |
| diagram_format | plantuml | detected: ARCHITECTURE.md:9 |
| project_root | D:/I-fikra/backend-claude-skills/backend-skills-pack/tests/fixture-b | asked (caller) |
| output_folder | docs/design/ | asked (caller) |
| project_rules_file | ARCHITECTURE.md | detected: ARCHITECTURE.md:1 |
| version_control | git | asked (caller) |

## Rule overrides
| Project rule (file:line) | Default rule overridden | Effect |
|---|---|---|
| ARCHITECTURE.md:5 (R1 Storage layout) | DB-02 (each context's tables in their own schema) | All modules share one schema `stockroom`; isolation is by table-name prefix of the module's three-letter code. Modules never read or write another module's tables, so the "only that module writes" part of DB-02 still holds. R1 states it is the only default rule it overrides. |
