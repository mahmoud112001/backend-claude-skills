# 01 Strategic design

## Inputs
- docs/design/project-profile.md (architecture_style = microservices, asked; events_messaging = outbox + NATS JetStream, ARCHITECTURE.md:8).
- docs/design/00-project-brief.md: Requirements, Actors, Goals, Decisions, Open questions.
- Rules: default-rulebook.md; ARCHITECTURE.md (R1 overrides DB-02: one shared schema `stockroom`, module-prefixed tables, only the owner reads or writes its tables).

## Decisions
| Id | Decision | Why | Source |
|---|---|---|---|
| D1-1 | Three bounded contexts: Catalog, Stock, Purchasing. | The language changes three times: describing what exists (product, warehouse, bin), counting and committing quantities, and deciding what to reorder. Different actors per group (staff registering, shipping system, purchasing). | brief Actors; REQ-1 to REQ-20; proposed cut |
| D1-2 | Module codes: Catalog = `cat`, Stock = `stk`, Purchasing = `pur`. | R1 needs a three-letter prefix per module; these match the R1 examples. | ARCHITECTURE.md:5 |
| D1-3 | One microservice per context (three deployables), all using the shared `stockroom` schema, each touching only its own prefixed tables. | Profile architecture_style is microservices (asked); R1 still binds. | project-profile.md D0-P2; ARCHITECTURE.md:5 |
| D1-4 | Contexts integrate only by integration events through each module's outbox and NATS JetStream, subjects `stockroom.<code>.<event_name>`; consumers deduplicate by event id. No context calls another context synchronously. | Profile events_messaging; R1 forbids reading another module's tables, so data needed locally arrives as events. | ARCHITECTURE.md:8; proposed |
| D1-5 | Stock keeps a local, event-fed list of known SKUs, warehouses and bins (from Catalog) to validate receipts, reservations and adjustments. | R1 forbids reading `cat_` tables; avoids a runtime call between services. | ARCHITECTURE.md:5; proposed |
| D1-6 | Purchasing owns low-stock thresholds and reorder suggestions, and reacts to Stock's availability event. | Thresholds exist only to drive suggestions (REQ-12, REQ-13); the reorder decision is Purchasing's language. | README:14-15; proposed |
| D1-7 | The outbound shipping system is an external client of Stock through Stock's gRPC open host service (StockService). | It is outside the system and calls reserve, release, pick. | REQ-5, REQ-9, REQ-10; proto:7 |
| D1-8 | Identity and access is a generic subdomain, reused (platform auth / gRPC interceptor), not a bounded context in this design. | Roles are not defined (brief Q5); no REQ owns it. | brief Q5; proposed |
| D1-9 | Pick (REQ-10) belongs to Stock: it removes reserved quantity from on hand. | Brief D0-3 keeps pick in scope as a stock-leaving behaviour. | brief D0-3; docs/context.puml:9 |

## Open questions
| Id | Question | Why it matters | Proposed default |
|---|---|---|---|
| Q1-1 | How long until a reservation expires? (brief Q1) | Drives the expiry job and limits (REQ-19). | Configurable duration; no number in the design. |
| Q1-2 | When a reservation expires, is its quantity released automatically? (brief Q2) | Changes reserved and available quantity, and the events Purchasing sees. | Yes: expiry releases the reserved quantity. |
| Q1-3 | Is a low-stock threshold compared with available or on hand, and is a suggestion raised once or each time? (brief Q6) | Defines when Purchasing raises a suggestion (REQ-13). | Compare available; at most one open suggestion per SKU and warehouse. |
| Q1-4 | Which adjustment reason codes exist? (brief Q3) | REQ-11 requires a code. | Enumerated set defined by the business, editable as configuration. |
| Q1-5 | May one reservation span bins within its warehouse? (brief Q4) | Affects how Stock allocates a reservation to stock levels. | One warehouse per reservation (REQ-6); bin allocation decided inside Stock, may span bins. |
| Q1-6 | Who may call which operation? (brief Q5) | Authorisation in the generic identity subdomain. | Actor per operation as in docs/context.puml. |
| Q1-7 | Does accepting a suggestion create a purchase order? (brief Q7) | Would add an ordering capability and possibly a new context. | No: accept only records the decision. |
| Q1-8 | Microservices with one shared schema couple the three services at the database (shared migrations, one instance). Keep this, or move to a modular monolith (profile Q1) or a schema per service? | Changes deployment and migration ownership, not the context cut. | Keep the user's answer (microservices) and R1; each service owns migrations for its own prefix. |
| Q1-9 | If Stock receives a request for a SKU, warehouse or bin that Catalog has registered but whose event has not yet arrived, what happens? | Eventual consistency between Catalog and Stock (D1-5). | Reject with NOT_FOUND (retryable); the caller retries. |
| Q1-10 | Can products, warehouses or bins be edited or retired after registration? | Would add Catalog events that Stock and Purchasing must handle. | Out of scope for now; register only (REQ-1 to REQ-3). |

## Domain
Stockroom keeps an accurate count of SKUs across a few warehouses and bins and lets an outside shipping system reserve, release and pick stock safely, with automatic reorder suggestions for purchasing (brief Goals; README:3, README:10-14). It wins when stock is never oversold or negative (REQ-6, REQ-18) and loses when counts or reservations are wrong.

## Subdomains
| Subdomain | Type | Why (source) |
|---|---|---|
| Stock control | core | Safe reservation, pick and accurate counts are the product's purpose and the outside system depends on them (brief Goals; REQ-5 to REQ-10, REQ-18). |
| Product and location catalog | supporting | Needed to name SKUs, warehouses and bins, specific to this business but not a differentiator (REQ-1 to REQ-3); proposed. |
| Replenishment | supporting | Automatic reorder suggestions serve purchasing; useful but a simple threshold rule (REQ-12 to REQ-16); proposed. |
| Identity and access | generic | Same everywhere; reuse the platform's authentication and role checks rather than build (brief Q5); proposed. |

## Bounded contexts
| Context | Subdomain | Responsibility | Owns REQ | Deployable |
|---|---|---|---|---|
| Catalog | Product and location catalog | Registers products (SKU, code, name, unit), warehouses and bins; publishes them. Module code `cat`. | REQ-1, REQ-2, REQ-3 | catalog-service; tables `stockroom.cat_*` |
| Stock | Stock control | Stock levels per SKU and bin: receipts, reservations, releases, picks, adjustments, expiry, availability; never negative. Module code `stk`. | REQ-4, REQ-5, REQ-6, REQ-7, REQ-8, REQ-9, REQ-10, REQ-11, REQ-17, REQ-18, REQ-19, REQ-20 | stock-service; tables `stockroom.stk_*` |
| Purchasing | Replenishment | Low-stock thresholds per SKU and warehouse; raises reorder suggestions automatically; records accept or dismiss. Module code `pur`. | REQ-12, REQ-13, REQ-14, REQ-15, REQ-16 | purchasing-service; tables `stockroom.pur_*` |

## Context map
| Upstream | Downstream | Relationship | Mechanism | What flows |
|---|---|---|---|---|
| Catalog | Stock | customer-supplier | Integration events via `cat` outbox, NATS subjects `stockroom.cat.<event_name>` | ProductRegistered, WarehouseRegistered, BinRegistered (ids and keys Stock needs to validate; D1-5) |
| Catalog | Purchasing | customer-supplier | Integration events via `cat` outbox, NATS subjects `stockroom.cat.<event_name>` | ProductRegistered, WarehouseRegistered (to validate threshold targets) |
| Stock | Purchasing | open host service / published language | Integration events via `stk` outbox, NATS subjects `stockroom.stk.<event_name>` | AvailabilityChanged (SKU, warehouse, available) used to compare with thresholds (REQ-13) |
| Stock | OutboundShipping (external system) | open host service / published language | Synchronous gRPC StockService (proto/stockroom/v1/stockroom.proto) | ReserveStock, ReleaseReservation, PickReservation, GetAvailability |

Purchasing sends nothing to Stock or Catalog (separate ways in that direction; Q1-7 default).

## Published language
| Context | Integration events (names) | Public operations (names) |
|---|---|---|
| Catalog | ProductRegistered, WarehouseRegistered, BinRegistered | RegisterProduct, RegisterWarehouse, RegisterBin |
| Stock | AvailabilityChanged | ReceiveGoods, ReserveStock, ReleaseReservation, PickReservation, AdjustStock, GetAvailability |
| Purchasing | ReorderSuggestionRaised, ReorderSuggestionAccepted, ReorderSuggestionDismissed | SetLowStockThreshold, AcceptReorderSuggestion, DismissReorderSuggestion, ListReorderSuggestions |

## Ubiquitous language
| Term | Context | Meaning | Not to be confused with |
|---|---|---|---|
| Product | Catalog | A stocked item identified by SKU, with code, name and unit of measure (REQ-1). | Stock's SKU reference, which carries no name or unit. |
| SKU | Catalog | The unique stock-keeping identifier given when a product is registered (REQ-1). | Stock's SKU, a reference only. |
| SKU | Stock | Reference to a Catalog product, known locally from ProductRegistered; the key of stock levels. | Catalog's Product, which owns the descriptive data. |
| SKU | Purchasing | Reference to a Catalog product that a threshold or suggestion is about. | Catalog's Product. |
| Warehouse | Catalog | A registered site that contains bins (REQ-2). | Stock's warehouse, the scope of reservations and availability. |
| Warehouse | Stock | The scope in which reservations must be covered and availability is reported (REQ-6, REQ-17). | Catalog's warehouse record. |
| Warehouse | Purchasing | The scope of a threshold and a suggestion (REQ-12). | Catalog's warehouse record. |
| Bin | Catalog | A registered location inside one warehouse (REQ-3). | Stock's bin, where quantity is held. |
| Bin | Stock | The place a stock level's quantity sits (stock.go:10). | Catalog's bin record. |
| Stock level | Stock | On hand and reserved quantity of one SKU in one bin (stock.go:7). | Availability, a per-warehouse total. |
| On hand | Stock | Physical quantity present in a bin; never negative (REQ-18). | Available. |
| Reserved | Stock | Quantity committed to open reservations, not yet picked (REQ-5). | On hand, which still includes it. |
| Available | Stock | On hand minus reserved, per SKU and warehouse (REQ-20, REQ-17). | Purchasing's last known available, a copy that may lag. |
| Available | Purchasing | The last available quantity received in AvailabilityChanged, compared with the threshold (REQ-13). | Stock's live available, the source of truth. |
| Goods receipt | Stock | Adding a received quantity of a SKU to a bin (REQ-4). | Adjustment, which corrects a count. |
| Reservation | Stock | A hold of a quantity of a SKU in one warehouse for a shipment reference, keyed by request id for retry (REQ-5, REQ-8). | A pick, which removes stock. |
| Release | Stock | Ending a reservation without picking; its quantity becomes available again (REQ-9). | Expiry, which ends it by time (REQ-19). |
| Expiry | Stock | A reservation ending because its time ran out (REQ-19; duration Q1-1). | Release, asked for by the caller. |
| Pick | Stock | The shipment is picked: the reserved quantity leaves on hand (REQ-10). | Release, which returns quantity to available. |
| Adjustment | Stock | A count correction after a cycle count, with a reason code (REQ-11). | Goods receipt. |
| Reason code | Stock | Why an adjustment was made; list open (Q1-4). | Error reason in gRPC ErrorInfo (R3). |
| Low-stock threshold | Purchasing | Minimum level for a SKU in a warehouse; below it a suggestion is raised (REQ-12). | A stock limit; Stock enforces no threshold. |
| Reorder suggestion | Purchasing | A system-raised proposal to reorder a SKU for a warehouse; raised, accepted or dismissed (REQ-13 to REQ-16). | A purchase order (not in scope, Q1-7). |
| Accept | Purchasing | Purchasing agrees with a suggestion; recorded only (REQ-15). | Creating an order. |
| Dismiss | Purchasing | Purchasing rejects a suggestion (REQ-16). | Deleting it; the decision is kept. |
