# 01 Strategic design

## Inputs
- docs/design/project-profile.md: architecture_style = modular monolith, one module per bounded context; events_messaging = in-process domain events plus a transactional outbox table per module, drained by a background worker; no external broker.
- docs/design/00-project-brief.md: Goals, Actors, Requirements REQ-1 to REQ-30, Decisions D0-1 to D0-5, Open questions Q-1 to Q-12 and RQ-1.
- Rulebook: .claude/skills/backend-design-team/references/default-rulebook.md. No project rules file and no rule overrides (profile).
- prototype.html was not re-read; the brief cites it line by line.

## Decisions
- D1-1 Four bounded contexts: Catalog, Lending, Fines, Membership. Why: the meaning of "book", "copy" and "member" changes between search, circulation, money and the member register (see Ubiquitous language); 2 to 4 is the normal size for one small library (brief Goals). Proposed.
- D1-2 Copies (barcode, add, withdraw) belong to Lending, not Catalog. Why: the rule "a copy on loan cannot be withdrawn" (REQ-27) and the hold shelf (REQ-17, REQ-21) are circulation rules on the copy; keeping the copy in Lending keeps those invariants in one context. Proposed.
- D1-3 Catalog holds the bibliographic record and a read model of availability and due dates (REQ-2, REQ-4), fed by Lending integration events. Catalog is never the source of truth for availability. Proposed.
- D1-4 Fines is its own context. Why: money rules (REQ-19, REQ-23) and the balance change for different reasons and people (desk payments) than loans. Proposed.
- D1-5 Lending enforces "owes fines cannot borrow" (REQ-9) from a local copy of the balance fed by the Fines integration event FineBalanceChanged. This is eventually consistent (outbox lag); see SQ-1. Proposed.
- D1-6 Fines creates a fine from the Lending integration event LoanEnded (REQ-19); Lending never computes money. Proposed.
- D1-7 Membership owns the member register (REQ-28) and the mapping from signed-in identity to member (REQ-29). Sign-in itself is the generic Identity subdomain and is out of scope, as the brief proposes (Q-1).
- D1-8 Email delivery (REQ-16) is the generic Notification subdomain: Lending decides when to notify; sending goes through an outbound port to a bought email service behind an anticorruption adapter inside the Lending module. Not a bounded context. Proposed.
- D1-9 Each context is one NestJS module with its own PostgreSQL schema and its own outbox table (profile architecture_style, events_messaging). The style is not changed.
- D1-10 Every context-map mechanism is an integration event through the outbox, because the profile uses events. Lending, Fines and Catalog keep local read copies of the data they need. The sole exception is one synchronous in-process query, Membership's open-host operation ResolveCurrentMember, called by the API guard of Catalog, Lending and Fines to map the signed-in identity to a member and role (REQ-29); a role check must be current at the moment of the request, so it cannot wait for outbox lag. No other synchronous cross-module call is allowed. Proposed.
- D1-11 Rules with stated values are taken from the brief as facts: 3 loans (REQ-8), 14 days (REQ-10, REQ-12), one renewal (REQ-12), 3-day hold shelf (REQ-17), 0.25 per day late (REQ-19). Everything else the brief leaves open stays an open question.
- D1-12 Fixed F1 (07-review-loop1.md, STR-03; closes carried-forward CQ-7 at the strategic level): the Catalog/Membership "separate ways" row is replaced by Membership upstream of Catalog, open host service, synchronous in-process query ResolveCurrentMember at the API guard; the same query is added to the Membership to Lending and Membership to Fines rows; D1-10 names it as the sole synchronous exception. Why: the Librarian check for AddBook (REQ-24) and the member checks in Lending and Fines need the role from Membership (REQ-29).
- D1-13 Fixed F9 (07-review-loop1.md): REQ-30 (pick up a shelved hold copy) is owned by Lending alone, proposed, pending RQ-1. Why: Lending owns holds, the hold shelf and copies (REQ-17, REQ-21, D1-2), and the pickup turns a shelved copy into a loan; either answer to RQ-1 (holder's Borrow or a librarian desk action) stays inside Lending, so the owner does not depend on RQ-1. RQ-1 itself is not decided here. Proposed.
- D1-14 Fixed F6 (loop 2) (07-review.md, DOC-04): GetBorrowRequest, the public Lending query exposed by 06-api.md:79, is added to the Lending public operations in Published language.

## Open questions
| Id | Question | Why it matters | Proposed default |
|---|---|---|---|
| SQ-1 | Is it acceptable that a member who has just paid may stay blocked from borrowing for a few seconds, until FineBalanceChanged reaches Lending? | D1-5 makes the fine block eventually consistent. | Yes; the outbox worker delivers within seconds. |
| RQ-3 | Is it acceptable that a member who has just returned a late book can still borrow for a few seconds, until the fine reaches Lending? | D1-5 eventual consistency, the opposite case of SQ-1. | Yes; same outbox lag as SQ-1. |
| SQ-2 | Does "total" in "available of total" (REQ-2) count withdrawn copies? | Catalog availability numbers. | No; withdrawn copies are excluded. |
| SQ-3 | Does a copy on the hold shelf count as available in the catalog (REQ-2) and for Borrow (REQ-5)? | Visitors could see a copy that only one member may take. | No; it counts as not available. |
| SQ-4 | Which email service, and what does the hold-ready email say (REQ-16)? | Generic subdomain to buy; brief Unknowns. | A transactional email service chosen at build time; email names the title and the pickup deadline. |
| SQ-5 | If the email fails, does the hold still go to the shelf? | REQ-16, REQ-17 coupling. | Yes; email is retried, the hold-shelf timer starts on check in. |
| Q-1 | How do members and librarians sign in? (brief) | Identity is generic; REQ-29. | Out of scope; identity already known to the backend. |
| Q-2 | Can a member hold a title with an available copy? (brief) | REQ-6. | No; reject the hold. |
| Q-3 | Does the 3-book limit count holds? (brief) | REQ-8. | Loans only. |
| Q-4 | What happens when the 3-day hold-shelf period ends? (brief) | REQ-17. | Hold expires; copy goes to next hold or becomes available. |
| Q-5 | Fine cap and currency? (brief) | REQ-19. | No cap; currency configurable. |
| Q-6 | Does "owe fines" mean any balance above zero? (brief) | REQ-9. | Yes. |
| Q-7 | Partial payment and overpayment? (brief) | REQ-23. | Partial allowed; overpayment rejected. |
| Q-8 | Can an overdue loan be renewed? (brief) | REQ-12. | Not stated; ask the user. |
| Q-9 | Remove books, edit or deactivate members? (brief) | Lifecycle of Catalog and Membership. | Out of scope. |
| Q-10 | Are ISBN, barcode and card number unique? (brief) | REQ-24, REQ-25, REQ-28. | All unique. |
| Q-11 | What counts as a day late? (brief) | REQ-19, REQ-22 (both contexts use "days late"). | Calendar days after the due date. |
| Q-12 | Check in a copy that is not on loan? (brief) | REQ-20. | Reject with an error. |
| RQ-1 | Who picks up a shelved hold copy: the holder via Borrow, or a librarian desk action? (brief) | REQ-30 actor and command; owner Lending either way (D1-13). | The holder uses Borrow; the shelf copy is lent to them (brief default, not decided here). |

## Domain
Shelfmark lets one small public library lend its books: members find books, borrow copies and place holds, and librarians run the desk, fines and catalogue (brief Goals). The library wins when members get the books they want fairly and on time (loan limits, renewals, first-come holds) and loses when copies, queues or fines are wrong (proposed reading of the Goals).

## Subdomains
| Subdomain | Type | Why (source) |
|---|---|---|
| Circulation | core | Loans, renewals, holds queue, hold shelf and check in carry almost all the library's specific rules (REQ-5 to REQ-17, REQ-20 to REQ-22, REQ-25 to REQ-27); this is what the product is for (brief Goals). Proposed classification. |
| Catalogue | supporting | Books with title, author, ISBN and a simple search (REQ-1 to REQ-4, REQ-24); needed, but plain search over a small collection is not a differentiator. Proposed. |
| Fines | supporting | Late-return fines and desk payments (REQ-18, REQ-19, REQ-23) with the library's own rate; no card processing is shown, so it is not generic payments. Proposed. |
| Membership | supporting | Register of members with name, email and card number (REQ-28) used at the desk (REQ-23). Proposed. |
| Identity | generic | Sign-in for members and librarians (REQ-29, Q-1); solved the same way everywhere; buy or reuse an identity provider. Proposed. |
| Notification | generic | Hold-ready email (REQ-16); use a bought email service. Proposed. |

## Bounded contexts
| Context | Subdomain | Responsibility | Owns REQ | Deployable |
|---|---|---|---|---|
| Catalog | Catalogue | Bibliographic records, catalog search and book detail, with an availability read model fed by Lending | REQ-1, REQ-2, REQ-3, REQ-4, REQ-24 | NestJS module `catalog`, schema `catalog` |
| Lending | Circulation | Copies, loans, renewals, holds queue, hold shelf, shelved-hold pickup (REQ-30: proposed, pending RQ-1), check in, overdue list, hold-ready notification trigger | REQ-5, REQ-6, REQ-7, REQ-8, REQ-9, REQ-10, REQ-11, REQ-12, REQ-13, REQ-14, REQ-15, REQ-16, REQ-17, REQ-20, REQ-21, REQ-22, REQ-25, REQ-26, REQ-27, REQ-30 | NestJS module `lending`, schema `lending` |
| Fines | Fines | Fine accrual on late return, member balance, payments | REQ-18, REQ-19, REQ-23 | NestJS module `fines`, schema `fines` |
| Membership | Membership | Member register and the mapping from signed-in identity to member and role | REQ-28, REQ-29 | NestJS module `membership`, schema `membership` |

All four modules run in one deployable (profile architecture_style). Each module has its own outbox table drained by the shared background worker (profile events_messaging).

## Context map
| Upstream | Downstream | Relationship | Mechanism | What flows |
|---|---|---|---|---|
| Catalog | Lending | customer-supplier | integration event BookAdded via Catalog outbox | Book id, title and author, so Lending can accept copies and holds for a book and show titles (REQ-11, REQ-14, REQ-22, REQ-25) |
| Lending | Catalog | customer-supplier | integration event BookAvailabilityChanged via Lending outbox | Per book: available and total copy counts and the earliest due date (REQ-2, REQ-4) |
| Membership | Lending | customer-supplier | integration event MemberRegistered via Membership outbox; open host service: synchronous in-process query ResolveCurrentMember at the API guard | Member id, name, email (overdue list REQ-22, hold email REQ-16); member id and role of the signed-in identity for member and librarian operations (REQ-29) |
| Membership | Fines | customer-supplier | integration event MemberRegistered via Membership outbox; open host service: synchronous in-process query ResolveCurrentMember at the API guard | Member id and card number, so the desk can pay by card (REQ-23); member id and role of the signed-in identity for GetMyFines and RecordFinePayment (REQ-29) |
| Lending | Fines | customer-supplier | integration event LoanEnded via Lending outbox | Loan id, member id, due date, return time (REQ-19) |
| Fines | Lending | customer-supplier | integration event FineBalanceChanged via Fines outbox | Member id and whether a balance is owed (REQ-9) |
| Catalog | Fines | separate ways | none | No data needed; fines are per member, not per book (proposed) |
| Membership | Catalog | open host service | synchronous in-process query ResolveCurrentMember at the API guard | Member id and role of the signed-in identity, so only a librarian may call AddBook (REQ-24, REQ-29) |
| Fines | Membership | separate ways | none | Membership needs no balance |

External: Lending calls a bought email service through an anticorruption adapter (D1-8). Membership conforms to the identity provider chosen under Q-1 (D1-7).

## Published language
| Context | Integration events (names) | Public operations (names) |
|---|---|---|
| Catalog | BookAdded | SearchCatalog, GetBookDetails, AddBook |
| Lending | BookAvailabilityChanged, LoanEnded | BorrowBook, PlaceHold, CancelHold, RenewLoan, CheckInCopy, AddCopy, WithdrawCopy, ListMyLoans, ListMyHolds, ListOverdueLoans, GetBorrowRequest |
| Fines | FineBalanceChanged | GetMyFines, RecordFinePayment |
| Membership | MemberRegistered | RegisterMember, ResolveCurrentMember |

## Ubiquitous language
| Term | Context | Meaning | Not to be confused with |
|---|---|---|---|
| Book | Catalog | A bibliographic record: title, author, ISBN (REQ-24) | A physical Copy; Book in Lending |
| Book | Lending | The title a hold queue and copies belong to, known by id and title from BookAdded | The Catalog record it was copied from; a Copy |
| Availability | Catalog | "available of total" copies and earliest due date, a read model from Lending (REQ-2, REQ-4) | The copy state in Lending, which is the truth |
| Search | Catalog | Match books by title or author (REQ-1) | Listing a member's loans |
| ISBN | Catalog | Identifier of a book edition (REQ-24); uniqueness is Q-10 | Barcode |
| Copy | Lending | One physical item of a book, with a barcode, in a circulation state: available, on loan, on hold shelf, withdrawn (REQ-25, REQ-26) | Book; the counts in Catalog Availability |
| Barcode | Lending | Label scanned to identify a copy at check in (REQ-20, REQ-25) | ISBN; card number |
| Borrower | Lending | A member as seen by circulation: loan count, fine block, email (REQ-8, REQ-9) | Member record in Membership; Account in Fines |
| Loan | Lending | A copy lent to a member for 14 days, renewable once (REQ-10, REQ-12) | A Fine; a Hold |
| Due date | Lending | Date a loan must be returned: borrowed date plus 14 days, moved by a renewal (REQ-10, REQ-12) | Hold-shelf deadline |
| Renewal | Lending | Extending a loan by another 14 days, once, and only when no one holds the book (REQ-12, REQ-13) | A new loan |
| Hold | Lending | A member's place in the first-come queue for a book with no available copy (REQ-6, REQ-7) | A loan; a copy on the hold shelf |
| Queue position | Lending | Rank of a hold among open holds for the same book (REQ-14) | Number of copies |
| Hold shelf | Lending | Where a returned copy waits 3 days for the first holder (REQ-17, REQ-21) | Available copies |
| Check in | Lending | Scanning a returned copy; ends the loan (REQ-20) | Borrow; Payment |
| Overdue | Lending | A loan whose due date has passed and which is not ended (REQ-22) | A Fine, which exists only after return (REQ-19) |
| Days late | Lending | Days between due date and today for an open overdue loan (REQ-22); definition Q-11 | Days late in Fines |
| Withdraw | Lending | Taking a damaged or lost copy out of circulation; not allowed while on loan (REQ-26, REQ-27) | Deleting a book |
| Fine | Fines | Amount charged for one late return, 0.25 per day late (REQ-19) | Overdue; Balance |
| Days late | Fines | Days between due date and return time of an ended loan, used to price a fine (REQ-19); definition Q-11 | Days late in Lending, which is for open loans |
| Balance | Fines | Total fines minus payments for a member (REQ-18) | A single Fine |
| Account | Fines | The member as a payer: balance and payments, found by card number (REQ-23) | Member record; Borrower |
| Payment | Fines | Money recorded at the desk against a member's balance (REQ-23); rules Q-7 | Online card payment (not shown) |
| Member | Membership | A registered person with name, email and card number (REQ-28) | A signed-in user account in Identity; Borrower; Account |
| Card number | Membership | Library card id printed for the member, used at the desk (REQ-23, REQ-28); uniqueness Q-10 | Member id; barcode |
| Signed-in member | Membership | A request whose identity maps to a registered member (REQ-29) | Visitor, who needs no sign-in (REQ-29) |
| Librarian | Membership | A staff role allowed to use the desk and admin operations (brief Actors) | Member |
