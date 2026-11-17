# 07 Design review (loop 1)

## Inputs
Design files read in full (line counts): project-profile.md (38), 00-project-brief.md (93), 00-state.md (35), 01-strategic.md (97), 02-tactical-catalog.md (81), 02-tactical-stock.md (96), 02-tactical-purchasing.md (91), 03-db-design.md (63), 03-db-design-catalog.md (96), 03-db-design-stock.md (196), 03-db-design-purchasing.md (157), 04-erd.md (262), 05-diagrams.md (84), 05-diagrams-use-cases.md (87), 05-diagrams-flows.md (192), 06-api.md (114), 06-api.proto (215), 07-lint.md (18).

Rule files: default-rulebook.md (91); ARCHITECTURE.md (10). R1 overrides DB-02, so DB-02's "own schema" part was not checked; R1 (shared schema `stockroom`, 3-letter prefix, owner-only access) was checked instead.

Prototype read directly: README.md (25), proto/stockroom/v1/stockroom.proto (37), internal/stock/stock.go (16), docs/context.puml (10), docker-compose.yml (18), go.mod (11).

Stated size: "a few warehouses" (README:3). No load figure is given.

## Decisions
- Verdict: **fail** (1 High).
- Totals: High 1, Medium 6, Low 7.
- R1 to R6 hold in every artifact: all 21 tables carry the module prefix, no FK crosses a module, ids are `CHAR(26)` with no database default, subjects follow `stockroom.<module>.<event_name>`, all diagrams are PlantUML, proto naming follows R6.
- The stub proto is wire-compatible with 06-api.proto: fields 1 to 5 of ReserveStockRequest, field 1 of ReserveStockResponse and all of GetAvailability keep their numbers and types.
- F1 is rated High on the assumption that the projection and the policy are built as two consumers, which is how 02 lists them. If the author intended one handler, the fix is one sentence, but the design does not say so today.

## Open questions
| Id | Business decision needed | Found in | Proposed default |
|---|---|---|---|
| OQ-1 | Does Purchasing need to list and review suggestions, and with which filters? The prototype says "review reorder suggestions" but the brief has no requirement for it (see F5). | docs/context.puml:8; 00-project-brief.md:63-64 | Yes: list by status, newest first, optional SKU and warehouse filter (as 06 D6-12 already proposes). |
| OQ-2 | A threshold is set for a SKU that has never had stock in that warehouse, so no AvailabilityChanged exists. Is that "below the threshold"? | 02-tactical-purchasing.md:20 (D2-9), :14 (D2-3) | No suggestion until the first stock event for that SKU and warehouse (what the design does now). |
| OQ-3 | Who sets a low-stock threshold: warehouse staff or purchasing? README:14 does not say (see F8). Already open as brief Q5, pur Q2-7, Q5-2 and Q6-6; listed here so that it is answered once. | 00-project-brief.md:60 | Warehouse staff, as the 02 trigger states. |

## Findings
| Id | Severity | Rule | Location | Case | Fix | Owner phase |
|---|---|---|---|---|---|---|
| F1 | High | BUG (DB-05) | 02-tactical-purchasing.md:77 and :86; 03-db-design-purchasing.md:139 | AvailabilityChanged has two consumers in Purchasing: the policy TrackAvailabilityAgainstThreshold (:77, "Deduplicate by event id") and the read model KnownAvailability (:86). `pur_inbox` has `PK event_id` only (03:139). When both are built as consumers, the first inserts the inbox row; the second gets a duplicate key and, per D3-9, acks the event as "already handled". Result: either the threshold never records the new available (a drop below raises no suggestion, REQ-13 fails silently) or KnownAvailability is never updated (a new threshold is seeded with a stale value). FLOW-6 (05-diagrams-flows.md:150-151) also shows "skip (ack)" with no projection step. | In pur 02 state one handler per AvailabilityChanged, in one transaction with one inbox row: upsert KnownAvailability first, then issue RecordAvailability if a threshold exists. Phase 5 then adds the projection step to FLOW-6. | 2 |
| F2 | Medium | BUG (race) | 02-tactical-purchasing.md:20 | D2-9: "On creation it seeds last known available from the KnownAvailability read model". When SetLowStockThreshold (threshold 50) reads KnownAvailability at version 5 (available 100) and, before it commits, AvailabilityChanged version 6 (available 40) arrives, the policy finds no threshold and skips. The threshold then commits with available 100 and `is_below = false`. Stock is below the threshold with no suggestion until the next stock movement for that SKU and warehouse. | Add to D2-9: SetLowStockThreshold reads the `pur_known_availability` row with a locking read inside its transaction, and the AvailabilityChanged handler takes the same row lock before it looks up the threshold. | 2 |
| F3 | Medium | BUG | 03-db-design-purchasing.md:43 against :105-109 | `ck_pur_threshold_snapshot` requires `last_source_event_id IS NOT NULL` whenever `last_available` is set. `pur_known_availability` has no event id column. When a threshold is created for a SKU whose availability is known (the usual case), the seed of D2-9 has no event id to write, so the insert breaks the CHECK or the developer invents a value. | Add `source_event_id CHAR(26) NOT NULL` to `pur_known_availability`; phase 4 adds the column to the ERD. | 3 |
| F4 | Medium | TAC-10 | 03-db-design-purchasing.md:125; 02-tactical-purchasing.md:21 | The outbox example subject is `stockroom.pur.low_stock_detected`, and `pur_inbox` (03:139) dedups "its own LowStockDetected". So the internal events LowStockThresholdSet, LowStockDetected and AvailabilityRecovered are relayed to NATS in the R4 integration-subject namespace. When another service subscribes to `stockroom.pur.>`, it receives events that 01 Published language does not list, and they become a contract. Stock does the opposite (03-db-design.md:21: internal events are not written to the outbox). Rated Medium because no other context consumes them today. | In pur D2-10 state that the relay hands internal outbox rows to the in-process policy and never publishes them to NATS; change the example subject at 03-pur:125 to an integration event. | 2 |
| F5 | Medium | MISSING | 00-project-brief.md:63-64 | docs/context.puml:8 says "purchasing --> stockroom : review reorder suggestions". The brief has REQ-15 (accept) and REQ-16 (dismiss) but no requirement to see suggestions. ListReorderSuggestions exists only as a design proposal traced to REQ-13, REQ-15 and REQ-16 (02-tactical-purchasing.md:83), none of which asks for a list. When the brief is used as the acceptance list, listing is untested and can be dropped. | Add REQ-21 "Purchasing lists reorder suggestions", source docs/context.puml:8, owner Purchasing. Phases 1, 2 and 6 then cite it on ListReorderSuggestions. Filters go to OQ-1. | 0 |
| F6 | Medium | DOC-04 | 02-tactical-purchasing.md:47, :50, :67-72 | Purchasing 02 names the field `sku_id` in both aggregates and in every event payload. 03 (03-db-design.md:25, D3-12), 06 (06-api.md:27, D6-13) and Stock's AvailabilityChanged (02-tactical-stock.md:78) name it `sku` and mean the SKU value. Q3-1 asks 02 to rename it and 02 has not. When a subscriber of ReorderSuggestionRaised is built from 02, it expects `sku_id`, and may take it for the product ULID. | Rename `sku_id` to `sku` in pur 02 (entities and event payloads) and close Q3-1. | 2 |
| F7 | Medium | BUG (race) | 02-tactical-stock.md:21 and :49 | D2-10 covers conflicts by `version`, and :49 says the root is "created by the first ReceiveGoods or AdjustStock". When two ReceiveGoods calls for a new SKU and warehouse (different bins) run at once, both find no root and both insert. One breaks `uq_stk_warehouse_stock_sku_wh` (03-db-design-stock.md:36). There is no version conflict to catch, and no listed error covers it, so the caller gets an unmapped internal error. | Add to D2-10: a duplicate key on root creation is treated as CONCURRENT_UPDATE and retried. | 2 |
| F8 | Low | DOC-02 | 00-project-brief.md:60 | REQ-12 gives Actor "Warehouse staff" with source README:14. README:14 names no actor for setting a threshold. 05-diagrams-use-cases.md:20 (Q5-2) then says the brief names Purchasing, which it does not. | Mark the REQ-12 actor as *proposed* and point to brief Q5. Phase 5 corrects the wording of Q5-2. | 0 |
| F9 | Low | BUG | 02-tactical-stock.md:63 | ReserveStock lists no outcome for a known SKU and known warehouse that has no WarehouseStock yet (nothing ever received there). When the shipping system reserves in that case, the result is undefined: INSUFFICIENT_STOCK, a not-found error or an internal error. | Add to the ReserveStock row: no WarehouseStock for the SKU and warehouse fails with INSUFFICIENT_STOCK. | 2 |
| F10 | Low | BUG | 03-db-design-stock.md:188 | "Updates use `WHERE status = 'Open' AND version = ?`" for a reservation, but `stk_reservation` (:60-70) has no `version` column; the version is on `stk_warehouse_stock`. | Reword: the reservation update uses `WHERE status = 'Open'`, and the root update checks `version`. | 3 |
| F11 | Low | BUG | 05-diagrams-flows.md:64 and :122 | FLOW-2 draws `A -> P : StockReserved`, and FLOW-5 draws the policy as triggered by StockReserved. 03-db-design.md:21 (D3-8) says Stock's internal events are not written anywhere and expiry is a sweep over `stk_reservation`. When a developer follows the flow, they build an event delivery that the storage design does not have. | Replace the arrow at :64 with a note "the sweep reads open reservations by expires_at", and label :122 the same way. | 5 |
| F12 | Low | API-04 | 06-api.md:66 and :70 against 02-tactical-stock.md:62 and :66 | 06 lists REQUEST_ID_REUSED for ReceiveGoods and AdjustStock; the 02 `Fails when` cells do not. When 02 is used to write the domain tests, the reuse case is missing. | Add REQUEST_ID_REUSED (*proposed*, Q6-4) to both 02 rows. | 2 |
| F13 | Low | DOC-02 | 02-tactical-stock.md:22; 03-db-design.md:18 | Both cite `proto:21` for the int64 quantity. proto:21 is `string reservation_id = 1;`. The quantity is at proto:16. | Change the citation to proto:16 in both files (phase 3 for 03-db-design.md:18). | 2 |
| F14 | Low | BUG (stale) | 02-tactical-stock.md:37; 02-tactical-purchasing.md:28, :36, :49; project-profile.md:12; 00-project-brief.md:23 | Questions that another artifact has already answered are still open with a different default. stk Q2-9 and pur Q2-9 ask for Catalog payloads that 02-tactical-catalog.md:64-66 defines. pur Q2-1 says "use the event's broker sequence" and :49 says "sequence or occurred-at", while stk D2-9 and 03 D3-13 fix the order field as the WarehouseStock `version`. Profile Q1 and brief Q8 still propose "modular monolith" although D0-P2 records the answer "microservices". A developer who reads pur 02 alone builds ordering on the broker sequence. | Close each question with a pointer to the answering decision. Phase 0 closes profile Q1 and brief Q8. | 2 |

## Lint findings rejected
| Lint id | Why rejected |
|---|---|
| none | 07-lint.md reports 0 findings, so there is nothing to confirm or reject. |

## Requirement trace
| REQ | Context | Command / query | Operation | Storage | Status (ok / MISSING / out of scope) |
|---|---|---|---|---|---|
| REQ-1 | Catalog | RegisterProduct | CatalogService.RegisterProduct | cat_product | ok |
| REQ-2 | Catalog | RegisterWarehouse | CatalogService.RegisterWarehouse | cat_warehouse | ok |
| REQ-3 | Catalog | RegisterBin | CatalogService.RegisterBin | cat_bin | ok |
| REQ-4 | Stock | ReceiveGoods | StockService.ReceiveGoods | stk_warehouse_stock, stk_stock_level, stk_stock_movement | ok (F7) |
| REQ-5 | Stock | ReserveStock | StockService.ReserveStock | stk_reservation, stk_reservation_allocation | ok (F9) |
| REQ-6 | Stock | ReserveStock (invariant) | StockService.ReserveStock | in code under the root version | ok |
| REQ-7 | Stock | ReserveStock (INSUFFICIENT_STOCK) | StockService.ReserveStock | none needed | ok |
| REQ-8 | Stock | ReserveStock (request_id) | StockService.ReserveStock | uq_stk_reservation_request | ok |
| REQ-9 | Stock | ReleaseReservation | StockService.ReleaseReservation | stk_reservation.status | ok |
| REQ-10 | Stock | PickReservation | StockService.PickReservation | stk_reservation.status, stk_stock_level | ok |
| REQ-11 | Stock | AdjustStock | StockService.AdjustStock | stk_stock_level, stk_stock_movement | ok |
| REQ-12 | Purchasing | SetLowStockThreshold | PurchasingService.SetLowStockThreshold | pur_low_stock_threshold | ok (F2, F3, F8) |
| REQ-13 | Purchasing | RecordAvailability, RaiseReorderSuggestion (policies) | none: policy-triggered (06 Not exposed) | pur_low_stock_threshold, pur_reorder_suggestion | ok in trace; at risk from F1 and F2 |
| REQ-14 | Purchasing | no actor command creates a suggestion | none: RaiseReorderSuggestion is not exposed | none needed | ok |
| REQ-15 | Purchasing | AcceptReorderSuggestion | PurchasingService.AcceptReorderSuggestion | pur_reorder_suggestion | ok |
| REQ-16 | Purchasing | DismissReorderSuggestion | PurchasingService.DismissReorderSuggestion | pur_reorder_suggestion | ok |
| REQ-17 | Stock | GetAvailability | StockService.GetAvailability | computed from stk_stock_level | ok |
| REQ-18 | Stock | invariant on every Stock command | none: invariant | ck_stk_stock_level_qty | ok |
| REQ-19 | Stock | ExpireReservation (policy) | none: policy-triggered (06 Not exposed) | stk_reservation.expires_at, ix_stk_reservation_expiry | ok (duration is brief Q1) |
| REQ-20 | Stock | GetAvailability; invariant | StockService.GetAvailability | computed, not stored | ok |
| (no REQ) | Purchasing | ListReorderSuggestions | PurchasingService.ListReorderSuggestions | pur_reorder_suggestion | MISSING in the brief (F5): docs/context.puml:8 |

Prototype elements traced: README items 1 to 10 and both closing sentences; both stub rpcs and every stub field; StockLevel fields and `Available()`; the three context.puml arrows. Only the "review reorder suggestions" arrow has no REQ.

## Not checked
- `design_check.py` was not run; 07-lint.md was taken as its output.
- The PlantUML blocks were not rendered, and 06-api.proto was not compiled with `protoc`.
- MariaDB 11.4 syntax was not executed: the generated column `raised_marker` in a UNIQUE key, the CHECK expressions, ENUM behaviour under strict mode.
- The fix proposed for F2 (locking read against the handler) was reasoned through, not tested against InnoDB isolation behaviour.
- JetStream delivery, redelivery and dead-letter settings; outbox relay ordering with several relay instances.
- Authentication and authorisation (identity is out of the design, 01 D1-8).
- Performance of the WarehouseStock aggregate for a SKU with many bins or open reservations; no load figure exists to judge it against.
- DOC-02 was sampled (about 15 citations), not checked for every statement.
- `tests/results/` and other fixture folders were not read, as instructed.
