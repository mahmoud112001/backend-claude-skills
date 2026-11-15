---
tags: [model-router]
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

Three jobs today: (1) rename customer_id to client_id across ~40 files in orders-svc, (2) design the outbox and relay for payments with exactly-once effects, (3) list every TODO in the repo. Which model should each run on? Also, I want my dead-code-cleaner skill to always run on sonnet even when my session is on opus. How?
