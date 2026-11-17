# 00 Project brief: Shelfmark

## Inputs
- prototype.html (type: ui, one HTML page with 5 screens). Read in full.
- Repo: no other project files. Profile is in project-profile.md.
- Screen ids used as sources: S1 screen-catalog, S2 screen-book, S3 screen-my-loans, S4 screen-desk, S5 screen-admin.
- docs/design/07-review-loop1.md (F9, RQ-1) read for the F9 fix.

## Decisions
D0-1 The admin screen (S5) and the librarian desk (S4) are in scope: they are part of the prototype and the intro says librarians run the desk (prototype.html:8).
D0-2 Each button is treated as a candidate command and each table as a candidate query, as the skill says.
D0-3 Automatic behaviours shown as text (fines on late return, email on hold-ready, hold shelf expiry) are requirements because the prototype states them.
D0-4 Values shown only in sample rows (for example "J. Park", "ISBN 978-0-00-000000-0") are examples, not rules.
D0-5 Fixed F9: REQ-30 added for picking up a shelved hold. The prototype shows the hold shelf but no pickup control, so the source is marked missing. Who performs the pickup is not decided; it is open question RQ-1.

## Open questions
| Id | Question | Why it matters | Proposed default |
|---|---|---|---|
| Q-1 | How do members and librarians sign in, and is there a sign-in screen? | S2 and S3 say "signed-in member"; no screen shows sign-in. | Out of scope for this design; assume an identity already known to the backend. |
| Q-2 | Can a member hold a title that has an available copy? | Prototype shows Place hold only when no copy is available. | No; reject the hold. |
| Q-3 | Does the 3-book limit count holds, or only loans? | Text says "on loan". | Loans only. |
| Q-4 | When the 3-day hold-shelf period ends, what happens to the copy and to the hold? | Only the 3 days is stated. | Hold expires, the copy goes to the next hold or becomes available. |
| Q-5 | Is there a cap on the fine, and what is the currency? | Only "0.25 per day late" and "0.75" are shown. | No cap; currency configurable. |
| Q-6 | Does "owe fines" mean any balance above zero? | Blocks borrowing (S2). | Yes, any balance above zero. |
| Q-7 | Can a partial payment be recorded, and can it exceed the balance? | The Amount field has no stated rule. | Partial allowed; overpayment rejected. |
| Q-8 | Can a book be renewed while overdue? | Renewal rule mentions only one renewal and holds. | Not stated; ask. |
| Q-9 | Can a book with copies, loans or holds be removed? Can members be edited or deactivated? | Only add actions are shown, plus Withdraw copy. | Out of scope. |
| Q-10 | Is the member card number unique, and is the ISBN unique? | Fields are shown with no constraints. | Both unique. |
| Q-11 | What counts as a day late (grace, closing days)? | Fine calculation. | Calendar days after the due date. |
| Q-12 | Should a returned copy be checkable when it is not on loan? | Check in only says it ends the loan. | Reject with an error. |
| RQ-1 | How does a member take a copy that waits for them on the hold shelf: their own Borrow action, or a desk action by the librarian? The prototype shows neither. | REQ-30 (F9); prototype.html:23, :38. Decides the actor and the command for the pickup. | The holder uses Borrow; the shelf copy is lent to them. |

## Goals
- Members find books, borrow copies and place holds (prototype.html:8).
- Librarians run the desk: check in, track overdue loans, take fine payments, manage the catalogue and members (prototype.html:8).
- Serve one small public library (prototype.html:8).

## Actors
| Actor | Description | Source |
|---|---|---|
| Visitor | Any visitor; can search the catalog | S1 title, prototype.html:11 |
| Member | Signed-in library member | S2, S3 titles |
| Librarian | Staff running the desk and the catalogue | S4, S5 titles |
| System | Automatic fines, emails and hold shelf timing | prototype.html:38, 40 |

## Screens / entry points
| Screen or entry point | Purpose | Source |
|---|---|---|
| S1 Catalog | Search books and see availability | prototype.html:10-18 |
| S2 Book detail | Borrow or place a hold | prototype.html:20-26 |
| S3 My loans | Loans, renewals, holds, fines | prototype.html:28-41 |
| S4 Librarian desk | Check in, overdue list, fine payments | prototype.html:43-52 |
| S5 Catalogue admin | Add book, add copy, withdraw copy, register member | prototype.html:54-60 |

## Requirements
| REQ | Requirement (one behaviour each) | Actor | Source |
|---|---|---|---|
| REQ-1 | Search the catalog by title or author | Visitor | S1 search input and button, :12 |
| REQ-2 | The catalog lists title, author and available copies as "available of total" | Visitor | S1 table, :14-16 |
| REQ-3 | Open a book's details from the catalog | Visitor | S1 Details link, :15-16 |
| REQ-4 | Book detail shows title, author, ISBN, copy count and, when on loan, the due date | Member | S2, :22 |
| REQ-5 | Borrow a book; the button is shown only when a copy is available | Member | S2 Borrow, :23 |
| REQ-6 | Place a hold; the button is shown only when no copy is available | Member | S2 Place hold, :24 |
| REQ-7 | Holds are served first come, first served | Member, System | S2, :24 |
| REQ-8 | A member can have at most 3 books on loan | Member | S2 note, :25 |
| REQ-9 | A member who owes fines cannot borrow | Member | S2 note, :25 |
| REQ-10 | A loan lasts 14 days | Member | S3 note, :34 |
| REQ-11 | A member sees their loans with title, borrowed date and due date | Member | S3 table, :31-32 |
| REQ-12 | Renew a loan, once only, for another 14 days | Member | S3 Renew, :32, :34 |
| REQ-13 | A loan cannot be renewed when another member holds the book | Member | S3 note, :34 |
| REQ-14 | A member sees their holds with title and queue position | Member | S3 My holds, :36-37 |
| REQ-15 | Cancel a hold | Member | S3 Cancel hold, :37 |
| REQ-16 | When a held book is returned, the holding member is emailed | System | S3 note, :38 |
| REQ-17 | A returned copy for a held book is kept on the hold shelf for 3 days | System | S3 note, :38; S4, :46 |
| REQ-18 | A member sees the total fines owed | Member | S3 My fines, :40 |
| REQ-19 | A fine of 0.25 per day late is added automatically when a book is returned late | System | S3, :40 |
| REQ-20 | Check in a returned copy by scanning its barcode; this ends the loan | Librarian | S4, :45-46 |
| REQ-21 | On check in, if someone holds the book, the copy goes to the hold shelf | Librarian, System | S4, :46 |
| REQ-22 | The desk lists overdue loans with member, title and days late | Librarian | S4, :48-49 |
| REQ-23 | Record a fine payment for a member by card number and amount | Librarian | S4, :51 |
| REQ-24 | Add a book with title, author and ISBN | Librarian | S5 Add book, :56 |
| REQ-25 | Add a copy of a book with a barcode | Librarian | S5 Add copy, :57 |
| REQ-26 | Withdraw a copy that is damaged or lost | Librarian | S5 Withdraw copy, :58 |
| REQ-27 | A copy on loan cannot be withdrawn | Librarian | S5, :58 |
| REQ-28 | Register a member with name, email and card number | Librarian | S5 Register member, :59 |
| REQ-29 | Borrow, place hold and renew are for signed-in members; the catalog is open to any visitor | Visitor, Member | S1 and S2/S3 titles, :11, :21, :29 |
| REQ-30 | The member whose hold is on the hold shelf can pick up the shelved copy, and it becomes a loan to them. Who performs it (Borrow or a desk action) is open: RQ-1 | Member or Librarian (RQ-1) | missing in the prototype: no pickup control on any screen; only the shelf state is shown (S3 note, :38; S4, :46). Raised by review F9 |

## Data seen in the prototype
| Data element | Where seen | Notes (type, format, rules shown) |
|---|---|---|
| Book: title, author, ISBN | S1, S2, S5 | ISBN example 978-0-00-000000-0 |
| Copy: barcode | S4, S5 | Physical copy of a book; can be withdrawn |
| Available copies | S1 | "2 of 3": available of total |
| Member: name, email, card number | S4, S5 | Card number identifies the member at payment |
| Loan: borrowed, due | S3 | Dates such as "1 May", "15 May"; 14 days |
| Renewal count | S3 note | Once only |
| Hold: position | S3 | Queue position, first come first served |
| Hold shelf | S3, S4 | Copy kept 3 days |
| Fine: total owed | S3 | Amount, 0.25 per day late; shown as 0.75 |
| Payment: member card, amount | S4 | No format shown |
| Overdue: member, title, days late | S4 | Integer days |

## Unknowns
| Unknown | What would settle it |
|---|---|
| Sign-in and roles (Q-1) | A decision from the user on identity handling |
| Hold eligibility and hold expiry (Q-2, Q-4) | User statement of the rules |
| Fine limits, currency, payment rules (Q-5, Q-6, Q-7, Q-11) | User statement of the rules |
| Renewal while overdue (Q-8) | User statement |
| Edit or remove for books and members (Q-9) | User statement |
| Uniqueness of ISBN, barcode and card number (Q-10) | User statement |
| Email content and sending rules | User statement |
| Who picks up a shelved hold (RQ-1) | User decision: Borrow by the holder, or a desk action |
| Backend stack, store, API style (profile Q-P1 to Q-P11) | User answers |
