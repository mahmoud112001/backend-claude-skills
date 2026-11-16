# 07 Design review (loop 1)

## Inputs
All files read in full by the reviewer, who authored none of them (REV-01).

| File | Lines |
|---|---|
| docs/design/project-profile.md | 49 |
| .claude/skills/backend-design-team/references/default-rulebook.md (rules; no project rules file, no overrides) | 91 |
| docs/design/00-project-brief.md | 110 |
| prototype.html (the prototype, 5 screens, re-read directly) | 62 |
| docs/design/01-strategic.md | 118 |
| docs/design/02-tactical-catalog.md / -lending.md / -fines.md / -membership.md | 71 / 123 / 77 / 65 |
| docs/design/03-db-design.md / -lending.md / -fines.md | 151 / 192 / 98 |
| docs/design/04-erd.md | 185 |
| docs/design/05-diagrams.md / 05-diagrams-flows.md | 173 / 160 |
| docs/design/06-api.md | 152 |
| docs/design/06-api.openapi.yaml / -common / -catalog / -lending / -membership / -fines | 63 / 111 / 105 / 293 / 85 / 79 |
| docs/design/07-lint.md | 18 |
| docs/design/00-state.md (carried-forward items CQ-6, CQ-7, TAC-04 L1) | 38 |

Expected load: one small public library (brief Goals, prototype.html:8). No numbers are stated.

## Decisions
- Verdict: **fail** (3 High). Totals: High 3, Medium 7, Low 3.
- D7-1 Carried-forward CQ-7 is confirmed and is F1 (High, STR-03). The role check is a synchronous call that 01 both omits and forbids.
- D7-2 Carried-forward CQ-6 is resolved in substance by 03 D3-9 (`lending.book_circulation.version` is the event version, and `catalog.book_availability.source_version` guards the upsert). Only the stale open question remains: F11 (Low).
- D7-3 Carried-forward TAC-04 L1 is rejected (see Lint findings rejected). The real defect on that event is its delivery, F2.
- D7-4 Every REQ-1 to REQ-29 has exactly one owner in 01 and a command or query in 02 (STR-02, TAC-07 hold). The trace found one behaviour with no REQ at all (F9).
- D7-5 Rules checked artifact by artifact and found to hold: DOC-01, DOC-05, STR-01, STR-02, STR-04, TAC-01, TAC-03, TAC-05 to TAC-10, DB-01 to DB-05, DB-08, ERD-01, API-01 to API-05, API-08. The exceptions are the findings below.

## Open questions
| Id | Business decision needed | Found in | Proposed default |
|---|---|---|---|
| RQ-1 | How does a member take a copy that waits for them on the hold shelf: their own Borrow action, or a desk action by the librarian? The prototype shows neither. | F9; prototype.html:23, :38 | The holder uses Borrow; the shelf copy is lent to them (as 02 Lending LendCopy already assumes). |
| RQ-2 | A member borrows a book online, and the system picks the copy. How is the physical copy the member takes matched to the copy on the loan? | F7; prototype.html:23, :45 | The loan shows the barcode of the assigned copy; the member takes that copy. |
| RQ-3 | Is it acceptable that a member who has just returned a late book can still borrow for a few seconds, until the fine reaches Lending? SQ-1 asks only about the opposite case (just paid, still blocked). | 01-strategic.md:25 | Yes; same outbox lag as SQ-1. |
| RQ-4 | Is the 3-day hold-shelf period 72 hours from check in, or the end of the third calendar day? | 02-tactical-lending.md:57 | End of the third calendar day in the library time zone. |
| RQ-5 | Maximum length of a member name. 200 characters is written into the store with no question raised. | F13 | 200 characters. |

## Findings
| Id | Severity | Rule | Location | Case | Fix | Owner phase |
|---|---|---|---|---|---|---|
| F1 | High | STR-03 | 01-strategic.md:76 ("Catalog \| Membership \| separate ways \| none"); 01-strategic.md:19 ("no synchronous cross-module calls are proposed") | When a developer builds AddBook from 01, Catalog may not call Membership, so the Librarian check required by 03-db-design.md:144 ("API guard via ResolveCurrentMember") and 06-api.md D6-16 cannot be built. The same call is used by Lending (D2-10) and Fines (D2-10) with no context-map mechanism. This is carried-forward CQ-7 (02-tactical-catalog.md:29). | In 01: replace the Catalog/Membership row with "Membership upstream, open host service, synchronous in-process query ResolveCurrentMember at the API guard"; add the same mechanism to the Membership to Lending and Membership to Fines rows; amend D1-10 to name this one synchronous query. Then close CQ-7 in 02 Catalog and redraw the edge in 05 CTX-map. | 1 |
| F2 | High | BUG | 03-db-design-lending.md:172 ("CopyPlacedOnHoldShelf is written as two rows, each with its own message_id"); 03-db-design.md:20 ("redelivers an outbox row to all its handlers") | When a copy is shelved for a hold, the delayed row is delivered at pickupDeadline to every handler, including NotifyHolderOnHoldShelf. Its message_id differs from the first row, so `notification_id` (03-db-design-lending.md:139) does not deduplicate, and the member gets a second "your book is ready" email at the moment the hold expires. This breaks HoldReadyNotification invariant (a), one email per placement. | Add a nullable column `target_consumer` to `lending.outbox` (null = all handlers) and state that the two rows set NotifyHolderOnHoldShelf and ExpireHoldOnShelfDeadline. | 3 |
| F3 | High | MISSING | 06-api.md:18 (D6-8 "Keys are kept 24 hours ... scoped to caller identity plus operation"); 06-api.md:35 (AQ-2 "03 has no table for them") | When the desk retries a timed-out recordFinePayment with the same Idempotency-Key, no table exists to recognise the key, so a second payment row is written and the balance drops twice. Seven operations require the key and none has storage. AQ-2 is a design gap, not a business decision. | In 03, add one `idempotency_record` table per module (caller, operation, key, request_hash, status, body, created_at; PK caller, operation, key), written in the command's transaction, as AQ-2 already proposes. Add the tables to 04. | 3 |
| F4 | Medium | BUG | 02-tactical-lending.md:74 (PlaceHold fails when "BookUnknown, CopyAvailable (Q-2), HoldAlreadyPlaced, BookOnLoanToMember"); 03-db-design-lending.md:94 | When a member registered seconds ago places a hold before MemberRegistered is applied in Lending, the insert breaks `FK member_id -> lending.borrower` and no domain error is mapped. 06-api.md:69 lists no `borrower-unknown` for placeHold, although D6-16 promises it. | Add BorrowerUnknown to PlaceHold `Fails when` in 02 Lending; then add `borrower-unknown` to placeHold in 06-api.md and the lending contract. | 2 |
| F5 | Medium | BUG | 02-tactical-lending.md:21 (D2-11 "applies an event only when its occurredAt ... is newer"); 03-db-design-lending.md:192 ("RecordFineStatus compares `fine_status_account_version`") | When a fine and a payment for one account are recorded in the same millisecond, a developer following 02 compares occurredAt and may keep the older status, leaving a paid member blocked or an owing member free. 03 compares accountVersion. The two artifacts disagree (DQ-3). | In 02 Lending, change D2-11, the FineStatus row (line 61) and RecordFineStatus (line 68) to order by accountVersion; keep asOf for display. Close DQ-3. | 2 |
| F6 | Medium | MISSING | 06-api.md:34 (AQ-1 "02 has no query for a borrow outcome, and the refused slot is hard deleted"); 03-db-design-lending.md:11 | When borrowBook answers 202 and LendCopy then refuses (the last copy was just taken), the slot row is deleted and nothing records the refusal. The member sees neither a loan nor an error, and a replay with the same key returns the stored 202 "pending" for 24 hours. REQ-5 has no observable outcome on this path. | In 02 Lending, add the query GetBorrowRequest over a kept LoanRefused record, as AQ-1 proposes; 03 and 06 follow. | 2 |
| F7 | Medium | BUG | 06-api.openapi-lending.yaml:241-251 (schema `Loan`: loanId, bookId, title, status, borrowedAt, dueDate, renewed) | When a book has two available copies, LendCopy assigns copy A, but the response names no copy. The member takes copy B from the shelf. At return, check in of barcode B answers copy-not-on-loan, the loan on A never ends, it becomes overdue, and a fine is charged later. | Add `barcode` (the assigned copy) to the `Loan` schema. The matching rule itself is RQ-2. | 6 |
| F8 | Medium | MISSING | 03-db-design.md:30 (DQ-2 "rebuild BookAvailability by republishing one snapshot per `lending.book_circulation` row"); 02-tactical-catalog.md:66 | When `catalog.book_availability` must be rebuilt after outbox rows were deleted, replay is impossible and 02 Lending has no command or job that republishes snapshots. The rebuild that DB-06 and TAC-09 require is named but cannot be run. | In 03 (Lending, Enforced in code or a note on `lending.outbox`), define the rebuild as a Lending maintenance job that writes one BookAvailabilityChanged row per `book_circulation` row with its current version. | 3 |
| F9 | Medium | MISSING | 00-project-brief.md:59 (REQ-5 "the button is shown only when a copy is available"); 02-tactical-lending.md:73 | When the holder is emailed and opens the book, the shelf copy counts as not available (SQ-3), so Borrow is hidden by REQ-5. No REQ and no screen element covers taking the shelved copy. 02 silently reuses BorrowBook ("or on the shelf for this member"). | Add a REQ to the brief for picking up a shelved hold, with its source marked as missing in the prototype, and raise RQ-1. No design change until answered. | 0 |
| F10 | Medium | BUG | 06-api.openapi-membership.yaml:28 (`email: {type: string, maxLength: 320`); 03-db-design.md:120 (`char_length(email) <= 254`) | When a librarian registers a member with a 300-character email, the request passes the contract and the EmailAddress rule (syntax only), then fails `ck_member_email` with no mapped error. | Set `maxLength: 254` in the contract. | 6 |
| F11 | Low | DOC-04 | 02-tactical-catalog.md:28 (CQ-6 still listed as open) | When a developer reads 02 Catalog, the ordering key looks undecided, although 03 D3-9 and the Lending payload (`version`, 02-tactical-lending.md:97) settle it. | Under 02 Catalog Decisions, note that CQ-6 is resolved by 03 D3-9; remove it from 00-state carried-forward items. | 2 |
| F12 | Low | DOC-04 | 05-diagrams.md:148 (`f2 -.->\|ref\| l1`) | The same REF `fines.fine.loan_id` points at `lending.book_circulation` in 05 and at `lending.loan` in 04-erd.md:56. A reader cannot tell which table holds the id. | Change the edge in 05 to `f2 -.->\|ref\| l3`. | 5 |
| F13 | Low | DECISION | 02-tactical-membership.md:38 ("at most 200 characters (proposed)") | When a member's full name is longer than 200 characters, RegisterMember rejects it, and no open question records the limit. Catalog raised the same kind of limit as CQ-8; D3-15 does not list this one. | Move the limit to Open questions in 02 Membership (RQ-5). | 2 |

## Lint findings rejected
| Lint id | Why rejected |
|---|---|
| L1 (TAC-04, 02-tactical-lending.md:94) | `CopyPlacedOnHoldShelf` is `<Noun><PastVerb>` with a place suffix: "copy placed on hold shelf" states a fact and asks for nothing. Both consumers decide their own action, and ExpireShelvedHold re-checks state and deadline. The heuristic misread the suffix. The delivery problem of this event is F2, not a naming problem. |

## Requirement trace
| REQ | Context | Command / query | Operation | Storage | Status (ok / MISSING / out of scope) |
|---|---|---|---|---|---|
| REQ-1 | Catalog | SearchCatalog | searchCatalog | catalog.book (trgm indexes) | ok |
| REQ-2 | Catalog | SearchCatalog, BookAvailability | searchCatalog | catalog.book_availability | ok (rebuild: F8) |
| REQ-3 | Catalog | SearchCatalog, GetBookDetails | getBookDetails | catalog.book | ok |
| REQ-4 | Catalog | GetBookDetails | getBookDetails | catalog.book, book_availability.earliest_due_date | ok |
| REQ-5 | Lending | BorrowBook, LendCopy | borrowBook | lending.loan_slot, lending.loan | ok (outcome: F6; copy: F7) |
| REQ-6 | Lending | PlaceHold | placeHold | lending.hold | ok (F4) |
| REQ-7 | Lending | PlaceHold, LendCopy | placeHold | lending.hold.sequence, uq_hold_sequence | ok |
| REQ-8 | Lending | BorrowBook, CancelLoanSlot, ReleaseLoanSlot | borrowBook | lending.loan_slot | ok |
| REQ-9 | Lending | BorrowBook, RecordFineStatus | borrowBook | lending.borrower.owes_fines | ok (F5) |
| REQ-10 | Lending | LendCopy | no operation: policy-triggered | lending.loan.due_date | ok |
| REQ-11 | Lending | ListMyLoans | listMyLoans | lending.loan | ok |
| REQ-12 | Lending | RenewLoan | renewLoan | lending.loan.renewed, due_date | ok |
| REQ-13 | Lending | RenewLoan | renewLoan | lending.hold (state waiting) | ok |
| REQ-14 | Lending | ListMyHolds | listMyHolds | lending.hold | ok |
| REQ-15 | Lending | CancelHold | cancelHold | lending.hold.state | ok |
| REQ-16 | Lending | SendHoldReadyEmail | no operation: policy-triggered | lending.hold_ready_notification | ok (duplicate email: F2) |
| REQ-17 | Lending | CheckInCopy, ExpireShelvedHold | checkInCopy | lending.hold.pickup_deadline, lending.outbox.deliver_not_before | ok (pickup: F9) |
| REQ-18 | Fines | GetMyFines | getMyFines | fines.account.balance_minor | ok |
| REQ-19 | Fines | ChargeLateFine | no operation: policy-triggered | fines.fine | ok |
| REQ-20 | Lending | CheckInCopy | checkInCopy | lending.loan.returned_at | ok |
| REQ-21 | Lending | CheckInCopy | checkInCopy | lending.book_copy.state, lending.hold | ok |
| REQ-22 | Lending | ListOverdueLoans | listOverdueLoans | lending.loan (ix_loan_overdue), lending.borrower.name | ok |
| REQ-23 | Fines | RecordFinePayment, OpenAccount | recordFinePayment | fines.payment, fines.account | ok (retry safety: F3) |
| REQ-24 | Catalog | AddBook | addBook | catalog.book | ok (role check: F1) |
| REQ-25 | Lending | AddCopy, OpenBookCirculation | addCopy | lending.book_copy | ok |
| REQ-26 | Lending | WithdrawCopy | withdrawCopy | lending.book_copy.state, withdrawn_at | ok |
| REQ-27 | Lending | WithdrawCopy | withdrawCopy | enforced in code (state transition) | ok |
| REQ-28 | Membership | RegisterMember | registerMember | membership.member | ok (F10) |
| REQ-29 | Membership | ResolveCurrentMember | resolveCurrentMember | membership.member (uq_member_email) | ok (context map: F1) |
| none | Lending | pick up a shelved hold (prototype.html:38) | none | lending.loan.from_hold_id | MISSING in the brief (F9) |

Prototype pass: every button, input and table on S1 to S5 maps to a REQ above. Sign-in has no screen and is brief Q-1 (out of scope). The only behaviour with no REQ is the pickup of a shelved copy (F9).

## Not checked
- The OpenAPI files were read, not run through a validator; `$ref` paths between the six files were checked by eye only.
- Mermaid diagrams were not rendered.
- `design_check.py` was not re-run; 07-lint.md was taken as its output.
- DOC-02 was sampled (about 10 statements across 01 and 02), not checked on every statement.
- Technical values marked *proposed* (2-second wait, 24-hour key retention, 3 server retries, page sizes, rate limits) were not judged; they are already in AQ-1, AQ-2, AQ-6, AQ-7 and AQ-10.
- NestJS and PostgreSQL feasibility (pg_trgm availability, in-process wait for LoanStarted) was not verified.
- 00-state.md lists only Q-1 to Q-12 as open questions; whether the orchestrator collects SQ, CQ, LQ, FQ, OQ-M, DQ, EQ, DG and AQ items there was not reviewed.
