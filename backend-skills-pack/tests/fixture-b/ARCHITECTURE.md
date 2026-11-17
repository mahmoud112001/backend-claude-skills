# Architecture rules

These rules are binding for every design and code change in Stockroom.

- **R1 Storage layout.** All modules share one database schema, `stockroom`. Each table name starts with its module's three-letter code and an underscore (for example `cat_`, `stk_`, `pur_`). Modules never read or write another module's tables. This rule overrides default rule DB-02 (one schema per module); it is the only default rule this file overrides.
- **R2 Ids.** Every id is a ULID string, generated in the domain layer, never by the database.
- **R3 Errors.** gRPC errors carry a canonical status code plus a `google.rpc.ErrorInfo` detail whose `reason` is UPPER_SNAKE_CASE (for example `INSUFFICIENT_STOCK`).
- **R4 Events.** Integration events are written to a per-module outbox table in the same transaction and relayed to NATS JetStream. Subjects are `stockroom.<module>.<event_name>`. Consumers deduplicate by event id.
- **R5 Diagrams.** All diagrams are PlantUML.
- **R6 Naming.** Tables and columns use snake_case; protobuf messages use PascalCase and fields snake_case.
