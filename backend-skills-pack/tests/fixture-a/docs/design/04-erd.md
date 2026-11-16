# 04 ERD

## Inputs
- docs/design/project-profile.md: diagram_format = mermaid.
- docs/design/03-db-design.md (Catalog, Membership, Modules table), 03-db-design-lending.md, 03-db-design-fines.md: tables, keys, FKs, REFs.

## Decisions
- D4-1 One `erDiagram` per module (4) plus one overview `flowchart` (1). Every table in the 03 Modules table appears by its exact physical name (24 tables: catalog 5, lending 10, fines 6, membership 3).
- D4-2 Table names contain a dot, so they are written as quoted entity names, for example `"catalog.book"`. This needs a Mermaid version that accepts quoted entity names (10.x or later).
- D4-3 Each table lists only its key columns (PK, FK, REF, and UK where 03 declares a plain unique key on that column). The 300-line limit (DOC-01) rules out listing every column. Types, nulls, defaults and checks stay in 03. The exceptions are the columns that 03 added in the fixes F2 and F6 (`lending.outbox.target_consumer`, `lending.loan_slot.state`, `refused_at`, `reason`), which are drawn so the fix is visible.
- D4-4 Mermaid has no REF key marker. A REF column is drawn with the comment `REF <Context>.<Aggregate>` and no relationship line inside the module diagrams. Cross-module REFs are drawn only in the overview, as dotted lines labelled `ref`.
- D4-5 Relationship lines come only from the FK lines in 03. Every FK is ON DELETE RESTRICT except `catalog.book_availability.book_id` (CASCADE), as in 03.
- D4-6 Each `idempotency_record` table is drawn with its composite PK (`caller`, `operation`, `key`) and no relationship line, because 03 lists no FK or REF on it (D3-17).
- Fixed F2, F3, F6: F2 adds `lending.outbox.target_consumer` (03-db-design-lending.md D3-L5); F3 adds `catalog.idempotency_record`, `lending.idempotency_record`, `fines.idempotency_record` and `membership.idempotency_record` (03 D3-17); F6 adds `state`, `refused_at` and `reason` to `lending.loan_slot` (03-db-design-lending.md D3-L3).

## Open questions
| Id | Question | Why it matters | Proposed default |
|---|---|---|---|
| EQ-1 | Mermaid `erDiagram` cannot show partial unique indexes, CHECKs or ON DELETE actions. Are notes enough? | Diagram detail is lower than 03. | Keep 03 as the source for these; this file shows keys and relationships only. |
| EQ-2 | 03 lists no FK on `catalog.outbox`, `catalog.inbox`, the four `idempotency_record` tables, `lending.outbox`, `lending.inbox`, `fines.outbox`, `fines.inbox` and `membership.outbox`, and no REF for `aggregate_id`. Is that final? | These tables are drawn without relationship lines. | Yes, as in 03. |

## Overview: modules and cross-module REFs
Drawn from the 03 Modules table and the REF lines in 03.

```mermaid
flowchart LR
  subgraph Catalog["module Catalog (schema catalog)"]
    c_book["catalog.book"]
    c_ba["catalog.book_availability"]
    c_out["catalog.outbox"]
    c_in["catalog.inbox"]
    c_idem["catalog.idempotency_record"]
  end
  subgraph Lending["module Lending (schema lending)"]
    l_circ["lending.book_circulation"]
    l_copy["lending.book_copy"]
    l_loan["lending.loan"]
    l_hold["lending.hold"]
    l_bor["lending.borrower"]
    l_slot["lending.loan_slot"]
    l_hrn["lending.hold_ready_notification"]
    l_out["lending.outbox"]
    l_in["lending.inbox"]
    l_idem["lending.idempotency_record"]
  end
  subgraph Fines["module Fines (schema fines)"]
    f_acc["fines.account"]
    f_fine["fines.fine"]
    f_pay["fines.payment"]
    f_out["fines.outbox"]
    f_in["fines.inbox"]
    f_idem["fines.idempotency_record"]
  end
  subgraph Membership["module Membership (schema membership)"]
    m_mem["membership.member"]
    m_out["membership.outbox"]
    m_idem["membership.idempotency_record"]
  end
  l_circ -. ref .-> c_book
  l_bor -. ref .-> m_mem
  f_acc -. ref .-> m_mem
  f_fine -. ref .-> l_loan
```

Legend: dotted `ref` lines are plain id columns with no foreign key (03: REF lines).

## Catalog
Drawn from 03-db-design.md, tables in module Catalog.

```mermaid
erDiagram
  "catalog.book" {
    uuid book_id PK
    char13 isbn UK "uq_book_isbn"
  }
  "catalog.book_availability" {
    uuid book_id PK, FK
  }
  "catalog.outbox" {
    uuid message_id PK
  }
  "catalog.inbox" {
    text consumer PK
    uuid message_id PK
  }
  "catalog.idempotency_record" {
    text caller PK
    text operation PK
    uuid key PK
  }
  "catalog.book" ||--o| "catalog.book_availability" : "book_id (CASCADE)"
```

## Lending
Drawn from 03-db-design-lending.md.

```mermaid
erDiagram
  "lending.book_circulation" {
    uuid book_id PK "REF Catalog.Book"
  }
  "lending.book_copy" {
    uuid copy_id PK
    uuid book_id FK
    text barcode UK "uq_copy_barcode"
  }
  "lending.loan" {
    uuid loan_id PK
    uuid book_id FK
    uuid copy_id FK
    uuid member_id FK
    uuid from_hold_id FK
  }
  "lending.hold" {
    uuid hold_id PK
    uuid book_id FK
    uuid member_id FK
    uuid copy_id FK
  }
  "lending.borrower" {
    uuid member_id PK "REF Membership.Member"
  }
  "lending.loan_slot" {
    uuid loan_id PK
    uuid member_id FK
    uuid book_id FK
    text state "reserved or refused (F6)"
    timestamptz refused_at "null = not refused (F6)"
    text reason "null = not refused (F6)"
  }
  "lending.hold_ready_notification" {
    uuid notification_id PK
    uuid hold_id FK
  }
  "lending.outbox" {
    uuid message_id PK
    text target_consumer "null = all handlers (F2)"
  }
  "lending.inbox" {
    text consumer PK
    uuid message_id PK
  }
  "lending.idempotency_record" {
    text caller PK
    text operation PK
    uuid key PK
  }
  "lending.book_circulation" ||--o{ "lending.book_copy" : "book_id"
  "lending.book_circulation" ||--o{ "lending.loan" : "book_id"
  "lending.book_copy" ||--o{ "lending.loan" : "copy_id"
  "lending.borrower" ||--o{ "lending.loan" : "member_id"
  "lending.hold" |o--o{ "lending.loan" : "from_hold_id"
  "lending.book_circulation" ||--o{ "lending.hold" : "book_id"
  "lending.borrower" ||--o{ "lending.hold" : "member_id"
  "lending.book_copy" |o--o{ "lending.hold" : "copy_id"
  "lending.borrower" ||--o{ "lending.loan_slot" : "member_id"
  "lending.book_circulation" ||--o{ "lending.loan_slot" : "book_id"
  "lending.hold" ||--o{ "lending.hold_ready_notification" : "hold_id"
```

## Fines
Drawn from 03-db-design-fines.md.

```mermaid
erDiagram
  "fines.account" {
    uuid account_id PK
    uuid member_id UK "REF Membership.Member; uq_account_member"
    text card_number UK "uq_account_card"
  }
  "fines.fine" {
    uuid fine_id PK
    uuid account_id FK
    uuid loan_id UK "REF lending.loan (F12); uq_fine_loan"
  }
  "fines.payment" {
    uuid payment_id PK
    uuid account_id FK
  }
  "fines.outbox" {
    uuid message_id PK
  }
  "fines.inbox" {
    text consumer PK
    uuid message_id PK
  }
  "fines.idempotency_record" {
    text caller PK
    text operation PK
    uuid key PK
  }
  "fines.account" ||--o{ "fines.fine" : "account_id"
  "fines.account" ||--o{ "fines.payment" : "account_id"
```

## Membership
Drawn from 03-db-design.md, tables in module Membership.

```mermaid
erDiagram
  "membership.member" {
    uuid member_id PK
    text card_number UK "uq_member_card"
  }
  "membership.outbox" {
    uuid message_id PK
  }
  "membership.idempotency_record" {
    text caller PK
    text operation PK
    uuid key PK
  }
```

Note: `uq_member_email` is on `lower(email)`, an expression, so it is not drawn as a column key (see 03).
