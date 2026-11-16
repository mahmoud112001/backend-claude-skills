# 05 Diagrams: key flows

Part of [05-diagrams.md](05-diagrams.md).

## Inputs
- docs/design/project-profile.md: diagram_format = mermaid; events_messaging = in-process domain events plus a transactional outbox per module, no broker.
- docs/design/01-strategic.md: Context map.
- docs/design/02-tactical-catalog.md, 02-tactical-lending.md, 02-tactical-fines.md, 02-tactical-membership.md: Commands, Domain events, Policies, Queries and read models.

## Decisions
- D5-6 Flows drawn: member registration, add book, borrow, check in with hold, hold shelf expiry, fine payment. Each crosses a context or sits behind a core-subdomain REQ (Circulation).
- D5-7 Event names in flows use the `Emits` and `Consumers` columns of 02. Outbox is shown as a participant per emitting module, per the profile.
- Fixed L1: 05-diagrams.md was 311 lines (over 300). Key flows moved here unchanged; the main file links to this part.

## Open questions
| Id | Question | Proposed default |
|---|---|---|
| DG-3 | 02 names no operation for the call to the email service, only SendHoldReadyEmail. | Drawn as a participant EmailService with a "send email" message (01 D1-8). |

## Key flows

### FLOW-1 RegisterMember
Drawn from: 02-tactical-membership.md Commands, Domain events; 02-tactical-lending.md and 02-tactical-fines.md Policies; 01 Context map.
```mermaid
sequenceDiagram
  actor Librarian
  participant M as Member
  participant MO as membership.outbox
  participant L as Lending
  participant F as Fines
  Librarian->>M: RegisterMember
  alt not-librarian, invalid-name, invalid-email, invalid-card-number, card-number-taken, email-taken
    M-->>Librarian: error
  else registered
    M->>MO: MemberRegistered
    MO->>L: RegisterBorrowerOnMemberRegistered
    L->>L: RegisterBorrower on Borrower
    MO->>F: OpenAccountOnMemberRegistered
    F->>F: OpenAccount on Account
    Note over F: CardNumberTaken is alerted, no retry
  end
```

### FLOW-2 AddBook
Drawn from: 02-tactical-catalog.md Commands, Domain events; 02-tactical-lending.md Policies.
```mermaid
sequenceDiagram
  actor Librarian
  participant B as Book
  participant CO as catalog.outbox
  participant L as BookCirculation
  Librarian->>B: AddBook
  alt TitleMissing, AuthorMissing, InvalidIsbn, DuplicateIsbn, NotLibrarian
    B-->>Librarian: error
  else added
    B->>CO: BookAdded
    CO->>L: OpenCirculationOnBookAdded
    L->>L: OpenBookCirculation
  end
```

### FLOW-3 BorrowBook
Drawn from: 02-tactical-lending.md Commands, Domain events, Policies, Aggregates (REQ-5 to REQ-10, Circulation core subdomain).
```mermaid
sequenceDiagram
  actor Member
  participant BO as Borrower
  participant LO as lending.outbox
  participant BC as BookCirculation
  participant FS as fines.outbox
  Note over BO,FS: FineBalanceChanged from Fines keeps FineStatus current
  FS->>BO: UpdateFineBlockOnBalanceChanged then RecordFineStatus
  Member->>BO: BorrowBook
  alt BorrowerUnknown, BookUnknown, NoCopyAvailable, OwesFines, LoanLimitReached, LoanForBookExists
    BO-->>Member: error
  else slot reserved
    BO->>LO: LoanSlotReserved
    LO->>BC: LendCopyOnSlotReserved then LendCopy
    alt copy available or on shelf for this member
      BC->>LO: LoanStarted and BookAvailabilityChanged
    else no copy
      BC->>LO: LoanRefused
      LO->>BO: CancelSlotOnLoanRefused then CancelLoanSlot
    end
  end
```

### FLOW-4 CheckInCopy
Drawn from: 02-tactical-lending.md Commands, Domain events, Policies; 02-tactical-fines.md Policies; 02-tactical-catalog.md Queries and read models (REQ-16, REQ-17, REQ-19, REQ-20, REQ-21).
```mermaid
sequenceDiagram
  actor Librarian
  participant BC as BookCirculation
  participant LO as lending.outbox
  participant BO as Borrower
  participant F as Account
  participant C as BookAvailability
  participant HN as HoldReadyNotification
  participant E as EmailService
  Librarian->>BC: CheckInCopy
  alt CopyNotFound, CopyNotOnLoan
    BC-->>Librarian: error
  else loan ended
    BC->>LO: LoanEnded
    LO->>BO: ReleaseSlotOnLoanEnded then ReleaseLoanSlot
    LO->>F: ChargeFineOnLoanEnded then ChargeLateFine
    alt AccountNotFound
      F-->>LO: retry with backoff, then alert
    else days late above 0
      F->>F: FineCharged and FineBalanceChanged
    end
    BC->>LO: BookAvailabilityChanged
    LO->>C: projection upsert
    opt a hold is Waiting
      BC->>LO: CopyPlacedOnHoldShelf
      LO->>HN: NotifyHolderOnHoldShelf then SendHoldReadyEmail
      alt EmailServiceUnavailable
        HN-->>LO: retry with backoff, hold stays on shelf
      else sent
        HN->>E: send email
        HN->>HN: HoldReadyEmailSent
      end
    end
  end
```

### FLOW-5 ExpireShelvedHold
Drawn from: 02-tactical-lending.md Policies, Commands, Decisions D2-8 (REQ-17).
```mermaid
sequenceDiagram
  participant BC as BookCirculation
  participant LO as lending.outbox
  BC->>LO: CopyPlacedOnHoldShelf, deliver not before pickupDeadline
  LO->>BC: ExpireHoldOnShelfDeadline then ExpireShelvedHold
  alt hold no longer OnShelf, or deadline not passed
    BC->>BC: no-op
  else expired
    BC->>LO: HoldExpired
    BC->>LO: CopyPlacedOnHoldShelf for next hold, or BookAvailabilityChanged
  end
```

### FLOW-6 RecordFinePayment
Drawn from: 02-tactical-fines.md Commands, Domain events; 02-tactical-lending.md Policies (REQ-9, REQ-23).
```mermaid
sequenceDiagram
  actor Librarian
  participant F as Account
  participant FO as fines.outbox
  participant BO as Borrower
  Librarian->>F: RecordFinePayment
  alt AccountNotFound, InvalidPaymentAmount, PaymentExceedsBalance, NotLibrarian
    F-->>Librarian: error
  else recorded
    F->>F: PaymentRecorded
    F->>FO: FineBalanceChanged
    FO->>BO: UpdateFineBlockOnBalanceChanged then RecordFineStatus
    Note over BO: BorrowerUnknown retries, older events ignored
  end
```
