---
tags: [reuse-first]
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

In orders-svc I'm adding an export endpoint that needs URL-safe slugs from order titles like 'Cafe Order #12'. I'm about to write a slug function. Before I do, check whether we already have something, or whether I should add a library.
