# 02 Tactical design: Stock

## Inputs
- docs/design/project-profile.md (microservices, shared schema `stockroom` per R1, outbox + NATS JetStream, ULID ids, gRPC ErrorInfo reasons).
- docs/design/01-strategic.md: Decisions D1-1 to D1-9, Open questions Q1-1 to Q1-10, Stock context row (module `stk`, REQ-4 to REQ-11, REQ-17 to REQ-20), context map rows Catalog -> Stock, Stock -> Purchasing, Stock -> OutboundShipping, Published language, Ubiquitous language.
- docs/design/00-project-brief.md: rows REQ-4, REQ-5, REQ-6, REQ-7, REQ-8, REQ-9, REQ-10, REQ-11, REQ-17, REQ-18, REQ-19, REQ-20; Actors; Data seen (StockLevel stock.go:7, Reservation proto:21, Availability proto:32-37).
- Rules: default-rulebook.md; ARCHITECTURE.md R1 (overrides DB-02), R2, R3, R4, R6.

## Decisions
| Id | Decision | Why | Source |
|---|---|---|---|
| D2-1 | One aggregate `WarehouseStock` per SKU and warehouse. It holds the per-bin `StockLevel` entities and the open `Reservation` entities of that SKU in that warehouse. | REQ-6 checks unreserved stock across all bins of one warehouse, and reserving must change reserved quantity and create the reservation atomically (TAC-03). A separate Reservation aggregate would make the oversell check eventually consistent. | REQ-6, REQ-18, REQ-20; stock.go:7; proposed |
| D2-2 | Reserved quantity is held per bin (as in stock.go), so each reservation carries `BinAllocation` values; the aggregate chooses the bins. | stock.go keeps on_hand and reserved per SKU per bin; Q1-5 default lets a reservation span bins of one warehouse. | stock.go:7; Q1-5; proposed |
| D2-3 | Available is computed, never stored: per warehouse, sum of on hand minus sum of reserved. | REQ-20 defines it; storing it would add a second truth. | REQ-20; stock.go:16 |
| D2-4 | ReserveStock is idempotent on `request_id`: a retry with the same request id returns the original reservation id and emits nothing. The request id is unique across all of Stock, enforced by a unique key in the store (the one cross-aggregate rule, protected by the store, not by an event). | REQ-8; request id is caller-generated. | REQ-8; proto:13 |
| D2-5 | ReleaseReservation and PickReservation on a reservation already in the target state succeed with no change and no event; on a reservation in another closed state they fail with RESERVATION_NOT_OPEN. | Makes the outside system's retries safe. | proposed |
| D2-6 | Expiry is a policy, not an actor: each reservation stores `expires_at` set at reservation time; `ReservationExpiryPolicy` issues `ExpireReservation` when that time passes, implemented as a durable sweep over open reservations (not an in-memory timer). Expiry releases the quantity (Q1-2 default). | REQ-19; survives restarts; no API operation for expiry (API-02). | REQ-19; Q1-1; Q1-2; proposed |
| D2-7 | Closed reservations (released, picked, expired) are kept as rows for idempotency and audit but are not loaded with the aggregate; only open reservations take part in invariants. | Keeps the aggregate small (TAC-11). | proposed |
| D2-8 | Stock validates SKU, warehouse and bin against local read models `KnownProducts`, `KnownWarehouses`, `KnownBins`, fed by Catalog's integration events. These are pre-checks, not invariants; Catalog stays the source of truth. | D1-5; R1 forbids reading `cat_` tables. | D1-5; ARCHITECTURE.md:5 |
| D2-9 | `AvailabilityChanged` (integration) is emitted by every command that changes on hand or reserved of a WarehouseStock, carrying on hand, reserved, available and the aggregate version, so Purchasing can drop out-of-order copies. A pick changes on hand and reserved but not available; it still emits. | Published language D1 lists AvailabilityChanged; version gives ordering for an at-least-once relay (R4). | 01 Published language; ARCHITECTURE.md:8; proposed |
| D2-10 | WarehouseStock uses optimistic concurrency (version); a conflicting command is retried by the application service a bounded number of times, then fails with CONCURRENT_UPDATE (retryable). | Reservations on a popular SKU contend on one aggregate. | proposed |
| D2-11 | Quantities are whole numbers (int64) and every command quantity must be greater than zero, except the counted quantity of AdjustStock, which may be zero. | proto and stock.go use int64; zero-quantity receipts or reservations mean nothing. | proto:21; stock.go:7; proposed |
| D2-12 | ReceiveGoods and AdjustStock carry a caller request id; a repeat with the same id is a no-op. | Makes staff retries safe (API-03 in phase 6). | proposed |
| D2-13 | Actor names: `WarehouseStaff`, `OutboundShipping`, `Reader` (brief Actors; 01 context map). | Exact spelling for triggers. | brief Actors; 01 Context map |

## Open questions
| Id | Question | Why it matters | Proposed default |
|---|---|---|---|
| Q2-1 | How long until a reservation expires, and does expiry release the quantity? (Q1-1, Q1-2) | Sets `expires_at` and the effect of ExpireReservation. | Configurable duration, no number in design; expiry releases the quantity. |
| Q2-2 | Does AdjustStock take the counted quantity (absolute) or a difference (delta)? | Changes the command input and the retry behaviour. | Counted quantity; the aggregate computes and records the difference. |
| Q2-3 | What if a cycle count in a bin is lower than the quantity reserved in that bin? | Would break reserved <= on hand per bin (REQ-18, REQ-20). | Reject with COUNT_BELOW_RESERVED; staff release or move reservations first. |
| Q2-4 | May a reservation be picked or released partly? (brief Unknowns: partial pick) | Changes PickReservation and ReleaseReservation inputs. | No: whole reservation only. |
| Q2-5 | In which order are bins chosen when a reservation spans bins? (Q1-5) | Decides which bins hold the reserved quantity and what pickers see. | Bins with the most available first, to split as little as possible. |
| Q2-6 | What if a reserve retry reuses a request id with a different SKU, warehouse, quantity or shipment reference? | REQ-8 covers only true retries. | Fail with REQUEST_ID_REUSED (ALREADY_EXISTS); nothing changes. |
| Q2-7 | Can an expired reservation still be picked if the goods were already taken? | Expiry and pick race in the real warehouse. | No: fail with RESERVATION_NOT_OPEN; the caller reserves again. |
| Q2-8 | Which adjustment reason codes exist? (Q1-4) | AdjustStock validates the code. | Business-defined enumerated set held as configuration; unknown code fails with REASON_CODE_UNKNOWN. |
| Q2-9 | What fields do Catalog's ProductRegistered, WarehouseRegistered and BinRegistered carry? 01 names them but lists no payload. | Stock's read models need sku, warehouse_id, and bin_id with its warehouse_id. | ProductRegistered: product_id, sku. WarehouseRegistered: warehouse_id. BinRegistered: bin_id, warehouse_id. To be confirmed by Catalog's 02. |
| Q2-10 | A request names a SKU, warehouse or bin whose Catalog event has not arrived yet. (Q1-9) | Eventual consistency with Catalog. | Fail with SKU_NOT_FOUND, WAREHOUSE_NOT_FOUND or BIN_NOT_FOUND (NOT_FOUND, retryable). |
| Q2-11 | Who may call which Stock operation? (Q1-6) | Authorisation in the generic identity subdomain. | As triggers here: WarehouseStaff receives and adjusts, OutboundShipping reserves, releases and picks, Reader reads. |

## Aggregates
| Aggregate | Root entity | Contains (entities, value objects) | References by id | Invariants (REQ) | Created by |
|---|---|---|---|---|---|
| WarehouseStock | WarehouseStock | StockLevel (entity), Reservation (entity), BinAllocation (value object), Quantity (value object), ReasonCode (value object), ReservationStatus (value object), RequestId (value object), ShipmentRef (value object) | sku and warehouse_id (Catalog product and warehouse), bin_id (Catalog bin) | One WarehouseStock per SKU and warehouse (store unique key). Per bin: 0 <= reserved <= on hand, so on hand and available never go negative (REQ-18, REQ-20). Available = sum on hand minus sum reserved (REQ-20). A reservation is accepted only if its quantity <= available in this warehouse, all in one transaction (REQ-6). Reserved of each bin equals the sum of open reservations' allocations on that bin; a reservation's allocations sum to its quantity (REQ-5). Request id unique across Stock: enforced by a store unique key, not by an event (REQ-8). SKU, warehouse and bin existence is a pre-check against Catalog-fed read models, eventually consistent with Catalog (D2-8). | actor:WarehouseStaff |

## Entities and value objects
| Name | Kind (entity / value object) | Belongs to | Fields | Rules |
|---|---|---|---|---|
| WarehouseStock | entity | WarehouseStock | id (ULID), sku, warehouse_id, version | Root; created by the first ReceiveGoods or AdjustStock for its SKU and warehouse (D2-1). |
| StockLevel | entity | WarehouseStock | id (ULID), bin_id, on_hand (Quantity), reserved (Quantity) | One per bin with stock of this SKU (stock.go:7); 0 <= reserved <= on_hand (REQ-18). Created inside the root on first receipt or count in a bin. |
| Reservation | entity | WarehouseStock | id (ULID), request_id (RequestId), shipment_ref (ShipmentRef), quantity (Quantity), allocations (list of BinAllocation), status (ReservationStatus), reserved_at, expires_at, closed_at | Status moves Open -> Released, Picked or Expired, once (REQ-9, REQ-10, REQ-19). Quantity > 0. Lives and closes with the root. |
| BinAllocation | value object | WarehouseStock | bin_id, quantity (Quantity) | Quantity > 0; replaced, never edited. |
| Quantity | value object | WarehouseStock | value (int64) | value >= 0; command inputs > 0 except a counted quantity (D2-11). |
| ReasonCode | value object | WarehouseStock | code | Member of the configured set (Q2-8). |
| ReservationStatus | value object | WarehouseStock | value: Open, Released, Picked, Expired | Enumerated; no transition out of a closed value. |
| RequestId | value object | WarehouseStock | value (caller string) | Non-empty; unique across Stock for reservations (REQ-8). |
| ShipmentRef | value object | WarehouseStock | value (caller string) | Non-empty (REQ-5). |

## Commands
| Command | Aggregate | Trigger | Emits | Fails when | REQ |
|---|---|---|---|---|---|
| ReceiveGoods | WarehouseStock | actor:WarehouseStaff | GoodsReceived, AvailabilityChanged | INVALID_QUANTITY (quantity <= 0); SKU_NOT_FOUND; BIN_NOT_FOUND (bin not in KnownBins, Q2-10); CONCURRENT_UPDATE | REQ-4, REQ-18, REQ-20 |
| ReserveStock | WarehouseStock | actor:OutboundShipping | StockReserved, AvailabilityChanged | INVALID_QUANTITY; SKU_NOT_FOUND; WAREHOUSE_NOT_FOUND; INSUFFICIENT_STOCK (quantity > available in the warehouse, REQ-6, REQ-7); REQUEST_ID_REUSED (Q2-6); CONCURRENT_UPDATE. A true retry returns the first reservation id (D2-4). | REQ-5, REQ-6, REQ-7, REQ-8, REQ-18, REQ-20 |
| ReleaseReservation | WarehouseStock | actor:OutboundShipping | ReservationReleased, AvailabilityChanged | RESERVATION_NOT_FOUND; RESERVATION_NOT_OPEN (picked or expired; already released is a no-op, D2-5); CONCURRENT_UPDATE | REQ-9, REQ-20 |
| PickReservation | WarehouseStock | actor:OutboundShipping | ReservationPicked, AvailabilityChanged | RESERVATION_NOT_FOUND; RESERVATION_NOT_OPEN (released or expired, Q2-7; already picked is a no-op); CONCURRENT_UPDATE | REQ-10, REQ-18, REQ-20 |
| AdjustStock | WarehouseStock | actor:WarehouseStaff | StockAdjusted, AvailabilityChanged | INVALID_QUANTITY (counted < 0); REASON_CODE_UNKNOWN (Q2-8); SKU_NOT_FOUND; BIN_NOT_FOUND; COUNT_BELOW_RESERVED (Q2-3); CONCURRENT_UPDATE | REQ-11, REQ-18, REQ-20 |
| ExpireReservation | WarehouseStock | policy:ReservationExpiryPolicy | ReservationExpired, AvailabilityChanged | Reservation no longer open: no-op, no event; CONCURRENT_UPDATE (retried) | REQ-19, REQ-20 |

## Domain events
| Event | Emitted by | Kind | Payload | Consumers |
|---|---|---|---|---|
| GoodsReceived | WarehouseStock | internal | event_id, warehouse_stock_id, sku, warehouse_id, bin_id, quantity, request_id, occurred_at | none |
| StockReserved | WarehouseStock | internal | event_id, warehouse_stock_id, reservation_id, request_id, sku, warehouse_id, quantity, allocations, shipment_ref, expires_at, occurred_at | ReservationExpiryPolicy |
| ReservationReleased | WarehouseStock | internal | event_id, reservation_id, sku, warehouse_id, quantity, occurred_at | none |
| ReservationPicked | WarehouseStock | internal | event_id, reservation_id, sku, warehouse_id, quantity, allocations, occurred_at | none |
| ReservationExpired | WarehouseStock | internal | event_id, reservation_id, sku, warehouse_id, quantity, occurred_at | none |
| StockAdjusted | WarehouseStock | internal | event_id, warehouse_stock_id, sku, warehouse_id, bin_id, previous_on_hand, counted_on_hand, difference, reason_code, request_id, occurred_at | none |
| AvailabilityChanged | WarehouseStock | integration | event_id, sku, warehouse_id, on_hand, reserved, available, version, occurred_at; subject `stockroom.stk.availability_changed` (R4) | Purchasing |

## Policies
| Policy | When (event) | Then (command) | Context | On failure |
|---|---|---|---|---|
| ReservationExpiryPolicy | StockReserved | ExpireReservation | Stock | Runs when expires_at passes (durable sweep, D2-6). CONCURRENT_UPDATE: retry on the next sweep. Reservation already closed: no-op. Repeated failure for one reservation: alert operations. |

## Queries and read models
| Query / read model | Kind (query / read model / cache) | Source | Rebuild or invalidation | Staleness | REQ |
|---|---|---|---|---|---|
| GetAvailability | query | WarehouseStock (stk tables: StockLevel rows per SKU, optional warehouse filter); returns on_hand, reserved, available per warehouse | Not stored; computed on read | None (reads committed state) | REQ-17, REQ-20 |
| KnownProducts | read model | Catalog integration event ProductRegistered (`stockroom.cat.product_registered`), deduplicated by event id | Replay of Catalog's ProductRegistered stream; upsert by product id | Lag of the NATS relay; unknown SKU is NOT_FOUND, retryable (Q2-10) | REQ-4, REQ-5, REQ-11 |
| KnownWarehouses | read model | Catalog integration event WarehouseRegistered (`stockroom.cat.warehouse_registered`), deduplicated by event id | Replay of Catalog's WarehouseRegistered stream; upsert by warehouse id | Lag of the NATS relay (Q2-10) | REQ-5 |
| KnownBins | read model | Catalog integration event BinRegistered (`stockroom.cat.bin_registered`), with its warehouse id (Q2-9), deduplicated by event id | Replay of Catalog's BinRegistered stream; upsert by bin id | Lag of the NATS relay (Q2-10) | REQ-4, REQ-11 |

## Out of scope
| REQ | Why |
|---|---|
| none | Every Stock REQ maps to a command or query above. |
