# Mapping aggregates to a non-relational store

Read this when the profile's `database` type is not relational. Keep the 03 format: write `### Collection:`, `### Item:` or `### Node:` in place of `### Table:`. The `(module: <Context>)` suffix and the `Aggregate:` line stay.

| Store type | Aggregate maps to | What replaces FK / constraints | Transaction boundary |
|---|---|---|---|
| Document | one document per aggregate root, with children and value objects embedded | references by id; validation schema on the collection; unique indexes | one document |
| Key-value / wide-column | one item (or one partition) per aggregate, with the key designed from the access patterns in 02 | key design; conditional writes for invariants | one item or partition |
| Graph | aggregate root node; children as nodes linked by ownership edges | uniqueness/existence constraints where supported; cross-context links are id properties, not edges | per write query |
| Event store | one stream per aggregate instance | invariants checked in the aggregate before append; expected-version on append | one stream append |

Rules that still apply: DB-01 (no store-level link across modules; use plain id fields), DB-02, DB-03, DB-05 (an outbox or equivalent, such as a change stream with deduplication, when events are used), DB-06.
Say under Decisions what the store cannot enforce, and list each such invariant under "Enforced in code".
Indexes: one per query or read-model access pattern from 02. Name the pattern.
