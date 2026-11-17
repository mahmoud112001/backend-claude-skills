# Trigger tests (sonnet, --setting-sources project, only the pack installed)

Cases: 54. Failures: 1. Errors (no verdict): 9.

| Skill | Expect | Result | Invoked | Prompt |
|---|---|---|---|---|
| api-endpoints | yes | PASS | Skill(api-endpoints) | Our tactical design for the Orders context has the commands PlaceOrder and CancelOrder ... |
| api-endpoints | yes | PASS | Skill(api-endpoints) | Design the API contract for the commands and queries in our DDD tactical design: operat... |
| api-endpoints | no | PASS | - | Implement the POST /orders handler in Express with request validation. |
| architecture-conformance | yes | PASS | Skill(architecture-conformance) | Check whether the code in src/ follows the architecture rules written in ARCHITECTURE.m... |
| architecture-conformance | yes | PASS | Skill(architecture-conformance) | Does my diff against main break any of the layering rules we wrote in docs/ddd/service-... |
| architecture-conformance | no | PASS | - | Explain in two sentences what hexagonal architecture is. |
| backend-design-team | yes | PASS | /backend-design-team | /backend-design-team start prototype/ |
| backend-design-team | yes | PASS | /backend-design-team | /backend-design-team resume |
| backend-design-team | no | PASS | - | Run a full DDD backend design team on my prototype: profile, strategic and tactical des... |
| db-design-erd | yes | PASS | Skill(db-design-erd) | Phase 3 of the backend design: map the aggregates of our tactical design to PostgreSQL ... |
| db-design-erd | yes | PASS | Skill(db-design-erd) | Turn our DDD aggregates into a database design per module and an ER diagram. Design only. |
| db-design-erd | no | PASS | - | Write an Alembic migration that adds a nullable phone column to the users table. |
| ddd-strategic | yes | PASS | Skill(ddd-strategic) | From this brief, do the DDD strategic design: subdomains (core, supporting, generic), b... |
| ddd-strategic | yes | PASS | Skill(ddd-strategic) | Phase 1 of a backend design for a used-goods marketplace: identify the bounded contexts... |
| ddd-strategic | no | PASS | - | Write a Java class for an Order entity with getters and setters. |
| ddd-tactical | yes | PASS | Skill(ddd-tactical) | For the Booking bounded context, define the aggregates with their invariants, the comma... |
| ddd-tactical | yes | PASS | Skill(ddd-tactical) | Phase 2 tactical design for the Payments context: entities, value objects, domain event... |
| ddd-tactical | no | PASS | - | Which bounded contexts should a food delivery platform have? Just list them. |
| dead-code-cleaner | yes | PASS | /dead-code-cleaner | /dead-code-cleaner report src |
| dead-code-cleaner | yes | PASS | /dead-code-cleaner | /dead-code-cleaner report |
| dead-code-cleaner | no | PASS | - | Find the unused functions and the duplicated code in this repo and delete them. |
| design-diagrams | yes | PASS | Skill(design-diagrams) | Phase 5 of the backend design: draw the use-case diagrams per bounded context, the data... |
| design-diagrams | yes | PASS | Skill(design-diagrams) | From our DDD design files, draw the cross-context flows of commands, events and policie... |
| design-diagrams | no | PASS | - | Draw a Mermaid pie chart of our monthly costs: rent 50, food 30, other 20. |
| design-docs-organizer | yes | PASS | Skill(design-docs-organizer) | Phase 8 of the backend design: move the design files into phase folders, fix the links ... |
| design-docs-organizer | yes | PASS | Skill(design-docs-organizer) | Organize the numbered backend design files (00-project-brief.md to 07-review.md) into f... |
| design-docs-organizer | no | PASS | - | Write a README for a small Python library that parses dates. |
| design-review-fix | yes | PASS | Skill(design-review-fix) | Phase 7: independently review our backend design files against the prototype and the br... |
| design-review-fix | yes | PASS | Skill(design-review-fix) | Review the backend design documents (strategic, tactical, database, API) for DDD mistak... |
| design-review-fix | no | PASS | - | Review this Python function for bugs: def add(a, b): return a - b |
| dispatching-parallel-agents | yes | FAIL | - | Three unrelated test files fail for different reasons: auth.test.ts (token expiry), bil... |
| dispatching-parallel-agents | yes | PASS | Skill(dispatching-parallel-agents) | I have four independent subsystems to investigate, with no shared files. Split the work... |
| dispatching-parallel-agents | no | PASS | - | Fix the single failing test in utils.test.ts; it expects trim() to remove tabs. |
| model-router | yes | PASS | Skill(model-router) | Which Claude model alias should I use for bulk file renaming versus a security review, ... |
| model-router | yes | PASS | Skill(model-router) | Should my new subagent run on haiku or opus, and where do I set that? |
| model-router | no | PASS | - | Write a haiku about autumn rain. |
| project-understanding | yes | PASS | Skill(project-understanding) | Phase 0 of a backend design: read the prototype in prototype/ and write the draft proje... |
| project-understanding | yes | PASS | Skill(project-understanding) | Read our UI mockups and README and draft project-profile.md, marking each field as dete... |
| project-understanding | no | PASS | - | Write a CONTRIBUTING.md that explains how to open a pull request. |
| reuse-first | yes | PASS | Skill(reuse-first) | I need a helper that turns titles into URL slugs in our Node app. Before writing it, ch... |
| reuse-first | yes | PASS | Skill(reuse-first) | We need retry with exponential backoff for HTTP calls in our Python service. Should we ... |
| reuse-first | no | ERROR | You've hit your 5-hour limit · resets 2:10am (Africa/Cairo) | Rename the variable usr to user in app.py. |
| skill-creator | yes | PASS | You've hit your 5-hour limit · resets 2:10am (Africa/Cairo) | /skill-creator create a skill that formats SQL files |
| skill-creator | yes | PASS | You've hit your 5-hour limit · resets 2:10am (Africa/Cairo) | /skill-creator improve the description of the reuse-first skill |
| skill-creator | no | ERROR | You've hit your 5-hour limit · resets 2:10am (Africa/Cairo) | Create a new Claude Code skill that summarizes git logs. |
| skill-security-audit | yes | PASS | You've hit your 5-hour limit · resets 2:10am (Africa/Cairo) | /skill-security-audit https://github.com/example/some-skill |
| skill-security-audit | yes | PASS | You've hit your 5-hour limit · resets 2:10am (Africa/Cairo) | /skill-security-audit .claude/skills/reuse-first |
| skill-security-audit | no | ERROR | You've hit your 5-hour limit · resets 2:10am (Africa/Cairo) | Is this third-party skill safe to install? Audit it for me: https://github.com/example/... |
| test-driven-development | yes | ERROR | You've hit your 5-hour limit · resets 2:10am (Africa/Cairo) | Implement a function that validates IBAN numbers in our Python project. |
| test-driven-development | yes | ERROR | You've hit your 5-hour limit · resets 2:10am (Africa/Cairo) | Fix the bug where submit_form accepts an empty email address. |
| test-driven-development | no | ERROR | You've hit your 5-hour limit · resets 2:10am (Africa/Cairo) | Add a .gitignore entry for .env files. |
| verification-before-completion | yes | ERROR | You've hit your 5-hour limit · resets 2:10am (Africa/Cairo) | I've finished the refactor. Confirm that everything passes, then tell me it's done. |
| verification-before-completion | yes | ERROR | You've hit your 5-hour limit · resets 2:10am (Africa/Cairo) | Is the login bug fixed now? If the tests pass, say it's complete so I can open the PR. |
| verification-before-completion | no | ERROR | You've hit your 5-hour limit · resets 2:10am (Africa/Cairo) | What does the -I flag of the Python interpreter do? |
