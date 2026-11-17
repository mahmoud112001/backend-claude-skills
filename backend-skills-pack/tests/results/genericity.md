# Genericity check (S4)

Command: `python3 -I tests/genericity-check.py --allow tests/genericity-allow.tsv` · Date: 2026-11-17
Scope: skills/ and agents/ (examples/ and tests/ skipped). Terms: project names (i-fikra, fikra, node-playground), domain words (Orders, Billing, Enrollment, Subscription, Offers, LiveSession, Marketplace, Wallet; capitalised), absolute paths (drive letters, /home/, /Users/), usernames.

## First run: 1 hit
- skills/backend-design-team/SKILL.md:44 [domain] 'Order': judged generic example ("Order matters: aggregates decide the tables"), allowed. Leaks found: 0. Fixes: none needed.
- Extra case-insensitive sweep of the domain words: 26 lowercase hits, all generic English ("order", "reading order", "offer to sell" in an Apache licence). No leak.

## Final output
```
ALLOWED skills/backend-design-team/SKILL.md:44 [domain] 'Order': generic English ("Order matters"), not the Orders domain
total hits: 1, allowed: 1, unexplained: 0
exit=0
```
