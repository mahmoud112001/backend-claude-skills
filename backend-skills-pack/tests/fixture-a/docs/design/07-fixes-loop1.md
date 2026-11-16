# 07 Fixes (loop 1)

## Inputs
- [07-review-loop1.md](07-review-loop1.md) findings F1..F13 and open questions RQ-1..RQ-5.
- Most fixes were applied in the previous session (files edited after the review); this pass verified each by grep and closed the gaps.

## Decisions
- D7F-1 Every fix follows the review's proposed fix; no business choice was made. RQ-1..RQ-5 stay open with proposed defaults.
- D7F-2 07-review.md renamed to 07-review-loop1.md so the loop 2 reviewer writes a fresh 07-review.md; all references updated.

## Open questions
- RQ-1..RQ-5, listed in [00-state.md](00-state.md) and in the owning files (brief RQ-1; 06 RQ-2; 01 RQ-3; 02 Lending RQ-4; 02 Membership RQ-5).

## Fixes
| Id | Sev | Before this pass | Change (file: anchor) |
|---|---|---|---|
| F1 | High | done earlier | 01 D1-10, D1-12, context map rows Membership to Catalog/Lending/Fines; 02 Catalog D2-11 (CQ-7 closed); 05 CTX-map |
| F2 | High | done earlier | 03 D3-12; 03 Lending D3-L5, `lending.outbox.target_consumer` + ck_lending_outbox_target; 04 |
| F3 | High | done earlier | 03 D3-17..D3-20, `idempotency_record` in all four modules; 04; 06 D6-8, AQ-2 closed |
| F4 | Medium | done earlier | 02 Lending PlaceHold fails BorrowerUnknown; 06 placeHold `borrower-unknown`; lending yaml x-error-codes |
| F5 | Medium | done earlier | 02 Lending D2-11, FineStatus, RecordFineStatus order by accountVersion; 03 DQ-3 closed |
| F6 | Medium | done earlier | 02 Lending D2-15, LoanSlot state, GetBorrowRequest, LQ-12; 03 Lending D3-L3; 04; 06 getBorrowRequest, D6-20, AQ-1 closed |
| F7 | Medium | done earlier | lending yaml `Loan.barcode`; 06 D6-3; rule left as RQ-2 |
| F8 | Medium | partial | done earlier: 03 Lending D3-L6 job RepublishBookAvailability, 03 catalog.book_availability note. Now: 02 Catalog BookAvailability rebuild text points to the job (was "replay or ask Lending") |
| F9 | Medium | done earlier | brief D0-5, REQ-30 (source marked missing), RQ-1; no design change beyond 02 Lending LQ-13 |
| F10 | Medium | done earlier | membership yaml email maxLength 254 |
| F11 | Low | partial | done earlier: 02 Catalog D2-10, CQ-6 removed. Now: removed CQ-6/CQ-7/L1 from 00-state carried-forward list |
| F12 | Low | partial | done earlier: 05 edge `f2 -.->\|ref\| l3`. Now: 03 Fines REF line and 04 fines.fine label say `lending.loan` (were "Lending.BookCirculation") |
| F13 | Low | partial | done earlier: 02 Membership RQ-5, PersonName. Now: 03 member.name note cites RQ-5 proposed default |
| RQ-3, RQ-4 | n/a | not recorded in owners | Now: added to 01 Open questions (RQ-3) and 02 Lending Open questions (RQ-4) |

Totals: 13 of 13 fixed (9 done earlier, 4 partial and completed now); 0 moved to open questions beyond RQ-1..RQ-5 raised by the review.

## Lint after fixes
design_check.py lint: 1 finding, 0 High. L1 Medium TAC-04 (CopyPlacedOnHoldShelf) is the false positive review 1 rejected.

## Skill or agent bugs noticed
- design_check.py TAC-04 heuristic flags `<Noun><PastVerb><place suffix>` event names (CopyPlacedOnHoldShelf) as not past tense. False positive, seen twice (phase 2 and phase 7).
- design-review-fix gives no rule for where a fixer logs per-finding status, and the orchestrator had no fix log; after a crash the fix state had to be rebuilt by grep. Proposed: require a 07-fixes-loop<k>.md written as fixes land.
- The reviewer writes 07-review.md on every loop; nothing says to keep the loop 1 file, so loop 2 would overwrite it.
