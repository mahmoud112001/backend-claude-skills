# 07 Design review (loop 2)

## Inputs
Design files read in full (line counts): project-profile.md (38), 00-project-brief.md (97), 00-state.md (36), 01-strategic.md (98), 02-tactical-catalog.md (81), 02-tactical-stock.md (97), 02-tactical-purchasing.md (98), 03-db-design.md (65), 03-db-design-catalog.md (96), 03-db-design-stock.md (196), 03-db-design-purchasing.md (164), 04-erd.md (267), 05-diagrams.md (84), 05-diagrams-use-cases.md (87), 05-diagrams-flows.md (193), 06-api.md (116), 06-api.proto (215), 07-lint.md (17). Previous loop's record, read only to check the fixes: 07-review-loop1.md (85), 07-fixes-loop1.md (13).

Rule files: default-rulebook.md (91); ARCHITECTURE.md (10). R1 overrides DB-02, so the "own schema per context" part of DB-02 was not checked; R1 (one shared schema `stockroom`, three-letter prefix, owner-only access) was checked instead.

Prototype read directly: README.md (25), proto/stockroom/v1/stockroom.proto (37), internal/stock/stock.go (16), docs/context.puml (10), docker-compose.yml (18), go.mod (11).

Stated size: "a few warehouses" (README:3). No load figure is given.

## Decisions
- Verdict: **pass** (no High).
- Totals: High 0, Medium 3, Low 11.
- Loop 1 fixes checked against the files as they are now:
  - F3 (seed event id), F4 (internal events not relayed), F5 (REQ-21), F6 (`sku` naming in pur 02) and F7 (duplicate key on root creation) are fixed where the finding pointed.
  - F1 is fixed in 02 (one handler, one inbox row) and in the `pur_inbox` key, so no event is lost any more. Two leftovers remain: 03 still describes two consumers (F1 below) and FLOW-6 still has no projection step (F2 below).
  - F2 is fixed for the case where a `pur_known_availability` row exists. The case with no row depends on an unstated isolation level (F4 below).
  - The seven Low findings of loop 1 were not sent for fixing and are all still open (F5 to F11 below).
- R1 to R6 hold in every artifact: 21 tables, all prefixed; no FK crosses a module; ids are `CHAR(26)` with no database default; integration subjects follow `stockroom.<module>.<event_name>`; every diagram is PlantUML; proto naming follows R6.
- 06-api.proto stays wire-compatible with the stub: every stub field keeps its number and type; only fields, rpcs and services were added.
- F1 is rated Medium, not High, because with the (`event_id`, `consumer`) key a two-consumer build loses no event; it only reopens the narrow seed race that loop 1 rated Medium.

## Open questions
| Id | Business decision needed | Found in | Proposed default |
|---|---|---|---|
| OQ-1 | A threshold is set for a SKU that has never had stock in that warehouse, so no availability is known. Is that "below the threshold"? (carried from loop 1 OQ-2) | 02-tactical-purchasing.md:15, :21 | No suggestion until the first stock event for that SKU and warehouse (what the design does now). |
| OQ-2 | Who sets a low-stock threshold: warehouse staff or purchasing? README:14 names no actor (see F5). Open as brief Q5, pur Q2-7, Q5-2, Q6-6; listed so that it is answered once. | 00-project-brief.md:62 | Warehouse staff, as the 02 trigger states. |
| OQ-3 | Is a SKU case-sensitive, and is lower-case input rejected or converted? F3 depends on the answer (cat Q2-1). | 02-tactical-catalog.md:24; 03-db-design-catalog.md:27 | Convert to upper case in every context that accepts a SKU. |

## Findings
| Id | Severity | Rule | Location | Case | Fix | Owner phase | Previous |
|---|---|---|---|---|---|---|---|
| F1 | Medium | BUG (contradiction) | 03-db-design.md:22; 03-db-design-purchasing.md:16, :146 against 02-tactical-purchasing.md:25 | 02 D2-13 says "AvailabilityChanged has one consumer in Purchasing: in one transaction with one inbox row". 03 says "AvailabilityChanged feeds both TrackAvailabilityAgainstThreshold and the KnownAvailability projection" and the `consumer` ENUM lists both names with the note "AvailabilityChanged has two consumers". When a developer builds from 03, the projection and the policy run as two consumers in two transactions. The policy can then skip an event (no threshold yet), SetLowStockThreshold seeds from the not-yet-updated `pur_known_availability` row, and the projection updates it afterwards: the new threshold holds a stale available and raises no suggestion until the next stock movement. The row-lock protocol of D2-9 assumes one handler. It is also undefined which ENUM value the single handler writes. | In 03 D3-9, in the "Fixed F1" row of 03-pur and in the `consumer` note, say that AvailabilityChanged has one handler that writes one inbox row; keep one ENUM value for it (`TrackAvailabilityAgainstThreshold`) and drop `KnownAvailability`. | 3 | still open (rest of loop 1 F1) |
| F2 | Medium | BUG | 05-diagrams-flows.md:14, :150-152 | D5-4 says "The projection step of FLOW-6 is not added; it awaits the 02 purchasing change". 02 has changed (D2-13). FLOW-6 still goes from the inbox straight to "no threshold for SKU and warehouse: skip (ack)". When a developer follows the flow, an event for a SKU with no threshold is acked without the KnownAvailability upsert. A threshold set later is seeded with no availability, so stock that is already below it raises no suggestion (against pur D2-9 and Q2-2). | Add one step before the `alt` in FLOW-6: the handler upserts KnownAvailability (same transaction), then looks up the threshold. Remove the "awaits" sentence from D5-4. | 5 | still open (rest of loop 1 F1) |
| F3 | Medium | BUG | 03-db-design-catalog.md:27; 02-tactical-stock.md:19; 02-tactical-purchasing.md:20 | Catalog stores the SKU "upper case" (cat Q2-1 default, applied in 03) and publishes that value; Stock and Purchasing compare `sku` in `ascii_bin` against KnownProducts and state no normalisation. RegisterProductResponse returns only `product_id`. When staff register `abc-1` and then call ReceiveGoods, ReserveStock or SetLowStockThreshold with `abc-1`, the lookup against `ABC-1` fails with SKU_NOT_FOUND, which 06 marks "retryable", so the caller retries for ever. | Add to stk D2-8 and pur D2-8: an incoming `sku` goes through the same Sku normalisation as Catalog (cat Q2-1) before the lookup. The rule itself stays open (OQ-3). | 2 | new |
| F4 | Low | BUG (race) | 02-tactical-purchasing.md:21 | D2-9 closes the seed race with "a locking read" of the KnownAvailability row. When no row exists yet (first stock event for a SKU and warehouse), there is no row to lock; the fix then holds only through an InnoDB gap lock, which exists under REPEATABLE READ and not under READ COMMITTED. The design states no isolation level. Under READ COMMITTED the handler inserts the row, sees no committed threshold and skips; the threshold commits with no availability. | Add to D2-9: these two transactions run at REPEATABLE READ (the InnoDB default), so the locking read on a missing row blocks the handler's insert. | 2 | new (limit of the loop 1 F2 fix) |
| F5 | Low | DOC-02 | 00-project-brief.md:62; 05-diagrams-use-cases.md:20 | REQ-12 gives Actor "Warehouse staff" with source README:14, which names no actor. Q5-2 then says the brief names Purchasing for REQ-12, which it does not. | Mark the REQ-12 actor *proposed* and point to brief Q5. Phase 5 corrects the wording of Q5-2. | 0 | still open (loop 1 F8) |
| F6 | Low | BUG | 02-tactical-stock.md:64 | ReserveStock lists no outcome for a known SKU and warehouse with no WarehouseStock yet (nothing ever received there). The result is undefined: INSUFFICIENT_STOCK, a not-found error or an internal error. | Add to the ReserveStock row: no WarehouseStock for the SKU and warehouse fails with INSUFFICIENT_STOCK. | 2 | still open (loop 1 F9) |
| F7 | Low | BUG | 03-db-design-stock.md:188 | "Updates use `WHERE status = 'Open' AND version = ?`", but `stk_reservation` has no `version` column; the version is on `stk_warehouse_stock`. | Reword: the reservation update uses `WHERE status = 'Open'`, and the root update checks `version`. | 3 | still open (loop 1 F10) |
| F8 | Low | BUG | 05-diagrams-flows.md:65, :123 | FLOW-2 draws `A -> P : StockReserved` and FLOW-5 shows the policy triggered by StockReserved. 03 D3-8 says Stock's internal events are written nowhere and expiry is a sweep over `stk_reservation`. A developer who follows the flow builds an event delivery that storage does not have. | Replace the arrow at :65 with a note "the sweep reads open reservations by expires_at"; relabel :123 the same way. | 5 | still open (loop 1 F11) |
| F9 | Low | API-04 | 06-api.md:68, :72 against 02-tactical-stock.md:63, :67 | 06 lists REQUEST_ID_REUSED for ReceiveGoods and AdjustStock; the 02 `Fails when` cells do not. Domain tests written from 02 miss the reuse case. | Add REQUEST_ID_REUSED (*proposed*, Q6-4) to both 02 rows. | 2 | still open (loop 1 F12) |
| F10 | Low | DOC-02 | 02-tactical-stock.md:22; 03-db-design.md:18 | Both cite `proto:21` for the int64 quantity. proto:21 is `string reservation_id = 1;`; the quantity is at proto:16. | Change the citation to proto:16 (phase 3 for 03-db-design.md:18). | 2 | still open (loop 1 F13) |
| F11 | Low | BUG (stale) | 02-tactical-stock.md:38; 02-tactical-purchasing.md:34, :42, :56; 03-db-design.md:25, :35; project-profile.md:12; 00-project-brief.md:24 | Questions already answered elsewhere stay open with a different default. stk Q2-9 and pur Q2-9 ask for Catalog payloads that 02-tactical-catalog.md:64-66 defines. pur Q2-1 says "use the event's broker sequence" and :56 "sequence or occurred-at", while stk D2-9 and 03 D3-13 fix the order field as the WarehouseStock `version`. 03 D3-12 and Q3-1 still say pur 02 has a field `sku_id` to rename; it was renamed (pur D2-17). Profile Q1 and brief Q8 still propose "modular monolith" although D0-P2 records "microservices". A developer who reads pur 02 alone orders events by broker sequence. | Close each question with a pointer to the answering decision; phase 3 drops the `sku_id` sentence; phase 0 closes profile Q1 and brief Q8. | 2 | still open (loop 1 F14), one new location |
| F12 | Low | DOC-04 | 05-diagrams-use-cases.md:80; 02-tactical-purchasing.md:5-6; 06-api.md:77 | REQ-21 was added but not carried everywhere. The use case reads "ListReorderSuggestions (REQ-13, REQ-15, REQ-16)" with no REQ-21. pur 02 Inputs still say "REQ-12 to REQ-16" and "REQ-21 ... is being added to the brief". 06 traces the operation to REQ-13, REQ-15, REQ-16 and REQ-21, while 02:90 traces the query to REQ-21 only. A trace built from 05 shows REQ-21 with no use case. | Use `REQ-21` alone on ListReorderSuggestions in 05 and 06; update the two Inputs lines in pur 02. | 5 | new (from the loop 1 F5 fix) |
| F13 | Low | ERD-01 | 04-erd.md:262 against 03-db-design-purchasing.md:147 | The ERD legend says columns marked `?` are NULL. `pur_inbox.subject` is drawn `subject : VC(128)` (not null), but 03 makes it NULL for internal events handed over in process. A migration written from the ERD rejects the LowStockDetected inbox row. | Draw `subject? : VC(128)` in `pur_inbox`. | 4 | new (from the loop 1 F4 fix) |
| F14 | Low | DOC-06 | 05-diagrams-flows.md:14 against 05-diagrams-use-cases.md:14; 05-diagrams.md:18 | The id D5-4 names two decisions: "ListReorderSuggestions is linked to the actor Purchasing" (use cases) and "Fixed F1: inbox dedup ..." (flows). The index says D5-4 is in the use-cases file only. A reference to D5-4 is ambiguous. | Renumber the flows decision to D5-6 and list it in the index line. | 5 | new (from the loop 1 F1 fix) |

## Lint findings rejected
| Lint id | Why rejected |
|---|---|
| none | 07-lint.md reports 0 findings, so there is nothing to confirm or reject. |

## Requirement trace
| REQ | Context | Command / query | Operation | Storage | Status (ok / MISSING / out of scope) |
|---|---|---|---|---|---|
| REQ-1 | Catalog | RegisterProduct | CatalogService.RegisterProduct | cat_product | ok (F3) |
| REQ-2 | Catalog | RegisterWarehouse | CatalogService.RegisterWarehouse | cat_warehouse | ok |
| REQ-3 | Catalog | RegisterBin | CatalogService.RegisterBin | cat_bin | ok |
| REQ-4 | Stock | ReceiveGoods | StockService.ReceiveGoods | stk_warehouse_stock, stk_stock_level, stk_stock_movement | ok (F9) |
| REQ-5 | Stock | ReserveStock | StockService.ReserveStock | stk_reservation, stk_reservation_allocation | ok (F6) |
| REQ-6 | Stock | ReserveStock (invariant) | StockService.ReserveStock | in code under the root version | ok |
| REQ-7 | Stock | ReserveStock (INSUFFICIENT_STOCK) | StockService.ReserveStock | none needed | ok |
| REQ-8 | Stock | ReserveStock (request_id) | StockService.ReserveStock | uq_stk_reservation_request | ok |
| REQ-9 | Stock | ReleaseReservation | StockService.ReleaseReservation | stk_reservation.status | ok |
| REQ-10 | Stock | PickReservation | StockService.PickReservation | stk_reservation.status, stk_stock_level | ok |
| REQ-11 | Stock | AdjustStock | StockService.AdjustStock | stk_stock_level, stk_stock_movement | ok (F9) |
| REQ-12 | Purchasing | SetLowStockThreshold | PurchasingService.SetLowStockThreshold | pur_low_stock_threshold | ok (F3, F4, F5) |
| REQ-13 | Purchasing | RecordAvailability, RaiseReorderSuggestion (policies) | none: policy-triggered (06 Not exposed) | pur_low_stock_threshold, pur_reorder_suggestion, pur_known_availability | ok in trace; delayed in the cases of F1, F2 and F4 |
| REQ-14 | Purchasing | no actor command creates a suggestion | none: RaiseReorderSuggestion is not exposed | none needed | ok |
| REQ-15 | Purchasing | AcceptReorderSuggestion | PurchasingService.AcceptReorderSuggestion | pur_reorder_suggestion | ok |
| REQ-16 | Purchasing | DismissReorderSuggestion | PurchasingService.DismissReorderSuggestion | pur_reorder_suggestion | ok |
| REQ-17 | Stock | GetAvailability | StockService.GetAvailability | computed from stk_stock_level | ok |
| REQ-18 | Stock | invariant on every Stock command | none: invariant | ck_stk_stock_level_qty | ok |
| REQ-19 | Stock | ExpireReservation (policy) | none: policy-triggered (06 Not exposed) | stk_reservation.expires_at, ix_stk_reservation_expiry | ok (duration is brief Q1) |
| REQ-20 | Stock | GetAvailability; invariant | StockService.GetAvailability | computed, not stored | ok |
| REQ-21 | Purchasing | ListReorderSuggestions | PurchasingService.ListReorderSuggestions | pur_reorder_suggestion | ok (F12; filters are brief Q9) |

Prototype elements traced: README items 1 to 10 and both closing sentences; both stub rpcs and every stub field; StockLevel fields and `Available()`; the three context.puml arrows. Each one now has a REQ. No prototype element is MISSING.

## Not checked
- `design_check.py` was not run; 07-lint.md was taken as its output.
- The PlantUML blocks were not rendered, and 06-api.proto was not compiled with `protoc`.
- MariaDB 11.4 syntax was not executed: the generated column `raised_marker` in a UNIQUE key, the CHECK expressions, ENUM behaviour under strict mode.
- InnoDB locking behaviour behind F1 and F4 (row lock, gap lock per isolation level) was reasoned through, not tested.
- JetStream delivery, redelivery and dead-letter settings; outbox relay ordering with several relay instances; the in-process hand-over of internal `pur_outbox` rows with more than one service instance.
- Index cover for ListReorderSuggestions without a status filter (DB-07): the filters and order are still a business question (brief Q9), so the indexes were not judged.
- Authentication and authorisation (identity is out of the design, 01 D1-8).
- Performance of the WarehouseStock aggregate for a SKU with many bins or open reservations; no load figure exists to judge it against.
- DOC-02 was sampled (about 15 citations), not checked for every statement.
- 00-state.md was read for context only; its Open questions row still says Q1-Q8 and does not list brief Q9.
- `tests/results/` and other fixture folders were not read, as instructed.
