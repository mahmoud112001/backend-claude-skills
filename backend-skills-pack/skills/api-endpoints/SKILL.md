---
name: api-endpoints
description: Phase 6 of a backend design. Maps actor-triggered commands and queries to operations in the profile's API style (REST, GraphQL, gRPC, async...), with errors, idempotency, pagination and actors. Writes 06-api.md, plus a contract file only if the profile asks. Not for implementing handlers.
model: opus
allowed-tools: Read Glob Grep Write Edit
---

# api-endpoints

Model: opus. The API is the contract other teams build against: wrong idempotency or errors become production incidents.

Source: the rules adapt api-design (ECC, MIT), cut to design rules with no framework code, and contract-first (ECC, MIT), which contributes "one authoritative contract artifact" and the change protocol.

Read first: `project-profile.md` (api_style, api_contract_file, error_format, naming_convention, id_convention). From each `02-tactical-*.md` read Commands, Queries and read models, and Aggregates (Created by). Read the Decisions in 03, and the project rules file on API matters if one exists. Style-specific rules are in [references/api-styles.md](references/api-styles.md): read only the section for the profile's style.

## Method

1. **Only actor-triggered commands become command operations.** A command with `policy:` trigger is **never** exposed, and neither is the creation of an aggregate whose `Created by` is a policy. If the prototype shows a screen that seems to need one, raise an open question; do not add the operation.
2. **Every query and read model** an actor uses becomes a query operation. A list query is paginated with a stable sort, and states its filters.
3. **One operation, one command or query.** The name follows the profile's naming convention. The mapping is written in the `Maps to` column, using the exact 02 name.
4. **Errors.** Each command operation lists its domain errors, taken from `Fails when` in 02 and from the invariants, plus validation, not-found, conflict (concurrency and version) and forbidden. Use the profile's `error_format` exactly. If it is silent, write an open question with a proposed format.
5. **Idempotency.** Every command operation states one of: a natural key (with which field), a client idempotency key (with how long it is kept, and what a replay returns), or "safe to retry because <reason>".
6. **Actors and authorization.** Each operation names the actor or role allowed to call it, from the trigger in 02. An authorization rule the brief does not show is an open question.
7. **Context boundaries.** An operation exposes only its own context's model. Data owned by another context comes from a read model in this context or from that context's published operations.
8. **Versioning and change.** State the versioning approach the API style uses. A breaking change to a published operation needs a new version or a new operation (from contract-first).
9. **Contract file.** Only when `api_contract_file` is not `none`: write `06-api.<ext>` (for example `06-api.openapi.yaml`, `06-api.graphql`, `06-api.proto`) as the single authoritative contract, generated from the table in 06. `06-api.md` points to it. Never keep two sources that disagree.

## Output: `06-api.md` (at most 300 lines; split into `06-api-<context>.md` if longer)

```markdown
# 06 API design
## Inputs / ## Decisions / ## Open questions
## Conventions        (style, naming, ids, pagination, versioning, error format: each cited from the profile)
## Operations
| Operation | Signature | Kind | Maps to | Actor | Idempotency | Errors | REQ |
## Errors
| Code | Meaning | Raised by | Retry? |
## Not exposed
| Command | Why (policy-triggered / internal) |
```

Format rules (a script reads them):
- The Signature is in the profile's style: `POST /resources`, `mutation createThing`, `rpc CreateThing`, `publish thing.requested`, and so on.
- Kind is `command` or `query`. Maps to is the exact 02 name. Idempotency and Errors are never empty for commands.
- REQ lists ids. Every REQ that has an actor-triggered command or a query appears in at least one row.

## Self-check (put this in your reply)

API-01 to API-08, DOC-01 to DOC-04, and the project rules on the API. Mark each PASS or FAIL, with evidence. Fix MUST failures before you reply.

Reply in at most 300 words: the files, the operation counts (command and query), the commands deliberately not exposed, the open questions (top 3), and the self-check.

## Fix mode

When the prompt gives findings, fix only those findings, and add `Fixed F<n>` under Decisions. Business decisions go to Open questions.
