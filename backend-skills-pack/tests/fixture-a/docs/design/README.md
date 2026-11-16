# Backend design

## Summary

The design covers Shelfmark, a library lending system for one small library, split into four bounded contexts: Catalog, Lending, Fines and Membership. It runs as a modular monolith with PostgreSQL, one schema per context, and in-process events with an outbox. Review loop 2 passed with 0 High, 5 Medium and 7 Low findings, and 11 of 12 loop-2 findings were fixed. Seventeen open questions remain for the business: Q-1 to Q-12 in the brief and RQ-1 to RQ-5.

## Reading order

| # | File | Title | What it gives you |
|---|---|---|---|
| 1 | [project-profile.md](project-profile.md) | Project profile: Shelfmark | Stack, architecture style and rule overrides that every phase follows. |
| 2 | [00-state.md](00-state.md) | Design state | Phase status, review loop totals and the open questions list. |
| 3 | [00-project-brief.md](brief/00-project-brief.md) | 00 Project brief: Shelfmark | Goals, actors, requirements REQ-1 to REQ-30 and the open questions Q-1 to Q-12. |
| 4 | [01-strategic.md](strategic/01-strategic.md) | 01 Strategic design | Four bounded contexts, the context map and the published language. |
| 5 | [02-tactical-catalog.md](tactical/02-tactical-catalog.md) | 02 Tactical design: Catalog | Catalog aggregates, commands, events and read models. |
| 6 | [02-tactical-fines.md](tactical/02-tactical-fines.md) | 02 Tactical design: Fines | Fines account, fine charging and payments, with their events and policies. |
| 7 | [02-tactical-lending.md](tactical/02-tactical-lending.md) | 02 Tactical design: Lending | Lending aggregates, borrow and hold rules, and fine status ordering. |
| 8 | [02-tactical-membership.md](tactical/02-tactical-membership.md) | 02 Tactical design: Membership | Member registration, its single integration event and the name limit question. |
| 9 | [03-db-design-fines.md](data/03-db-design-fines.md) | 03 Database design: Fines | Fines schema tables, constraints and idempotency storage. |
| 10 | [03-db-design-lending.md](data/03-db-design-lending.md) | 03 Database design: Lending | Lending schema tables, slot and hold constraints, and borrower fine fields. |
| 11 | [03-db-design.md](data/03-db-design.md) | 03 Database design | Shared database decisions, plus the Catalog and Membership tables. |
| 12 | [04-erd.md](data/04-erd.md) | 04 ERD | Entity relationship diagrams per module and the cross-module REF overview. |
| 13 | [05-diagrams-flows.md](diagrams/05-diagrams-flows.md) | 05 Diagrams: key flows | Sequence diagrams for the six key flows, from registration to fine payment. |
| 14 | [05-diagrams.md](diagrams/05-diagrams.md) | 05 Diagrams | Use case, database module and context map diagrams. |
| 15 | [06-api.md](api/06-api.md) | 06 API design | REST operations, error mapping, conventions and API decisions. |
| 16 | [06-api.openapi-catalog.yaml](api/06-api.openapi-catalog.yaml) | OpenAPI fragment: Catalog | Catalog part of the OpenAPI contract. |
| 17 | [06-api.openapi-common.yaml](api/06-api.openapi-common.yaml) | OpenAPI fragment: common | Shared schemas and error types used by the contexts. |
| 18 | [06-api.openapi-fines.yaml](api/06-api.openapi-fines.yaml) | OpenAPI fragment: Fines | Fines part of the OpenAPI contract. |
| 19 | [06-api.openapi-lending.yaml](api/06-api.openapi-lending.yaml) | OpenAPI fragment: Lending | Lending part of the OpenAPI contract. |
| 20 | [06-api.openapi-membership.yaml](api/06-api.openapi-membership.yaml) | OpenAPI fragment: Membership | Membership part of the OpenAPI contract. |
| 21 | [06-api.openapi.yaml](api/06-api.openapi.yaml) | OpenAPI root: Shelfmark API | Root of the Shelfmark OpenAPI contract that references the fragments. |
| 22 | [07-fixes-loop1.md](review/07-fixes-loop1.md) | 07 Fixes (loop 1) | How each of the 13 loop-1 findings was fixed. |
| 23 | [07-lint.md](review/07-lint.md) | 07 Lint | Lint results and the findings that were rejected. |
| 24 | [07-review-loop1.md](review/07-review-loop1.md) | 07 Design review (loop 1) | First review: verdict fail with 3 High findings. |
| 25 | [07-review.md](review/07-review.md) | 07 Design review (loop 2) | Second review: verdict pass with 0 High, plus the requirement trace. |
