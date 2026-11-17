# 03 Database design: Purchasing (module `pur`)

Part of [03-db-design.md](03-db-design.md). The shared conventions are D3-1 to D3-15 there.

## Inputs
- docs/design/02-tactical-purchasing.md: Aggregates (LowStockThreshold, ReorderSuggestion), Entities and value objects, Commands, Domain events, Queries and read models (ListReorderSuggestions, KnownProducts, KnownWarehouses, KnownAvailability), Decisions D2-1 to D2-12, Open questions Q2-1 to Q2-9.
- docs/design/03-db-design.md: Decisions D3-1 to D3-15, Open questions Q3-1 to Q3-8.

## Decisions
| Id | Decision | Why | Source |
|---|---|---|---|
| D3-P1 | The value objects AvailabilitySnapshot, TriggerSnapshot and SuggestionDecision are embedded columns, because each aggregate holds one of each. | DB-03: a single value object is embedded. | pur Entities |
| D3-P2 | `is_below` is stored as 02 says. A CHECK ties it to `last_available < quantity`, so it can never drift from its definition. | pur Entities: is_below is derived. | REQ-13, pur D2-3 |
| D3-P3 | `pur_reorder_suggestion.threshold_id` has an FK to `pur_low_stock_threshold` (same module) with ON DELETE RESTRICT. Thresholds are never deleted (pur Q2-6). | DB-04 inside a module. | pur Aggregates |

## Open questions
| Id | Question | Why it matters | Proposed default |
|---|---|---|---|
| Q3-P1 | Should `pur_known_product` keep the product ULID as well as the SKU? It depends on Q3-1. | It decides the key of the read model. | Key on `sku`, and also keep `product_id`, which is unique too. |

## Tables
### Table: pur_low_stock_threshold (module: Purchasing)
Aggregate: LowStockThreshold (root)

| Column | Type | Null | Default | Constraint | Notes (invariant / REQ) |
|---|---|---|---|---|---|
| threshold_id | CHAR(26) | NOT NULL | - | PK | ULID (pur D2-12) |
| sku | VARCHAR(64) ascii_bin | NOT NULL | - | UNIQUE with warehouse_id | 02 field `sku_id` (D3-12, Q3-1) |
| warehouse_id | CHAR(26) | NOT NULL | - | - | Catalog warehouse |
| quantity | BIGINT | NOT NULL | - | CHECK >= 0 | ThresholdQuantity. Zero disables suggestions (pur Q2-4, *proposed*) |
| last_available | BIGINT | NULL | NULL | CHECK >= 0 | AvailabilitySnapshot.available. NULL means no availability is known yet |
| last_source_version | BIGINT | NULL | NULL | CHECK | source_order = Stock version (D3-13). NULL together with last_available |
| last_source_event_id | CHAR(26) | NULL | NULL | CHECK | source_event_id. NULL together with last_available |
| last_received_at | DATETIME(6) | NULL | NULL | CHECK | UTC. NULL together with last_available |
| is_below | BOOLEAN | NOT NULL | FALSE | CHECK | Derived (D3-P2) |
| version | BIGINT | NOT NULL | 1 | CHECK >= 1 | Optimistic concurrency (pur D2-11) |
| updated_at | DATETIME(6) | NOT NULL | - | - | UTC |
- PK threshold_id
- REF sku -> Catalog.Product (id only, no FK)
- REF warehouse_id -> Catalog.Warehouse (id only, no FK)
- UNIQUE uq_pur_threshold_sku_wh (sku, warehouse_id): one threshold per SKU and warehouse (REQ-12). It also serves RecordAvailability's lookup by the AvailabilityChanged key
- CHECK ck_pur_threshold_qty: quantity >= 0 AND version >= 1
- CHECK ck_pur_threshold_snapshot: (last_available IS NULL AND last_source_version IS NULL AND last_source_event_id IS NULL AND last_received_at IS NULL) OR (last_available >= 0 AND last_source_version IS NOT NULL AND last_source_event_id IS NOT NULL AND last_received_at IS NOT NULL)
- CHECK ck_pur_threshold_below: is_below = (last_available IS NOT NULL AND last_available < quantity)

### Table: pur_reorder_suggestion (module: Purchasing)
Aggregate: ReorderSuggestion (root)

| Column | Type | Null | Default | Constraint | Notes (invariant / REQ) |
|---|---|---|---|---|---|
| suggestion_id | CHAR(26) | NOT NULL | - | PK | ULID (pur D2-12) |
| sku | VARCHAR(64) ascii_bin | NOT NULL | - | - | D3-12 |
| warehouse_id | CHAR(26) | NOT NULL | - | - | Catalog warehouse |
| threshold_id | CHAR(26) | NOT NULL | - | FK | D3-P3 |
| status | ENUM('Raised','Accepted','Dismissed') | NOT NULL | 'Raised' | - | SuggestionStatus (REQ-15, REQ-16) |
| threshold_quantity | BIGINT | NOT NULL | - | CHECK >= 0 | TriggerSnapshot |
| available_at_trigger | BIGINT | NOT NULL | - | CHECK >= 0 | TriggerSnapshot |
| detected_at | DATETIME(6) | NOT NULL | - | - | TriggerSnapshot, UTC |
| raised_at | DATETIME(6) | NOT NULL | - | - | UTC |
| decided_by | VARCHAR(128) ascii_bin | NULL | NULL | CHECK | SuggestionDecision. NULL means not yet decided (Q3-6) |
| decided_at | DATETIME(6) | NULL | NULL | CHECK | NULL means not yet decided |
| note | VARCHAR(1000) | NULL | NULL | - | NULL means no note was given (pur Entities, Q3-6) |
| raised_marker | TINYINT | NULL | generated | PERSISTENT AS (IF(status = 'Raised', 1, NULL)) | Used only by the open-suggestion key (D3-15) |
| version | BIGINT | NOT NULL | 1 | CHECK >= 1 | pur D2-11 |
- PK suggestion_id
- FK threshold_id -> pur_low_stock_threshold(threshold_id) ON DELETE RESTRICT
- REF sku -> Catalog.Product (id only, no FK)
- REF warehouse_id -> Catalog.Warehouse (id only, no FK)
- UNIQUE uq_pur_suggestion_open (sku, warehouse_id, raised_marker): at most one Raised suggestion per SKU and warehouse. A duplicate maps to SUGGESTION_ALREADY_OPEN (pur D2-5)
- CHECK ck_pur_suggestion_decision: (status = 'Raised' AND decided_by IS NULL AND decided_at IS NULL AND note IS NULL) OR (status <> 'Raised' AND decided_by IS NOT NULL AND decided_at IS NOT NULL)
- CHECK ck_pur_suggestion_qty: threshold_quantity >= 0 AND available_at_trigger >= 0 AND available_at_trigger < threshold_quantity AND version >= 1
- IDX ix_pur_suggestion_threshold (threshold_id): serves the FK
- IDX ix_pur_suggestion_list (status, raised_at, suggestion_id): serves ListReorderSuggestions by status, newest first (Q3-7, *proposed*)
- IDX uq_pur_suggestion_open (sku, warehouse_id, ...): serves the optional SKU and warehouse filter (Q3-7)

### Table: pur_known_product (module: Purchasing)
Aggregate: read model KnownProducts

| Column | Type | Null | Default | Constraint | Notes (invariant / REQ) |
|---|---|---|---|---|---|
| sku | VARCHAR(64) ascii_bin | NOT NULL | - | PK | SKU_NOT_FOUND pre-check (pur D2-8) |
| product_id | CHAR(26) | NOT NULL | - | UNIQUE | From ProductRegistered (Q3-P1) |
| updated_at | DATETIME(6) | NOT NULL | - | - | UTC |
- PK sku
- REF product_id -> Catalog.Product (id only, no FK)
- UNIQUE uq_pur_known_product_id (product_id)
- Rebuilt by replaying `stockroom.cat.product_registered`

### Table: pur_known_warehouse (module: Purchasing)
Aggregate: read model KnownWarehouses

| Column | Type | Null | Default | Constraint | Notes (invariant / REQ) |
|---|---|---|---|---|---|
| warehouse_id | CHAR(26) | NOT NULL | - | PK | From WarehouseRegistered |
| updated_at | DATETIME(6) | NOT NULL | - | - | UTC |
- PK warehouse_id
- REF warehouse_id -> Catalog.Warehouse (id only, no FK)
- Rebuilt by replaying `stockroom.cat.warehouse_registered`

### Table: pur_known_availability (module: Purchasing)
Aggregate: read model KnownAvailability

| Column | Type | Null | Default | Constraint | Notes (invariant / REQ) |
|---|---|---|---|---|---|
| sku | VARCHAR(64) ascii_bin | NOT NULL | - | PK | From AvailabilityChanged |
| warehouse_id | CHAR(26) | NOT NULL | - | PK | From AvailabilityChanged |
| available | BIGINT | NOT NULL | - | CHECK >= 0 | Seeds a new threshold only (pur D2-9) |
| source_version | BIGINT | NOT NULL | - | CHECK >= 1 | Upsert only if it is newer (D3-13) |
| updated_at | DATETIME(6) | NOT NULL | - | - | UTC |
- PK sku, warehouse_id
- REF sku -> Catalog.Product (id only, no FK)
- REF warehouse_id -> Catalog.Warehouse (id only, no FK)
- CHECK ck_pur_known_avail: available >= 0 AND source_version >= 1
- Rebuilt by replaying `stockroom.stk.availability_changed`, keeping the highest source_version per key

### Table: pur_outbox (module: Purchasing)
Aggregate: outbox

| Column | Type | Null | Default | Constraint | Notes (invariant / REQ) |
|---|---|---|---|---|---|
| event_id | CHAR(26) | NOT NULL | - | PK | ULID. Equals the payload event_id |
| aggregate_type | ENUM('LowStockThreshold','ReorderSuggestion') | NOT NULL | - | - | Emitter |
| aggregate_id | CHAR(26) | NOT NULL | - | - | threshold_id or suggestion_id |
| event_type | ENUM('LowStockThresholdSet','LowStockDetected','AvailabilityRecovered','ReorderSuggestionRaised','ReorderSuggestionAccepted','ReorderSuggestionDismissed') | NOT NULL | - | - | 02 names. The first three are internal (pur D2-10) |
| subject | VARCHAR(128) ascii_bin | NOT NULL | - | CHECK prefix | For example `stockroom.pur.low_stock_detected` (D3-7) |
| payload | JSON | NOT NULL | - | CHECK JSON_VALID | Payload per pur Domain events |
| occurred_at | DATETIME(6) | NOT NULL | - | - | UTC. Same transaction as the change (DB-05) |
| published_at | DATETIME(6) | NULL | NULL | - | NULL means not yet relayed |
- PK event_id
- CHECK ck_pur_outbox_subject: subject LIKE 'stockroom.pur.%'
- CHECK ck_pur_outbox_payload: JSON_VALID(payload)
- IDX ix_pur_outbox_pending (published_at, event_id): serves the relay scan and the purge (Q3-3)

### Table: pur_inbox (module: Purchasing)
Aggregate: inbox

| Column | Type | Null | Default | Constraint | Notes (invariant / REQ) |
|---|---|---|---|---|---|
| event_id | CHAR(26) | NOT NULL | - | PK | Dedup of AvailabilityChanged, Catalog events and its own LowStockDetected (D3-9) |
| subject | VARCHAR(128) ascii_bin | NOT NULL | - | - | Source subject |
| processed_at | DATETIME(6) | NOT NULL | - | - | UTC. Same transaction as the handler's change |
- PK event_id
- IDX ix_pur_inbox_processed (processed_at): serves the retention purge (Q3-3)

## Enforced in code
| Invariant | Why not in the store | Where enforced |
|---|---|---|
| LowStockDetected is emitted only on a crossing to below (REQ-13, pur D2-3) | It compares the old row with the new one. | The LowStockThreshold aggregate. The is_below CHECK keeps the stored state consistent |
| An older availability never replaces a newer one (pur Q2-1) | It compares with the stored version. | RecordAvailability: `last_source_version < incoming version`, else STALE_AVAILABILITY |
| A decided suggestion never changes again (REQ-15, REQ-16) | A CHECK can't see the previous value. | ReorderSuggestion. Updates use `WHERE status = 'Raised' AND version = ?` |
| ReorderSuggestion is created only by policy (REQ-14, pur D2-6) | Who may call is not a data rule. | No API operation; RaiseSuggestionOnLowStock only |
| SKU and warehouse are known (pur D2-8) | They are another module's data (DB-01). | Pre-check against pur_known_product and pur_known_warehouse |

## Caches
| Cache | Key | TTL | Invalidation | Source |
|---|---|---|---|---|
| none | - | - | - | ListReorderSuggestions reads the source table (pur Queries). |
