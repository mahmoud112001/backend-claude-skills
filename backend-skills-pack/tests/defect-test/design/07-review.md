# 07 Design review (loop 1)

## Inputs
Reviewer: design-reviewer, fresh context, authored none of the artifacts (REV-01). Model: claude-fable-5-2.

| File | Lines |
|---|---|
| project-profile.md | 50 |
| brief/00-project-brief.md | 115 |
| README.md | 30 |
| strategic/01-strategic.md | 123 |
| tactical/02-tactical-catalog.md | 73 |
| tactical/02-tactical-lending.md | 137 |
| tactical/02-tactical-fines.md | 78 |
| tactical/02-tactical-membership.md | 68 |
| data/03-db-design.md | 200 |
| data/03-db-design-lending.md | 230 |
| data/03-db-design-fines.md | 119 |
| data/04-erd.md | 215 |
| diagrams/05-diagrams.md | 180 |
| diagrams/05-diagrams-flows.md | 160 |
| api/06-api.md | 164 |
| api/06-api.openapi.yaml | 65 |
| api/06-api.openapi-catalog.yaml | 105 |
| api/06-api.openapi-common.yaml | 111 |
| api/06-api.openapi-fines.yaml | 62 |
| api/06-api.openapi-lending.yaml | 294 |
| api/06-api.openapi-membership.yaml | 86 |

- Rules: .claude/skills/backend-design-team/references/default-rulebook.md (91 lines). No project rules file and no rule overrides (project-profile.md:44, :50), so every default rule applies.
- Prototype: prototype.html is not in the design folder and the folder it lives in was out of bounds for this review. It was NOT re-read (see Not checked).
- 07-lint.md: not present in the design folder. No lint findings to confirm or reject.
- Expected load: one small public library (brief:36). No numbers stated.

## Decisions
- Verdict: **fail**. 6 High, 1 Medium, 4 Low.
- All six High findings sit in the Fines context (02, 03, 06). Catalog, Lending and Membership trace cleanly.
- REQ-18 (member sees total fines owed) is the only requirement with no command, query or operation.
- The README summary ("Review loop 2 passed with 0 High", README.md:5) does not describe the files as they are now.

## Open questions
| Id | Business decision needed | Found in | Proposed default |
|---|---|---|---|
| RQ-6 | Does the member see only the total fines owed, or each fine too? Two artifacts propose different defaults. | 02-tactical-fines.md:31 (FQ-6: total plus list) vs 06-api.md:56 (AQ-11: balance only) | Balance only in v1, as REQ-18 states; the list is added later as an optional field. |
| RQ-7 | Must the reason for a withdrawal (damaged or lost, REQ-26) be recorded? WithdrawCopy takes no reason. | brief:83; 02-tactical-lending.md:92 | Not recorded in v1. |

## Findings
| Id | Severity | Rule | Location | Case | Fix | Owner phase |
|---|---|---|---|---|---|---|
| F1 | High | TAC-01 | tactical/02-tactical-fines.md:39 (also :44) | `Contains` lists "Member (Membership aggregate)" and the Account entity has the field `member (Member)`. When a developer builds Account from this row, the Fines aggregate embeds the Membership aggregate, so loading or saving an Account reads or writes Membership data. 03 stores only `member_id` (03-db-design-fines.md:27) and D2-3 (:12) says only the id and card number are copied, so 02 contradicts both. | In :39 remove "Member (Membership aggregate)" from Contains and add "Member (Membership) by memberId" to References by id. In :44 change `member (Member)` to `memberId`. | 2 |
| F2 | High | TAC-04 | tactical/02-tactical-fines.md:63 | `SuspendBorrowing` is an imperative: it asks Lending to act, so it is a command sent as an event. When ChargeLateFine commits, it must write an event that (a) 01 does not publish (01-strategic.md:91, breaks TAC-10), (b) no Lending policy consumes (02-tactical-lending.md:113-123), and (c) the store rejects, because `ck_fines_outbox_type` allows only 'FineBalanceChanged' (03-db-design-fines.md:82): the insert fails and the fine transaction rolls back. The block is already carried by `FineBalanceChanged.owesFines` (:62). | Delete the SuspendBorrowing row. No other file changes. | 2 |
| F3 | High | TAC-07 / MISSING | tactical/02-tactical-fines.md:72-73 (also :78) | The Queries and read models table has a header and no rows. REQ-18 (brief:75) is owned by Fines (01-strategic.md:66) and has no command or query, although :78 claims "All Fines REQs map to a command or query", D2-10 (:19) describes GetMyFines, and 01 publishes it (01-strategic.md:91). When a member opens My fines (S3), the design defines nothing to read the balance. | Add one row: `GetMyFines | query | Account row by memberId of the signed-in member (D2-10); returns balance | none; live read | none | REQ-18, REQ-29`. | 2 |
| F4 | High | DB-01 | data/03-db-design-fines.md:53 | `FK loan_id -> lending.loan(loan_id) ON DELETE RESTRICT` is a foreign key from schema `fines` to schema `lending`. When the modules are migrated or split, `fines.fine` cannot exist without the Lending schema, and Lending can never purge a loan row. It contradicts D3-4 "Foreign keys exist only inside one schema" (03-db-design.md:14) and the ERD, which draws the column as a REF (04-erd.md:62, :174). The file has no REF line for `loan_id`. | Replace the line with `REF loan_id -> Lending.Loan (id only, no FK)`. `uq_fine_loan` (:54) stays and still indexes the column. | 3 |
| F5 | High | API-02 | api/06-api.md:93 | `openAccount  POST /v1/fine-accounts  maps to OpenAccount  actor Librarian`. OpenAccount is triggered by `policy:OpenAccountOnMemberRegistered` and Account is `Created by` that policy (02-tactical-fines.md:39, :53). When a librarian calls it, an Account is created outside MemberRegistered, with a memberId and card number that Membership never issued. It contradicts D6-2 (:13, "never exposed ... Account"), the count at :95 (10 commands; the table has 11), and the contract, which has no such path (06-api.openapi.yaml:26-59). OpenAccount is also absent from Not exposed (:151-164 lists 9 of the 10 policy commands). | Delete row :93. Add to Not exposed: `OpenAccount | policy-triggered (OpenAccountOnMemberRegistered); creates Account, Created by a policy`. | 6 |
| F6 | High | MISSING (REV-03) / DOC-05 | api/06-api.md:92 (Operations table, :74-93); api/06-api.openapi.yaml:56-57 | No `getMyFines` operation exists, so REQ-18 has no API. The table has 7 query rows while :95 says 8, and D6-11 (:22) and AQ-11 (:56) already describe `/v1/members/me/fines`. The root contract points `/v1/members/me/fines` at `./06-api.openapi-fines.yaml#/paths/~1v1~1members~1me~1fines`, but that file defines only `/v1/fine-payments` (06-api.openapi-fines.yaml:8): the `$ref` does not resolve, so the contract fails to bundle. The `MyFines` schema (06-api.openapi-fines.yaml:49) is unused. | After F3: add the row `getMyFines | GET /v1/members/me/fines | query | GetMyFines | Member | n/a (safe) | unauthenticated, not-member, rate-limited | REQ-18, REQ-29`, and add the matching `get` path in 06-api.openapi-fines.yaml returning `MyFines`. | 6 |
| F7 | Medium | BUG (DOC-04 follow-on of F3) | diagrams/05-diagrams.md:92-99 | UC-Fines declares `Member((Member))` and gives it no edge; the boundary holds RecordFinePayment, OpenAccount and ChargeLateFine only. When a reader checks who serves REQ-18, the diagram shows the Member doing nothing in Fines. | After F3: add `GMF["GetMyFines (REQ-18, REQ-29)"]` inside the subgraph and `Member --> GMF`. | 5 |
| F8 | Low | STR-03 | strategic/01-strategic.md:82 (drawn at diagrams/05-diagrams.md:179) | The pair Membership/Fines has two rows: customer-supplier with MemberRegistered and ResolveCurrentMember (:77), and "Fines / Membership / separate ways / none" (:82). When a reader looks at CTX-map, the same two contexts are shown both integrated and not integrated. | Delete row :82 (and the edge at 05-diagrams.md:179), or reword its Relationship cell to "no flow in this direction". | 1 |
| F9 | Low | DOC-04 | tactical/02-tactical-fines.md:31 vs api/06-api.md:56 | FQ-6 proposes "Total plus the list of fines"; AQ-11 proposes "balance only", and the `MyFines` schema has `balance` only (06-api.openapi-fines.yaml:49-53). When FQ-6 is read alone, a developer builds a fines list that the contract cannot return. This is a business choice (RQ-6). | Change the FQ-6 proposed default to "Total only in v1 (06 AQ-11)". Do not pick the answer; RQ-6 stays open. | 2 |
| F10 | Low | DOC-04 | strategic/01-strategic.md:54 | The Circulation subdomain row lists "REQ-5 to REQ-17, REQ-20 to REQ-22, REQ-25 to REQ-27" and omits REQ-30, which Lending owns at :65. When a reader traces REQ-30 to a subdomain, it has none. | Append ", REQ-30" to the REQ list at :54. | 1 |
| F11 | Low | DOC-04 | tactical/02-tactical-membership.md:19 | The fix note says the Inputs line matches "01-strategic.md:80", but :80 is the Catalog/Fines row; the Fines/Membership row is :82. When a reader follows the citation, the wrong row is found. | Change ":80" to ":82" (or drop the citation if F8 deletes the row). | 2 |

## Lint findings rejected
| Lint id | Why rejected |
|---|---|
| none | 07-lint.md does not exist in the design folder; there were no lint findings to confirm or reject. |

## Requirement trace
| REQ | Context | Command / query | Operation | Storage | Status (ok / MISSING / out of scope) |
|---|---|---|---|---|---|
| REQ-1 | Catalog | SearchCatalog | searchCatalog | catalog.book | ok |
| REQ-2 | Catalog | SearchCatalog, BookAvailability | searchCatalog | catalog.book_availability | ok |
| REQ-3 | Catalog | SearchCatalog, GetBookDetails | searchCatalog, getBookDetails | catalog.book | ok |
| REQ-4 | Catalog | GetBookDetails | getBookDetails | catalog.book, catalog.book_availability | ok |
| REQ-5 | Lending | BorrowBook, LendCopy, GetBorrowRequest | borrowBook, getBorrowRequest | lending.loan_slot, lending.loan | ok |
| REQ-6 | Lending | PlaceHold | placeHold | lending.hold | ok |
| REQ-7 | Lending | PlaceHold, LendCopy | placeHold | lending.hold.sequence | ok |
| REQ-8 | Lending | BorrowBook, ReleaseLoanSlot, CancelLoanSlot | borrowBook | lending.loan_slot | ok |
| REQ-9 | Lending | BorrowBook, RecordFineStatus | borrowBook | lending.borrower.owes_fines | ok (eventual, SQ-1, RQ-3) |
| REQ-10 | Lending | LendCopy | none (policy) | lending.loan.due_date | ok |
| REQ-11 | Lending | ListMyLoans | listMyLoans | lending.loan | ok |
| REQ-12 | Lending | RenewLoan | renewLoan | lending.loan.renewed | ok |
| REQ-13 | Lending | RenewLoan | renewLoan | lending.hold | ok |
| REQ-14 | Lending | ListMyHolds | listMyHolds | lending.hold | ok |
| REQ-15 | Lending | CancelHold | cancelHold | lending.hold | ok |
| REQ-16 | Lending | SendHoldReadyEmail | none (policy) | lending.hold_ready_notification | ok |
| REQ-17 | Lending | CheckInCopy, ExpireShelvedHold | checkInCopy | lending.hold, lending.outbox.deliver_not_before | ok (RQ-4 open) |
| REQ-18 | Fines | none | none | fines.account.balance_minor | **MISSING** (F3, F6, F7) |
| REQ-19 | Fines | ChargeLateFine | none (policy) | fines.fine | ok (F2 and F4 touch it) |
| REQ-20 | Lending | CheckInCopy | checkInCopy | lending.loan.returned_at | ok |
| REQ-21 | Lending | CheckInCopy | checkInCopy | lending.book_copy, lending.hold | ok |
| REQ-22 | Lending | ListOverdueLoans | listOverdueLoans | lending.loan, lending.borrower | ok |
| REQ-23 | Fines | RecordFinePayment, OpenAccount | recordFinePayment | fines.payment, fines.account | ok (F5: extra operation) |
| REQ-24 | Catalog | AddBook | addBook | catalog.book | ok |
| REQ-25 | Lending | AddCopy, OpenBookCirculation | addCopy | lending.book_copy | ok |
| REQ-26 | Lending | WithdrawCopy | withdrawCopy | lending.book_copy | ok (RQ-7 open) |
| REQ-27 | Lending | WithdrawCopy | withdrawCopy | lending.book_copy.state | ok |
| REQ-28 | Membership | RegisterMember | registerMember | membership.member | ok |
| REQ-29 | Membership | ResolveCurrentMember | resolveCurrentMember | membership.member | ok |
| REQ-30 | Lending | BorrowBook, LendCopy | borrowBook | lending.loan.from_hold_id | ok (proposed, RQ-1 open) |

## Not checked
- **The prototype.** prototype.html is not under the design folder, and its folder was excluded from this review. The brief's sources (line numbers, screens S1 to S5) were not verified, and no screen element was traced back to a REQ. The prototype half of REV-03 is therefore open: the brief may itself miss a requirement.
- 07-lint.md and `design_check.py` output: neither exists here, so the `script` checks (DOC-01 line limits aside, which were counted by hand) were done by reading only.
- docs/design/07-review-loop1.md and the loop-2 review that many "Fixed F<n>" notes cite: not in the folder, so those fix claims were not verified against their findings.
- README.md: its summary line (:5) and its reading-order numbering (:11-12 skip 2) are stale, but README belongs to no phase 0 to 6, so it is noted here and not routed as a finding.
- project-profile.md:42 names a project_root in another folder; whether the profile matches this copy of the design was not checked.
- OpenAPI files were read, not parsed or bundled by a tool; apart from F6, `$ref` targets were checked by eye.
- Mermaid diagrams were not rendered.
- DOC-02 was sampled (about 10 statements across 01 and 02), not checked line by line.
- Load, performance and security (token handling, rate limits AQ-7) were not reviewed beyond the rulebook rules.
