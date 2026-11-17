# 06 API design

The authoritative contract is [06-api.proto](06-api.proto), generated from the Operations table below. It supersedes the prototype stub `proto/stockroom/v1/stockroom.proto` and stays wire-compatible with it (D6-2).

## Inputs
- docs/design/project-profile.md: api_style gRPC; api_contract_file proto; error_format canonical status + `google.rpc.ErrorInfo` reason UPPER_SNAKE_CASE; id_convention ULID; naming_convention protobuf messages PascalCase, fields snake_case; architecture_style microservices.
- docs/design/02-tactical-catalog.md, 02-tactical-stock.md, 02-tactical-purchasing.md: Commands, Queries and read models, Aggregates (Created by), Decisions, Open questions.
- docs/design/03-db-design.md: Decisions D3-1 to D3-15, Open questions Q3-1 to Q3-8.
- proto/stockroom/v1/stockroom.proto (prototype stub: StockService.ReserveStock, StockService.GetAvailability).
- Rules: default-rulebook.md (API-01 to API-08, DOC-01 to DOC-04); ARCHITECTURE.md R2 (ULID), R3 (errors), R6 (naming). R1 overrides DB-02 only; it does not touch API rules.

## Decisions
| Id | Decision | Why | Source |
|---|---|---|---|
| D6-1 | One gRPC service per context: `CatalogService`, `StockService`, `PurchasingService`, all in package `stockroom.v1`. | One service per context (api-styles gRPC); the stub already publishes `stockroom.v1.StockService`, and moving it to another package would change the full method names the shipping system calls. | proto:5, proto:7; 01 D1-3 |
| D6-2 | The stub's messages keep every field number and type. Additions only: `ReserveStockResponse.expires_at = 2`, `GetAvailabilityRequest.warehouse_id = 2`. 06-api.proto replaces the stub file at implementation; there is one contract source. | Fields are never renumbered (api-styles gRPC); contract-first "one authoritative artifact". | proto:12-37 |
| D6-3 | Versioning: package version `stockroom.v1`. Within v1 only additive changes (new fields, new rpcs, new enum values); removed fields are `reserved`. A breaking change needs a new rpc or `stockroom.v2`. | api-styles gRPC; contract-first change protocol. | *proposed* |
| D6-4 | Every error is a canonical status code plus one `google.rpc.ErrorInfo` with `reason` = the 02 failure name, `domain` = `stockroom.<module>` (`stockroom.cat`, `stockroom.stk`, `stockroom.pur`), and `metadata` naming the offending field or id where useful. | R3; one reason vocabulary shared with 02 (DOC-04). The `domain` value is *proposed*. | ARCHITECTURE.md:7 |
| D6-5 | Generic reasons added for every operation, not named in 02: `MISSING_FIELD` (INVALID_ARGUMENT, metadata `field`), `UNAUTHENTICATED` (UNAUTHENTICATED), `ACTOR_NOT_ALLOWED` (PERMISSION_DENIED); for the list query `INVALID_PAGE_TOKEN`, `INVALID_PAGE_SIZE` (INVALID_ARGUMENT). Catalog keeps its own 02 reasons `MISSING_PRODUCT_FIELD`, `MISSING_WAREHOUSE_FIELD`, `MISSING_BIN_FIELD`. | Validation and forbidden must be listed (API-04); identity is not designed (01 D1-8). | *proposed* |
| D6-6 | Purchasing's 02 "version conflict" is exposed with reason `CONCURRENT_UPDATE` (ABORTED), the same reason Stock uses. | One spelling for one meaning (DOC-04). | stk D2-10; pur D2-11 |
| D6-7 | Catalog register operations are idempotent on the natural key (SKU; warehouse code; warehouse id + bin code): identical data returns the existing id; different data fails ALREADY_EXISTS. No request id. | cat Q2-8 default; Catalog aggregates are immutable (cat D2-7), so there is no version conflict. | cat Q2-8, cat D2-7 |
| D6-8 | ReserveStock, ReceiveGoods and AdjustStock dedupe on the caller's `request_id`, kept permanently: reservations stay as rows when closed (stk D2-7) and movements are kept (Q3-5 default). Separate namespaces for reservations and movements (Q3-4 default). Length up to 128 ascii (Q3-2 default). | stk D2-4, D2-12; a window shorter than the row lifetime adds nothing. | stk D2-4, D2-12; 03 D3-14 |
| D6-9 | ReleaseReservation, PickReservation, AcceptReorderSuggestion and DismissReorderSuggestion take no request id: repeating the same transition is a no-op success. | stk D2-5; pur D2-7. | stk D2-5; pur D2-7 |
| D6-10 | ReceiveGoods takes `bin_id` but no `warehouse_id`; the warehouse is the bin's warehouse from KnownBins. | 02 ReceiveGoods fails only with BIN_NOT_FOUND, not a warehouse error; avoids a bin/warehouse mismatch error. | stk Commands; stk Q2-9 |
| D6-11 | GetAvailability is not paginated: it returns at most one row per warehouse for one SKU, ordered by `warehouse_id` ascending. Adding paging to the stub's rpc would truncate results for existing callers. | Bounded result; stub compatibility (D6-2). | proto:24-30; stk D2-3 |
| D6-12 | ListReorderSuggestions uses `page_size`/`page_token` (default 50, max 200), order `raised_at` desc then `suggestion_id` desc, filters status, sku, warehouse_id. The token is opaque and encodes the last (raised_at, suggestion_id). | api-styles gRPC; filters and order from Q3-7 default. Page sizes are *proposed*. | 03 Q3-7 |
| D6-13 | Purchasing exposes the field `sku` (the SKU value), not `sku_id`. | 03 D3-12 / Q3-1 default; matches AvailabilityChanged and Stock. | 03 D3-12 |
| D6-14 | Internal read models (KnownProducts, KnownWarehouses, KnownBins, KnownAvailability) are not exposed; they serve pre-checks only. No operation returns another context's data (no product name or warehouse name outside Catalog). | API-07; R1. | stk D2-8; pur D2-8 |
| D6-15 | `decided_by` is taken from the caller's credentials, never from the request body. | A caller must not record a decision in another person's name. | *proposed* |
| D6-16 | Enum values follow proto style with a type prefix and a zero UNSPECIFIED value; mapping to 02: `Open`/`Released`/`Picked`/`Expired` -> `RESERVATION_STATUS_*`, `Raised`/`Accepted`/`Dismissed` -> `SUGGESTION_STATUS_*`. | Proto3 enum convention; explicit mapping keeps names traceable (DOC-04). | R6; *proposed* |
| D6-17 | Fixed F5: ListReorderSuggestions traces to REQ-21 "Purchasing lists reorder suggestions". | Listing is now a brief requirement. | 07 F5 |
| D6-18 | Fixed F7: ReceiveGoods and AdjustStock map a duplicate key on first root creation (same SKU and warehouse) to CONCURRENT_UPDATE [ABORTED]; retry is safe (same `request_id`). Both rows already list it; the Errors table meaning is widened. | No unmapped internal error for the race. | 07 F7; stk D2-10 |

## Open questions
| Id | Question | Why it matters | Proposed default |
|---|---|---|---|
| Q6-1 | Staff must pass `warehouse_id` and `bin_id` to ReceiveGoods, AdjustStock and SetLowStockThreshold, but Catalog has no lookup query (cat D2-8, Q2-6). How do they find ids they did not register themselves? | Without a lookup the UI cannot list warehouses and bins. | Add `GetProduct`, `ListWarehouses`, `ListBins` queries to 02 Catalog, then to CatalogService. Not added here (API-01). |
| Q6-2 | How do callers authenticate, and how is the actor or role carried? (01 Q1-6, D1-8) | Every operation's Actor column relies on it. | mTLS for system callers (OutboundShipping); bearer token with a role claim for people; roles `WarehouseStaff`, `OutboundShipping`, `Purchasing`, `Reader`. |
| Q6-3 | Who may call GetAvailability? Stock Q2-11 says Reader; the stub says the shipping system needs it. | Authorization rule. | Reader and OutboundShipping. |
| Q6-4 | A ReceiveGoods or AdjustStock retry reuses a request id with different data. 02 does not say. | Silent no-op would hide a caller bug. | Fail with `REQUEST_ID_REUSED` (ALREADY_EXISTS), as ReserveStock (stk Q2-6). Listed in the rows as *proposed*. |
| Q6-5 | Does the shipping system need to read a reservation (status, allocations, expires_at) or find it by `shipment_ref`? | No 02 query covers it; after a lost response it can only retry ReserveStock. | No: ReserveStock retry with the same request_id returns the reservation id and expires_at. |
| Q6-6 | Who may set thresholds, and who accepts or dismisses suggestions? (pur Q2-7) | Authorization. | SetLowStockThreshold: WarehouseStaff; Accept, Dismiss, List: Purchasing. |
| Q6-7 | Who may register products, warehouses and bins? (cat Q2-7) | Authorization. | WarehouseStaff only. |
| Q6-8 | Maximum length of the decision `note`? (Q3-6) | Validation. | 1000 characters; longer fails INVALID_ARGUMENT with reason `NOTE_TOO_LONG` (not yet in the contract). |
| Q6-9 | Is GetAvailability's unbounded per-warehouse list acceptable if warehouses grow large? | D6-11 skips paging. | Yes for now; add a new paged rpc if a SKU is ever in more than about 500 warehouses. |
| Q6-10 | Should the API expose a rate limit (RESOURCE_EXHAUSTED) per caller? | Contract other teams code against. | Yes: RESOURCE_EXHAUSTED with reason `RATE_LIMITED`, limits set in config. |

## Conventions
| Topic | Rule | Source |
|---|---|---|
| Style | gRPC, proto3, contract in [06-api.proto](06-api.proto) | profile api_style, api_contract_file |
| Naming | rpc `VerbNoun` = exact 02 name; messages `<Rpc>Request` / `<Rpc>Response` PascalCase; fields snake_case | profile naming_convention; R6 |
| Ids | ULID strings, generated by the server's domain layer; caller-supplied `request_id` and `shipment_ref` are opaque strings | profile id_convention; R2 |
| Pagination | `page_size` + opaque `page_token`; `next_page_token` empty on the last page; stable order stated per query | api-styles gRPC; D6-12 |
| Versioning | package `stockroom.v1`; additive only within v1 | D6-3 |
| Errors | canonical status + `google.rpc.ErrorInfo` (`reason` UPPER_SNAKE_CASE, `domain`, `metadata`) | profile error_format; R3; D6-4 |
| Concurrency | No client version field; server retries a version conflict a bounded number of times, then ABORTED `CONCURRENT_UPDATE` | stk D2-10; pur D2-11 |
| Time | `google.protobuf.Timestamp`, UTC | 03 D3-4 |

## Operations
Common errors on every operation (not repeated per row): `UNAUTHENTICATED`, `ACTOR_NOT_ALLOWED`. Status in brackets.

| Operation | Signature | Kind | Maps to | Actor | Idempotency | Errors | REQ |
|---|---|---|---|---|---|---|---|
| RegisterProduct | `rpc RegisterProduct(RegisterProductRequest) returns (RegisterProductResponse)` | command | RegisterProduct | WarehouseStaff (Q6-7) | Natural key `sku`: identical data returns the existing `product_id`; different data fails SKU_ALREADY_EXISTS (D6-7) | MISSING_PRODUCT_FIELD [INVALID_ARGUMENT]; INVALID_SKU [INVALID_ARGUMENT]; UNKNOWN_UNIT_OF_MEASURE [INVALID_ARGUMENT]; SKU_ALREADY_EXISTS [ALREADY_EXISTS]; PRODUCT_CODE_ALREADY_EXISTS [ALREADY_EXISTS] | REQ-1 |
| RegisterWarehouse | `rpc RegisterWarehouse(RegisterWarehouseRequest) returns (RegisterWarehouseResponse)` | command | RegisterWarehouse | WarehouseStaff (Q6-7) | Natural key `code`: identical data returns the existing `warehouse_id` (D6-7) | MISSING_WAREHOUSE_FIELD [INVALID_ARGUMENT]; WAREHOUSE_CODE_ALREADY_EXISTS [ALREADY_EXISTS] | REQ-2 |
| RegisterBin | `rpc RegisterBin(RegisterBinRequest) returns (RegisterBinResponse)` | command | RegisterBin | WarehouseStaff (Q6-7) | Natural key (`warehouse_id`, `code`): identical data returns the existing `bin_id` (D6-7) | MISSING_BIN_FIELD [INVALID_ARGUMENT]; WAREHOUSE_NOT_FOUND [NOT_FOUND]; BIN_CODE_ALREADY_EXISTS [ALREADY_EXISTS] | REQ-3 |
| ReceiveGoods | `rpc ReceiveGoods(ReceiveGoodsRequest) returns (ReceiveGoodsResponse)` | command | ReceiveGoods | WarehouseStaff (stk Q2-11) | Client key `request_id`, kept permanently; replay returns `replayed = true` and current availability, no change (D6-8) | MISSING_FIELD [INVALID_ARGUMENT]; INVALID_QUANTITY [INVALID_ARGUMENT]; SKU_NOT_FOUND [NOT_FOUND, retryable]; BIN_NOT_FOUND [NOT_FOUND, retryable]; REQUEST_ID_REUSED [ALREADY_EXISTS] (*proposed*, Q6-4); CONCURRENT_UPDATE [ABORTED] | REQ-4, REQ-18, REQ-20 |
| ReserveStock | `rpc ReserveStock(ReserveStockRequest) returns (ReserveStockResponse)` | command | ReserveStock | OutboundShipping (stk Q2-11) | Client key `request_id`, kept permanently; replay returns the first `reservation_id` and `expires_at`, no event (stk D2-4) | MISSING_FIELD [INVALID_ARGUMENT]; INVALID_QUANTITY [INVALID_ARGUMENT]; SKU_NOT_FOUND [NOT_FOUND, retryable]; WAREHOUSE_NOT_FOUND [NOT_FOUND, retryable]; INSUFFICIENT_STOCK [FAILED_PRECONDITION]; REQUEST_ID_REUSED [ALREADY_EXISTS]; CONCURRENT_UPDATE [ABORTED] | REQ-5, REQ-6, REQ-7, REQ-8, REQ-18, REQ-20 |
| ReleaseReservation | `rpc ReleaseReservation(ReleaseReservationRequest) returns (ReleaseReservationResponse)` | command | ReleaseReservation | OutboundShipping (stk Q2-11) | Safe to retry because releasing an already released reservation succeeds with no change (stk D2-5) | MISSING_FIELD [INVALID_ARGUMENT]; RESERVATION_NOT_FOUND [NOT_FOUND]; RESERVATION_NOT_OPEN [FAILED_PRECONDITION]; CONCURRENT_UPDATE [ABORTED] | REQ-9, REQ-20 |
| PickReservation | `rpc PickReservation(PickReservationRequest) returns (PickReservationResponse)` | command | PickReservation | OutboundShipping (stk Q2-11) | Safe to retry because picking an already picked reservation succeeds with no change (stk D2-5) | MISSING_FIELD [INVALID_ARGUMENT]; RESERVATION_NOT_FOUND [NOT_FOUND]; RESERVATION_NOT_OPEN [FAILED_PRECONDITION]; CONCURRENT_UPDATE [ABORTED] | REQ-10, REQ-18, REQ-20 |
| AdjustStock | `rpc AdjustStock(AdjustStockRequest) returns (AdjustStockResponse)` | command | AdjustStock | WarehouseStaff (stk Q2-11) | Client key `request_id`, kept permanently; replay returns `replayed = true`, the recorded difference and current availability (D6-8) | MISSING_FIELD [INVALID_ARGUMENT]; INVALID_QUANTITY [INVALID_ARGUMENT]; REASON_CODE_UNKNOWN [INVALID_ARGUMENT]; SKU_NOT_FOUND [NOT_FOUND, retryable]; BIN_NOT_FOUND [NOT_FOUND, retryable]; COUNT_BELOW_RESERVED [FAILED_PRECONDITION]; REQUEST_ID_REUSED [ALREADY_EXISTS] (*proposed*, Q6-4); CONCURRENT_UPDATE [ABORTED] | REQ-11, REQ-18, REQ-20 |
| GetAvailability | `rpc GetAvailability(GetAvailabilityRequest) returns (GetAvailabilityResponse)` | query | GetAvailability | Reader, OutboundShipping (Q6-3) | n/a (read) | MISSING_FIELD [INVALID_ARGUMENT]; unknown SKU returns an empty list | REQ-17, REQ-20 |
| SetLowStockThreshold | `rpc SetLowStockThreshold(SetLowStockThresholdRequest) returns (SetLowStockThresholdResponse)` | command | SetLowStockThreshold | WarehouseStaff (Q6-6) | Natural key (`sku`, `warehouse_id`), upsert: the same quantity again leaves state unchanged and raises nothing (pur D2-9, D2-3) | MISSING_FIELD [INVALID_ARGUMENT]; INVALID_THRESHOLD [INVALID_ARGUMENT]; SKU_NOT_FOUND [NOT_FOUND, retryable]; WAREHOUSE_NOT_FOUND [NOT_FOUND, retryable]; CONCURRENT_UPDATE [ABORTED] | REQ-12, REQ-13 |
| AcceptReorderSuggestion | `rpc AcceptReorderSuggestion(AcceptReorderSuggestionRequest) returns (AcceptReorderSuggestionResponse)` | command | AcceptReorderSuggestion | Purchasing (Q6-6) | Safe to retry because a second accept succeeds with no change and no event (pur D2-7) | MISSING_FIELD [INVALID_ARGUMENT]; SUGGESTION_NOT_FOUND [NOT_FOUND]; SUGGESTION_ALREADY_DECIDED [FAILED_PRECONDITION]; CONCURRENT_UPDATE [ABORTED] | REQ-15 |
| DismissReorderSuggestion | `rpc DismissReorderSuggestion(DismissReorderSuggestionRequest) returns (DismissReorderSuggestionResponse)` | command | DismissReorderSuggestion | Purchasing (Q6-6) | Safe to retry because a second dismiss succeeds with no change and no event (pur D2-7) | MISSING_FIELD [INVALID_ARGUMENT]; SUGGESTION_NOT_FOUND [NOT_FOUND]; SUGGESTION_ALREADY_DECIDED [FAILED_PRECONDITION]; CONCURRENT_UPDATE [ABORTED] | REQ-16 |
| ListReorderSuggestions | `rpc ListReorderSuggestions(ListReorderSuggestionsRequest) returns (ListReorderSuggestionsResponse)` | query | ListReorderSuggestions | Purchasing (Q6-6) | n/a (read) | INVALID_PAGE_TOKEN [INVALID_ARGUMENT]; INVALID_PAGE_SIZE [INVALID_ARGUMENT] | REQ-13, REQ-15, REQ-16, REQ-21 |

## Errors
| Code | Meaning | Raised by | Retry? |
|---|---|---|---|
| UNAUTHENTICATED [UNAUTHENTICATED] | No valid caller credentials | all | After fixing credentials |
| ACTOR_NOT_ALLOWED [PERMISSION_DENIED] | Caller's role may not call this rpc | all | No |
| MISSING_FIELD [INVALID_ARGUMENT] | A required field is empty; `metadata.field` names it | Stock and Purchasing rpcs | No |
| MISSING_PRODUCT_FIELD [INVALID_ARGUMENT] | code, name or unit empty | RegisterProduct | No |
| INVALID_SKU [INVALID_ARGUMENT] | SKU fails the format (cat Q2-1) | RegisterProduct | No |
| UNKNOWN_UNIT_OF_MEASURE [INVALID_ARGUMENT] | Unit not in the allowed list (cat Q2-2) | RegisterProduct | No |
| SKU_ALREADY_EXISTS [ALREADY_EXISTS] | Another product has this SKU with different data | RegisterProduct | No |
| PRODUCT_CODE_ALREADY_EXISTS [ALREADY_EXISTS] | Another product has this code (cat Q2-3) | RegisterProduct | No |
| MISSING_WAREHOUSE_FIELD [INVALID_ARGUMENT] | code or name empty | RegisterWarehouse | No |
| WAREHOUSE_CODE_ALREADY_EXISTS [ALREADY_EXISTS] | Code taken with different data | RegisterWarehouse | No |
| MISSING_BIN_FIELD [INVALID_ARGUMENT] | code empty | RegisterBin | No |
| BIN_CODE_ALREADY_EXISTS [ALREADY_EXISTS] | Code taken in that warehouse | RegisterBin | No |
| WAREHOUSE_NOT_FOUND [NOT_FOUND] | Warehouse unknown (in Stock and Purchasing: not yet seen from Catalog) | RegisterBin, ReserveStock, SetLowStockThreshold | Catalog: no. Stock, Purchasing: yes, with backoff (stk Q2-10, pur D2-8) |
| SKU_NOT_FOUND [NOT_FOUND] | SKU not yet seen from Catalog | ReceiveGoods, ReserveStock, AdjustStock, SetLowStockThreshold | Yes, with backoff |
| BIN_NOT_FOUND [NOT_FOUND] | Bin not yet seen from Catalog | ReceiveGoods, AdjustStock | Yes, with backoff |
| INVALID_QUANTITY [INVALID_ARGUMENT] | quantity <= 0, or counted quantity < 0 (stk D2-11) | ReceiveGoods, ReserveStock, AdjustStock | No |
| INSUFFICIENT_STOCK [FAILED_PRECONDITION] | quantity > available in the warehouse; nothing reserved (REQ-7) | ReserveStock | Only after stock changes |
| REQUEST_ID_REUSED [ALREADY_EXISTS] | request_id already used with different data | ReserveStock; ReceiveGoods, AdjustStock (*proposed*) | No |
| RESERVATION_NOT_FOUND [NOT_FOUND] | No reservation with that id | ReleaseReservation, PickReservation | No |
| RESERVATION_NOT_OPEN [FAILED_PRECONDITION] | Reservation is in another closed state | ReleaseReservation, PickReservation | No |
| REASON_CODE_UNKNOWN [INVALID_ARGUMENT] | Reason code not in the configured set (stk Q2-8) | AdjustStock | No |
| COUNT_BELOW_RESERVED [FAILED_PRECONDITION] | Count lower than reserved in the bin (stk Q2-3) | AdjustStock | After releasing reservations |
| INVALID_THRESHOLD [INVALID_ARGUMENT] | quantity < 0 (pur Q2-4) | SetLowStockThreshold | No |
| SUGGESTION_NOT_FOUND [NOT_FOUND] | No suggestion with that id | AcceptReorderSuggestion, DismissReorderSuggestion | No |
| SUGGESTION_ALREADY_DECIDED [FAILED_PRECONDITION] | Suggestion already has the opposite decision | AcceptReorderSuggestion, DismissReorderSuggestion | No |
| CONCURRENT_UPDATE [ABORTED] | Version conflict, or a duplicate key when two first ReceiveGoods/AdjustStock calls create the same SKU and warehouse root, after bounded server retries | all Stock commands, Purchasing commands | Yes, same request |
| INVALID_PAGE_TOKEN [INVALID_ARGUMENT] | Token malformed or from other filters | ListReorderSuggestions | No; restart listing |
| INVALID_PAGE_SIZE [INVALID_ARGUMENT] | page_size < 0 or > 200 | ListReorderSuggestions | No |

## Not exposed
| Command | Why (policy-triggered / internal) |
|---|---|
| ExpireReservation | policy-triggered: ReservationExpiryPolicy, durable sweep (stk D2-6); REQ-19 is visible only through GetAvailability |
| RecordAvailability | policy-triggered: TrackAvailabilityAgainstThreshold on Stock's AvailabilityChanged |
| RaiseReorderSuggestion | policy-triggered: RaiseSuggestionOnLowStock; ReorderSuggestion is `Created by` policy, so no rpc creates it (REQ-14, pur D2-6) |
