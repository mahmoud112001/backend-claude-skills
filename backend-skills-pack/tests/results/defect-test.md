# Planted-defect test

Date: 2026-11-17 · Design: tests/defect-test/design/ (copy of fixture A) · Key: [defect-key.md](defect-key.md) · Review: tests/defect-test/design/07-review.md
Reviewer: design-reviewer, fresh context, Fable 5.2 (self-reported). Inputs: the copy, its brief and the default rulebook; told not to read tests/results/ or any fixture folder.
Review totals: High 6, Medium 1, Low 4. Verdict fail.

| Planted | Kind | Result | Finding id(s) |
|---|---|---|---|
| D1 | FK across bounded contexts | found (High) | F4 (DB-01) |
| D2 | Aggregate holds another aggregate | found (High) | F1 (TAC-01) |
| D3 | Command published as an event | found (High) | F2 (TAC-04) |
| D4 | Brief requirement REQ-18 uncovered | found (High, plus Medium) | F3 (query), F6 (endpoint; also a dangling `$ref` in 06-api.openapi.yaml I missed while planting), F7 (use case) |
| D5 | Endpoint creates a policy-created aggregate | found (High) | F5 (API-02) |

**5 of 5 found.** No planted defect was missed, so the gate passes.

Extra findings: 4 (all Low), 0 false positives as far as checked.
- F8: real extra defect. 01-strategic.md:82 still has a Fines/Membership "separate ways" row next to the customer-supplier row (verified by reading the line). It was left over in fixture A.
- F9 (FQ-6 vs AQ-11 defaults differ), F10 (REQ-30 missing from the Circulation subdomain row), F11 (wrong line citation): plausible real leftovers in fixture A, not verified line by line.
- Not counted as findings: the reviewer's notes that the README summary is stale and that "Fixed F<n>" notes cite review files that are absent. Both come from deleting the review folder.

Misses: none, so no fix is proposed.
