# Backend design

## Summary

The design covers the Stockroom backend for a few warehouses: stock on hand, reservations, adjustments, picking, a product catalog and reorder suggestions. It is split into three bounded contexts (Catalog, Stock, Purchasing), each a microservice that shares one database schema and writes only its own prefixed tables. The phase 7 review passed its second loop with no High findings, leaving 3 Medium and 11 Low findings carried forward. Eight business questions are still open, plus three review questions (OQ-1 to OQ-3); the design is in phase 8 (arrange).

## Reading order

| # | File | Title | What it gives you |
|---|---|---|---|
| 1 | [project-profile.md](project-profile.md) | Project profile: Stockroom | Architecture style, detected stack, rule overrides and profile questions. |
| 2 | [00-state.md](00-state.md) | Design state | Phase-by-phase status, gate results, review loops and carried-forward findings. |
| 3 | [00-project-brief.md](brief/00-project-brief.md) | 00 Project brief: Stockroom | Goals, actors, requirements and the business questions to answer. |
| 4 | [01-strategic.md](strategic/01-strategic.md) | 01 Strategic design | Three bounded contexts, their integration and the ubiquitous language. |
| 5 | [02-tactical-catalog.md](tactical/02-tactical-catalog.md) | 02 Tactical design: Catalog | Catalog aggregates, commands, events and policies. |
| 6 | [02-tactical-purchasing.md](tactical/02-tactical-purchasing.md) | 02 Tactical design: Purchasing | Purchasing aggregates, commands, events and reorder-suggestion policies. |
| 7 | [02-tactical-stock.md](tactical/02-tactical-stock.md) | 02 Tactical design: Stock | Stock aggregates, commands, events and reservation policies. |
| 8 | [03-db-design-catalog.md](data/03-db-design-catalog.md) | 03 Database design: Catalog (module `cat`) | Catalog tables, enforced rules and caches. |
| 9 | [03-db-design-purchasing.md](data/03-db-design-purchasing.md) | 03 Database design: Purchasing (module `pur`) | Purchasing tables, enforced rules and caches. |
| 10 | [03-db-design-stock.md](data/03-db-design-stock.md) | 03 Database design: Stock (module `stk`) | Stock tables, enforced rules and caches. |
| 11 | [03-db-design.md](data/03-db-design.md) | 03 Database design | Shared database design: modules, the single schema and table rules. |
| 12 | [04-erd.md](data/04-erd.md) | 04 ERD | Entity-relationship diagrams for the whole system and each module. |
| 13 | [05-diagrams-flows.md](diagrams/05-diagrams-flows.md) | 05 Diagrams: key flows | Sequence diagrams of the key business flows. |
| 14 | [05-diagrams-use-cases.md](diagrams/05-diagrams-use-cases.md) | 05 Diagrams: use cases | Use-case diagrams for each actor. |
| 15 | [05-diagrams.md](diagrams/05-diagrams.md) | 05 Diagrams | Index of the diagram set: use cases, database modules, flows and context map. |
| 16 | [06-api.md](api/06-api.md) | 06 API design | gRPC conventions, operations, error reasons and what is not exposed. |
| 17 | [06-api.proto](api/06-api.proto) | proto contract | The protobuf contract for the three services, wire-compatible with the stub. |
| 18 | [07-fixes-loop1.md](review/07-fixes-loop1.md) | 07 Fixes, loop 1 | Fixes applied after the first review loop. |
| 19 | [07-lint.md](review/07-lint.md) | 07 Lint | Lint findings on the design files. |
| 20 | [07-review-loop1.md](review/07-review-loop1.md) | 07 Design review (loop 1) | First review: findings, requirement trace and checks not done. |
| 21 | [07-review.md](review/07-review.md) | 07 Design review (loop 2) | Second review: verdict pass with no High, carried findings and open questions. |
