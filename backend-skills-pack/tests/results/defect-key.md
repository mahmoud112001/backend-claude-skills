# Planted-defect answer key

Written 2026-11-17, after tests/defect-test/design/07-review.md was saved. Copy of tests/fixture-a/docs/design/ (fixture A unchanged).
Prep: deleted review/, 00-state.md, .organize-manifest.json; removed "(07 review)", "(F3)/(F6)" and "(07 RQ-1, F9)" from open-question rows (06-api.md AQ-1, AQ-2, RQ-2; 01-strategic.md RQ-3; 02-tactical-lending.md RQ-4, LQ-13); removed README rows linking deleted files. Decisions and Inputs lines citing the old review were left as they were.

| Id | Kind | File | Section | What I changed |
|---|---|---|---|---|
| D1 | FK across bounded contexts | data/03-db-design-fines.md:53 | `fines.fine` keys | `REF loan_id -> lending.loan (id only, no FK)` became `FK loan_id -> lending.loan(loan_id) ON DELETE RESTRICT` |
| D2 | Aggregate holds another aggregate | tactical/02-tactical-fines.md:39, :44 | Aggregates; Entities | Account `Contains` gained `Member (Membership aggregate)` and lost `memberId` from References; Account entity field `memberId` became `member (Member)` |
| D3 | Command published as an event | tactical/02-tactical-fines.md:63 | Domain events | Added integration event `SuspendBorrowing` (imperative) from ChargeLateFine to Lending |
| D4 | Brief requirement with no coverage (REQ-18) | api/06-api.md (Operations, Errors), api/06-api.openapi-fines.yaml, diagrams/05-diagrams.md, tactical/02-tactical-fines.md | Operations; contract path; UC-Fines; Queries | Removed `getMyFines` row, the `/v1/members/me/fines` path and header mention, the GMF use case node and edge, the GetMyFines query row; error row `account-not-found` no longer lists getMyFines |
| D5 | Endpoint creates a policy-created aggregate | api/06-api.md:93, Not exposed | Operations | Added `openAccount POST /v1/fine-accounts` (Librarian) mapping to OpenAccount; removed the OpenAccount row from Not exposed |
