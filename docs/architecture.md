# Local architecture

OrderSync Lab begins as a small modular Django application backed by PostgreSQL.

```text
Demo client -> Django API -> PostgreSQL
```

The preparation milestone deliberately contains no order models, queues, AWS SDKs, or cloud resources. Its only purpose is to prove that the repository, Python runtime, database connection, health endpoint, and test tooling are reproducible.

The next milestone will add explicit application boundaries for:

- order ingestion;
- idempotency;
- background processing;
- the fictional Warehouse adapter;
- audit events and structured logs.

These boundaries will allow the local queue and integration adapter to be replaced later without coupling the domain model directly to an AWS service.

