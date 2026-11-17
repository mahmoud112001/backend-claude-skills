# 05 Diagrams

## Inputs
- project-profile.md: diagram_format = plantuml; architecture_style = microservices; events_messaging = outbox + NATS JetStream.
- 00-project-brief.md: Actors. Actor names follow the 02 triggers (WarehouseStaff, Purchasing, OutboundShipping, Reader).
- 01-strategic.md: Context map, Published language.
- 02-tactical-catalog.md, 02-tactical-stock.md, 02-tactical-purchasing.md: Commands, Domain events, Policies, Queries and read models.
- 03-db-design.md: Modules table. The `REF` lines of 03-db-design-stock.md and 03-db-design-purchasing.md give the cross-module references.

## Decisions
| Id | Decision | Why |
|---|---|---|
| D5-1 | Use cases show commands and queries only; read models (KnownProducts and so on) are not use cases. | They are fed by events, not triggered by an actor. |
| D5-2 | The database overview draws one `ref` line per module pair (stk to cat, pur to cat), not one per column. | The overview is not the ERD; the columns are in 04. |
| D5-3 | Flows use the 02 names. The relay (NATS JetStream subject) is a participant between outbox and consumer. | Profile events_messaging. |
| D5-4 | ListReorderSuggestions is linked to the actor Purchasing. | Pur Q2-7 proposes it; the 02 file has no trigger for queries (see Q5-1). |

## Open questions
| Id | Question | Why it matters | Proposed default |
|---|---|---|---|
| Q5-1 | Who may call ListReorderSuggestions and GetAvailability? 02 gives no trigger for queries (pur Q2-7, stk Q2-11 are proposals). | The links from actor to query are not decided. | Draw as in the proposals: Purchasing and Reader. |
| Q5-2 | Which actor sets a low-stock threshold: WarehouseStaff (as in the Purchasing 02 trigger) or Purchasing (as in the brief Actors line for REQ-12)? | Changes one actor link. | WarehouseStaff, as the 02 trigger states. |
| Q5-3 | The 02 files give no failure branch for Catalog commands beyond Fails when. | Flow 1 shows only the failure reasons 02 lists. | As drawn. |

## Use cases

### UC-Catalog
Drawn from: 02-tactical-catalog.md Commands, Policies (none), Queries (none).
```plantuml
@startuml
left to right direction
actor WarehouseStaff
rectangle "Catalog" {
  usecase "RegisterProduct (REQ-1)" as RP
  usecase "RegisterWarehouse (REQ-2)" as RW
  usecase "RegisterBin (REQ-3)" as RB
}
WarehouseStaff --> RP
WarehouseStaff --> RW
WarehouseStaff --> RB
@enduml
```

### UC-Stock
Drawn from: 02-tactical-stock.md Commands, Policies, Queries and read models.
```plantuml
@startuml
left to right direction
actor WarehouseStaff
actor OutboundShipping
actor Reader
rectangle "Stock" {
  usecase "ReceiveGoods (REQ-4, REQ-18, REQ-20)" as RG
  usecase "AdjustStock (REQ-11, REQ-18, REQ-20)" as AS
  usecase "ReserveStock (REQ-5, REQ-6, REQ-7, REQ-8, REQ-18, REQ-20)" as RS
  usecase "ReleaseReservation (REQ-9, REQ-20)" as RR
  usecase "PickReservation (REQ-10, REQ-18, REQ-20)" as PR
  usecase "GetAvailability (REQ-17, REQ-20)" as GA
  usecase "ExpireReservation <<policy>> (REQ-19, REQ-20)" as ER
}
WarehouseStaff --> RG
WarehouseStaff --> AS
OutboundShipping --> RS
OutboundShipping --> RR
OutboundShipping --> PR
Reader --> GA
@enduml
```

### UC-Purchasing
Drawn from: 02-tactical-purchasing.md Commands, Policies, Queries and read models.
```plantuml
@startuml
left to right direction
actor WarehouseStaff
actor Purchasing
rectangle "Purchasing" {
  usecase "SetLowStockThreshold (REQ-12, REQ-13)" as ST
  usecase "RecordAvailability <<policy>> (REQ-13)" as RA
  usecase "RaiseReorderSuggestion <<policy>> (REQ-13, REQ-14)" as RRS
  usecase "AcceptReorderSuggestion (REQ-15)" as ARS
  usecase "DismissReorderSuggestion (REQ-16)" as DRS
  usecase "ListReorderSuggestions (REQ-13, REQ-15, REQ-16)" as LRS
}
WarehouseStaff --> ST
Purchasing --> ARS
Purchasing --> DRS
Purchasing --> LRS
@enduml
```

## Database modules

### DB-modules
Drawn from: 03-db-design.md Modules; REF lines of 03-db-design-stock.md and 03-db-design-purchasing.md. One shared schema `stockroom` (R1 overrides DB-02).
```plantuml
@startuml
package "schema stockroom" {
  package "cat (Catalog)" as cat {
    node cat_product
    node cat_warehouse
    node cat_bin
    node cat_outbox
  }
  package "stk (Stock)" as stk {
    node stk_warehouse_stock
    node stk_stock_level
    node stk_reservation
    node stk_reservation_allocation
    node stk_stock_movement
    node stk_known_product
    node stk_known_warehouse
    node stk_known_bin
    node stk_outbox
    node stk_inbox
  }
  package "pur (Purchasing)" as pur {
    node pur_low_stock_threshold
    node pur_reorder_suggestion
    node pur_known_product
    node pur_known_warehouse
    node pur_known_availability
    node pur_outbox
    node pur_inbox
  }
}
stk ..> cat : ref
pur ..> cat : ref
@enduml
```

## Key flows

### FLOW-1 Register in Catalog and feed Stock and Purchasing
Drawn from: 02-tactical-catalog.md Commands and Domain events; 02-tactical-stock.md and 02-tactical-purchasing.md Queries and read models; 01 Context map.
```plantuml
@startuml
actor WarehouseStaff
participant "RegisterProduct" as C
participant "Product" as A
queue "cat_outbox" as O
queue "NATS stockroom.cat.product_registered" as N
participant "stk_inbox / KnownProducts (Stock)" as S
participant "pur_inbox / KnownProducts (Purchasing)" as P
WarehouseStaff -> C : RegisterProduct
C -> A : register
alt fails
  A --> WarehouseStaff : INVALID_SKU / MISSING_PRODUCT_FIELD / UNKNOWN_UNIT_OF_MEASURE / SKU_ALREADY_EXISTS / PRODUCT_CODE_ALREADY_EXISTS
else ok
  A -> O : ProductRegistered (same transaction)
  O -> N : relay
  N -> S : ProductRegistered (dedup by event id)
  N -> P : ProductRegistered (dedup by event id)
end
@enduml
```
RegisterWarehouse (WarehouseRegistered to Stock and Purchasing) and RegisterBin (BinRegistered to Stock) follow the same shape on subjects `stockroom.cat.warehouse_registered` and `stockroom.cat.bin_registered`.

### FLOW-2 ReserveStock
Drawn from: 02-tactical-stock.md Commands, Domain events, Policies; 01 Context map (Stock to OutboundShipping).
```plantuml
@startuml
actor OutboundShipping
participant "ReserveStock" as C
participant "WarehouseStock" as A
queue "stk_outbox" as O
participant "ReservationExpiryPolicy" as P
OutboundShipping -> C : ReserveStock (request_id, sku, warehouse_id, quantity, shipment_ref)
C -> A : reserve
alt fails
  A --> OutboundShipping : INVALID_QUANTITY / SKU_NOT_FOUND / WAREHOUSE_NOT_FOUND / INSUFFICIENT_STOCK / REQUEST_ID_REUSED / CONCURRENT_UPDATE
else ok
  A -> A : StockReserved
  A -> O : AvailabilityChanged (same transaction)
  A --> OutboundShipping : reservation id
  A -> P : StockReserved
end
@enduml
```

### FLOW-3 ReleaseReservation and PickReservation
Drawn from: 02-tactical-stock.md Commands, Domain events.
```plantuml
@startuml
actor OutboundShipping
participant "WarehouseStock" as A
queue "stk_outbox" as O
alt ReleaseReservation
  OutboundShipping -> A : ReleaseReservation
  A -> A : ReservationReleased
else PickReservation
  OutboundShipping -> A : PickReservation
  A -> A : ReservationPicked
end
alt fails
  A --> OutboundShipping : RESERVATION_NOT_FOUND / RESERVATION_NOT_OPEN / CONCURRENT_UPDATE
else ok
  A -> O : AvailabilityChanged (same transaction)
end
@enduml
```

### FLOW-4 ReceiveGoods and AdjustStock
Drawn from: 02-tactical-stock.md Commands, Domain events.
```plantuml
@startuml
actor WarehouseStaff
participant "WarehouseStock" as A
queue "stk_outbox" as O
alt ReceiveGoods
  WarehouseStaff -> A : ReceiveGoods
  A -> A : GoodsReceived
else AdjustStock
  WarehouseStaff -> A : AdjustStock
  A -> A : StockAdjusted
end
alt fails
  A --> WarehouseStaff : INVALID_QUANTITY / SKU_NOT_FOUND / BIN_NOT_FOUND / REASON_CODE_UNKNOWN / COUNT_BELOW_RESERVED / CONCURRENT_UPDATE
else ok
  A -> O : AvailabilityChanged (same transaction)
end
@enduml
```
REASON_CODE_UNKNOWN and COUNT_BELOW_RESERVED apply to AdjustStock only.

### FLOW-5 Reservation expiry
Drawn from: 02-tactical-stock.md Policies, Commands.
```plantuml
@startuml
participant "ReservationExpiryPolicy" as P
participant "ExpireReservation" as C
participant "WarehouseStock" as A
queue "stk_outbox" as O
P -> C : StockReserved, when expires_at passes (durable sweep)
C -> A : expire
alt reservation no longer open
  A --> P : no-op, no event
else CONCURRENT_UPDATE
  A --> P : retry on next sweep
else ok
  A -> A : ReservationExpired
  A -> O : AvailabilityChanged (same transaction)
end
@enduml
```

### FLOW-6 AvailabilityChanged to ReorderSuggestionRaised
Drawn from: 02-tactical-stock.md Domain events; 02-tactical-purchasing.md Commands, Domain events, Policies; 01 Context map (Stock to Purchasing).
```plantuml
@startuml
queue "stk_outbox" as SO
queue "NATS stockroom.stk.availability_changed" as N
participant "TrackAvailabilityAgainstThreshold" as P1
participant "RecordAvailability" as C1
participant "LowStockThreshold" as T
queue "pur_outbox" as PO
participant "RaiseSuggestionOnLowStock" as P2
participant "RaiseReorderSuggestion" as C2
participant "ReorderSuggestion" as R
SO -> N : AvailabilityChanged
N -> P1 : AvailabilityChanged (dedup by event id)
alt no threshold for SKU and warehouse
  P1 --> N : skip (ack)
else threshold exists
  P1 -> C1 : RecordAvailability
  C1 -> T : record
  alt STALE_AVAILABILITY
    T --> P1 : ignored, success
  else version conflict
    T --> P1 : retry via JetStream redelivery, then dead-letter and alert
  else crossing to below
    T -> PO : LowStockDetected (same transaction)
    PO -> P2 : LowStockDetected
    P2 -> C2 : RaiseReorderSuggestion
    C2 -> R : raise
    alt SUGGESTION_ALREADY_OPEN
      R --> P2 : treated as done
    else ok
      R -> PO : ReorderSuggestionRaised (same transaction)
    end
  end
end
@enduml
```

### FLOW-7 Accept or dismiss a suggestion
Drawn from: 02-tactical-purchasing.md Commands, Domain events. Behind REQ-15 and REQ-16, which are not core; shown because the decision events are published.
```plantuml
@startuml
actor Purchasing
participant "ReorderSuggestion" as R
queue "pur_outbox" as O
alt AcceptReorderSuggestion
  Purchasing -> R : AcceptReorderSuggestion
else DismissReorderSuggestion
  Purchasing -> R : DismissReorderSuggestion
end
alt fails
  R --> Purchasing : SUGGESTION_NOT_FOUND / SUGGESTION_ALREADY_DECIDED / version conflict
else ok (first decision only)
  R -> O : ReorderSuggestionAccepted or ReorderSuggestionDismissed
end
@enduml
```

## Context map

### CTX-map
Drawn from: 01-strategic.md Context map.
```plantuml
@startuml
rectangle "Catalog (cat)" as Cat
rectangle "Stock (stk)" as Stk
rectangle "Purchasing (pur)" as Pur
rectangle "OutboundShipping (external)" as Ship
Cat --> Stk : customer-supplier\nevents via cat outbox, NATS stockroom.cat.<event_name>\nProductRegistered, WarehouseRegistered, BinRegistered
Cat --> Pur : customer-supplier\nevents via cat outbox, NATS stockroom.cat.<event_name>\nProductRegistered, WarehouseRegistered
Stk --> Pur : open host service / published language\nevents via stk outbox, NATS stockroom.stk.<event_name>\nAvailabilityChanged
Stk --> Ship : open host service / published language\nsync gRPC StockService\nReserveStock, ReleaseReservation, PickReservation, GetAvailability
@enduml
```
