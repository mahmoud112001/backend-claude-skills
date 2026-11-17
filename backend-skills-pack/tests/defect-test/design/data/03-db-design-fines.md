# 03 Database design: Fines

## Inputs
- docs/design/03-db-design.md: Decisions D3-1 to D3-20 and Open questions DQ-1, DQ-2, DQ-4 to DQ-8 apply here.
- docs/design/06-api.md: D6-8 (recordFinePayment requires an Idempotency-Key). docs/design/07-review-loop1.md: F3.
- docs/design/02-tactical-fines.md: Aggregates, Entities and value objects, Commands, Domain events, Policies, Queries and read models.
- docs/design/project-profile.md: PostgreSQL, UUIDv7, snake_case, transactional outbox per module.

## Decisions
- D3-F1 `fines.account.balance_minor` is stored and changed in the same transaction as each fine or payment row (Fines D2-1). `CHECK balance_minor >= 0` lets the store reject a payment above the balance (FQ-2).
- D3-F2 `uq_fine_loan` is unique on loan_id across all accounts, which is stricter than the per-account rule in Fines D2-5. Why: a UUIDv7 loan id belongs to exactly one member.
- D3-F3 Fines and payments carry no currency column. They use `fines.account.currency` (D3-7).
- D3-F4 `fines.idempotency_record` serves recordFinePayment (F3, D3-17 to D3-20). The record commits with the payment row and the balance change, so a retried payment with the same key replays the first response and the balance drops once.

## Open questions
| Id | Question | Why it matters | Proposed default |
|---|---|---|---|
| none | All open questions are in 03-db-design.md (DQ-1, DQ-4, DQ-6) and 02-tactical-fines.md (FQ-1 to FQ-9) | | |

## Tables

### Table: fines.account (module: Fines)
Aggregate: Account (root)
| Column | Type | Null | Default | Constraint | Notes (invariant / REQ) |
|---|---|---|---|---|---|
| account_id | uuid | no | none | PK | UUIDv7 |
| member_id | uuid | no | none | uq_account_member | one account per member (Fines D2-3) |
| card_number | text | no | none | uq_account_card | CardNumberTaken; RecordFinePayment lookup (REQ-23, Q-10) |
| currency | char(3) | no | none | CHECK currency ~ '^[A-Z]{3}$' | D3-7, FQ-1 |
| balance_minor | bigint | no | 0 | ck_account_balance | REQ-18; never negative (FQ-2) |
| opened_at | timestamptz | no | none | | |
| version | bigint | no | 1 | | concurrency; FineBalanceChanged.accountVersion (Fines D2-8) |
- PK account_id
- REF member_id -> Membership.Member (id only, no FK)
- UNIQUE uq_account_member (member_id) — serves GetMyFines
- UNIQUE uq_account_card (card_number) — serves RecordFinePayment
- CHECK ck_account_balance: balance_minor >= 0

### Table: fines.fine (module: Fines)
Aggregate: Account (child of Account)
| Column | Type | Null | Default | Constraint | Notes (invariant / REQ) |
|---|---|---|---|---|---|
| fine_id | uuid | no | none | PK | |
| account_id | uuid | no | none | FK | |
| loan_id | uuid | no | none | uq_fine_loan | one fine per loan (Fines D2-5, D3-F2) |
| due_date | date | no | none | | from LoanEnded |
| returned_at | timestamptz | no | none | | from LoanEnded |
| days_late | integer | no | none | CHECK days_late > 0 | REQ-19 |
| amount_minor | bigint | no | none | CHECK amount_minor > 0 | 0.25 per day (REQ-19), account currency |
| charged_at | timestamptz | no | none | | |
- PK fine_id
- FK account_id -> fines.account(account_id) ON DELETE RESTRICT
- FK loan_id -> lending.loan(loan_id) ON DELETE RESTRICT
- UNIQUE uq_fine_loan (loan_id) — a duplicate LoanEnded is a no-op
- IDX ix_fine_account (account_id, charged_at) — FK; serves GetMyFines list (FQ-6)

### Table: fines.payment (module: Fines)
Aggregate: Account (child of Account)
| Column | Type | Null | Default | Constraint | Notes (invariant / REQ) |
|---|---|---|---|---|---|
| payment_id | uuid | no | none | PK | |
| account_id | uuid | no | none | FK | |
| amount_minor | bigint | no | none | CHECK amount_minor > 0 | InvalidPaymentAmount (REQ-23, FQ-2) |
| recorded_by | text | no | none | CHECK char_length(recorded_by) BETWEEN 1 AND 255 | librarian identity subject (DQ-6) |
| recorded_at | timestamptz | no | none | | |
- PK payment_id
- FK account_id -> fines.account(account_id) ON DELETE RESTRICT
- IDX ix_payment_account (account_id, recorded_at) — FK

### Table: fines.outbox (module: Fines)
Aggregate: outbox
| Column | Type | Null | Default | Constraint | Notes (invariant / REQ) |
|---|---|---|---|---|---|
| message_id | uuid | no | none | PK | = eventId |
| event_type | text | no | none | ck_fines_outbox_type | |
| aggregate_id | uuid | no | none | | account_id |
| payload | jsonb | no | none | | FineBalanceChanged payload |
| occurred_at | timestamptz | no | none | | |
| attempts | integer | no | 0 | CHECK attempts >= 0 | |
| published_at | timestamptz | yes | null | | null = not yet delivered to all handlers |
- PK message_id
- CHECK ck_fines_outbox_type: event_type IN ('FineBalanceChanged')
- IDX ix_fines_outbox_pending (occurred_at) WHERE published_at IS NULL — serves the outbox worker

### Table: fines.inbox (module: Fines)
Aggregate: inbox
| Column | Type | Null | Default | Constraint | Notes (invariant / REQ) |
|---|---|---|---|---|---|
| consumer | text | no | none | PK | OpenAccountOnMemberRegistered, ChargeFineOnLoanEnded |
| message_id | uuid | no | none | PK | |
| processed_at | timestamptz | no | none | | |
- PK consumer, message_id

### Table: fines.idempotency_record (module: Fines)
Aggregate: inbox (idempotency record for API commands, D3-17; not an aggregate)
| Column | Type | Null | Default | Constraint | Notes (invariant / REQ) |
|---|---|---|---|---|---|
| caller | text | no | none | PK, ck_fines_idem_caller | identity provider subject of the caller (DQ-6) |
| operation | text | no | none | PK, ck_fines_idem_operation | 06 operationId (D3-19) |
| key | uuid | no | none | PK | Idempotency-Key header (06 D6-8) |
| request_hash | bytea | no | none | ck_fines_idem_hash | SHA-256 of the canonical request (D3-19) |
| status | smallint | no | none | ck_fines_idem_status | HTTP status of the first response |
| body | jsonb | yes | null | | first response body; null = the response had no body |
| created_at | timestamptz | no | none | | purge after 24 hours (D3-20, AQ-2) |
- PK caller, operation, key
- CHECK ck_fines_idem_caller: char_length(caller) BETWEEN 1 AND 255
- CHECK ck_fines_idem_operation: operation IN ('recordFinePayment')
- CHECK ck_fines_idem_hash: octet_length(request_hash) = 32
- CHECK ck_fines_idem_status: status BETWEEN 200 AND 499 AND status NOT IN (401, 429)
- IDX ix_fines_idem_created (created_at) — serves the 24-hour purge job
- Written in the recordFinePayment transaction (D3-18, D3-F4).

## Enforced in code
| Invariant | Why not in the store | Where enforced |
|---|---|---|
| Balance = fines minus payments (REQ-18) | Sum over child rows | Account, same transaction under `fines.account.version` |
| Fine = 0.25 per day late (REQ-19) | The rate and the currency are configuration (FQ-1) | Account ChargeLateFine |
| Payment precision (FQ-9) | Minor units already make sub-unit amounts impossible to store; parsing happens at the API | Money value object |
| Only a Librarian records a payment (REQ-23) | Identity lives outside the store | API guard via ResolveCurrentMember |
