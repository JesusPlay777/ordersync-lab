# Local AWS SAM validation

This stage validates the Lambda packaging and event wiring without calling AWS deployment APIs
or creating cloud resources. AWS SAM uses Docker to build and invoke the same two handlers
already covered by the test suite. The first build downloads the public Lambda base image.

## What the template models

- `OrderSyncApiFunction` runs `ordersync_lab.lambda_http.handler` behind an HTTP API v2 proxy.
- `OrderSyncWorkerFunction` runs `ordersync_lab.lambda_worker.handler` from EventBridge Scheduler.
- Both functions build from `Dockerfile.lambda`; their local tags differ only so SAM can manage
  two function artifacts. A deployment design can publish the same image digest to one ECR
  repository and select each handler with `ImageConfig.Command`.
- The schedule is `DISABLED` in the template. Enabling it requires a later explicit decision.

The template intentionally does not define RDS, VPC, ECR, Parameter Store, Secrets Manager, or
deployment permissions. Local PostgreSQL continues to supply the database through the Compose
network.

## Prerequisites

- Docker Desktop with WSL integration.
- AWS SAM CLI.
- The Compose database running and healthy.

Prepare the fictional local environment file without overwriting an existing one:

```bash
make sam-prepare-env
docker compose up -d db
```

`sam-env.local.json` is ignored by Git. Its example contains only fictional local credentials;
never replace it with cloud credentials and commit it.

The same variable names are declared in `template.yaml` with non-production placeholders because
SAM only overrides environment variables already defined by the template. The ignored local file
replaces them with the Compose database values during emulation.

## Validate and build

```bash
make sam-validate
make sam-build
```

`sam validate --lint` checks the SAM and CloudFormation structure. `sam build` builds Lambda
container images locally and writes generated artifacts under the ignored `.aws-sam/` directory.
Neither command deploys resources.

## Invoke each handler

```bash
make sam-local-api-invoke
make sam-local-worker-invoke
```

The commands attach the Lambda containers to `ordersync-lab_default`, allowing them to resolve
the Compose database as `db`. The HTTP invocation should return the health response. The worker
invocation returns a bounded-batch summary and may process due jobs in the local database.

To expose the HTTP API emulator at `http://127.0.0.1:3000`:

```bash
make sam-local-api
```

Port 3000 is the default. If another local process already uses it, choose a free port without
editing project files:

```bash
make sam-local-api SAM_PORT=3001
```

Stop it with `Ctrl+C`. This local emulator verifies event translation and container startup, but
it does not reproduce IAM, Lambda concurrency, VPC networking, RDS behavior, or CloudWatch.
