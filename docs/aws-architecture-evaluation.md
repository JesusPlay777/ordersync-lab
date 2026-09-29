# AWS architecture evaluation

- Status: Complete; no resources created
- Date: 2026-09-29
- Proposed Region: `us-east-1` (N. Virginia)
- Account context: AWS Free plan created after July 15, 2025

## Executive result

The recommended first AWS deployment is intentionally small and serverless:

- Amazon API Gateway HTTP API as the public HTTPS entry point.
- One AWS Lambda function, packaged as a container image, for the Django API.
- One scheduled AWS Lambda function, using the same image, for due synchronization jobs.
- Amazon EventBridge Scheduler to invoke the worker once per minute.
- Amazon RDS for PostgreSQL, Single-AZ, `db.t4g.micro`, 20 GiB, and no public access.
- One private Amazon ECR repository with a short lifecycle policy.
- Systems Manager Parameter Store Standard for non-sensitive configuration.
- One AWS Secrets Manager secret for database credentials and the Django secret key.
- Amazon CloudWatch Logs, metrics, and a small alarm set with explicit retention.

The existing PostgreSQL `SyncJob` remains the durable queue in the first deployment. Amazon SQS
is not selected yet because it would introduce a database-to-queue dual-write problem and an
outbox publisher without solving a current scale constraint. SQS remains the preferred next
step when measured load or operational requirements justify that extra boundary.

This decision is recorded in
[ADR 0003](adr/0003-serverless-aws-baseline.md). Nothing in this evaluation authorizes an AWS
deployment, account-plan change, or billable resource creation.

## Workload assumptions

The decision applies only while these assumptions remain true:

- Fewer than 10,000 API requests and 1,000 submitted orders per month.
- Order processing normally completes in seconds and always in less than 15 minutes.
- A worker pickup delay of up to one minute is acceptable for the portfolio demonstration.
- The system stores fictional data and no personal, payment, or employer information.
- Availability is suitable for a lab; Multi-AZ recovery is not required.
- One API environment and one database are sufficient.
- Traffic is intermittent, making idle cost more important than constant low latency.

Changing these assumptions requires revisiting the ADR before changing infrastructure.

## Local-to-AWS component map

| Local responsibility | Current implementation | Proposed AWS implementation |
| --- | --- | --- |
| Public API | Django development server in Docker | API Gateway HTTP API to Lambda |
| API compute | Long-running `api` container | Lambda container image |
| Background worker | Long-running Compose worker | Scheduled Lambda invocation |
| Durable work | PostgreSQL `SyncJob` rows | The same model in RDS PostgreSQL |
| Domain database | PostgreSQL 17 container | RDS for PostgreSQL, private Single-AZ |
| Container images | Local Docker images | One private ECR repository |
| Non-secret settings | Compose environment variables | Parameter Store Standard |
| Secrets | Local-only environment values | One Secrets Manager secret |
| Logs | Container standard output | Structured CloudWatch Logs |
| Metrics and alerts | Local inspection | CloudWatch metrics and alarms |
| HTTPS entry | Bound localhost port | Regional API Gateway HTTP API endpoint |

The Django domain, idempotency constraints, audit model, Atlas boundary, and status API remain
independent from the selected compute service.

## API and worker compute: Fargate versus Lambda

| Criterion | ECS on Fargate | AWS Lambda |
| --- | --- | --- |
| Existing container fit | Runs the current API and worker with few changes. | Reuses a container image but requires HTTP and worker handlers. |
| Execution model | Long-running tasks with no hard duration limit. | Short, event-driven invocations with a 15-minute maximum. |
| Idle behavior | A continuously available task consumes vCPU and memory while idle. | Standard functions charge for requests and execution duration. |
| API entry | Normally requires an ALB for this design. | Integrates directly with API Gateway. |
| Worker behavior | Preserves the current polling loop exactly. | EventBridge invokes a bounded batch processor periodically. |
| Scaling | Desired task count and ECS service autoscaling. | Automatic per-invocation scaling; concurrency must be capped for RDS. |
| Operational surface | ECS service, task definitions, ALB, target groups, and scaling. | Function configuration, API integration, and scheduler. |
| Best fit here | Strongest compatibility, but relatively high idle cost. | Strongest low-traffic cost profile; jobs fit the duration limit. |

AWS describes Lambda as suitable for short event-driven tasks and Fargate as suitable for
long-running container workloads. Lambda invocations have a 15-minute maximum. See the
[official Fargate or Lambda decision guide](https://docs.aws.amazon.com/decision-guides/latest/decision-guides/fargate-or-lambda.html).

### Indicative Fargate baseline

Using the current AWS N. Virginia example rates, one Linux/x86 task with 0.25 vCPU and 0.5 GiB
running for 730 hours is approximately USD 9 per month. Two always-running tasks are therefore
approximately USD 18 before networking, database, logs, or storage. An ALB adds an hourly charge:
its base hourly rate alone is approximately USD 16.43 for 730 hours, before LCUs and public IPv4
charges. Rates must be recalculated immediately before deployment.

Sources: [Fargate pricing](https://aws.amazon.com/fargate/pricing/) and
[Elastic Load Balancing pricing](https://aws.amazon.com/elasticloadbalancing/pricing/).

### Decision

Choose Lambda for both the API and worker in the first deployment. The expected workload is
intermittent, every job is short, and minimizing idle infrastructure is more valuable than
preserving the exact container runtime behavior.

Use one optimized container image with two handlers:

- an HTTP handler adapting Django's ASGI application to Lambda; and
- a worker handler that claims and processes a bounded number of due `SyncJob` rows.

The worker runs once per minute through EventBridge Scheduler. Cloud retry delays become 60 and
300 seconds through environment configuration; the local 5 and 30 second defaults remain useful
for fast demonstrations and tests. EventBridge Scheduler currently includes 14 million free
invocations per month, far above one invocation per minute. See
[EventBridge pricing](https://aws.amazon.com/eventbridge/pricing/).

### Fargate reconsideration triggers

Reconsider Fargate if any of the following becomes true:

- work can exceed 15 minutes;
- traffic becomes steady enough that cold starts or per-invocation execution are a poor fit;
- the Lambda HTTP adapter requires intrusive Django compromises;
- a persistent connection or continuous poller becomes necessary; or
- measured cost is lower for continuously allocated compute.

## Durable work: SQS versus PostgreSQL

| Criterion | Amazon SQS Standard | PostgreSQL `SyncJob` |
| --- | --- | --- |
| Delivery | Managed at-least-once delivery; duplicates remain possible. | Transactional row committed with the order. |
| Atomic acceptance | Requires a transactional outbox or reconciliation publisher. | Order, idempotency record, audit event, and job commit together. |
| Retry and isolation | Visibility timeout, redrive policy, and DLQ. | Existing due time, attempt history, stale-lock recovery, and failure state. |
| Scale | Independent queue scaling and multiple consumers. | Database locks and polling eventually constrain throughput. |
| Operational evidence | Queue metrics and DLQ inspection. | Attempts and audit events already appear in the status API. |
| Current code impact | Adds publisher, message contract, consumer, and reconciliation. | Already implemented and covered by concurrency tests. |
| Low-volume cost | First 1 million requests per month are currently free. | Included in the selected RDS workload. |

SQS is an at-least-once system, so consumers must remain idempotent. Lambda can receive batches
from SQS and retry them; partial batch responses avoid replaying records that already succeeded.
See [SQS pricing](https://aws.amazon.com/sqs/pricing/),
[SQS at-least-once delivery](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/standard-queues-at-least-once-delivery.html), and
[Lambda SQS error handling](https://docs.aws.amazon.com/lambda/latest/dg/services-sqs-errorhandling.html).

### Decision

Keep `SyncJob` in PostgreSQL for the first deployment. EventBridge invokes the worker every
minute; the worker uses the existing `select_for_update(skip_locked=True)` claim and layered
idempotency behavior.

Introduce SQS Standard plus a dead-letter queue only when one of these triggers is measured:

- multiple independent consumers need the same integration event;
- queue contention materially affects database performance;
- the worker cannot drain the backlog within the accepted delay;
- operators require managed redrive independent from the database; or
- an external producer must submit work without database access.

When SQS is introduced, retain `SyncJob` as a transactional outbox until publication is confirmed.
Never replace the atomic database commit with an uncoordinated database write followed by
`SendMessage`.

## PostgreSQL: RDS decision

Choose Amazon RDS for PostgreSQL because the domain already depends on PostgreSQL transactions,
constraints, row locks, and advisory locks. Replacing it would expand the project beyond the
AWS learning objective.

Initial shape:

- `db.t4g.micro`, subject to Region and Free-plan availability at deployment time;
- Single-AZ, 20 GiB general-purpose SSD;
- storage encryption enabled;
- no public accessibility;
- database security group accepts PostgreSQL only from the Lambda security group;
- TLS required for application connections;
- one-day automated backup retention for the lab; and
- deletion protection during an active demo, disabled only during intentional teardown.

Multi-AZ, read replicas, Performance Insights paid retention, and RDS Proxy are deferred. Limit
Lambda reserved concurrency initially so the connection count stays bounded. Reconsider RDS
Proxy only after CloudWatch shows connection pressure.

AWS lists `db.t3.micro` and `db.t4g.micro` as RDS options available to Free-plan customers using
credits. This must not be interpreted as a permanent zero-cost database. See
[RDS Free Tier](https://aws.amazon.com/rds/free/) and
[RDS PostgreSQL pricing](https://aws.amazon.com/rds/postgresql/pricing/).

## Container registry: ECR decision

Use one private ECR repository and one shared image for the API, worker, and migration handler.
Use immutable commit-SHA tags, enable scan-on-push, and keep at most the latest three release
images plus the active image.

ECR currently offers new customers 500 MB per month of private repository storage for one year;
storage beyond the allowance is illustrated at USD 0.10 per GB-month. In-Region transfer from
private ECR to Lambda or Fargate is listed at no charge. Keep the compressed image below 500 MB
where practical. See [ECR pricing](https://aws.amazon.com/ecr/pricing/).

## Configuration and secrets

Use Parameter Store Standard for non-sensitive values:

- Django allowed hosts;
- retry delays and maximum attempts;
- job lock timeout;
- log level; and
- environment name.

Standard parameters and standard-throughput API interactions are currently available at no
additional charge. See
[Systems Manager pricing](https://aws.amazon.com/systems-manager/pricing/).

Use one Secrets Manager JSON secret for database credentials and `DJANGO_SECRET_KEY`. Secrets
Manager supports lifecycle management and future rotation. Current public pricing is USD 0.40
per secret-month plus USD 0.05 per 10,000 API calls. See
[Secrets Manager pricing](https://aws.amazon.com/secrets-manager/pricing/).

For the first lab deployment, resolve the secret during deployment and inject encrypted Lambda
environment values. Automatic rotation is deferred because a rotated value would require
runtime retrieval or coordinated function configuration. Runtime secret retrieval must not be
added without also designing private connectivity to Secrets Manager.

## Observability decision

Write structured JSON to standard output and send it to CloudWatch Logs. Every entry must include
the correlation ID, OrderSync order UUID, component, event name, and safe error code. Never log
idempotency keys, authorization values, database credentials, or raw stack traces in API output.

Create explicit log groups with seven-day retention. Use service metrics before adding custom
metrics. The first alarm set is:

- API Lambda errors and throttles;
- worker Lambda errors and duration near its timeout;
- API Gateway `5XX` responses;
- RDS CPU, database connections, and free storage;
- failed orders or stale pending work through one custom metric; and
- worker scheduler invocation failures.

CloudWatch currently includes 5 GB of logs, 10 custom or detailed metrics, and 10 standard alarm
metrics in its free tier. Log volume must still be bounded with retention and concise structured
events. See [CloudWatch pricing](https://aws.amazon.com/cloudwatch/pricing/).

## Public entry: ALB versus API Gateway

| Criterion | Application Load Balancer | API Gateway HTTP API |
| --- | --- | --- |
| Natural compute target | ECS/Fargate services | Lambda functions |
| Idle charge | Hourly charge plus LCU and public IPv4 dimensions | No minimum fee; request and transfer based |
| Routing need here | More capability than one API requires | Sufficient for one versioned JSON API |
| TLS | ACM certificate and listener configuration | AWS-managed endpoint initially |
| Operational work | Subnets, target group, health checks, listener, scaling | API routes, integration, throttling, logs |

Choose API Gateway HTTP API. It matches Lambda, avoids a continuously billed load balancer, and
currently includes one million HTTP API calls per month for new customers during the stated
offer period. Use the generated `execute-api` hostname initially; a custom domain, Route 53 zone,
and WAF are deferred because they add cost without proving the integration workflow.

Sources: [API Gateway pricing](https://aws.amazon.com/api-gateway/pricing/) and
[Elastic Load Balancing pricing](https://aws.amazon.com/elasticloadbalancing/pricing/).

## Network and security baseline

- Place RDS in private subnets across two Availability Zones, while keeping the database
  Single-AZ.
- Attach the API and worker functions to the private subnets so they can reach RDS.
- Do not create a NAT gateway in the first version.
- Do not allow the functions to call internet services or AWS data-plane APIs at runtime.
- Use deployment-time configuration injection; add a VPC endpoint or approved egress only when
  a measured requirement appears.
- Use separate least-privilege IAM roles for API, worker, migration, and deployment operations.
- Give only the deployment role permission to push images or change infrastructure.
- Encrypt RDS, ECR, CloudWatch log groups, parameters, and secrets with their appropriate
  AWS-managed encryption defaults unless a customer-managed key is justified.
- Apply API Gateway throttling and a small Lambda reserved-concurrency limit.

AWS notes that a VPC-connected Lambda needs NAT for public internet access or VPC endpoints for
private AWS service access. Avoiding both is a deliberate cost and security constraint in this
baseline. See
[Lambda VPC networking](https://docs.aws.amazon.com/lambda/latest/dg/troubleshooting-networking.html)
and [private RDS access](https://docs.aws.amazon.com/AmazonRDS/latest/gettingstartedguide/security-public-private.html).

## Cost envelope and guardrails

Assumed monthly usage is 10,000 API requests, 1,000 orders, one worker schedule per minute, less
than 500 MB of private image storage, and less than 1 GB of logs.

| Service | Current public allowance or price signal | Expected lab treatment |
| --- | --- | --- |
| Lambda | 1 million requests and 400,000 GB-seconds per month | Expected inside allowance at assumed traffic |
| API Gateway HTTP API | 1 million calls per month during the published new-customer offer | Expected inside allowance |
| EventBridge Scheduler | 14 million invocations per month | About 43,800 invocations per 30-day month |
| RDS PostgreSQL | Eligible micro classes consume Free-plan credits | Dominant credit consumer; calculate before launch |
| ECR private | 500 MB per month for a new customer for one year | One optimized image and lifecycle policy |
| Parameter Store Standard | No additional charge at standard throughput | A few non-sensitive parameters |
| Secrets Manager | USD 0.40 per secret-month plus API calls | One secret; small but non-zero credit use |
| CloudWatch | 5 GB logs and limited metrics/alarms | Seven-day retention and low log volume |
| SQS | 1 million requests per month | Not created in the first deployment |

Lambda's published free tier includes one million requests and 400,000 GB-seconds per month. See
[Lambda pricing](https://aws.amazon.com/lambda/pricing/).

The account's Free plan ends after six months or when credits are exhausted, whichever happens
first. AWS states that a Free-plan account then closes automatically unless it is upgraded; its
content is retained for 90 days before deletion. This project must not rely on an unverified
credit balance. See
[AWS Free plan conditions](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/free-tier-plans.html).

Before any deployment:

1. Verify the exact credit balance, plan end date, and service eligibility in Billing.
2. Produce and save an AWS Pricing Calculator estimate for `us-east-1`.
3. Confirm the existing zero-spend alert recipient and Free Tier usage alerts.
4. Define a maximum deployment window and teardown date.
5. Tag every resource with `Project=OrderSyncLab`, `Environment=demo`, and `Owner`.
6. Confirm that the plan contains no NAT gateway, ALB, RDS Proxy, WAF, paid custom domain, or
   Multi-AZ database.
7. Obtain an explicit go-ahead before applying infrastructure.

## Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Django container cold start | Optimize one image, lazy-load nonessential code, and measure before accepting the design. |
| Lambda-to-RDS connection exhaustion | Reserved concurrency, short connections, and RDS connection alarms. |
| One-minute worker pickup latency | Accept for the lab; move to SQS event delivery if requirements change. |
| Single-AZ database interruption | Accept for a lab, retain backups, and document that this is not production HA. |
| Secrets do not rotate automatically | Restrict access and require redeployment after manual rotation in this phase. |
| PostgreSQL queue becomes a bottleneck | Measure backlog age and lock contention; introduce the outbox-to-SQS design on trigger. |
| Free credits hide steady-state cost | Store a calculator estimate and a post-credit monthly estimate before launch. |
| Free plan expires with resources present | Set a teardown date and export any evidence before the plan end date. |

## Implementation sequence after approval

This study creates no infrastructure. A later approved implementation should proceed in this
order:

1. Add Lambda API, worker, and migration handlers while preserving local Docker execution.
2. Add tests for API Gateway events, scheduled worker invocation, and cloud retry settings.
3. Add infrastructure as code and inspect its plan without applying it.
4. Complete the Pricing Calculator estimate and security checklist.
5. Deploy ECR and the minimum runtime for a time-boxed demonstration.
6. Run the existing happy-path, replay, conflict, recovery, and exhaustion evidence in AWS.
7. Export logs and cost evidence, then tear down or explicitly approve continued operation.

## Official references

- [AWS Free plan conditions](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/free-tier-plans.html)
- [AWS Lambda pricing](https://aws.amazon.com/lambda/pricing/)
- [Fargate or Lambda decision guide](https://docs.aws.amazon.com/decision-guides/latest/decision-guides/fargate-or-lambda.html)
- [AWS Fargate pricing](https://aws.amazon.com/fargate/pricing/)
- [Amazon SQS pricing](https://aws.amazon.com/sqs/pricing/)
- [Amazon RDS Free Tier](https://aws.amazon.com/rds/free/)
- [Amazon ECR pricing](https://aws.amazon.com/ecr/pricing/)
- [Systems Manager pricing](https://aws.amazon.com/systems-manager/pricing/)
- [Secrets Manager pricing](https://aws.amazon.com/secrets-manager/pricing/)
- [CloudWatch pricing](https://aws.amazon.com/cloudwatch/pricing/)
- [API Gateway pricing](https://aws.amazon.com/api-gateway/pricing/)
- [Elastic Load Balancing pricing](https://aws.amazon.com/elasticloadbalancing/pricing/)
- [EventBridge pricing](https://aws.amazon.com/eventbridge/pricing/)
