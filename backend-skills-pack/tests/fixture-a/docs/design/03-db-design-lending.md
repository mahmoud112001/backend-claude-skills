# 03 Database design: Lending

## Inputs
- docs/design/03-db-design.md: Decisions D3-1 to D3-20 and Open questions DQ-1, DQ-2, DQ-4 to DQ-8 apply here.
- docs/design/02-tactical-lending.md: Aggregates, Entities and value objects, Commands, Domain events, Policies, Queries and read models; D2-11, D2-15, LoanSlot, GetBorrowRequest.
- docs/design/06-api.md: D6-8, D6-9 (Lending operations with an Idempotency-Key). docs/design/07-review-loop1.md: F2, F3, F6, F8.
- docs/design/project-profile.md: PostgreSQL, UUIDv7, snake_case, transactional outbox per module.

## Decisions
- D3-L1 Copies, loans and holds are child tables of `lending.book_circulation`; ended loans and closed holds stay as history rows (Lending D2-9).
- D3-L2 The physical table for Copy is `lending.book_copy` (*proposed*): it avoids the SQL keyword COPY.
- D3-L3 `lending.loan_slot` has a lifecycle state (02 D2-15). CancelLoanSlot sets `state = 'refused'` with `refused_at` and `reason` and keeps the row, so GetBorrowRequest can report the refusal. ReleaseLoanSlot still hard deletes a `reserved` slot after LoanEnded: the loan row keeps that history (DB-11). Refused rows are excluded from the 3-loan count and from `uq_slot_member_book`, and are hard deleted by a purge job after the LQ-12 retention (proposed 30 days).
- D3-L4 `lending.hold_ready_notification` has an FK only to `lending.hold`. Its member_id and book_id are copies taken from the hold when the row is created.
- D3-L5 `lending.outbox.target_consumer` (F2): null = deliver to all handlers; a value = deliver only to that policy. CopyPlacedOnHoldShelf is always written as two targeted rows, so NotifyHolderOnHoldShelf never sees the delayed row and the email is sent once per placement (HoldReadyNotification invariant a).
- D3-L6 BookAvailability rebuild (F8). Maintenance job RepublishBookAvailability (*proposed* name; technical, not a 02 command, changes no aggregate state): for each `lending.book_circulation` row, in pages ordered by `book_id`, one transaction reads the row, its `book_copy` rows and active `loan` rows, and writes one BookAvailabilityChanged outbox row with a new message_id and `version` = the row's current `version`. Catalog applies it through its normal upsert; a book whose Catalog row already holds that version is skipped by the `source_version` guard (D3-9). Run by an operator after `catalog.book_availability` is truncated (always truncate first, as 03-db-design.md:90 says).
- D3-L7 `lending.idempotency_record` serves borrowBook, placeHold, addCopy, checkInCopy and the optional key of renewLoan, cancelHold, withdrawCopy (F3, D3-17 to D3-20). A replayed borrowBook returns the stored 202; the outcome is then read through GetBorrowRequest.
- Fixed F1 (loop 2): the `lending.hold.pickup_deadline` note cites RQ-4 and its proposed default instead of stating "shelved time + 3 days"; the rule stays open in RQ-4.
- Fixed F5 (loop 2): D3-L6 requires truncating `catalog.book_availability` before RepublishBookAvailability, because an equal `source_version` is skipped.

## Open questions
| Id | Question | Why it matters | Proposed default |
|---|---|---|---|
| none | All open questions are in 03-db-design.md (DQ-1, DQ-2, DQ-5, DQ-7) and 02-tactical-lending.md (LQ-6, LQ-9, LQ-12) | | |

## Tables

### Table: lending.book_circulation (module: Lending)
Aggregate: BookCirculation (root)
| Column | Type | Null | Default | Constraint | Notes (invariant / REQ) |
|---|---|---|---|---|---|
| book_id | uuid | no | none | PK | = Catalog book id (Lending D2-3) |
| title | text | no | none | CHECK char_length(title) >= 1 | BibliographicSummary from BookAdded |
| author | text | no | none | CHECK char_length(author) >= 1 | BibliographicSummary |
| next_hold_sequence | bigint | no | 1 | CHECK next_hold_sequence >= 1 | D3-13 |
| opened_at | timestamptz | no | none | | |
| version | bigint | no | 1 | | concurrency; also BookAvailabilityChanged.version (D3-9) |
- PK book_id
- REF book_id -> Catalog.Book (id only, no FK)

### Table: lending.book_copy (module: Lending)
Aggregate: BookCirculation (child of BookCirculation)
| Column | Type | Null | Default | Constraint | Notes (invariant / REQ) |
|---|---|---|---|---|---|
| copy_id | uuid | no | none | PK | |
| book_id | uuid | no | none | FK | |
| barcode | text | no | none | uq_copy_barcode, ck_copy_barcode | Barcode (Lending D2-7, LQ-9, DQ-7) |
| state | text | no | 'available' | ck_copy_state | invariant (a) |
| added_at | timestamptz | no | none | | REQ-25 |
| withdrawn_at | timestamptz | yes | null | ck_copy_withdrawn | null = not withdrawn (REQ-26) |
- PK copy_id
- FK book_id -> lending.book_circulation(book_id) ON DELETE RESTRICT
- UNIQUE uq_copy_barcode (barcode) — BarcodeTaken; serves FindCopyByBarcode
- CHECK ck_copy_barcode: barcode = btrim(barcode) AND char_length(barcode) BETWEEN 1 AND 64
- CHECK ck_copy_state: state IN ('available','on_loan','on_hold_shelf','withdrawn')
- CHECK ck_copy_withdrawn: (state = 'withdrawn') = (withdrawn_at IS NOT NULL)
- IDX ix_copy_book (book_id, state) — FK; aggregate load and availability counts

### Table: lending.loan (module: Lending)
Aggregate: BookCirculation (child of BookCirculation)
| Column | Type | Null | Default | Constraint | Notes (invariant / REQ) |
|---|---|---|---|---|---|
| loan_id | uuid | no | none | PK | = loan slot id (Lending D2-5); makes LendCopy idempotent |
| book_id | uuid | no | none | FK | |
| copy_id | uuid | no | none | FK | |
| member_id | uuid | no | none | FK | |
| from_hold_id | uuid | yes | null | FK | null = not picked up from the shelf |
| borrowed_at | timestamptz | no | none | | REQ-5 |
| due_date | date | no | none | | borrowed day + 14 (REQ-10); + 14 on renewal (REQ-12, LQ-3) |
| renewed | boolean | no | false | | at most one renewal (REQ-12, invariant d) |
| returned_at | timestamptz | yes | null | ck_loan_returned | null = active loan (REQ-20) |
- PK loan_id
- FK book_id -> lending.book_circulation(book_id) ON DELETE RESTRICT
- FK copy_id -> lending.book_copy(copy_id) ON DELETE RESTRICT
- FK member_id -> lending.borrower(member_id) ON DELETE RESTRICT
- FK from_hold_id -> lending.hold(hold_id) ON DELETE RESTRICT
- UNIQUE uq_loan_active_copy (copy_id) WHERE returned_at IS NULL — invariant (b)
- UNIQUE uq_loan_active_member_book (member_id, book_id) WHERE returned_at IS NULL — LoanForBookExists (LQ-6)
- CHECK ck_loan_returned: returned_at IS NULL OR returned_at >= borrowed_at
- IDX ix_loan_book (book_id, returned_at) — FK; aggregate load, earliest due date
- IDX ix_loan_copy (copy_id) — FK; CheckInCopy
- IDX ix_loan_member (member_id, returned_at, due_date) — FK; serves ListMyLoans
- IDX ix_loan_overdue (due_date) WHERE returned_at IS NULL — serves ListOverdueLoans
- IDX ix_loan_from_hold (from_hold_id) — FK

### Table: lending.hold (module: Lending)
Aggregate: BookCirculation (child of BookCirculation)
| Column | Type | Null | Default | Constraint | Notes (invariant / REQ) |
|---|---|---|---|---|---|
| hold_id | uuid | no | none | PK | |
| book_id | uuid | no | none | FK | |
| member_id | uuid | no | none | FK | |
| sequence | bigint | no | none | uq_hold_sequence | queue order (REQ-7) |
| state | text | no | 'waiting' | ck_hold_state | |
| placed_at | timestamptz | no | none | | REQ-6 |
| copy_id | uuid | yes | null | FK, ck_hold_shelf | set when shelved; null = never shelved |
| pickup_deadline | timestamptz | yes | null | ck_hold_shelf | per RQ-4 (proposed: end of the third calendar day in the library time zone) (REQ-17); null = never shelved |
| closed_at | timestamptz | yes | null | ck_hold_closed | null = open (waiting or on_shelf) |
- PK hold_id
- FK book_id -> lending.book_circulation(book_id) ON DELETE RESTRICT
- FK member_id -> lending.borrower(member_id) ON DELETE RESTRICT
- FK copy_id -> lending.book_copy(copy_id) ON DELETE RESTRICT
- UNIQUE uq_hold_sequence (book_id, sequence) — REQ-7
- UNIQUE uq_hold_open_member_book (member_id, book_id) WHERE state IN ('waiting','on_shelf') — HoldAlreadyPlaced (invariant l, LQ-6)
- UNIQUE uq_hold_shelf_copy (copy_id) WHERE state = 'on_shelf' — one shelf hold per copy
- CHECK ck_hold_state: state IN ('waiting','on_shelf','fulfilled','cancelled','expired')
- CHECK ck_hold_shelf: (state <> 'on_shelf' OR (copy_id IS NOT NULL AND pickup_deadline IS NOT NULL)) AND (state <> 'waiting' OR (copy_id IS NULL AND pickup_deadline IS NULL))
- CHECK ck_hold_closed: (state IN ('waiting','on_shelf')) = (closed_at IS NULL)
- IDX ix_hold_book_queue (book_id, state, sequence) — FK; aggregate load, queue position (ListMyHolds)
- IDX ix_hold_member (member_id, state) — FK; serves ListMyHolds
- IDX ix_hold_copy (copy_id) — FK

### Table: lending.borrower (module: Lending)
Aggregate: Borrower (root)
| Column | Type | Null | Default | Constraint | Notes (invariant / REQ) |
|---|---|---|---|---|---|
| member_id | uuid | no | none | PK | = Membership member id; RegisterBorrower idempotent |
| name | text | no | none | CHECK char_length(name) >= 1 | ContactDetails (REQ-22) |
| email | text | no | none | CHECK char_length(email) >= 3 | ContactDetails (REQ-16) |
| owes_fines | boolean | no | false | | FineStatus (REQ-9, Q-6) |
| fine_status_as_of | timestamptz | yes | null | | null = no FineBalanceChanged applied yet |
| fine_status_account_version | bigint | yes | null | | ordering key (02 D2-11); null = none applied yet |
| registered_at | timestamptz | no | none | | |
| version | bigint | no | 1 | | concurrency; serialises slot reservation |
- PK member_id
- REF member_id -> Membership.Member (id only, no FK)

### Table: lending.loan_slot (module: Lending)
Aggregate: Borrower (child of Borrower)
| Column | Type | Null | Default | Constraint | Notes (invariant / REQ) |
|---|---|---|---|---|---|
| loan_id | uuid | no | none | PK | slot id = loan id (Lending D2-5) |
| member_id | uuid | no | none | FK | |
| book_id | uuid | no | none | FK | |
| reserved_at | timestamptz | no | none | | |
| state | text | no | 'reserved' | ck_slot_state | reserved = counts toward the limit; refused = history only (02 D2-15) |
| refused_at | timestamptz | yes | null | ck_slot_refused | null = not refused |
| reason | text | yes | null | ck_slot_refused, ck_slot_reason | LoanRefused reason; null = not refused |
- PK loan_id — also serves GetBorrowRequest (by loanId, owner checked on member_id)
- FK member_id -> lending.borrower(member_id) ON DELETE RESTRICT
- FK book_id -> lending.book_circulation(book_id) ON DELETE RESTRICT — BookUnknown
- UNIQUE uq_slot_member_book (member_id, book_id) WHERE state = 'reserved' — invariant (c), LQ-6; refused slots excluded (D2-15)
- CHECK ck_slot_state: state IN ('reserved','refused')
- CHECK ck_slot_refused: (state = 'refused') = (refused_at IS NOT NULL) AND (state = 'refused') = (reason IS NOT NULL) AND (refused_at IS NULL OR refused_at >= reserved_at)
- CHECK ck_slot_reason: reason IS NULL OR reason IN ('no_copy_available')
- IDX ix_slot_member (member_id, state) — FK; Borrower load and the 3-reserved-slot count
- IDX ix_slot_book (book_id) — FK
- IDX ix_slot_refused_purge (refused_at) WHERE state = 'refused' — serves the LQ-12 purge job

### Table: lending.hold_ready_notification (module: Lending)
Aggregate: HoldReadyNotification (root)
| Column | Type | Null | Default | Constraint | Notes (invariant / REQ) |
|---|---|---|---|---|---|
| notification_id | uuid | no | none | PK | = message_id of the CopyPlacedOnHoldShelf row targeted at NotifyHolderOnHoldShelf (D3-L5): one email per placement (REQ-16) |
| hold_id | uuid | no | none | FK | |
| member_id | uuid | no | none | | copy of the hold's member (D3-L4) |
| book_id | uuid | no | none | | copy of the hold's book (D3-L4) |
| title | text | no | none | | |
| recipient_name | text | no | none | | ContactDetails |
| recipient_email | text | no | none | | ContactDetails |
| pickup_deadline | timestamptz | no | none | | REQ-17 |
| status | text | no | 'pending' | ck_hrn_status | |
| attempts | integer | no | 0 | CHECK attempts >= 0 | |
| sent_at | timestamptz | yes | null | ck_hrn_sent | null = not sent yet |
| version | bigint | no | 1 | | concurrency |
- PK notification_id
- FK hold_id -> lending.hold(hold_id) ON DELETE RESTRICT
- CHECK ck_hrn_status: status IN ('pending','sent')
- CHECK ck_hrn_sent: (status = 'sent') = (sent_at IS NOT NULL)
- IDX ix_hrn_hold (hold_id) — FK

### Table: lending.outbox (module: Lending)
Aggregate: outbox
| Column | Type | Null | Default | Constraint | Notes (invariant / REQ) |
|---|---|---|---|---|---|
| message_id | uuid | no | none | PK | = eventId |
| event_type | text | no | none | ck_lending_outbox_type | |
| aggregate_id | uuid | no | none | | book_id or member_id |
| payload | jsonb | no | none | | 02 Lending payloads |
| occurred_at | timestamptz | no | none | | |
| deliver_not_before | timestamptz | no | now() | | pickupDeadline for the expiry delivery (D3-11) |
| target_consumer | text | yes | null | ck_lending_outbox_target | null = deliver to all handlers; else only this policy (D3-L5, F2) |
| attempts | integer | no | 0 | CHECK attempts >= 0 | |
| published_at | timestamptz | yes | null | | null = not yet delivered to all (or the targeted) handlers |
- PK message_id
- CHECK ck_lending_outbox_type: event_type IN ('LoanSlotReserved','LoanRefused','LoanEnded','CopyPlacedOnHoldShelf','BookAvailabilityChanged')
- CHECK ck_lending_outbox_target: (target_consumer IS NULL OR target_consumer IN ('NotifyHolderOnHoldShelf','ExpireHoldOnShelfDeadline')) AND ((event_type = 'CopyPlacedOnHoldShelf') = (target_consumer IS NOT NULL))
- IDX ix_lending_outbox_pending (deliver_not_before) WHERE published_at IS NULL — serves the outbox worker
- CopyPlacedOnHoldShelf is written as two rows, each with its own message_id: one due now with `target_consumer = 'NotifyHolderOnHoldShelf'`, and one with deliver_not_before = pickupDeadline and `target_consumer = 'ExpireHoldOnShelfDeadline'`. The worker delivers each only to its target.
- BookAvailabilityChanged rows are also written by the rebuild job RepublishBookAvailability (D3-L6), one per `lending.book_circulation` row with its current `version`.

### Table: lending.inbox (module: Lending)
Aggregate: inbox
| Column | Type | Null | Default | Constraint | Notes (invariant / REQ) |
|---|---|---|---|---|---|
| consumer | text | no | none | PK | policy name, e.g. OpenCirculationOnBookAdded |
| message_id | uuid | no | none | PK | |
| processed_at | timestamptz | no | none | | |
- PK consumer, message_id

### Table: lending.idempotency_record (module: Lending)
Aggregate: inbox (idempotency record for API commands, D3-17; not an aggregate)
| Column | Type | Null | Default | Constraint | Notes (invariant / REQ) |
|---|---|---|---|---|---|
| caller | text | no | none | PK, ck_lending_idem_caller | identity provider subject of the caller (DQ-6) |
| operation | text | no | none | PK, ck_lending_idem_operation | 06 operationId (D3-19) |
| key | uuid | no | none | PK | Idempotency-Key header (06 D6-8, D6-9) |
| request_hash | bytea | no | none | ck_lending_idem_hash | SHA-256 of the canonical request (D3-19) |
| status | smallint | no | none | ck_lending_idem_status | HTTP status of the first response |
| body | jsonb | yes | null | | first response body; null = the response had no body |
| created_at | timestamptz | no | none | | purge after 24 hours (D3-20, AQ-2) |
- PK caller, operation, key
- CHECK ck_lending_idem_caller: char_length(caller) BETWEEN 1 AND 255
- CHECK ck_lending_idem_operation: operation IN ('borrowBook','placeHold','addCopy','checkInCopy','renewLoan','cancelHold','withdrawCopy')
- CHECK ck_lending_idem_hash: octet_length(request_hash) = 32
- CHECK ck_lending_idem_status: status BETWEEN 200 AND 499 AND status NOT IN (401, 429)
- IDX ix_lending_idem_created (created_at) — serves the 24-hour purge job
- Written in the command's transaction (D3-18, D3-L7).

## Enforced in code
| Invariant | Why not in the store | Where enforced |
|---|---|---|
| Copy state matches its active loan or shelf hold (invariants a, h) | Spans rows of three tables | BookCirculation, saved in one transaction under `version` |
| Due date = borrowed day + 14, renewal + 14 (REQ-10, REQ-12) | Depends on the configured time zone (DQ-1) | Loan entity |
| No renewal while a hold waits (REQ-13); hold only when no copy is available (REQ-6) | Cross-row conditions | BookCirculation RenewLoan, PlaceHold |
| FIFO serving; a shelf copy is lent only to its holder before the deadline (REQ-7, REQ-17) | Ordering and time rule | BookCirculation LendCopy, CheckInCopy, ExpireShelvedHold |
| No withdraw while on loan; check in only on loan; withdrawn and sent are final (REQ-26, REQ-27, Q-12) | State transitions, not row states | BookCirculation, HoldReadyNotification |
| At most 3 `reserved` slots, refused slots not counted (REQ-8, D2-15); no slot while owing fines (REQ-9) | Count over child rows; the fine flag comes from another context | Borrower BorrowBook, serialised by `lending.borrower.version` |
| Older FineBalanceChanged ignored (D2-11) | Conditional on the stored row | RecordFineStatus applies only when accountVersion > `fine_status_account_version` |
| Refused slot is final; CancelLoanSlot on a refused slot is a no-op (D2-15) | State transition, not a row state | Borrower CancelLoanSlot |
| BookAvailability rebuild snapshot matches its version (D3-L6) | Computed from several tables at one version | RepublishBookAvailability reads the circulation row, copies and loans in one transaction |
