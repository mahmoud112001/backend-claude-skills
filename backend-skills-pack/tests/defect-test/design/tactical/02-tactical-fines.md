# 02 Tactical design: Fines

## Inputs
- docs/design/project-profile.md: TypeScript with NestJS, PostgreSQL, modular monolith (one module per context), in-process events plus a transactional outbox per module drained by a background worker, UUIDv7 ids, RFC 9457 errors. No project rules file.
- docs/design/01-strategic.md: Fines row (owns REQ-18, REQ-19, REQ-23), context map rows Membership -> Fines (MemberRegistered), Lending -> Fines (LoanEnded), Fines -> Lending (FineBalanceChanged), Catalog/Fines and Fines/Membership separate ways; Published language of all contexts; Ubiquitous language (Fine, Days late in Fines, Balance, Account, Payment); D1-4, D1-5, D1-6, SQ-1.
- docs/design/00-project-brief.md: REQ-18, REQ-19, REQ-23; Actors (Member, Librarian, System); Q-5, Q-6, Q-7, Q-11, Q-10.
- Rulebook: .claude/skills/backend-design-team/references/default-rulebook.md.

## Decisions
- D2-1 One aggregate, Account, per member. It holds the member's fines and payments, so "balance = fines minus payments" (REQ-18) and the payment check (Q-7) are consistent in one transaction. Why: a payment is validated against the balance, and both fines and payments change it; splitting them would make the balance eventually consistent with itself. Proposed.
- D2-2 Fine and Payment are entities inside Account (they have ids and are listed to the member and desk), not separate aggregates. Their lifecycle is the account's; they are never edited after they are recorded (append-only ledger). Why: TAC-11 smallness is acceptable for one small library (brief Goals); see FQ-6 if histories grow. Proposed.
- D2-3 Account is created by policy from the Membership integration event MemberRegistered (context map Membership -> Fines), copying member id and card number. Fines never calls Membership, except the API-guard query ResolveCurrentMember (01 D1-10, D2-10). Source: 01 context map; mechanism proposed.
- D2-4 A fine is created only from the Lending integration event LoanEnded (D1-6, REQ-19). Fines computes days late and the amount; Lending never computes money (D1-6).
- D2-5 At most one fine per loan id per account. Why: LoanEnded can be delivered more than once by the outbox worker; the loan id is the natural idempotency key. Proposed.
- D2-6 Fine amount = 0.25 x days late, in the library currency (REQ-19). Days late uses the proposed default of Q-11 (calendar days after the due date). The rate 0.25 is from REQ-19; the currency and any cap stay open (Q-5).
- D2-7 Money is a value object with an exact decimal amount (minor units) and a currency; never floating point. Proposed.
- D2-8 Every change of balance (fine charged, payment recorded) emits the integration event FineBalanceChanged in the same transaction through the Fines outbox (profile events_messaging, 01 context map). Payload adds balance amount and the account version, so Lending can drop stale or out-of-order deliveries. Proposed.
- D2-9 A loan returned on time produces no fine and no event; ChargeLateFine is then a no-op. Proposed.
- D2-10 GetMyFines resolves the signed-in member through the Membership public operation ResolveCurrentMember at the API layer (01 Published language), then reads the Account by member id. Proposed.
- D2-11 RecordFinePayment finds the account by card number (REQ-23). Card number uniqueness follows the proposed default of Q-10. Proposed.
- Fixed F3 (loop 2): D2-3 now allows the one exception, the API-guard query ResolveCurrentMember (01 D1-10, D2-10), so it no longer contradicts D2-10 and the NotLibrarian guard.

## Open questions
| Id | Question | Why it matters | Proposed default |
|---|---|---|---|
| FQ-1 | Is there a cap on a single fine or on the balance, and what is the currency? (brief Q-5) | ChargeLateFine amount; Money currency. | No cap; one currency set in configuration. |
| FQ-2 | Can a payment be partial, and can it exceed the balance? (brief Q-7) | RecordFinePayment failures. | Partial allowed; amount must be above zero; overpayment rejected. |
| FQ-3 | What counts as a day late: grace period, closing days, which time zone? (brief Q-11) | Fine amount. | Calendar days after the due date, in the library's configured time zone; no grace. |
| FQ-4 | Does "owe fines" mean any balance above zero? (brief Q-6) | The owesFines flag in FineBalanceChanged drives REQ-9 in Lending. | Yes, any balance above zero. |
| FQ-5 | What if LoanEnded arrives before MemberRegistered has opened the account? | ChargeLateFine would find no account. | Retry with backoff; alert after the retry limit. Not expected, since a member must be registered before borrowing. |
| FQ-6 | Should the member and the desk see each fine and payment, or only the total? | REQ-18 shows only the total; affects GetMyFines and the Account size. | Total plus the list of fines (book-free: loan id, days late, amount, date). |
| FQ-7 | Can a librarian waive or correct a fine, or reverse a wrong payment? | Not shown in the prototype; an error today cannot be undone. | Out of scope for now. |
| FQ-8 | Should the desk see a member's balance before taking payment (lookup by card number)? | S4 shows only card number and amount fields. | Not required; RecordFinePayment returns the new balance. |
| FQ-9 | Is a payment amount restricted to the currency's minor unit (for example cents)? | Money validation. | Yes; reject amounts with more decimals than the currency allows. |

## Aggregates
| Aggregate | Root entity | Contains (entities, value objects) | References by id | Invariants (REQ) | Created by |
|---|---|---|---|---|---|
| Account | Account | Fine, Payment, Money, CardNumber, Member (Membership aggregate) | loanId (Lending Loan) | Balance equals the sum of fines minus the sum of payments and is never negative (REQ-18, REQ-23; never negative follows FQ-2 proposed default). A fine is 0.25 per day late, added only for a late return (REQ-19; day definition FQ-3). At most one Fine per loanId (D2-5, proposed). A payment amount is above zero and not above the balance (REQ-23; limits are FQ-2 proposed default). Only a Librarian records a payment (REQ-23). Exactly one Account per memberId and per card number (D2-3, Q-10 proposed default). The borrowing block in Lending (REQ-9) is eventually consistent: FineBalanceChanged then a Lending policy (D1-5, SQ-1). | policy:OpenAccountOnMemberRegistered |

## Entities and value objects
| Name | Kind (entity / value object) | Belongs to | Fields | Rules |
|---|---|---|---|---|
| Account | entity | Account | accountId (UUIDv7), member (Member), cardNumber, balance (Money), version, openedAt | Root. balance is derived from fines and payments and kept with them in one transaction (D2-1). version increments on every change (D2-8). |
| Fine | entity | Account | fineId (UUIDv7), loanId, dueDate, returnedAt, daysLate, amount (Money), chargedAt | Append-only; never edited (D2-2). daysLate > 0 (REQ-19). amount = 0.25 x daysLate (REQ-19). loanId unique within the account (D2-5). |
| Payment | entity | Account | paymentId (UUIDv7), amount (Money), recordedBy (librarian identity id), recordedAt | Append-only (D2-2). amount > 0 and not above the balance at recording time (FQ-2 proposed). |
| Money | value object | Account | amount (exact decimal), currency | Immutable; replaced, never edited (D2-7). No floating point. Currency from configuration (FQ-1). |
| CardNumber | value object | Account | value | Immutable copy from MemberRegistered (D2-3). Unique across accounts (Q-10 proposed default). |

## Commands
| Command | Aggregate | Trigger | Emits | Fails when | REQ |
|---|---|---|---|---|---|
| OpenAccount | Account | policy:OpenAccountOnMemberRegistered | none | An account already exists for the memberId (treated as a duplicate delivery and ignored, D2-5 idempotency); CardNumberTaken: another account has the card number (Q-10 proposed). | REQ-23 |
| ChargeLateFine | Account | policy:ChargeFineOnLoanEnded | FineCharged, FineBalanceChanged (only when days late > 0, D2-9) | AccountNotFound: no account for memberId (retry, FQ-5); a fine for the loanId already exists (duplicate delivery, ignored, D2-5). | REQ-19 |
| RecordFinePayment | Account | actor:Librarian | PaymentRecorded, FineBalanceChanged | AccountNotFound: no account for the card number; InvalidPaymentAmount: amount not above zero or wrong precision (FQ-2, FQ-9 proposed); PaymentExceedsBalance: amount above the balance (FQ-2 proposed); NotLibrarian: caller is not a Librarian (REQ-23). | REQ-23 |

## Domain events
| Event | Emitted by | Kind | Payload | Consumers |
|---|---|---|---|---|
| FineCharged | ChargeLateFine | internal | accountId, memberId, fineId, loanId, daysLate, amount, currency, chargedAt | none (audit; stays in Fines) |
| PaymentRecorded | RecordFinePayment | internal | accountId, memberId, paymentId, amount, currency, recordedBy, recordedAt | none (audit; stays in Fines) |
| FineBalanceChanged | ChargeLateFine, RecordFinePayment | integration | memberId, owesFines (balance > 0, FQ-4), balanceAmount, currency, accountVersion, occurredAt | Lending (context map Fines -> Lending, REQ-9) |
| SuspendBorrowing | ChargeLateFine | integration | memberId, accountVersion, occurredAt | Lending (Lending blocks the member's borrowing, REQ-9) |

## Policies
| Policy | When (event) | Then (command) | Context | On failure |
|---|---|---|---|---|
| OpenAccountOnMemberRegistered | MemberRegistered (Membership integration event) | OpenAccount | Fines, consuming Membership via context map Membership -> Fines | Duplicate delivery: ignore (inbox dedup by event id). CardNumberTaken: alert operators; no retry. Other errors: retry with backoff, then alert. |
| ChargeFineOnLoanEnded | LoanEnded (Lending integration event) | ChargeLateFine | Fines, consuming Lending via context map Lending -> Fines | Duplicate delivery: ignore (inbox dedup plus one fine per loanId). AccountNotFound: retry with backoff, then alert (FQ-5). Other errors: retry, then alert; never drop silently. |

## Queries and read models
| Query / read model | Kind (query / read model / cache) | Source | Rebuild or invalidation | Staleness | REQ |
|---|---|---|---|---|---|

## Out of scope
| REQ | Why |
|---|---|
| none | All Fines REQs (REQ-18, REQ-19, REQ-23) map to a command or query. |
