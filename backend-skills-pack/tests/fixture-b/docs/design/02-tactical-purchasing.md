# 02 Tactical design: Purchasing

## Inputs
- docs/design/project-profile.md (Go 1.22 + gRPC; MariaDB 11.4; microservices; outbox + NATS JetStream; ULID ids; R3 error format).
- docs/design/01-strategic.md: Decisions D1-1 to D1-9, Open questions Q1-1 to Q1-10, Purchasing row (module `pur`, REQ-12 to REQ-16), context map rows Catalog -> Purchasing and Stock -> Purchasing, Published language of Catalog, Stock and Purchasing, Ubiquitous language.
- docs/design/00-project-brief.md: rows REQ-12, REQ-13, REQ-14, REQ-15, REQ-16; Actors; Q6, Q7.
- Rules: default-rulebook.md; ARCHITECTURE.md R1 (overrides DB-02: one shared schema `stockroom`, tables `pur_*`, only Purchasing reads or writes them), R2 (ULID ids from the domain layer), R3 (gRPC status + ErrorInfo reason), R4 (outbox, subjects `stockroom.pur.<event_name>`, consumers deduplicate by event id).

## Decisions
| Id | Decision | Why | Source |
|---|---|---|---|
| D2-1 | Two aggregates: LowStockThreshold (one per SKU and warehouse) and ReorderSuggestion (one per raised suggestion). | The threshold rule (crossing below) and the suggestion lifecycle (raised, accepted, dismissed) are separate invariant clusters with separate lifecycles and actors. | REQ-12, REQ-13, REQ-15, REQ-16; proposed |
| D2-2 | LowStockThreshold keeps its own copy of the last known available quantity, so the "drops below" decision is taken inside one aggregate and one transaction. | REQ-13 compares available with the threshold; R1 forbids reading `stk_` tables, and AvailabilityChanged is the only source (01 context map). | REQ-13; ARCHITECTURE.md:5; proposed |
| D2-3 | A drop below is detected only on a crossing: last known available was at or above the threshold (or unknown) and the new available is strictly below it. Staying below does not raise again; rising back to at or above re-arms the threshold. | "drops below" in REQ-13 describes a transition; avoids a suggestion per stock movement (Q1-3 default). | REQ-13; 01 Q1-3; proposed |
| D2-4 | Raising a suggestion is eventually consistent with the threshold: LowStockThreshold emits LowStockDetected (internal), policy RaiseSuggestionOnLowStock issues RaiseReorderSuggestion in a separate transaction. | A command changes one aggregate instance per transaction (TAC-03). | proposed |
| D2-5 | "At most one open (Raised) suggestion per SKU and warehouse" (Q1-3 default) is enforced by a unique store key on the open suggestion of a SKU and warehouse; RaiseReorderSuggestion fails with SUGGESTION_ALREADY_OPEN and the policy treats that as done. | Set validation across ReorderSuggestion instances; a unique key is atomic without merging aggregates. | 01 Q1-3; proposed |
| D2-6 | ReorderSuggestion is created only by policy; no actor command creates one, and phase 6 must not expose RaiseReorderSuggestion. | REQ-14: staff cannot create suggestions by hand. | REQ-14 |
| D2-7 | Accept and dismiss are terminal and recorded only; they create no purchase order. Repeating the same decision is a no-op success; the opposite decision fails with SUGGESTION_ALREADY_DECIDED. | Q1-7 default; the decision is kept (ubiquitous language "Dismiss"). Same-decision retry makes the operation safe to retry. | REQ-15, REQ-16; 01 Q1-7; proposed |
| D2-8 | Purchasing validates SKU and warehouse against local read models KnownProducts and KnownWarehouses, fed by Catalog's ProductRegistered and WarehouseRegistered. An unknown id fails with NOT_FOUND (retryable). | R1 forbids reading `cat_` tables; context map Catalog -> Purchasing; same rule as Stock (Q1-9 default). | 01 context map; 01 Q1-9; proposed |
| D2-9 | SetLowStockThreshold creates the threshold or replaces its quantity (upsert on SKU and warehouse). On creation it seeds last known available from the KnownAvailability read model and evaluates the crossing at once. | Makes the operation safe to retry by natural key; avoids waiting for a later stock movement when stock is already low (see Q2-2). | REQ-12; proposed |
| D2-10 | Internal events (LowStockThresholdSet, LowStockDetected, AvailabilityRecovered) are written to the `pur` outbox in the same transaction, so the follow-up policy cannot be lost; they are not part of the published language and no other context subscribes to them. | R4 gives the outbox as the reliable channel; TAC-10 keeps internal events inside the context. | ARCHITECTURE.md:8; proposed |
| D2-11 | Both aggregate roots carry a version for optimistic concurrency; a concurrent AvailabilityChanged for the same SKU and warehouse retries the command. | Concurrent deliveries for one key must not lose a crossing. | DB-08; proposed |
| D2-12 | Ids (threshold id, suggestion id) are ULID strings generated in the domain layer. | R2. | ARCHITECTURE.md:6 |

## Open questions
| Id | Question | Why it matters | Proposed default |
|---|---|---|---|
| Q2-1 | AvailabilityChanged carries (SKU, warehouse, available) per 01. Can Stock add an ordering field (per SKU-warehouse sequence or occurred-at time) so Purchasing can drop out-of-order events? | JetStream redelivery or parallel consumers can deliver an older available after a newer one, causing a wrong crossing. | Ask Stock to include an occurred-at and a per SKU-warehouse sequence; Purchasing ignores an event older than the one it has. Until then, use the event's broker sequence. |
| Q2-2 | When a threshold is set and the last known available is already below it, is a suggestion raised at once? | REQ-13 says "drops below"; stock may already be low. | Yes: treat setting the threshold as a crossing (D2-9). |
| Q2-3 | After a suggestion is dismissed (or accepted) while available stays below, should a new suggestion be raised? | Defines how often purchasing is prompted (brief Q6). | No: a new suggestion only after available returns to at or above the threshold and drops again (D2-3). |
| Q2-4 | What values may a threshold take: whole units only, and may it be zero? | Unit of measure may allow fractions; zero would mean "never suggest". | Non-negative whole number, same unit as Stock's available; zero allowed and disables suggestions. |
| Q2-5 | Should a suggestion carry a proposed reorder quantity? | REQ-13 to REQ-16 name no quantity; purchasing may need one. | No quantity; the suggestion records the threshold and the available that triggered it. |
| Q2-6 | Can a threshold be removed, and what happens to an open suggestion then? | No REQ covers removal. | Out of scope; set the threshold to zero to stop new suggestions; open suggestions stay until decided. |
| Q2-7 | Who may set thresholds, and who may accept or dismiss (roles)? | Authorisation (brief Q5, 01 Q1-6). | SetLowStockThreshold: Warehouse staff; Accept, Dismiss, List: Purchasing. |
| Q2-8 | Does a suggestion expire if left undecided? | An open suggestion blocks new ones (D2-5). | No expiry. |
| Q2-9 | Which payload fields do ProductRegistered and WarehouseRegistered carry? Purchasing needs at least the SKU id and the warehouse id. | Purchasing must consume them exactly as Catalog publishes (01 lists names only). | SKU id for ProductRegistered; warehouse id for WarehouseRegistered; confirm in Catalog's 02. |

## Aggregates
| Aggregate | Root entity | Contains (entities, value objects) | References by id | Invariants (REQ) | Created by |
|---|---|---|---|---|---|
| LowStockThreshold | LowStockThreshold | ThresholdQuantity, AvailabilitySnapshot | SKU (Catalog), Warehouse (Catalog) | One threshold per SKU and warehouse (REQ-12). SKU and warehouse must be known from Catalog events, checked against KnownProducts and KnownWarehouses; eventually consistent with Catalog (REQ-12, D2-8). Threshold quantity is a valid ThresholdQuantity (Q2-4). An older availability never replaces a newer one (Q2-1). LowStockDetected is emitted only when available crosses from at or above (or unknown) to strictly below the threshold (REQ-13, D2-3). Raising the suggestion is eventually consistent: LowStockDetected, then policy RaiseSuggestionOnLowStock, then RaiseReorderSuggestion (D2-4). | actor:WarehouseStaff |
| ReorderSuggestion | ReorderSuggestion | SuggestionStatus, TriggerSnapshot, SuggestionDecision | SKU (Catalog), Warehouse (Catalog), LowStockThreshold | Created only by policy, never by a person (REQ-14). Status moves Raised -> Accepted or Raised -> Dismissed, once; a decided suggestion is kept and never changes again (REQ-15, REQ-16). At most one Raised suggestion per SKU and warehouse, enforced by a unique store key at creation (Q1-3, D2-5). | policy:RaiseSuggestionOnLowStock |

## Entities and value objects
| Name | Kind (entity / value object) | Belongs to | Fields | Rules |
|---|---|---|---|---|
| LowStockThreshold | entity | LowStockThreshold | threshold_id (ULID), sku_id, warehouse_id, quantity (ThresholdQuantity), last_available (AvailabilitySnapshot, absent until first known), is_below (bool), version, updated_at | Key (sku_id, warehouse_id) unique; is_below is derived from last_available < quantity and changes only through SetLowStockThreshold or RecordAvailability. |
| ThresholdQuantity | value object | LowStockThreshold | value (whole number) | value >= 0 (Q2-4); replaced, never edited. |
| AvailabilitySnapshot | value object | LowStockThreshold | available, source_event_id, source_order (sequence or occurred-at, Q2-1), received_at | Immutable; replaced only by a snapshot with a newer source_order. |
| ReorderSuggestion | entity | ReorderSuggestion | suggestion_id (ULID), sku_id, warehouse_id, threshold_id, status (SuggestionStatus), trigger (TriggerSnapshot), decision (SuggestionDecision, absent while Raised), raised_at, version | Created in status Raised; status changes only through AcceptReorderSuggestion or DismissReorderSuggestion. |
| SuggestionStatus | value object | ReorderSuggestion | one of Raised, Accepted, Dismissed | Enumerated; Accepted and Dismissed are terminal (REQ-15, REQ-16). |
| TriggerSnapshot | value object | ReorderSuggestion | threshold_quantity, available_at_trigger, detected_at | Copy of the values that caused the suggestion; immutable. |
| SuggestionDecision | value object | ReorderSuggestion | outcome (Accepted or Dismissed), decided_by (actor id from the identity subdomain), decided_at, note (optional free text; absent means no note given) | Set once; never edited (REQ-15, REQ-16). |

## Commands
| Command | Aggregate | Trigger | Emits | Fails when | REQ |
|---|---|---|---|---|---|
| SetLowStockThreshold | LowStockThreshold | actor:WarehouseStaff | LowStockThresholdSet; LowStockDetected when the new quantity puts the last known available strictly below it after it was not below (D2-3, D2-9); AvailabilityRecovered when the new quantity puts it at or above after it was below | SKU_NOT_FOUND: SKU not in KnownProducts (NOT_FOUND, retryable); WAREHOUSE_NOT_FOUND: warehouse not in KnownWarehouses (NOT_FOUND, retryable); INVALID_THRESHOLD: quantity not a valid ThresholdQuantity (INVALID_ARGUMENT); version conflict (ABORTED, retry) | REQ-12, REQ-13 |
| RecordAvailability | LowStockThreshold | policy:TrackAvailabilityAgainstThreshold | LowStockDetected on a crossing to below; AvailabilityRecovered on a crossing to at or above; nothing otherwise | STALE_AVAILABILITY: event older than last_available (ignored, success); version conflict (retry) | REQ-13 |
| RaiseReorderSuggestion | ReorderSuggestion | policy:RaiseSuggestionOnLowStock | ReorderSuggestionRaised | SUGGESTION_ALREADY_OPEN: a Raised suggestion exists for the SKU and warehouse (policy treats as done) | REQ-13, REQ-14 |
| AcceptReorderSuggestion | ReorderSuggestion | actor:Purchasing | ReorderSuggestionAccepted (only on the first accept) | SUGGESTION_NOT_FOUND (NOT_FOUND); SUGGESTION_ALREADY_DECIDED: suggestion is Dismissed (FAILED_PRECONDITION); version conflict (ABORTED, retry) | REQ-15 |
| DismissReorderSuggestion | ReorderSuggestion | actor:Purchasing | ReorderSuggestionDismissed (only on the first dismiss) | SUGGESTION_NOT_FOUND (NOT_FOUND); SUGGESTION_ALREADY_DECIDED: suggestion is Accepted (FAILED_PRECONDITION); version conflict (ABORTED, retry) | REQ-16 |

## Domain events
| Event | Emitted by | Kind | Payload | Consumers |
|---|---|---|---|---|
| LowStockThresholdSet | LowStockThreshold | internal | event_id, threshold_id, sku_id, warehouse_id, quantity, occurred_at | none (audit only) |
| LowStockDetected | LowStockThreshold | internal | event_id, threshold_id, sku_id, warehouse_id, threshold_quantity, available, occurred_at | RaiseSuggestionOnLowStock |
| AvailabilityRecovered | LowStockThreshold | internal | event_id, threshold_id, sku_id, warehouse_id, threshold_quantity, available, occurred_at | none (re-arm is state inside LowStockThreshold) |
| ReorderSuggestionRaised | ReorderSuggestion | integration | event_id, suggestion_id, sku_id, warehouse_id, threshold_quantity, available_at_trigger, raised_at | none in 01 (published on `stockroom.pur.reorder_suggestion_raised` for future subscribers) |
| ReorderSuggestionAccepted | ReorderSuggestion | integration | event_id, suggestion_id, sku_id, warehouse_id, decided_by, decided_at | none in 01 (published on `stockroom.pur.reorder_suggestion_accepted`) |
| ReorderSuggestionDismissed | ReorderSuggestion | integration | event_id, suggestion_id, sku_id, warehouse_id, decided_by, decided_at | none in 01 (published on `stockroom.pur.reorder_suggestion_dismissed`) |

## Policies
| Policy | When (event) | Then (command) | Context | On failure |
|---|---|---|---|---|
| TrackAvailabilityAgainstThreshold | AvailabilityChanged | RecordAvailability | Stock | Skip (ack) when no threshold exists for the SKU and warehouse; ack STALE_AVAILABILITY; retry version conflicts and transient errors via JetStream redelivery with backoff; after the retry limit, dead-letter and alert. Deduplicate by event id (R4). |
| RaiseSuggestionOnLowStock | LowStockDetected | RaiseReorderSuggestion | Purchasing | Ack SUGGESTION_ALREADY_OPEN as done; retry transient errors with backoff; after the retry limit, dead-letter and alert. Deduplicate by event id. |

## Queries and read models
| Query / read model | Kind (query / read model / cache) | Source | Rebuild or invalidation | Staleness | REQ |
|---|---|---|---|---|---|
| ListReorderSuggestions | query | `pur_` reorder suggestion table (ReorderSuggestion) | Reads current state; nothing to rebuild | None (reads the source of truth) | REQ-13, REQ-15, REQ-16 |
| KnownProducts | read model | Catalog ProductRegistered | Projected on each event, deduplicated by event id; rebuilt by replaying the `stockroom.cat.product_registered` stream | Event delivery lag (seconds); a missing SKU gives retryable NOT_FOUND | REQ-12 |
| KnownWarehouses | read model | Catalog WarehouseRegistered | Projected on each event, deduplicated by event id; rebuilt by replaying the `stockroom.cat.warehouse_registered` stream | Event delivery lag (seconds); a missing warehouse gives retryable NOT_FOUND | REQ-12 |
| KnownAvailability | read model | Stock AvailabilityChanged (all SKUs and warehouses, with or without a threshold) | Projected on each event, keeping only the newest per SKU and warehouse (Q2-1); rebuilt by replaying the `stockroom.stk.availability_changed` stream | Event delivery lag; used only to seed a new LowStockThreshold (D2-9), never as the truth of available | REQ-12, REQ-13 |

## Out of scope
| REQ | Why |
|---|---|
| none | All Purchasing REQs (REQ-12, REQ-13, REQ-14, REQ-15, REQ-16) map to a command or query. |
