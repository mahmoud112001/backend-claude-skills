# 03 Database design: Stock (module `stk`)

Part of [03-db-design.md](03-db-design.md). The shared conventions are D3-1 to D3-15 there.

## Inputs
- docs/design/02-tactical-stock.md: Aggregates (WarehouseStock), Entities and value objects, Commands, Domain events, Queries and read models (GetAvailability, KnownProducts, KnownWarehouses, KnownBins), Decisions D2-1 to D2-13, Open questions Q2-1 to Q2-11.
- docs/design/03-db-design.md: Decisions D3-1 to D3-15, Open questions Q3-1 to Q3-8.

## Decisions
| Id | Decision | Why | Source |
|---|---|---|---|
| D3-S1 | WarehouseStock maps to a root table plus three child tables: `stk_stock_level`, `stk_reservation` and `stk_stock_movement`. The BinAllocation value objects of a reservation are an owned table, `stk_reservation_allocation`, because a reservation has many of them. | Child entities live in the module with an FK to the root (DB-03). | stk D2-1, D2-2 |
| D3-S2 | Available is not a column. GetAvailability computes it as the sum of on_hand minus the sum of reserved, grouped by warehouse. | stk D2-3: storing it would make a second source of truth. | REQ-17, REQ-20 |
| D3-S3 | The per-bin rule `0 <= reserved <= on_hand` is a CHECK on `stk_stock_level`, so no write can break REQ-18 even if the code has a bug. | DB-04. | REQ-18, REQ-20 |
| D3-S4 | The reservation `closed_at` is NULL exactly when the status is `Open`. The expiry sweep uses the index (status, expires_at). | stk D2-6 says the sweep is durable. | REQ-19 |

## Open questions
| Id | Question | Why it matters | Proposed default |
|---|---|---|---|
| Q3-S1 | Should a StockLevel row whose on_hand and reserved are both 0 be deleted or kept? | Table growth versus losing the "bin once stocked" fact. | Keep it. A later receipt reuses the row. |

## Tables
### Table: stk_warehouse_stock (module: Stock)
Aggregate: WarehouseStock (root)

| Column | Type | Null | Default | Constraint | Notes (invariant / REQ) |
|---|---|---|---|---|---|
| warehouse_stock_id | CHAR(26) | NOT NULL | - | PK | ULID (R2) |
| sku | VARCHAR(64) ascii_bin | NOT NULL | - | UNIQUE with warehouse_id | Catalog SKU (D3-12) |
| warehouse_id | CHAR(26) | NOT NULL | - | - | Catalog warehouse |
| version | BIGINT | NOT NULL | 1 | CHECK >= 1 | Optimistic concurrency (stk D2-10). Published in AvailabilityChanged (stk D2-9) |
| created_at | DATETIME(6) | NOT NULL | - | - | UTC. Set by the first ReceiveGoods or AdjustStock |
- PK warehouse_stock_id
- REF sku -> Catalog.Product (id only, no FK)
- REF warehouse_id -> Catalog.Warehouse (id only, no FK)
- UNIQUE uq_stk_warehouse_stock_sku_wh (sku, warehouse_id): one WarehouseStock per SKU and warehouse (stk Aggregates)
- CHECK ck_stk_warehouse_stock_version: version >= 1
- IDX uq_stk_warehouse_stock_sku_wh (sku, warehouse_id): serves GetAvailability by SKU, with an optional warehouse filter

### Table: stk_stock_level (module: Stock)
Aggregate: WarehouseStock (child of WarehouseStock)

| Column | Type | Null | Default | Constraint | Notes (invariant / REQ) |
|---|---|---|---|---|---|
| stock_level_id | CHAR(26) | NOT NULL | - | PK | ULID |
| warehouse_stock_id | CHAR(26) | NOT NULL | - | FK | Root |
| bin_id | CHAR(26) | NOT NULL | - | UNIQUE with root | One row per bin (stock.go:7) |
| on_hand | BIGINT | NOT NULL | 0 | CHECK | REQ-18 |
| reserved | BIGINT | NOT NULL | 0 | CHECK | Equals the sum of the open allocations on this bin (in code) |
- PK stock_level_id
- FK warehouse_stock_id -> stk_warehouse_stock(warehouse_stock_id) ON DELETE CASCADE
- REF bin_id -> Catalog.Bin (id only, no FK)
- UNIQUE uq_stk_stock_level_bin (warehouse_stock_id, bin_id)
- CHECK ck_stk_stock_level_qty: reserved >= 0 AND on_hand >= reserved (REQ-18, REQ-20)
- IDX uq_stk_stock_level_bin (warehouse_stock_id, bin_id): serves the FK, aggregate load and GetAvailability sums

### Table: stk_reservation (module: Stock)
Aggregate: WarehouseStock (child of WarehouseStock)

| Column | Type | Null | Default | Constraint | Notes (invariant / REQ) |
|---|---|---|---|---|---|
| reservation_id | CHAR(26) | NOT NULL | - | PK | ULID. Returned to the caller (REQ-5) |
| warehouse_stock_id | CHAR(26) | NOT NULL | - | FK | Root |
| request_id | VARCHAR(128) ascii_bin | NOT NULL | - | UNIQUE | RequestId, unique across Stock (REQ-8, stk D2-4, Q3-2) |
| shipment_ref | VARCHAR(128) ascii_bin | NOT NULL | - | CHECK not empty | ShipmentRef (REQ-5, Q3-2) |
| quantity | BIGINT | NOT NULL | - | CHECK > 0 | stk D2-11 |
| status | ENUM('Open','Released','Picked','Expired') | NOT NULL | 'Open' | - | ReservationStatus (REQ-9, REQ-10, REQ-19) |
| reserved_at | DATETIME(6) | NOT NULL | - | - | UTC |
| expires_at | DATETIME(6) | NOT NULL | - | CHECK > reserved_at | Duration per stk Q2-1 |
| closed_at | DATETIME(6) | NULL | NULL | CHECK | NULL means still Open (D3-S4) |
- PK reservation_id
- FK warehouse_stock_id -> stk_warehouse_stock(warehouse_stock_id) ON DELETE CASCADE
- UNIQUE uq_stk_reservation_request (request_id)
- CHECK ck_stk_reservation_qty: quantity > 0 AND shipment_ref <> '' AND request_id <> ''
- CHECK ck_stk_reservation_times: expires_at > reserved_at
- CHECK ck_stk_reservation_closed: (status = 'Open') = (closed_at IS NULL)
- IDX ix_stk_reservation_root_status (warehouse_stock_id, status): serves the FK and loading the open reservations (stk D2-7)
- IDX ix_stk_reservation_expiry (status, expires_at): serves the ReservationExpiryPolicy sweep (stk D2-6)

### Table: stk_reservation_allocation (module: Stock)
Aggregate: WarehouseStock (child of WarehouseStock; owned value object BinAllocation of Reservation)

| Column | Type | Null | Default | Constraint | Notes (invariant / REQ) |
|---|---|---|---|---|---|
| reservation_id | CHAR(26) | NOT NULL | - | PK, FK | Owning reservation |
| bin_id | CHAR(26) | NOT NULL | - | PK | Bin chosen by the aggregate (stk D2-2, Q2-5) |
| quantity | BIGINT | NOT NULL | - | CHECK > 0 | BinAllocation quantity |
- PK reservation_id, bin_id
- FK reservation_id -> stk_reservation(reservation_id) ON DELETE CASCADE
- REF bin_id -> Catalog.Bin (id only, no FK)
- CHECK ck_stk_allocation_qty: quantity > 0
- IDX pk (reservation_id, bin_id): its leading column indexes the FK

### Table: stk_stock_movement (module: Stock)
Aggregate: WarehouseStock (child of WarehouseStock)

| Column | Type | Null | Default | Constraint | Notes (invariant / REQ) |
|---|---|---|---|---|---|
| movement_id | CHAR(26) | NOT NULL | - | PK | ULID |
| warehouse_stock_id | CHAR(26) | NOT NULL | - | FK | Root |
| bin_id | CHAR(26) | NOT NULL | - | - | Bin received into or counted |
| kind | ENUM('Receipt','Adjustment') | NOT NULL | - | - | ReceiveGoods or AdjustStock |
| request_id | VARCHAR(128) ascii_bin | NOT NULL | - | UNIQUE | Retry is a no-op (stk D2-12, Q3-4) |
| previous_on_hand | BIGINT | NOT NULL | - | CHECK >= 0 | Before the change |
| new_on_hand | BIGINT | NOT NULL | - | CHECK >= 0 | After the change. For an adjustment this is the counted quantity |
| difference | BIGINT | NOT NULL | - | CHECK | new_on_hand - previous_on_hand |
| reason_code | VARCHAR(32) ascii_bin | NULL | NULL | CHECK | NULL means a receipt, which has no reason. Code checked in code (stk Q2-8) |
| occurred_at | DATETIME(6) | NOT NULL | - | - | UTC |
- PK movement_id
- FK warehouse_stock_id -> stk_warehouse_stock(warehouse_stock_id) ON DELETE CASCADE
- REF bin_id -> Catalog.Bin (id only, no FK)
- UNIQUE uq_stk_stock_movement_request (request_id)
- CHECK ck_stk_movement_math: previous_on_hand >= 0 AND new_on_hand >= 0 AND difference = new_on_hand - previous_on_hand
- CHECK ck_stk_movement_kind: (kind = 'Receipt' AND difference > 0 AND reason_code IS NULL) OR (kind = 'Adjustment' AND reason_code IS NOT NULL AND reason_code <> '')
- IDX ix_stk_stock_movement_root (warehouse_stock_id, occurred_at): serves the FK

### Table: stk_known_product (module: Stock)
Aggregate: read model KnownProducts

| Column | Type | Null | Default | Constraint | Notes (invariant / REQ) |
|---|---|---|---|---|---|
| product_id | CHAR(26) | NOT NULL | - | PK | From ProductRegistered |
| sku | VARCHAR(64) ascii_bin | NOT NULL | - | UNIQUE | SKU pre-check (stk D2-8) |
| updated_at | DATETIME(6) | NOT NULL | - | - | UTC, the time of the projection |
- PK product_id
- REF product_id -> Catalog.Product (id only, no FK)
- UNIQUE uq_stk_known_product_sku (sku): serves the SKU_NOT_FOUND pre-check
- Rebuilt by replaying `stockroom.cat.product_registered` (upsert by product_id)

### Table: stk_known_warehouse (module: Stock)
Aggregate: read model KnownWarehouses

| Column | Type | Null | Default | Constraint | Notes (invariant / REQ) |
|---|---|---|---|---|---|
| warehouse_id | CHAR(26) | NOT NULL | - | PK | From WarehouseRegistered |
| updated_at | DATETIME(6) | NOT NULL | - | - | UTC |
- PK warehouse_id
- REF warehouse_id -> Catalog.Warehouse (id only, no FK)
- Rebuilt by replaying `stockroom.cat.warehouse_registered`

### Table: stk_known_bin (module: Stock)
Aggregate: read model KnownBins

| Column | Type | Null | Default | Constraint | Notes (invariant / REQ) |
|---|---|---|---|---|---|
| bin_id | CHAR(26) | NOT NULL | - | PK | From BinRegistered |
| warehouse_id | CHAR(26) | NOT NULL | - | - | Checks that a bin is in the warehouse (stk Q2-10) |
| updated_at | DATETIME(6) | NOT NULL | - | - | UTC |
- PK bin_id
- REF bin_id -> Catalog.Bin (id only, no FK)
- REF warehouse_id -> Catalog.Warehouse (id only, no FK)
- Rebuilt by replaying `stockroom.cat.bin_registered`

### Table: stk_outbox (module: Stock)
Aggregate: outbox

| Column | Type | Null | Default | Constraint | Notes (invariant / REQ) |
|---|---|---|---|---|---|
| event_id | CHAR(26) | NOT NULL | - | PK | ULID. Equals the payload event_id |
| aggregate_type | ENUM('WarehouseStock') | NOT NULL | - | - | Emitter |
| aggregate_id | CHAR(26) | NOT NULL | - | - | warehouse_stock_id |
| event_type | ENUM('AvailabilityChanged') | NOT NULL | - | - | Only the integration event (D3-8) |
| subject | VARCHAR(128) ascii_bin | NOT NULL | - | CHECK prefix | `stockroom.stk.availability_changed` (D3-7) |
| payload | JSON | NOT NULL | - | CHECK JSON_VALID | sku, warehouse_id, on_hand, reserved, available, version (stk D2-9) |
| occurred_at | DATETIME(6) | NOT NULL | - | - | UTC. Same transaction as the change (DB-05) |
| published_at | DATETIME(6) | NULL | NULL | - | NULL means not yet relayed |
- PK event_id
- CHECK ck_stk_outbox_subject: subject LIKE 'stockroom.stk.%'
- CHECK ck_stk_outbox_payload: JSON_VALID(payload)
- IDX ix_stk_outbox_pending (published_at, event_id): serves the relay scan and the purge (Q3-3)

### Table: stk_inbox (module: Stock)
Aggregate: inbox

| Column | Type | Null | Default | Constraint | Notes (invariant / REQ) |
|---|---|---|---|---|---|
| event_id | CHAR(26) | NOT NULL | - | PK | The consumed event's id. A duplicate key means already handled (D3-9) |
| subject | VARCHAR(128) ascii_bin | NOT NULL | - | - | For example `stockroom.cat.bin_registered` |
| processed_at | DATETIME(6) | NOT NULL | - | - | UTC. Same transaction as the read-model upsert |
- PK event_id
- IDX ix_stk_inbox_processed (processed_at): serves the retention purge (Q3-3)

## Enforced in code
| Invariant | Why not in the store | Where enforced |
|---|---|---|
| A reservation's quantity is at most the warehouse's available (REQ-6, REQ-7) | It is an aggregate over many rows. A CHECK sees only one row. | WarehouseStock.Reserve, under the version check (stk D2-10) |
| `reserved` of a bin equals the sum of the open allocations on that bin. A reservation's allocations sum to its quantity (REQ-5) | Cross-row sums. | The WarehouseStock aggregate. The row CHECK still blocks reserved > on_hand |
| A status moves only from Open, and only once (REQ-9, REQ-10, REQ-19) | A CHECK can't see the previous value without triggers. | ReservationStatus. Updates use `WHERE status = 'Open' AND version = ?` |
| SKU, warehouse and bin are known (stk D2-8) | The rows are in another module, so no FK (DB-01). | Pre-check against the stk_known_* tables |
| Reason code is in the configured set (stk Q2-8) | The set is configured. | ReasonCode value object |
| A retry with the same request_id but different data fails with REQUEST_ID_REUSED (stk Q2-6) | It compares the incoming data with the stored row. | ReserveStock application service |

## Caches
| Cache | Key | TTL | Invalidation | Source |
|---|---|---|---|---|
| none | - | - | - | GetAvailability is computed on read (stk Queries). |
