# 05 Diagrams: key flows

Part of [05-diagrams.md](05-diagrams.md). Use cases are in [05-diagrams-use-cases.md](05-diagrams-use-cases.md).

## Inputs
- project-profile.md: diagram_format = plantuml; events_messaging = outbox + NATS JetStream.
- 01-strategic.md: Context map.
- 02-tactical-catalog.md, 02-tactical-stock.md, 02-tactical-purchasing.md: Commands, Domain events, Policies, Queries and read models.

## Decisions
| Id | Decision | Why |
|---|---|---|
| D5-3 | Flows use the 02 names. The relay (NATS JetStream subject) is a participant between outbox and consumer. | Profile events_messaging. |
| D5-4 | Fixed F1: inbox dedup in FLOW-1 and FLOW-6 is per (event id, consumer). The projection step of FLOW-6 is not added; it awaits the 02 purchasing change. | Review F1. |

## Open questions
| Id | Question | Why it matters | Proposed default |
|---|---|---|---|
| Q5-3 | The 02 files give no failure branch for Catalog commands beyond Fails when. | Flow 1 shows only the failure reasons 02 lists. | As drawn. |

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
  N -> P : ProductRegistered (dedup by event id and consumer)
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
N -> P1 : AvailabilityChanged (dedup by event id and consumer)
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
