---
name: db-design-erd
description: Phases 3 and 4 of a backend design. Maps the tactical design's aggregates to a store (a schema per module, types, constraints, indexes, outbox and inbox when events are used), then draws the ERD in the profile's diagram format. Writes 03-db-design.md, 04-erd.md. Not for migrations.
model: opus
allowed-tools: Read Glob Grep Write Edit
---

# db-design-erd

Model: opus for phase 3, because schema choices protect the invariants. The diagram-writer runs the ERD part (phase 4) on sonnet.

Source: the reflexes in step 3 adapt data-modeling-discipline (backend-design plugin, MIT): invariants go into the schema, types are tight, not-null by default, no soft delete by reflex, and indexes are part of the schema.

Read first: `project-profile.md` (database, naming_convention, id_convention, events_messaging, architecture_style). From each `02-tactical-*.md` read Aggregates, Entities and value objects, Commands (Fails when), Domain events and Queries and read models. Also read the project rules file if the profile names one: rules about schemas and naming override the defaults.

## Phase 3: `03-db-design.md` (split into `03-db-design-<module>.md` if over 300 lines)

1. **Module per context.** Each bounded context owns one schema or namespace, unless the profile or project rules say otherwise. A project rule such as "one shared schema with table prefixes" wins: record it under Decisions as an override. Only the owning module writes its tables.
2. **Map the aggregates.** An aggregate root gets one table (or one document, item or node in a non-relational store; see [references/non-relational.md](references/non-relational.md)). Child entities get tables in the same module, with a foreign key to the root. Value objects become embedded columns, or an owned table when there are many of them. Every aggregate from 02 has a home.
3. **Constraints from invariants.** Each invariant in 02 is either enforced by the store or listed under "Enforced in code" with a reason. Use not-null by default (and say what a nullable column means), unique, check, enumerated sets, and foreign keys **inside the module only**, each with an explicit on-delete choice. Types are tight: no free text for dates, ids, money or enumerated sets; money is never floating point; time is zoned or UTC. Aggregate roots carry a `version` column for optimistic concurrency. Do not soft delete by reflex. Prefer hard delete, an archive table, or a lifecycle state, and say why.
4. **Cross-context references.** A reference to another context's aggregate is a plain id column and is listed as `REF`. **Never use a foreign key across modules.**
5. **Indexes.** Index every foreign key, every unique business key, and every filter or sort used by a query or read model in 02.
6. **Read models and caches.** A read model gets its own table, marked `Aggregate: read model <Name>`, rebuilt from its source. A cache in memory or an external cache gets no table: list it under "Caches", with its key, TTL and invalidation.
7. **Messaging.** Only when the profile's `events_messaging` uses events: an outbox table in **each module that emits integration events**, written in the same transaction as the state change. Each consuming module gets an inbox or deduplication table keyed by message id. Follow the profile's approach. If it names no mechanism, raise an open question; never invent a broker.
8. **Naming and ids.** Follow `naming_convention` and `id_convention` exactly. Where the profile is silent, write the choice as an open question with a proposed default.

Format (a script reads it):

```markdown
# 03 Database design
## Inputs / ## Decisions / ## Open questions
## Modules
| Module | Context | Schema or namespace | Tables |
## Tables
### Table: <physical_name> (module: <Context>)
Aggregate: <AggregateName> (root | child of <Root> | read model <Name> | outbox | inbox)
| Column | Type | Null | Default | Constraint | Notes (invariant / REQ) |
- PK <cols>
- FK <col> -> <physical_table>(<col>) ON DELETE <RESTRICT|CASCADE|SET NULL>
- REF <col> -> <OtherContext>.<Aggregate> (id only, no FK)
- UNIQUE <name> (<cols>)
- CHECK <name>: <expression>
- IDX <name> (<cols>) — serves <query>
## Enforced in code
| Invariant | Why not in the store | Where enforced |
## Caches
| Cache | Key | TTL | Invalidation | Source |
```

## Phase 4: `04-erd.md`

Draw from 03 only, in the profile's `diagram_format` (syntax in [references/erd-notation.md](references/erd-notation.md)). Draw one diagram per module, with every table and column marked PK, FK or REF, plus one overview diagram that shows the modules and their cross-module `REF`s as **dotted, labelled `ref`** lines, never as foreign-key relationships. Every table in 03 appears by its exact physical name. If the format can't express something, say so in a note.

## Self-check (put this in your reply)

Phase 3: DB-01 to DB-11, DOC-01 to DOC-04, and the project rules on storage or naming. Phase 4: ERD-01 and DOC-01. Mark each PASS or FAIL, with evidence. Fix MUST failures before you reply.

Reply in at most 300 words: the files, the modules and table counts, the overrides applied, the open questions (top 3), and the self-check.

## Fix mode

When the prompt gives findings, fix only those findings, with the smallest change, and add `Fixed F<n>` under Decisions. Business decisions go to Open questions.
