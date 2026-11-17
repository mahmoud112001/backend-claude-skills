# 00 Project brief: Stockroom

## Inputs
Prototype types: readme (README.md), spec (proto/stockroom/v1/stockroom.proto, docs/context.puml), code stub (internal/stock/stock.go). No UI.
Repo files read: ARCHITECTURE.md, go.mod, docker-compose.yml. Rulebook: default-rulebook.md.

## Decisions
D0-1 Requirements come from the README "What it must do" list, refined by the proto and Go stub where they show fields. Why: the README is the only full statement of behaviour.
D0-2 The proto stub covers only ReserveStock and GetAvailability; the other operations are treated as in scope because the README lists them, and their API shape is left to phase 6. Why: the proto says "the rest of the API is not designed yet".
D0-3 "Pick" (README item 6, context.puml:9) is in scope as a stock-leaving behaviour. Why: both files state it.
D0-4 ARCHITECTURE.md rules are not copied here; they are in the profile.
D0-5 Fixed F5: REQ-21 added (Purchasing lists reorder suggestions, docs/context.puml:8). Which filters apply stays an open question (Q9).

## Open questions
| Id | Question | Why it matters | Proposed default |
|---|---|---|---|
| Q1 | How long until a reservation expires? | README:18 says the business has not decided; drives expiry job and limits | Configurable value, no number fixed in design |
| Q2 | What happens when a reservation expires (stock released automatically)? | Affects available quantity and events | Expired reservation releases its quantity |
| Q3 | Which reason codes exist for adjustments? | README:13 requires a reason code but gives no list | Open enumerated set, defined by the business |
| Q4 | May a reservation span several warehouses or bins? | README:10 says one warehouse; the bin split is not stated | One warehouse per reservation; bin allocation left open |
| Q5 | Who may call which operation (roles)? | Only "read access" and staff/purchasing are named | Actor per operation as in context.puml |
| Q6 | Is a low-stock threshold compared with available or on-hand, and is a suggestion raised once or each time quantity falls? | README:14 says "available quantity drops below" but not repetition | Compare available; one open suggestion per SKU and warehouse |
| Q7 | What does accepting a suggestion do (create a purchase order)? | README:15 stops at accept or dismiss | Only records the decision; no order creation |
| Q8 | Architecture style (profile field missing) | See profile Q1 | Modular monolith |
| Q9 | Which filters does the suggestion list offer (status, SKU, warehouse)? | context.puml:8 shows listing but no filters | List by status, newest first, optional SKU and warehouse filter |

## Goals
- Keep track of stock of SKUs across a few warehouses and bins (README:3).
- Let an outside shipping system reserve, release and pick stock safely (README:10-12).
- Raise reorder suggestions automatically for purchasing (README:14).

## Actors
| Actor | Description | Source |
|---|---|---|
| Warehouse staff | Registers products, warehouses, bins; receives goods; adjusts counts | README:7-9, 13; docs/context.puml:3 |
| Purchasing | Lists, accepts or dismisses reorder suggestions | README:15; docs/context.puml:4, 8 |
| Outbound shipping system | Outside system that reserves, releases and picks | README:10-12; docs/context.puml:5 |
| Reader | Anyone with read access, asks availability | README:16 |
| System | Raises reorder suggestions automatically | README:14 |

## Screens / entry points
| Screen or entry point | Purpose | Source |
|---|---|---|
| gRPC StockService.ReserveStock | Reserve stock for a shipment | proto/stockroom/v1/stockroom.proto:8 |
| gRPC StockService.GetAvailability | On hand, reserved, available per warehouse | proto/stockroom/v1/stockroom.proto:9 |
| Release / pick / receive / adjust / register / suggestion operations | Named in README, not yet in proto | README:7-15 |

## Requirements
| REQ | Requirement (one behaviour each) | Actor | Source |
|---|---|---|---|
| REQ-1 | Register a product by SKU with code, name and unit of measure | Warehouse staff | README:7 |
| REQ-2 | Register a warehouse | Warehouse staff | README:8 |
| REQ-3 | Register bin locations inside a warehouse | Warehouse staff | README:8 |
| REQ-4 | Receive goods: a goods receipt adds quantity of a SKU to a bin | Warehouse staff | README:9 |
| REQ-5 | Reserve a quantity of a SKU for an outbound shipment, given request id, SKU, warehouse id, quantity and shipment reference; returns a reservation id | Outbound shipping system | README:10; proto:12-22 |
| REQ-6 | A reservation succeeds only if enough unreserved stock exists in one warehouse | Outbound shipping system | README:10 |
| REQ-7 | A failed reservation reports a clear reason | Outbound shipping system | README:10; ARCHITECTURE.md:7 |
| REQ-8 | A reserve call is safe to retry using the caller-generated request id | Outbound shipping system | proto:13 |
| REQ-9 | Release a reservation that is no longer needed | Outbound shipping system | README:11 |
| REQ-10 | When the shipment is picked, the reserved quantity leaves the stock | Outbound shipping system | README:12; docs/context.puml:9 |
| REQ-11 | Adjust the quantity of a SKU in a bin after a cycle count, with a reason code | Warehouse staff | README:13 |
| REQ-12 | Set a low-stock threshold for a SKU per warehouse | Warehouse staff | README:14 |
| REQ-13 | When available quantity drops below the threshold, a reorder suggestion is raised automatically | System | README:14 |
| REQ-14 | Staff cannot create reorder suggestions by hand | Warehouse staff | README:14 |
| REQ-15 | Accept a reorder suggestion | Purchasing | README:15 |
| REQ-16 | Dismiss a reorder suggestion | Purchasing | README:15 |
| REQ-17 | Show on hand, reserved and available of a SKU per warehouse | Reader | README:16; proto:24-37 |
| REQ-18 | Stock never goes negative | System | README:18 |
| REQ-19 | A reservation expires after a time the business has yet to decide | System | README:18 (duration is Q1) |
| REQ-20 | Available quantity equals on hand minus reserved | System | internal/stock/stock.go:16 |
| REQ-21 | Purchasing lists reorder suggestions | Purchasing | docs/context.puml:8 |

## Data seen in the prototype
| Data element | Where seen | Notes (type, format, rules shown) |
|---|---|---|
| SKU | README:7; proto:11 | string; code, name, unit of measure |
| Warehouse (warehouse_id) | README:8; proto:14 | string id (ULID per ARCHITECTURE.md:6) |
| Bin | README:8; stock.go:10 | belongs to a warehouse; BinID ULID |
| StockLevel | stock.go:7 | id, SKU, bin id, on_hand int64, reserved int64; one per SKU per bin |
| Goods receipt | README:9 | adds quantity to a bin |
| Reservation | README:10; proto:21 | reservation_id; request_id, shipment_ref, quantity int64 |
| Adjustment reason code | README:13 | list not given |
| Low-stock threshold | README:14 | per SKU per warehouse |
| Reorder suggestion | README:14-15 | states: raised, accepted, dismissed |
| Availability | proto:32-37 | warehouse_id, on_hand, reserved, available (int64) |

## Unknowns
| Unknown | What would settle it |
|---|---|
| Reservation expiry duration and behaviour | Business decision (Q1, Q2) |
| Adjustment reason codes | Business list (Q3) |
| Whether a reservation can be partial or span bins | Business rule (Q4) |
| Authorisation per operation | Role list (Q5) |
| Suggestion repetition and accept effect | Business rule (Q6, Q7) |
| Suggestion list filters | Business input (Q9) |
| Pick operation details (partial pick, who triggers) | Further prototype or business input |
| Unit of measure values and SKU format limits | Business input |
