# 02 Tactical design: Catalog

## Inputs
- docs/design/project-profile.md (Go 1.22 + gRPC, MariaDB, microservices, outbox + NATS JetStream, ULID ids, R3 error format).
- docs/design/01-strategic.md: Decisions D1-1 to D1-9, Open questions Q1-1 to Q1-10, Catalog row (REQ-1, REQ-2, REQ-3, module code `cat`), context map rows Catalog -> Stock and Catalog -> Purchasing, Published language, Ubiquitous language.
- docs/design/00-project-brief.md: REQ-1, REQ-2, REQ-3; Actors; Data seen in the prototype; Unknowns.
- Rules: default-rulebook.md; ARCHITECTURE.md R1 (overrides DB-02: shared schema `stockroom`, tables `cat_*`, only Catalog reads or writes them), R2 (ULID ids from the domain layer), R3 (gRPC status + ErrorInfo reason UPPER_SNAKE_CASE), R4 (per-module outbox, subjects `stockroom.cat.<event_name>`).

## Decisions
| Id | Decision | Why | Source |
|---|---|---|---|
| D2-1 | Three aggregates: Product, Warehouse, Bin. Each is created once and holds no invariant that needs another aggregate in the same transaction. | Smallest consistency units; a warehouse with all its bins would grow with every bin and is not needed by any invariant (TAC-11). | REQ-1, REQ-2, REQ-3; proposed |
| D2-2 | Bin is its own aggregate and references Warehouse by `WarehouseId`. RegisterBin checks that the warehouse exists by reading the Warehouse repository; this is safe because warehouses cannot be retired (Q1-10 default). | REQ-3 says bins are inside a warehouse; holding a reference keeps Warehouse small. | REQ-3; 01 Q1-10; proposed |
| D2-3 | Uniqueness rules (SKU across products, warehouse code across warehouses, bin code within a warehouse) are set validations: the command checks, and a unique key in the `cat_` tables is the final guard. A duplicate fails the command. | Uniqueness across instances cannot live in one instance; the store enforces it atomically (DB-04). | REQ-1; proposed |
| D2-4 | Every aggregate has a ULID id generated in the domain layer (`ProductId`, `WarehouseId`, `BinId`). The SKU is a separate natural key and is what Stock and Purchasing key on; events carry both. | R2; 01 ubiquitous language uses SKU as Stock's key. | ARCHITECTURE.md:6; 01 Ubiquitous language |
| D2-5 | All three events are integration events, written to the `cat` outbox in the same transaction as the aggregate and relayed to `stockroom.cat.<event_name>`. | 01 Published language and context map; R4. | ARCHITECTURE.md:8; 01 D1-4 |
| D2-6 | Catalog has no policies: it consumes no event from another context. | 01 context map: Catalog is only upstream. | 01 Context map |
| D2-7 | Register commands are not edits: once registered, Product, Warehouse and Bin are immutable in this design. | 01 Q1-10 default: register only. | 01 Q1-10; proposed |
| D2-8 | Catalog offers no read query in this phase; no Catalog REQ asks for one. | Coverage is by commands (TAC-07); a lookup can be added if Q2-6 says so. | REQ-1, REQ-2, REQ-3; proposed |

## Open questions
| Id | Question | Why it matters | Proposed default |
|---|---|---|---|
| Q2-1 | What are the SKU format limits (length, characters, case), and is SKU compared case-sensitively? | Defines validation and the unique key (brief Unknowns). | Non-empty, trimmed, at most 64 characters, `[A-Z0-9-_.]`, stored upper case, unique. |
| Q2-2 | Which units of measure are allowed? | Unit is an enumerated set or free text (brief Unknowns). | A configured enumerated list (for example `EA`, `BOX`, `KG`); unknown unit fails. |
| Q2-3 | Is product `code` different from SKU, and must it be unique? | REQ-1 names both; a second unique key changes errors and tables. | `code` is a separate business code, required, unique across products. |
| Q2-4 | What data does a warehouse have (code, name, address)? | REQ-2 only says "register a warehouse". | `code` (unique) and `name`, both required; no address. |
| Q2-5 | What data does a bin have, and is its code unique per warehouse or globally? | REQ-3 gives no fields. | `code` required, unique within its warehouse. |
| Q2-6 | Do staff or other contexts need to read or list products, warehouses or bins from Catalog? | Would add queries and gRPC operations not in 01 Published language. | Not now; add `GetProduct` / `ListProducts` queries only if a REQ appears. |
| Q2-7 | Who may register products, warehouses and bins? (01 Q1-6) | Authorisation in the identity subdomain. | Warehouse staff only, as in the brief Actors. |
| Q2-8 | Is a register call with the same key and same data a success (idempotent replay) or ALREADY_EXISTS? | Affects retry behaviour at the API (API-03). | Same key with identical data returns the existing id; different data fails with ALREADY_EXISTS. |

## Aggregates
| Aggregate | Root entity | Contains (entities, value objects) | References by id | Invariants (REQ) | Created by |
|---|---|---|---|---|---|
| Product | Product | Sku, ProductCode, ProductName, UnitOfMeasure | none | SKU is present and valid (REQ-1, Q2-1); code, name and unit are present (REQ-1); unit is an allowed unit (Q2-2, proposed); SKU unique across products, set validation with store unique key (REQ-1, D2-3); immutable once registered (D2-7, proposed). | actor:WarehouseStaff |
| Warehouse | Warehouse | WarehouseCode, WarehouseName | none | Code and name present (REQ-2, Q2-4 proposed); code unique across warehouses, set validation with store unique key (D2-3, proposed). | actor:WarehouseStaff |
| Bin | Bin | BinCode | Warehouse | A bin belongs to exactly one warehouse, fixed at registration (REQ-3); the warehouse exists at registration, checked by reading Warehouse in the same context (D2-2); bin code unique within its warehouse, set validation with store unique key (REQ-3, Q2-5 proposed). | actor:WarehouseStaff |

## Entities and value objects
| Name | Kind (entity / value object) | Belongs to | Fields | Rules |
|---|---|---|---|---|
| Product | entity | Product | product_id (ULID), sku (Sku), code (ProductCode), name (ProductName), unit_of_measure (UnitOfMeasure), registered_at (UTC time) | Aggregate root; id generated in the domain layer (R2). |
| Sku | value object | Product | value (string) | Non-empty; format per Q2-1 (proposed); immutable. |
| ProductCode | value object | Product | value (string) | Non-empty; uniqueness per Q2-3 (proposed). |
| ProductName | value object | Product | value (string) | Non-empty, trimmed; maximum length proposed 200 characters. |
| UnitOfMeasure | value object | Product | value (string from allowed list) | Must be in the allowed list (Q2-2, proposed). |
| Warehouse | entity | Warehouse | warehouse_id (ULID), code (WarehouseCode), name (WarehouseName), registered_at (UTC time) | Aggregate root; id generated in the domain layer (R2). |
| WarehouseCode | value object | Warehouse | value (string) | Non-empty; unique across warehouses (Q2-4, proposed). |
| WarehouseName | value object | Warehouse | value (string) | Non-empty, trimmed (Q2-4, proposed). |
| Bin | entity | Bin | bin_id (ULID), warehouse_id (ULID ref), code (BinCode), registered_at (UTC time) | Aggregate root; warehouse_id fixed at creation (REQ-3). |
| BinCode | value object | Bin | value (string) | Non-empty; unique within warehouse (Q2-5, proposed). |

## Commands
| Command | Aggregate | Trigger | Emits | Fails when | REQ |
|---|---|---|---|---|---|
| RegisterProduct | Product | actor:WarehouseStaff | ProductRegistered | INVALID_SKU (format, Q2-1); MISSING_PRODUCT_FIELD (code, name or unit empty); UNKNOWN_UNIT_OF_MEASURE (Q2-2); SKU_ALREADY_EXISTS; PRODUCT_CODE_ALREADY_EXISTS (if Q2-3 default holds) | REQ-1 |
| RegisterWarehouse | Warehouse | actor:WarehouseStaff | WarehouseRegistered | MISSING_WAREHOUSE_FIELD (code or name empty); WAREHOUSE_CODE_ALREADY_EXISTS | REQ-2 |
| RegisterBin | Bin | actor:WarehouseStaff | BinRegistered | WAREHOUSE_NOT_FOUND; MISSING_BIN_FIELD (code empty); BIN_CODE_ALREADY_EXISTS (in that warehouse) | REQ-3 |

## Domain events
| Event | Emitted by | Kind | Payload | Consumers |
|---|---|---|---|---|
| ProductRegistered | RegisterProduct | integration | event_id (ULID), occurred_at (UTC), product_id, sku, code, name, unit_of_measure | Stock, Purchasing |
| WarehouseRegistered | RegisterWarehouse | integration | event_id (ULID), occurred_at (UTC), warehouse_id, code, name | Stock, Purchasing |
| BinRegistered | RegisterBin | integration | event_id (ULID), occurred_at (UTC), bin_id, warehouse_id, code | Stock |

## Policies
| Policy | When (event) | Then (command) | Context | On failure |
|---|---|---|---|---|
| none | - | - | - | Catalog consumes no event (D2-6). |

## Queries and read models
| Query / read model | Kind (query / read model / cache) | Source | Rebuild or invalidation | Staleness | REQ |
|---|---|---|---|---|---|
| none | - | - | - | - | No Catalog REQ asks for a read (D2-8, Q2-6). |

## Out of scope
| REQ | Why |
|---|---|
| none | REQ-1, REQ-2 and REQ-3 are each covered by a command. Editing or retiring products, warehouses and bins is out of scope per 01 Q1-10. |
