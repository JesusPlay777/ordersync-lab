# ADR 0002: Use layered idempotency for order synchronization

- Status: Accepted
- Date: 2026-09-27

## Context

HTTP clients retry, workers can stop after a remote side effect, and a warehouse response can
be lost. State checks alone cannot prevent duplicates when requests race or failure timing is
unknown. The lab must prove that a replay cannot create another order or decrement stock twice.

## Decision

- Store `(source, idempotency_key)`, a canonical request fingerprint, and the original response.
- Enforce the unique business identity `(source, external_order_id)`.
- Use the immutable OrderSync UUID as the Atlas reservation key.
- Back every uniqueness rule with a PostgreSQL constraint.
- Store the order, idempotency record, first event, and pending job in one transaction.
- Retain idempotency records for the lifetime of this small lab.

## Consequences

- Identical retries return a deterministic result.
- Changed payloads cannot hide behind an existing key or order identifier.
- Concurrent requests use database arbitration instead of timing-sensitive checks.
- A worker can safely repeat an uncertain warehouse call.
- Canonicalization and response replay require explicit persistence and tests.
- A production system would need a documented retention policy.
