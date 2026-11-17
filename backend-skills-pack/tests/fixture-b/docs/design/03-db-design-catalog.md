# 03 Database design: Catalog (module `cat`)

Part of [03-db-design.md](03-db-design.md). The shared conventions are D3-1 to D3-15 there.

## Inputs
- docs/design/02-tactical-catalog.md: Aggregates (Product, Warehouse, Bin), Entities and value objects, Commands, Domain events, Decisions D2-1 to D2-8, Open questions Q2-1 to Q2-8.
- docs/design/03-db-design.md: Decisions D3-1 to D3-15, Open questions Q3-1 to Q3-8.

## Decisions
| Id | Decision | Why | Source |
|---|---|---|---|
| D3-C1 | `cat_bin.warehouse_id` has an FK to `cat_warehouse` with ON DELETE RESTRICT. This is allowed because both tables are in the Catalog module. | It makes "the warehouse exists at registration" a store guarantee. Warehouses are never retired (01 Q1-10). | cat D2-2 |
| D3-C2 | The uniqueness set validations are UNIQUE keys. The command maps a duplicate-key error to `*_ALREADY_EXISTS`. | cat D2-3 calls the unique key the final guard. | cat D2-3 |

## Open questions
| Id | Question | Why it matters | Proposed default |
|---|---|---|---|
| Q3-C1 | Is the product `code` unique? (cat Q2-3) | It decides whether `uq_cat_product_code` exists. | Yes, unique (the cat Q2-3 default). The key is applied and is *proposed*. |

## Tables
### Table: cat_product (module: Catalog)
Aggregate: Product (root)

| Column | Type | Null | Default | Constraint | Notes (invariant / REQ) |
|---|---|---|---|---|---|
| product_id | CHAR(26) | NOT NULL | - | PK | ULID, domain-generated (R2) |
| sku | VARCHAR(64) ascii_bin | NOT NULL | - | UNIQUE | Stored upper case. Format per cat Q2-1 (REQ-1) |
| code | VARCHAR(64) ascii_bin | NOT NULL | - | UNIQUE | ProductCode (REQ-1, Q3-C1) |
| name | VARCHAR(200) | NOT NULL | - | CHECK not blank | ProductName, at most 200 characters (cat Entities) |
| unit_of_measure | VARCHAR(16) ascii_bin | NOT NULL | - | - | Allowed list checked in code (cat Q2-2) |
| registered_at | DATETIME(6) | NOT NULL | - | - | UTC |
| version | BIGINT | NOT NULL | 1 | CHECK >= 1 | Optimistic concurrency (DB-08). Stays 1 while Product is immutable (cat D2-7) |
- PK product_id
- UNIQUE uq_cat_product_sku (sku)
- UNIQUE uq_cat_product_code (code)
- CHECK ck_cat_product_fields: sku <> '' AND code <> '' AND CHAR_LENGTH(TRIM(name)) > 0 AND unit_of_measure <> ''

### Table: cat_warehouse (module: Catalog)
Aggregate: Warehouse (root)

| Column | Type | Null | Default | Constraint | Notes (invariant / REQ) |
|---|---|---|---|---|---|
| warehouse_id | CHAR(26) | NOT NULL | - | PK | ULID (R2) |
| code | VARCHAR(64) ascii_bin | NOT NULL | - | UNIQUE | WarehouseCode (REQ-2, cat Q2-4) |
| name | VARCHAR(200) | NOT NULL | - | CHECK not blank | WarehouseName (cat Q2-4) |
| registered_at | DATETIME(6) | NOT NULL | - | - | UTC |
| version | BIGINT | NOT NULL | 1 | CHECK >= 1 | DB-08 |
- PK warehouse_id
- UNIQUE uq_cat_warehouse_code (code)
- CHECK ck_cat_warehouse_fields: code <> '' AND CHAR_LENGTH(TRIM(name)) > 0

### Table: cat_bin (module: Catalog)
Aggregate: Bin (root)

| Column | Type | Null | Default | Constraint | Notes (invariant / REQ) |
|---|---|---|---|---|---|
| bin_id | CHAR(26) | NOT NULL | - | PK | ULID (R2) |
| warehouse_id | CHAR(26) | NOT NULL | - | FK | Fixed at registration (REQ-3) |
| code | VARCHAR(64) ascii_bin | NOT NULL | - | UNIQUE with warehouse_id | BinCode, unique within its warehouse (REQ-3, cat Q2-5) |
| registered_at | DATETIME(6) | NOT NULL | - | - | UTC |
| version | BIGINT | NOT NULL | 1 | CHECK >= 1 | DB-08 |
- PK bin_id
- FK warehouse_id -> cat_warehouse(warehouse_id) ON DELETE RESTRICT
- UNIQUE uq_cat_bin_warehouse_code (warehouse_id, code)
- CHECK ck_cat_bin_code: code <> ''
- IDX uq_cat_bin_warehouse_code (warehouse_id, code): its leading column also indexes the FK

### Table: cat_outbox (module: Catalog)
Aggregate: outbox

| Column | Type | Null | Default | Constraint | Notes (invariant / REQ) |
|---|---|---|---|---|---|
| event_id | CHAR(26) | NOT NULL | - | PK | ULID. Equals the payload event_id |
| aggregate_type | ENUM('Product','Warehouse','Bin') | NOT NULL | - | - | Emitting aggregate |
| aggregate_id | CHAR(26) | NOT NULL | - | - | Id of the aggregate |
| event_type | ENUM('ProductRegistered','WarehouseRegistered','BinRegistered') | NOT NULL | - | - | 02 event name (D3-7) |
| subject | VARCHAR(128) ascii_bin | NOT NULL | - | CHECK prefix | For example `stockroom.cat.product_registered` (R4) |
| payload | JSON | NOT NULL | - | CHECK JSON_VALID | Payload per cat Domain events |
| occurred_at | DATETIME(6) | NOT NULL | - | - | UTC. Same transaction as the state change (DB-05) |
| published_at | DATETIME(6) | NULL | NULL | - | NULL means not yet relayed to JetStream |
- PK event_id
- CHECK ck_cat_outbox_subject: subject LIKE 'stockroom.cat.%'
- CHECK ck_cat_outbox_payload: JSON_VALID(payload)
- IDX ix_cat_outbox_pending (published_at, event_id): serves the relay scan for unpublished rows in ULID order and the retention purge (Q3-3)

## Enforced in code
| Invariant | Why not in the store | Where enforced |
|---|---|---|
| SKU format (cat Q2-1) | The format is still an open question. A REGEXP CHECK would hard-code an unconfirmed rule. | Sku value object |
| Unit of measure is in the allowed list (cat Q2-2) | The list is configured and would need a migration for every change. | UnitOfMeasure value object |
| Product, Warehouse and Bin are immutable once registered (cat D2-7) | The store can't forbid UPDATE without triggers. | The Catalog repository has no update path, and no command edits these aggregates |

## Caches
| Cache | Key | TTL | Invalidation | Source |
|---|---|---|---|---|
| none | - | - | - | Catalog has no query (cat D2-8). |
