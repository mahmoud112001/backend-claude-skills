# 05 Diagrams: use cases

Part of [05-diagrams.md](05-diagrams.md). Key flows are in [05-diagrams-flows.md](05-diagrams-flows.md).

## Inputs
- project-profile.md: diagram_format = plantuml.
- 00-project-brief.md: Actors. Actor names follow the 02 triggers (WarehouseStaff, Purchasing, OutboundShipping, Reader).
- 02-tactical-catalog.md, 02-tactical-stock.md, 02-tactical-purchasing.md: Commands, Policies, Queries and read models.

## Decisions
| Id | Decision | Why |
|---|---|---|
| D5-1 | Use cases show commands and queries only; read models (KnownProducts and so on) are not use cases. | They are fed by events, not triggered by an actor. |
| D5-4 | ListReorderSuggestions is linked to the actor Purchasing. | Pur Q2-7 proposes it; the 02 file has no trigger for queries (see Q5-1). |

## Open questions
| Id | Question | Why it matters | Proposed default |
|---|---|---|---|
| Q5-1 | Who may call ListReorderSuggestions and GetAvailability? 02 gives no trigger for queries (pur Q2-7, stk Q2-11 are proposals). | The links from actor to query are not decided. | Draw as in the proposals: Purchasing and Reader. |
| Q5-2 | Which actor sets a low-stock threshold: WarehouseStaff (as in the Purchasing 02 trigger) or Purchasing (as in the brief Actors line for REQ-12)? | Changes one actor link. | WarehouseStaff, as the 02 trigger states. |

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
