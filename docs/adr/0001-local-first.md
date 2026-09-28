# ADR 0001: Build a local vertical slice before selecting AWS services

- Status: Accepted
- Date: 2026-09-27

## Context

The project exists to demonstrate architecture and operational decisions, not to collect a list of AWS service names. Selecting cloud services before defining the workflow would make cost, reliability, and security tradeoffs difficult to justify.

## Decision

Build and validate the first workflow locally with Django and PostgreSQL. Keep the domain and integration boundaries independent from the future hosting, queue, and observability services.

No AWS resource will be created during the local preparation milestone.

## Consequences

- The first deliverable is reproducible without an AWS account.
- Idempotency and failure behavior can be tested before deployment.
- AWS services will be selected later through a documented architecture and cost comparison.
- Some local infrastructure will eventually be replaced by managed AWS services.

