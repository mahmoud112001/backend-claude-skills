# 03 Database design

This is the index file. The tables are in three module files, because one file would be over 300 lines (DOC-01). Those files are [03-db-design-catalog.md](03-db-design-catalog.md), [03-db-design-stock.md](03-db-design-stock.md) and [03-db-design-purchasing.md](03-db-design-purchasing.md).

## Inputs
- docs/design/project-profile.md: database relational / MariaDB 11.4; architecture_style microservices; events_messaging is a per-module outbox plus NATS JetStream with subjects `stockroom.<module>.<event_name>` and dedup by event id; id_convention ULID string from the domain layer; naming_convention snake_case with a module prefix; diagram_format plantuml.
- docs/design/01-strategic.md: Decisions D1-1 to D1-9 (module codes `cat`, `stk`, `pur` from D1-2; one service per context from D1-3; integration only through events from D1-4).
- docs/design/02-tactical-catalog.md, 02-tactical-stock.md, 02-tactical-purchasing.md: Aggregates, Entities and value objects, Commands, Domain events, Queries and read models, Decisions, Open questions.
- Rules: default-rulebook.md (DB-01 to DB-11, DOC-01 to DOC-04); ARCHITECTURE.md R1, R2, R4, R6.

## Decisions
| Id | Decision | Why | Source |
|---|---|---|---|
| D3-1 | **Override of DB-02 by R1.** All tables live in the one shared schema `stockroom`. Each table name starts with its module code: `cat_`, `stk_` or `pur_`. Only the owning service reads or writes its own tables. Each service gets its own MariaDB account, with table-level GRANTs on its own tables only (*proposed*). | R1 is binding and overrides DB-02 (one schema per module). Per-table grants make "only the owner touches it" checkable, because MariaDB grant wildcards cover schema names, not table names. | ARCHITECTURE.md:5; profile Rule overrides |
| D3-2 | Every table uses InnoDB and `utf8mb4`. The server runs with `sql_mode` including `STRICT_ALL_TABLES`, so that ENUM, NOT NULL and CHECK reject bad data instead of coercing it. | Strict mode is what makes the store-level constraints real. | *proposed* |
| D3-3 | Every id is `CHAR(26) CHARACTER SET ascii COLLATE ascii_bin` (written `CHAR(26)` below). An id has no database default and no AUTO_INCREMENT. Ids include the event ids in outboxes and inboxes. | R2: a ULID is generated in the domain layer, never by the database. | ARCHITECTURE.md:6 |
| D3-4 | Every timestamp is `DATETIME(6)` holding UTC. Each connection sets `time_zone = '+00:00'`. `TIMESTAMP` is not used. | The 02 files say UTC. `DATETIME` avoids session-zone conversion and the 2038 range limit. | 02 Entities (registered_at UTC); *proposed* |
| D3-5 | Quantities are `BIGINT` (signed int64), with a CHECK of `>= 0` wherever 02 says so. No money is stored. | Matches int64 in proto and stock.go (stk D2-11). | proto:21; stock.go:7 |
| D3-6 | A fixed enumerated set from 02 is a MariaDB `ENUM`, with values spelled exactly as in 02 (for example `Open`, `Raised`). Configured sets (unit of measure, adjustment reason code) are `VARCHAR`, validated in code. | A fixed set belongs in the store. A configured list would need a migration for every change (cat Q2-2, stk Q2-8). | 02 value objects |
| D3-7 | **One event naming form.** `event_type` holds the 02 event name in PascalCase (`AvailabilityChanged`). `subject` is `stockroom.<code>.<event_name>`, where event_name is the snake_case form of the event name (`stockroom.stk.availability_changed`, `stockroom.cat.product_registered`, `stockroom.pur.reorder_suggestion_raised`). | R4 subject form. One form in every module, as the caller asked; this keeps names consistent (DOC-04). | ARCHITECTURE.md:8; cat D2-5; stk Domain events; pur Domain events |
| D3-8 | There is an outbox in every module that emits: `cat_outbox`, `stk_outbox` and `pur_outbox`. A row is written in the same transaction as the state change. Stock writes only AvailabilityChanged, because its internal events have no consumer that needs the outbox: expiry is a durable sweep (stk D2-6). Purchasing also writes its internal events (pur D2-10). | DB-05; R4. | ARCHITECTURE.md:8; stk D2-6; pur D2-10 |
| D3-9 | Every consuming module has an inbox keyed by `event_id`: `stk_inbox` and `pur_inbox`. The inbox row is inserted in the same transaction as the handler's change. A duplicate key means the event was already handled, so the handler acks it. Catalog consumes nothing (cat D2-6), so it has no inbox. | DB-05; R4 "consumers deduplicate by event id". | ARCHITECTURE.md:8 |
| D3-10 | No soft delete. Closed reservations and decided suggestions are kept as lifecycle states (stk D2-7, pur D2-7). Catalog rows are never deleted (cat D2-7). Published outbox rows and old inbox rows are hard-deleted after a retention period (Q3-3). | DB-11: history is a lifecycle state, and transport rows have no business meaning. | stk D2-7; pur D2-7; cat D2-7 |
| D3-11 | A child FK inside an aggregate is `ON DELETE CASCADE`, because the child shares the root's lifecycle (TAC-08). An FK between two aggregates of one module is `ON DELETE RESTRICT`. No FK crosses a module. | DB-01, DB-04. | rulebook TAC-08, DB-01 |
| D3-12 | Stock and Purchasing store the Catalog SKU value in a column named `sku`. The Purchasing 02 field `sku_id` maps to `sku`, because AvailabilityChanged carries `sku` and Purchasing keys on it (Q3-1). | Catalog says Stock and Purchasing key on the SKU (cat D2-4). | cat D2-4; stk Domain events |
| D3-13 | Purchasing uses AvailabilityChanged `version` (the WarehouseStock version, stk D2-9) as the ordering field of AvailabilitySnapshot `source_order`. This answers pur Q2-1 at the storage level. | Stock already publishes a per SKU and warehouse sequence. | stk D2-9; pur Q2-1 |
| D3-14 | The table `stk_stock_movement` records each ReceiveGoods and AdjustStock under its request id. This makes a retry a no-op (stk D2-12) and keeps the StockAdjusted facts (Q3-5). | The 02 file needs a durable record of request ids. No 02 table held them. | stk D2-12; stk Domain events |
| D3-15 | "At most one Raised suggestion per SKU and warehouse" is enforced with a generated column `raised_marker`, which is 1 when the status is Raised and NULL otherwise, plus a UNIQUE key on (`sku`, `warehouse_id`, `raised_marker`). | MariaDB has no partial index. A unique key allows any number of NULLs. | pur D2-5 |

## Open questions
| Id | Question | Why it matters | Proposed default |
|---|---|---|---|
| Q3-1 | In Purchasing 02, is `sku_id` the Catalog product ULID or the SKU value? | AvailabilityChanged carries `sku`, not a product id, so the threshold key must match it. | The SKU value, in column `sku` (D3-12). Rename the field in pur 02. |
| Q3-2 | What are the maximum length and character set of the caller-supplied `request_id` and `shipment_ref`? | They set the column types and the unique key. | `VARCHAR(128)`, ascii, case-sensitive (`ascii_bin`). |
| Q3-3 | How long are published outbox rows and processed inbox rows kept? | Inbox retention must exceed the JetStream redelivery window, or a late duplicate is applied twice. | Outbox: 7 days after `published_at`. Inbox: 30 days. |
| Q3-4 | Do ReceiveGoods and AdjustStock request ids share one namespace with ReserveStock request ids? | It decides whether there is one unique key or two. | Separate namespaces: one unique key on `stk_reservation.request_id` and another on `stk_stock_movement.request_id`. |
| Q3-5 | Is the receipt and adjustment record (`stk_stock_movement`) kept forever, as an audit trail? | Storage growth; audit needs. | Kept forever (D3-14). |
| Q3-6 | What are the type of `decided_by` (an actor id from identity) and the maximum length of the decision `note`? | Identity is not designed (D1-8). | `decided_by` `VARCHAR(128)`; `note` up to 1000 characters. |
| Q3-7 | Which filters and sort does ListReorderSuggestions need? The 02 file gives none. | It sets the indexes. | Filter by status, optionally by SKU and warehouse. Order by `raised_at` descending, then `suggestion_id`. |
| Q3-8 | What are the lengths and case rules of warehouse name, product code, warehouse code and bin code? (cat Q2-1 to Q2-5) | They set the column types and unique-key collation. | Codes: `VARCHAR(64)` `ascii_bin`. Names: `VARCHAR(200)` in `utf8mb4`. SKU: stored upper case (cat Q2-1). |

## Modules
| Module | Context | Schema or namespace | Tables |
|---|---|---|---|
| cat | Catalog | `stockroom` (shared, prefix `cat_`, R1) | cat_product, cat_warehouse, cat_bin, cat_outbox |
| stk | Stock | `stockroom` (shared, prefix `stk_`, R1) | stk_warehouse_stock, stk_stock_level, stk_reservation, stk_reservation_allocation, stk_stock_movement, stk_known_product, stk_known_warehouse, stk_known_bin, stk_outbox, stk_inbox |
| pur | Purchasing | `stockroom` (shared, prefix `pur_`, R1) | pur_low_stock_threshold, pur_reorder_suggestion, pur_known_product, pur_known_warehouse, pur_known_availability, pur_outbox, pur_inbox |

## Tables
See the module files linked at the top. Each table appears in exactly one of them.

## Enforced in code
Each module file has its own list. Rules that hold across all modules:

| Invariant | Why not in the store | Where enforced |
|---|---|---|
| Only the owning service writes its prefixed tables (R1) | The schema is shared, so there is no FK or schema boundary. | Per-service DB account with table-level grants (D3-1); repositories per module |
| Ids are ULIDs generated in the domain layer (R2) | The database must not generate ids. A format CHECK would add little over a fixed `CHAR(26)` ascii column. | Domain id factory in each service |

## Caches
| Cache | Key | TTL | Invalidation | Source |
|---|---|---|---|---|
| none | - | - | - | No 02 file defines a cache. Read models are tables in the module files. |
