# 07 Design review (loop 2)

## Inputs
All files read in full by the reviewer, who authored none of them (REV-01). Reviewer model: Fable 5.2 (claude-fable-5-2).

| File | Lines |
|---|---|
| docs/design/project-profile.md | 50 |
| .claude/skills/backend-design-team/references/default-rulebook.md (rules; no project rules file, no overrides) | 91 |
| docs/design/00-project-brief.md | 115 |
| prototype.html (5 screens, re-read directly) | 62 |
| docs/design/01-strategic.md | 122 |
| docs/design/02-tactical-catalog.md / -lending.md / -fines.md / -membership.md | 73 / 133 / 77 / 67 |
| docs/design/03-db-design.md / -lending.md / -fines.md | 200 / 228 / 119 |
| docs/design/04-erd.md | 215 |
| docs/design/05-diagrams.md / 05-diagrams-flows.md | 175 / 160 |
| docs/design/06-api.md | 164 |
| docs/design/06-api.openapi.yaml / -common / -catalog / -lending / -membership / -fines | 65 / 111 / 105 / 294 / 86 / 79 |
| docs/design/07-lint.md | 18 |
| docs/design/07-review-loop1.md, 07-fixes-loop1.md, 00-state.md | 106 / 40 / 44 |

Expected load: one small public library (brief Goals, prototype.html:8). No numbers are stated.

## Decisions
- Verdict: **pass** (no High). Totals: High 0, Medium 5, Low 7.
- D7-1 All 13 loop 1 findings were checked in the files as they are now, not from 07-fixes-loop1.md. All 13 are fixed (table below). Three fixes left small follow-on gaps in files the fix did not touch: F3 and F9 here follow F1, F4 and F7 here follow F2 and F6.
- D7-2 Every REQ-1 to REQ-30 has exactly one owner in 01, a command or query in 02, an operation in 06 or a stated reason for none, and storage in 03 (STR-02, TAC-07, REV-03 hold). REQ-30 is mapped to BorrowBook as the proposed default of RQ-1, which stays open.
- D7-3 Prototype pass: every button, input, table and stated automatic behaviour on S1 to S5 has a REQ. Sign-in has no screen (Q-1). The shelved-hold pickup has no control and is REQ-30 with its source marked missing.
- D7-4 Rules checked artifact by artifact and found to hold: DOC-01, DOC-05, STR-01 to STR-04, TAC-01 to TAC-10, TAC-12, DB-01 to DB-06, DB-08, ERD-01, API-01 to API-05, API-08. Exceptions are the findings below.
- D7-5 Lint L1 is rejected again (see Lint findings rejected).

Loop 1 findings, re-verified:

| Loop 1 id | Status | Verified at |
|---|---|---|
| F1 (High, STR-03) | fixed | 01-strategic.md:19, :75, :76, :80; 02-tactical-catalog.md:20; 05-diagrams.md:168-170. Follow-on: F3, F9 below |
| F2 (High, BUG) | fixed | 03-db-design-lending.md:14, :179, :184, :186; 03-db-design.md:22. Follow-on: F7 below |
| F3 (High, MISSING) | fixed | 03-db-design.md:27-30, :116, :167; 03-db-design-lending.md:198; 03-db-design-fines.md:94; 04-erd.md; 06-api.md:19 |
| F4 (Medium) | fixed | 02-tactical-lending.md:83; 06-api.md:81; 06-api.openapi-lending.yaml:76 |
| F5 (Medium) | fixed | 02-tactical-lending.md:21, :70, :77; 03-db-design-lending.md:119, :226 |
| F6 (Medium) | fixed | 02-tactical-lending.md:25, :68, :127; 03-db-design-lending.md:12, :133-145; 06-api.md:79; lending yaml :31. Follow-on: F4, F6 below |
| F7 (Medium) | fixed | 06-api.openapi-lending.yaml:246; RQ-2 open in 06-api.md:44 |
| F8 (Medium) | fixed | 03-db-design-lending.md:15; 02-tactical-catalog.md:68. Residue: F5 below |
| F9 (Medium) | fixed | 00-project-brief.md:14, :31, :87; 01-strategic.md:22, :64; 02-tactical-lending.md:29, :48 |
| F10 (Medium) | fixed | 06-api.openapi-membership.yaml:29 |
| F11 (Low) | fixed | 02-tactical-catalog.md:19, :21; 00-state.md:44 |
| F12 (Low) | fixed | 05-diagrams.md:150; 04-erd.md:62, :174; 03-db-design-fines.md:53 |
| F13 (Low) | fixed | 02-tactical-membership.md:29, :40; 03-db-design.md:140 |

## Open questions
| Id | Business decision needed | Found in | Proposed default |
|---|---|---|---|
| RQ-1 | How does a member take a copy waiting on the hold shelf: their own Borrow, or a desk action? Still open. | 00-project-brief.md:31; REQ-30 | The holder uses Borrow (as 02 and 06 assume). |
| RQ-2 | How is the physical copy the member takes matched to the copy on the loan? Still open. | 06-api.md:44 | The loan shows the assigned barcode. |
| RQ-3 | May a member who just returned a late book still borrow for a few seconds? Still open. | 01-strategic.md:28 | Yes. |
| RQ-4 | Is the 3-day hold-shelf period 72 hours, or the end of the third calendar day? Still open, and the design body does not follow its default (F1). | 02-tactical-lending.md:47, :66 | End of the third calendar day in the library time zone. |
| RQ-5 | Maximum length of a member name. Still open. | 02-tactical-membership.md:29 | 200 characters. |

## Findings
| Id | Severity | Rule | Location | Case | Fix | Owner phase | Previous |
|---|---|---|---|---|---|---|---|
| F1 | Medium | DOC-03 | 02-tactical-lending.md:66 ("Shelved time plus 3 days (REQ-17)"); 02-tactical-lending.md:47 (RQ-4 default "End of the third calendar day"); 03-db-design-lending.md:94 ("shelved time + 3 days") | When a copy is shelved on Monday at 10:00, the PickupDeadline rule gives Thursday 10:00, and the RQ-4 proposed default gives Thursday 23:59 in the library zone. The same file states the 72-hour reading as fact while the question is open with the other default, so a developer builds either one. | In 02 Lending line 66, write "per RQ-4 (proposed: end of the third calendar day in the library time zone)". Then the note of `lending.hold.pickup_deadline` in 03 Lending cites RQ-4 the same way. | 2 | new (RQ-4 was raised in loop 1 with no finding) |
| F2 | Medium | BUG | 02-tactical-lending.md:53 ("(l) At most one open hold per member (LQ-6)"); 03-db-design-lending.md:101 (`uq_hold_open_member_book (member_id, book_id)`) | When a member with an open hold on book A places a hold on book B, a developer following invariant (l) as written rejects it with HoldAlreadyPlaced. LQ-6, LQ-8 ("No limit") and the unique index allow it: the rule is per member and book. | Change (l) to "At most one open hold per member per book (LQ-6)". | 2 | new |
| F3 | Medium | BUG | 02-tactical-fines.md:12 (D2-3 "Fines never calls Membership."); 02-tactical-fines.md:19 (D2-10 "resolves the signed-in member through the Membership public operation ResolveCurrentMember") | When a developer builds the Fines module from D2-3, the module may not import Membership, so the guard that D2-10, the NotLibrarian failure (line 54) and 01 D1-10 require cannot be wired. The two decisions in one file disagree after the F1 fix. | In D2-3, write "Fines never calls Membership, except the API-guard query ResolveCurrentMember (01 D1-10, D2-10)". | 2 | new (follow-on of loop 1 F1) |
| F4 | Medium | DOC-04 | 05-diagrams.md:54 ("BorrowBook (REQ-5, REQ-8, REQ-9, REQ-29)"), :67, :68; 05-diagrams.md:119-146 (DB-modules) | When a reader uses 05 as the map, the query GetBorrowRequest (02-tactical-lending.md:127, 06 getBorrowRequest) is not in UC-Lending, REQ-30 is missing from the BorrowBook and LendCopy labels and REQ-5 from CancelLoanSlot (D5-3 says labels come from 02), and DB-modules shows 20 tables while the 03 Modules table lists 24 (the four `idempotency_record` tables are missing, against D5-5). | In UC-Lending add `GetBorrowRequest (REQ-5, REQ-29)` with a Member edge and correct the three labels. In DB-modules add the four `idempotency_record` nodes. | 5 | new (follow-on of loop 1 F3, F6, F9) |
| F5 | Medium | BUG | 03-db-design-lending.md:15 ("Run by an operator after `catalog.book_availability` is truncated or found wrong") | When a Catalog row for book X holds wrong counts at source_version 7 and the operator runs RepublishBookAvailability without truncating, the job emits version 7, the guard `excluded.source_version > book_availability.source_version` (03-db-design.md:190) skips it, and the wrong row stays. Line 15 itself says an equal version is skipped. | Replace "is truncated or found wrong" with "is truncated (always truncate first, as 03-db-design.md:90 says)". | 3 | new (residue of loop 1 F8) |
| F6 | Low | DOC-04 | 01-strategic.md:89 (Lending public operations end at "ListOverdueLoans") | When a reader checks the published language of Lending, the public query GetBorrowRequest exposed by 06-api.md:79 is not listed. | Add GetBorrowRequest to the Lending row. | 1 | new (follow-on of loop 1 F6) |
| F7 | Low | DOC-04 | 02-tactical-lending.md:18 (D2-8 "the outbox row carries deliver not before = pickupDeadline") | When a developer reads 02 alone, CopyPlacedOnHoldShelf is one delayed row with two consumers, which is the loop 1 F2 defect. 03-db-design-lending.md:186 writes two targeted rows. | In D2-8, add "written as two targeted outbox rows (03 Lending D3-L5)". | 2 | new (follow-on of loop 1 F2) |
| F8 | Low | DOC-04 | 02-tactical-lending.md:30 ("Lint L4 (TAC-04) on CopyPlacedOnHoldShelf") | When a reader looks up L4 in 07-lint.md, it does not exist; the finding is L1 (07-lint.md:18). | Change "L4" to "L1". | 2 | new |
| F9 | Low | DOC-04 | 02-tactical-membership.md:5 ("rows Catalog/Fines to Membership (separate ways)") | When a reader checks the Membership inputs against 01, the Catalog row is no longer separate ways: 01-strategic.md:80 makes Membership an open host for Catalog. | Change to "row Fines to Membership (separate ways); open host rows to Catalog, Lending and Fines (ResolveCurrentMember)". | 2 | new (follow-on of loop 1 F1) |
| F10 | Low | DOC-04 | 06-api.openapi-lending.yaml:13 ("summary: BorrowBook (REQ-5, REQ-8, REQ-9, REQ-29)") | When the contract is read without 06-api.md, REQ-30 has no operation; 06-api.md:78 lists REQ-30 on borrowBook. | Add "REQ-30 (RQ-1 default)" to the summary. | 6 | new (follow-on of loop 1 F9) |
| F11 | Low | DOC-03 | 00-project-brief.md:26 (Q-8 default "Not stated; ask.") | When Q-8 is carried forward, it has no proposed default, while 02-tactical-lending.md:36 (LQ-2) proposes "allowed" and 06 builds on that. The brief and 01-strategic.md:40 give a reader no default to confirm. | Set the Q-8 default in the brief to "Allowed (LQ-2)"; 01 line 40 follows. | 0 | new |
| F12 | Low | BUG | 00-state.md:4 ("eferences\default-rulebook.md") | When 00-state.md is rendered, a broken fragment of the rules path stands as its own line under the header. | Delete line 4. | 0 (orchestrator) | new |

## Lint findings rejected
| Lint id | Why rejected |
|---|---|
| L1 (TAC-04, 02-tactical-lending.md:103) | `CopyPlacedOnHoldShelf` is `<Noun><PastVerb>` with a place suffix. It states a fact and asks for nothing: both consumers decide their own action, and ExpireShelvedHold re-checks state and deadline (02-tactical-lending.md:89). The heuristic misreads the suffix. Same reason as loop 1. |

## Requirement trace
| REQ | Context | Command / query | Operation | Storage | Status (ok / MISSING / out of scope) |
|---|---|---|---|---|---|
| REQ-1 | Catalog | SearchCatalog | searchCatalog | catalog.book (trgm indexes) | ok |
| REQ-2 | Catalog | SearchCatalog, BookAvailability | searchCatalog | catalog.book_availability | ok (rebuild note: F5) |
| REQ-3 | Catalog | SearchCatalog, GetBookDetails | getBookDetails | catalog.book | ok |
| REQ-4 | Catalog | GetBookDetails | getBookDetails | catalog.book, book_availability.earliest_due_date | ok |
| REQ-5 | Lending | BorrowBook, LendCopy, GetBorrowRequest | borrowBook, getBorrowRequest | lending.loan_slot, lending.loan | ok |
| REQ-6 | Lending | PlaceHold | placeHold | lending.hold | ok (invariant text: F2) |
| REQ-7 | Lending | PlaceHold, LendCopy | placeHold | lending.hold.sequence, uq_hold_sequence | ok |
| REQ-8 | Lending | BorrowBook, CancelLoanSlot, ReleaseLoanSlot | borrowBook | lending.loan_slot | ok |
| REQ-9 | Lending | BorrowBook, RecordFineStatus | borrowBook | lending.borrower.owes_fines, fine_status_account_version | ok |
| REQ-10 | Lending | LendCopy | no operation: policy-triggered | lending.loan.due_date | ok |
| REQ-11 | Lending | ListMyLoans | listMyLoans | lending.loan | ok |
| REQ-12 | Lending | RenewLoan | renewLoan | lending.loan.renewed, due_date | ok |
| REQ-13 | Lending | RenewLoan | renewLoan | lending.hold (state waiting) | ok |
| REQ-14 | Lending | ListMyHolds | listMyHolds | lending.hold | ok |
| REQ-15 | Lending | CancelHold | cancelHold | lending.hold.state | ok |
| REQ-16 | Lending | SendHoldReadyEmail | no operation: policy-triggered | lending.hold_ready_notification, lending.outbox.target_consumer | ok |
| REQ-17 | Lending | CheckInCopy, ExpireShelvedHold | checkInCopy | lending.hold.pickup_deadline, lending.outbox.deliver_not_before | ok (deadline rule: F1, RQ-4) |
| REQ-18 | Fines | GetMyFines | getMyFines | fines.account.balance_minor | ok |
| REQ-19 | Fines | ChargeLateFine | no operation: policy-triggered | fines.fine | ok |
| REQ-20 | Lending | CheckInCopy | checkInCopy | lending.loan.returned_at | ok |
| REQ-21 | Lending | CheckInCopy | checkInCopy | lending.book_copy.state, lending.hold | ok |
| REQ-22 | Lending | ListOverdueLoans | listOverdueLoans | lending.loan (ix_loan_overdue), lending.borrower.name | ok |
| REQ-23 | Fines | RecordFinePayment, OpenAccount | recordFinePayment | fines.payment, fines.account, fines.idempotency_record | ok |
| REQ-24 | Catalog | AddBook | addBook | catalog.book | ok |
| REQ-25 | Lending | AddCopy, OpenBookCirculation | addCopy | lending.book_copy | ok |
| REQ-26 | Lending | WithdrawCopy | withdrawCopy | lending.book_copy.state, withdrawn_at | ok |
| REQ-27 | Lending | WithdrawCopy | withdrawCopy | enforced in code (state transition) | ok |
| REQ-28 | Membership | RegisterMember | registerMember | membership.member | ok |
| REQ-29 | Membership | ResolveCurrentMember | resolveCurrentMember | membership.member (uq_member_email) | ok (Fines wording: F3) |
| REQ-30 | Lending | BorrowBook, LendCopy (RQ-1 proposed default) | borrowBook | lending.loan.from_hold_id, lending.hold.state | ok, pending RQ-1 (labels: F4, F10) |

Prototype pass: every state-changing or data-showing element on S1 to S5 maps to a REQ above. No element is without a REQ.

## Not checked
- The OpenAPI files were read, not run through a validator; `$ref` paths between the six files were checked by eye only.
- Mermaid diagrams were not rendered.
- `design_check.py` was not re-run; 07-lint.md was taken as its output. The reviewer has no shell.
- DOC-02 was sampled (about 10 statements across 01, 02 and 03), not checked on every statement.
- Technical values marked *proposed* (2-second wait, 24-hour key retention, 3 server retries, 30-day purges, page sizes, rate limits) were not judged; they are in AQ-6, AQ-7, AQ-10, AQ-12, LQ-12 and DQ-2.
- The advisory-lock idempotency protocol (03 D3-18) was read for consistency with 06 D6-8 only; its behaviour under PostgreSQL was not verified.
- NestJS and PostgreSQL feasibility (pg_trgm availability, in-process wait for LoanStarted) was not verified.
- Whether 00-state.md collects the SQ, CQ, LQ, FQ, OQ-M, DQ, EQ, DG and AQ questions was not reviewed.
