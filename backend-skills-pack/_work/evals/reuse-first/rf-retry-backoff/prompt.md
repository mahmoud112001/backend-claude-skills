---
tags: [reuse-first]
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

orders-svc calls the broker over HTTP (src/orders/infrastructure/broker.py). I want retries with exponential backoff. Should I add tenacity or backoff, or write my own?
