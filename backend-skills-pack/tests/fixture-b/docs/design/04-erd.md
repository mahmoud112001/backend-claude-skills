# 04 ERD

Format: PlantUML (profile `diagram_format`). Drawn from 03-db-design.md and its three parts only. Legend: `<<PK>>` primary key, `<<FK>>` foreign key inside the module (solid line), `<<REF>>` id of another context's aggregate (no FK, dotted `ref` line in the overview only). Columns marked `?` are NULL. Types are shortened: C26 is `CHAR(26)`, DT is `DATETIME(6)`, BI is `BIGINT`, VC is `VARCHAR`.

## Inputs
- docs/design/project-profile.md: diagram_format plantuml; architecture_style microservices; one shared schema `stockroom` (R1).
- docs/design/03-db-design.md (Modules table, D3-1 to D3-15), 03-db-design-catalog.md, 03-db-design-stock.md, 03-db-design-purchasing.md (Tables sections).

## Decisions
| Id | Decision | Why | Source |
|---|---|---|---|
| D4-1 | One diagram per module plus one overview. All 21 tables of 03 appear by physical name. | ERD rule in db-design-erd. | 03 Modules |
| D4-2 | Cross-module REFs are `<<REF>>` columns in the module diagrams, and dotted `ref` lines only in the overview. No relationship line crosses a module in a module diagram. | DB-01: no FK across modules. | 03 D3-1, Tables |
| D4-3 | The shared schema `stockroom` (R1 overrides DB-02) is shown as the outer frame of the overview. | Override recorded in 03 D3-1. | 03 D3-1 |
| D4-4 | `raised_marker` (generated column) and `pur_known_product.sku` (PK) are drawn as 03 states them. | Draw only what 03 says. | pur Tables |

## Open questions
- Q4-1 PlantUML entities cannot show CHECK, UNIQUE or index details. Those stay in 03. Proposed default: no action.
- Q4-2 Read-model rebuild sources (event subjects) and outbox/inbox event flow are not drawn in the ERD; they belong to the flow diagrams (phase 5). Proposed default: none.

## Overview
```plantuml
@startuml
rectangle "schema stockroom (shared, R1)" {
  package "cat (Catalog)" {
    [cat_product]
    [cat_warehouse]
    [cat_bin]
    [cat_outbox]
  }
  package "stk (Stock)" {
    [stk_warehouse_stock]
    [stk_stock_level]
    [stk_reservation]
    [stk_reservation_allocation]
    [stk_stock_movement]
    [stk_known_product]
    [stk_known_warehouse]
    [stk_known_bin]
    [stk_outbox]
    [stk_inbox]
  }
  package "pur (Purchasing)" {
    [pur_low_stock_threshold]
    [pur_reorder_suggestion]
    [pur_known_product]
    [pur_known_warehouse]
    [pur_known_availability]
    [pur_outbox]
    [pur_inbox]
  }
}
[stk_warehouse_stock] ..> [cat_product] : ref
[stk_warehouse_stock] ..> [cat_warehouse] : ref
[stk_stock_level] ..> [cat_bin] : ref
[stk_reservation_allocation] ..> [cat_bin] : ref
[stk_stock_movement] ..> [cat_bin] : ref
[stk_known_product] ..> [cat_product] : ref
[stk_known_warehouse] ..> [cat_warehouse] : ref
[stk_known_bin] ..> [cat_bin] : ref
[stk_known_bin] ..> [cat_warehouse] : ref
[pur_low_stock_threshold] ..> [cat_product] : ref
[pur_low_stock_threshold] ..> [cat_warehouse] : ref
[pur_reorder_suggestion] ..> [cat_product] : ref
[pur_reorder_suggestion] ..> [cat_warehouse] : ref
[pur_known_product] ..> [cat_product] : ref
[pur_known_warehouse] ..> [cat_warehouse] : ref
[pur_known_availability] ..> [cat_product] : ref
[pur_known_availability] ..> [cat_warehouse] : ref
@enduml
```

## Catalog (cat)
```plantuml
@startuml
hide circle
entity cat_product {
  product_id : C26 <<PK>>
  sku : VC(64)
  code : VC(64)
  name : VC(200)
  unit_of_measure : VC(16)
  registered_at : DT
  version : BI
}
entity cat_warehouse {
  warehouse_id : C26 <<PK>>
  code : VC(64)
  name : VC(200)
  registered_at : DT
  version : BI
}
entity cat_bin {
  bin_id : C26 <<PK>>
  warehouse_id : C26 <<FK>>
  code : VC(64)
  registered_at : DT
  version : BI
}
entity cat_outbox {
  event_id : C26 <<PK>>
  aggregate_type : ENUM
  aggregate_id : C26
  event_type : ENUM
  subject : VC(128)
  payload : JSON
  occurred_at : DT
  published_at? : DT
}
cat_warehouse ||--o{ cat_bin : "ON DELETE RESTRICT"
@enduml
```

## Stock (stk)
```plantuml
@startuml
hide circle
entity stk_warehouse_stock {
  warehouse_stock_id : C26 <<PK>>
  sku : VC(64) <<REF>>
  warehouse_id : C26 <<REF>>
  version : BI
  created_at : DT
}
entity stk_stock_level {
  stock_level_id : C26 <<PK>>
  warehouse_stock_id : C26 <<FK>>
  bin_id : C26 <<REF>>
  on_hand : BI
  reserved : BI
}
entity stk_reservation {
  reservation_id : C26 <<PK>>
  warehouse_stock_id : C26 <<FK>>
  request_id : VC(128)
  shipment_ref : VC(128)
  quantity : BI
  status : ENUM
  reserved_at : DT
  expires_at : DT
  closed_at? : DT
}
entity stk_reservation_allocation {
  reservation_id : C26 <<PK>> <<FK>>
  bin_id : C26 <<PK>> <<REF>>
  quantity : BI
}
entity stk_stock_movement {
  movement_id : C26 <<PK>>
  warehouse_stock_id : C26 <<FK>>
  bin_id : C26 <<REF>>
  kind : ENUM
  request_id : VC(128)
  previous_on_hand : BI
  new_on_hand : BI
  difference : BI
  reason_code? : VC(32)
  occurred_at : DT
}
entity stk_known_product {
  product_id : C26 <<PK>> <<REF>>
  sku : VC(64)
  updated_at : DT
}
entity stk_known_warehouse {
  warehouse_id : C26 <<PK>> <<REF>>
  updated_at : DT
}
entity stk_known_bin {
  bin_id : C26 <<PK>> <<REF>>
  warehouse_id : C26 <<REF>>
  updated_at : DT
}
entity stk_outbox {
  event_id : C26 <<PK>>
  aggregate_type : ENUM
  aggregate_id : C26
  event_type : ENUM
  subject : VC(128)
  payload : JSON
  occurred_at : DT
  published_at? : DT
}
entity stk_inbox {
  event_id : C26 <<PK>>
  subject : VC(128)
  processed_at : DT
}
stk_warehouse_stock ||--o{ stk_stock_level : "CASCADE"
stk_warehouse_stock ||--o{ stk_reservation : "CASCADE"
stk_warehouse_stock ||--o{ stk_stock_movement : "CASCADE"
stk_reservation ||--o{ stk_reservation_allocation : "CASCADE"
@enduml
```

## Purchasing (pur)
```plantuml
@startuml
hide circle
entity pur_low_stock_threshold {
  threshold_id : C26 <<PK>>
  sku : VC(64) <<REF>>
  warehouse_id : C26 <<REF>>
  quantity : BI
  last_available? : BI
  last_source_version? : BI
  last_source_event_id? : C26
  last_received_at? : DT
  is_below : BOOLEAN
  version : BI
  updated_at : DT
}
entity pur_reorder_suggestion {
  suggestion_id : C26 <<PK>>
  sku : VC(64) <<REF>>
  warehouse_id : C26 <<REF>>
  threshold_id : C26 <<FK>>
  status : ENUM
  threshold_quantity : BI
  available_at_trigger : BI
  detected_at : DT
  raised_at : DT
  decided_by? : VC(128)
  decided_at? : DT
  note? : VC(1000)
  raised_marker? : TINYINT
  version : BI
}
entity pur_known_product {
  sku : VC(64) <<PK>>
  product_id : C26 <<REF>>
  updated_at : DT
}
entity pur_known_warehouse {
  warehouse_id : C26 <<PK>> <<REF>>
  updated_at : DT
}
entity pur_known_availability {
  sku : VC(64) <<PK>> <<REF>>
  warehouse_id : C26 <<PK>> <<REF>>
  available : BI
  source_version : BI
  updated_at : DT
}
entity pur_outbox {
  event_id : C26 <<PK>>
  aggregate_type : ENUM
  aggregate_id : C26
  event_type : ENUM
  subject : VC(128)
  payload : JSON
  occurred_at : DT
  published_at? : DT
}
entity pur_inbox {
  event_id : C26 <<PK>>
  subject : VC(128)
  processed_at : DT
}
pur_low_stock_threshold ||--o{ pur_reorder_suggestion : "ON DELETE RESTRICT"
@enduml
```
