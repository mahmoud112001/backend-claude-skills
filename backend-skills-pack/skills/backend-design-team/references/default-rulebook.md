# Default design rulebook

Generic DDD and backend design rules, used by every phase and by the reviewer.
The project's own rules file (named in `project-profile.md`) overrides any rule here.
A conflict is recorded in the profile's "Rule overrides" table and reported to the user, never resolved silently.

Levels: a broken **MUST** is High and blocks the gate. A broken **SHOULD** is Medium: it is recorded and does not block.
The Check column says how a rule is verified: `script` means `design_check.py` checks it, `review` means a reader judges it.

## Documents (all artifacts)

| Id | Level | Rule | Check |
|---|---|---|---|
| DOC-01 | MUST | Each artifact starts with `## Inputs`, `## Decisions` and `## Open questions`, and has at most 300 lines. A larger one is split by context or module. | script |
| DOC-02 | MUST | Each statement taken from the prototype or brief cites its source (`REQ-n`, file, screen). Anything else is marked *proposed*. | review: sample 10 statements |
| DOC-03 | MUST | A business choice the inputs do not settle (prices, limits, durations, who may do what) goes to Open questions with a proposed default, never into the design as fact. | review |
| DOC-04 | MUST | A name is spelled the same in every artifact: an aggregate, command, event, table or operation. | script (cross-reference) + review |
| DOC-05 | MUST | Relative links between artifacts resolve. | script (phase 8) |
| DOC-06 | SHOULD | Every decision has an id (`D<phase>-<n>`) and one line of why. | review |

## Strategic design (01)

| Id | Level | Rule | Check |
|---|---|---|---|
| STR-01 | MUST | Every subdomain is classified core, supporting or generic, with a reason. | script: Type column filled |
| STR-02 | MUST | Every requirement (`REQ-n` in the brief) is owned by exactly one bounded context. | script |
| STR-03 | MUST | Every pair of contexts that exchanges data or calls has a context-map row naming the relationship (partnership, shared kernel, customer-supplier, conformist, anticorruption layer, open host service / published language, separate ways) and the integration mechanism. | script: rows exist + review |
| STR-04 | MUST | Each context has ubiquitous-language entries. A term with different meanings in two contexts is listed in both, and the difference is stated. | script: table exists + review |
| STR-05 | SHOULD | Contexts are cut where language or rules change, not one per entity or table. | review |
| STR-06 | SHOULD | Contexts map to deployables as the profile's architecture style says (for example, one module per context in a modular monolith). | review |

## Tactical design (02)

| Id | Level | Rule | Check |
|---|---|---|---|
| TAC-01 | MUST | An aggregate never contains another aggregate. It refers to other aggregates by id only. | script: Contains vs aggregate names |
| TAC-02 | MUST | Each invariant is enforced inside one aggregate. A rule that spans aggregates is eventually consistent (an event plus a policy), and the artifact says so. | review |
| TAC-03 | MUST | A command changes at most one aggregate instance per transaction. | review |
| TAC-04 | MUST | A domain event is a fact in the past tense (`<Noun><PastVerb>`) and never asks for an action. Anything that requests work is a command, even when it travels on a message channel. | script (heuristic) + review |
| TAC-05 | MUST | Every command has exactly one trigger: `actor:<Actor>` (reached through the API) or `policy:<Policy>` (reached from an event). | script |
| TAC-06 | MUST | Every aggregate states its creator (`Created by`), and this matches a command with a consistent trigger. | script |
| TAC-07 | MUST | Every requirement maps to at least one command or query, or is listed as out of scope with a reason. | script |
| TAC-08 | MUST | Value objects have no identity and are immutable. Entities inside an aggregate share the root's lifecycle. | review |
| TAC-09 | MUST | Read models and caches are not aggregates: they hold no invariants, they name their source and how they are rebuilt or invalidated, and they are never the source of truth. | script: Source filled + review |
| TAC-10 | MUST | An event consumed from another context is an integration event that its emitter lists with its payload. Internal events never cross a context boundary. | script + review |
| TAC-11 | SHOULD | Aggregates are small: the root plus what its invariants need. | review |
| TAC-12 | SHOULD | Every policy names its trigger event, the command it issues, and what happens if that command fails. | script (columns) + review |

## Database (03, 04)

| Id | Level | Rule | Check |
|---|---|---|---|
| DB-01 | MUST | No foreign key crosses a context or module. A cross-context reference is a plain id column, listed as `REF`. | script |
| DB-02 | MUST | Each context's tables live in their own schema or namespace. A table belongs to one module, and only that module writes to it. | script: module per table + review |
| DB-03 | MUST | Every aggregate in 02 has a home: a root table, collection or equivalent. Child entities and owned value objects live in the same module. | script |
| DB-04 | MUST | Invariants the store can enforce are enforced there: not-null, unique, check, foreign key within the module, enumerated sets. | review against 02 invariants |
| DB-05 | MUST | If the profile says events are used, an event leaves together with its state change (an outbox or equivalent in the same transaction), and consumers deduplicate (an inbox or idempotency record). | script (if the profile names an outbox) + review |
| DB-06 | MUST | Read models and caches are marked as such, and can be rebuilt from their source. | script: marked + review |
| DB-07 | SHOULD | Every foreign key, and every filter or sort used by a 02 query, has an index. | review |
| DB-08 | SHOULD | Aggregate roots carry a version for optimistic concurrency. | review |
| DB-09 | SHOULD | Types are tight: no free text for dates, ids, money or enumerated sets; money is never floating point; time is zoned or UTC. | review |
| DB-10 | SHOULD | Columns are not-null by default. A nullable column states what absence means. | review |
| DB-11 | SHOULD | No soft delete by reflex. Prefer hard delete, an archive table or an explicit lifecycle state, and say why. | review |
| ERD-01 | MUST | The ERD uses the profile's diagram format and shows every table in 03. Cross-module references are drawn differently from foreign keys (dotted, or labelled `ref`). | script |

## API (06)

| Id | Level | Rule | Check |
|---|---|---|---|
| API-01 | MUST | Every operation maps to exactly one command or query in 02, by the same name or a stated mapping. | script |
| API-02 | MUST | No operation invokes a policy-triggered command or creates an aggregate whose `Created by` is a policy. | script |
| API-03 | MUST | Every command operation states its idempotency: a natural key, an idempotency key, or "safe to retry because ...". | script |
| API-04 | MUST | Errors use the profile's error format. Each command lists its domain errors, taken from the invariants and the `Fails when` column in 02. | script (column) + review |
| API-05 | MUST | Operations follow the profile's API style and naming convention. | review |
| API-06 | SHOULD | List queries are paginated, with a stable order. | review |
| API-07 | SHOULD | An operation exposes only its own context's model. Data from other contexts comes from a read model or a published contract. | review |
| API-08 | SHOULD | Each operation names the actor or role allowed to call it. | script (column) |

## Review (07)

| Id | Level | Rule | Check |
|---|---|---|---|
| REV-01 | MUST | The reviewer authored none of the artifacts under review, and starts with a fresh context. | orchestrator |
| REV-02 | MUST | Each finding has a rule id (or `BUG` / `MISSING`), a location (`file:line`), a concrete case of what goes wrong, and the smallest fix. | script (columns) |
| REV-03 | MUST | Every prototype feature and every `REQ-n` is traced into the design, or reported as `MISSING`. | review + script trace |

## Severity of findings that are not rule violations

- **High:** data loss or corruption, a broken invariant, a missing requirement, or a contradiction between artifacts that leads a developer to build the wrong thing.
- **Medium:** a local inconsistency that is easy to fix, or a broken SHOULD rule.
- **Low:** naming or clarity.
