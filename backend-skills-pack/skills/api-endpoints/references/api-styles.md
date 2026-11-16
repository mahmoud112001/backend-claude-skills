# Style-specific API rules

Read only the section for the profile's `api_style`. The project rules file wins over anything here.

## REST (rules adapted from api-design)

- Resources are plural nouns, with one stable casing taken from the profile, and sub-resources nest one level at most. Each action that is not CRUD is a sub-resource verb (`POST /things/{id}/cancel`), named after the 02 command.
- Methods: `GET` reads and is safe; `POST` creates or acts; `PUT` replaces and is idempotent; `PATCH` is a partial update; `DELETE` removes and is idempotent.
- Status codes: 200 read or ok, 201 created (with Location), 202 accepted (async), 204 no content, 400 malformed, 401 unauthenticated, 403 forbidden, 404 not found, 409 conflict (state or version), 412 precondition failed (If-Match), 422 domain rule broken, 429 rate limited. A 500 is never used for client errors.
- Concurrency: an `ETag` or version on reads, with `If-Match` on updates to aggregate roots.
- Idempotency for `POST`: an `Idempotency-Key` header, stored per caller for a stated window, where a replay returns the first response.
- Pagination: a cursor for large or changing lists, an offset only for small, stable ones. Always state the sort key.
- Versioning: in the path (`/v1`) or in a header, whichever the profile states. Only additive changes are allowed within a version.

## GraphQL

- A command is a mutation `verbNoun(input: VerbNounInput!): VerbNounPayload!`. The payload carries the result and the domain errors as typed union members or `userErrors`, as the profile says. A query is a field on `Query`.
- Lists use connections (`first`/`after`, `edges`, `pageInfo`) with a stated order.
- Idempotency: mutations take a `clientMutationId` or an idempotency key argument; state its retention.
- Authorization is per field or per type. Name the actor in the table.
- No mutation exposes a policy-triggered command. If the brief needs live updates, push integration events read-only, over the protocol's streaming operation type.
- Change: deprecate with `@deprecated(reason:)`; never remove a field without a version plan.

## gRPC

- One service per context. A command is `rpc VerbNoun(VerbNounRequest) returns (VerbNounResponse)`. Lists use `page_size`/`page_token` with a stated order.
- Errors use canonical status codes (`INVALID_ARGUMENT`, `NOT_FOUND`, `ALREADY_EXISTS`, `FAILED_PRECONDITION`, `ABORTED` for concurrency, `PERMISSION_DENIED`), with a domain reason in the error details, in the profile's error format.
- Idempotency: a `request_id` field in command requests; the server deduplicates it for a stated window.
- Fields are never renumbered or reused. Removed fields are `reserved`. Packages are versioned (`<pkg>.v1`).
- If `api_contract_file` is `proto`, write `06-api.proto` as the authoritative contract.

## Async messaging (commands or queries over a broker)

- Command messages are named imperatively and go to a queue owned by the handling context. Integration events are past tense and go to a topic owned by the emitter. Never mix the two.
- Every message has a message id (used for deduplication), a correlation id, and a schema version.
- The reply or outcome is an event or a reply message. State the timeout and the dead-letter behaviour.
- If `api_contract_file` is `asyncapi`, write `06-api.asyncapi.yaml`.

## Other styles

Map each concept the same way: one operation per command or query, typed errors in the profile's format, an idempotency key or natural key, stable pagination, and an explicit versioning rule. Write the mapping under Conventions.
