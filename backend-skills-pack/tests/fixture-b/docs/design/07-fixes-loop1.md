# 07 Fixes, loop 1

Review: [07-review-loop1.md](07-review-loop1.md) · Loop 1 totals: High 1, Medium 6, Low 7. Low findings were not sent for fixing.

| Finding | Severity | Fixed by (agent) | Where changed |
|---|---|---|---|
| F1 | High | tactical-designer (pur), db-designer, diagram-writer | 02-tactical-purchasing.md D2-13 (:25), policies :84-85, read models :91-93; 03-db-design-purchasing.md :146-149 (`pur_inbox` PK event_id + consumer); 03-db-design.md D3-9 (:22); 04-erd.md D4-6; 05-diagrams-flows.md FLOW-1, FLOW-6 |
| F2 | Medium | tactical-designer (pur) | 02-tactical-purchasing.md D2-9 (:21), D2-14 (:26) |
| F3 | Medium | db-designer, diagram-writer | 03-db-design-purchasing.md :114 (`source_event_id`); 04-erd.md D4-5 |
| F4 | Medium | tactical-designer (pur), db-designer | 02-tactical-purchasing.md D2-10 (:22), D2-15, :74-76; 03-db-design-purchasing.md :131, :136, :145-147, D3-P4; 03-db-design.md D3-8 |
| F5 | Medium | project-reader, strategic-designer, tactical-designer (pur), api-designer | 00-project-brief.md REQ-21 (:69), D0-5, Q9; 01-strategic.md D1-10, :52; 02-tactical-purchasing.md :90, D2-16; 06-api.md :77, D6-17. Filters moved to open questions (brief Q9, pur Q2-10) |
| F6 | Medium | tactical-designer (pur), db-designer, diagram-writer | 02-tactical-purchasing.md :54, :57, :74-79, D2-17; 03-db-design-purchasing.md :33; 04-erd.md D4-7 |
| F7 | Medium | tactical-designer (stk), api-designer | 02-tactical-stock.md D2-10 (:21), D2-14; 06-api.md :107, D6-18 |
