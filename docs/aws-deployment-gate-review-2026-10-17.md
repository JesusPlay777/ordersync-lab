# AWS deployment gate review — 2026-10-17

**Decision: closed.** This is a read-only evidence review, not permission to create AWS
resources, publish an image, invoke a cloud migration, enable the public API, or upgrade the
account. Do not put account IDs, email addresses, credit identifiers, secrets, or public
Calculator share links in this repository.

## Evidence checked

| Control | Result on 2026-10-17 | Still required |
| --- | --- | --- |
| Account and Region | `sts:GetCallerIdentity` returned the `ordersync-operator` IAM user, and its account ID matched the user-provided console screenshot; the ID is intentionally omitted here. The `ordersync-identidad` profile targets `us-east-2`. A console screenshot showed Ohio enabled by default. | Recheck the **live** Free-plan state, credit balance, applicable products and plan end date immediately before approval. Region enablement does not prove that each product/configuration can be ordered. |
| Alerts | Earlier screenshots showed Free Tier usage alerts enabled and an `Active (legacy)` Zero-Spend Budget recipient. | Privately record the exact recipient and test alert delivery. Alerts notify; they are not a spending cap. |
| Saved estimate | No dated, saved Ohio AWS Pricing Calculator estimate exists yet. The public RDS price list for Ohio, published 2026-10-06, lists PostgreSQL Single-AZ `db.t4g.micro` at **USD 0.016/hour** (SKU `GGD6FE59WWUNDKDC`) and PostgreSQL Single-AZ gp3 at **USD 0.115/GB-month** (SKU `JQQGK6D789TWJF8B`). At 730 hours and 20 GB, RDS alone is **USD 13.98/month gross**. One secret at the published USD 0.40/secret-month makes an illustrative **USD 14.38/month floor**, before other services, taxes, eligible free usage, credits, backups and retained artifacts. | Create and save a complete `us-east-2` Calculator estimate with a deployment duration, monthly and upfront totals, and explicit exclusions. This floor is not a quote or cap. |
| RDS orderability | The template requests PostgreSQL `17.10`, Single-AZ `db.t4g.micro`, 20 GB gp3, encryption, one-day backup retention and private subnets. The named IAM user received `AccessDenied` for `rds:DescribeOrderableDBInstanceOptions`; this is **not** a finding that the configuration is unavailable. | In the Ohio RDS **Create database** form, confirm the exact engine version, class, storage and Free-plan option **without clicking Create**, or obtain narrowly scoped read-only permission for the API. Confirm backup/snapshot and surplus CPU-credit treatment. |
| Secrets Manager | The network template creates one generated secret and does not configure rotation. The public price is USD 0.40/secret-month plus API calls. | Check account-specific Free-plan access and each credit's applicable-service list; estimate calls and lifetime. |
| ECR | The template requests one private repository, immutable tags and scan-on-push. The locally built image reports approximately **853 MB uncompressed**; this is **not** its ECR-billed compressed size. The named IAM user received `AccessDenied` for `ecr:GetRegistryScanningConfiguration`. | Check Basic versus Enhanced registry scanning in Ohio, measure compressed pushed-image size and decide how many versions to retain. Do not push an image as a measurement step before approval. |
| Lambda, HTTP API, Scheduler and logs | The cloud template defines three 512-MiB image functions (timeouts 30/60/300 seconds), three seven-day log groups, an initially disabled execute-api endpoint and an initially disabled one-minute schedule. It creates **no alarms**. Local SAM build and all three handler invocations passed; the worker found an empty local queue. | Save workload assumptions for API calls, function duration, migration count, schedule-on time, logs and data transfer. Add or explicitly defer alarms; local success does not establish AWS quotas or account access. |
| Access and security | IAM read access for RDS and ECR is absent. The app and migration functions use the database master user; secret values are injected into Lambda environment configuration. Public API authentication, throttling and alarms are not implemented. The initial public endpoint is disabled. | Design narrowly scoped deployment/publish/invoke permissions; resolve or explicitly time-bound the master-user risk. Add authentication/rate controls and alarms before public exposure. Review the image digest and CloudFormation change sets before applying anything. |
| Teardown | RDS has `DeletionProtection: true` and `DeletionPolicy: Snapshot`; ECR has `EmptyOnDelete: false`. These settings can prevent simple stack deletion or leave retained, potentially billable data. | Name the operator, record a UTC start/end window, remove the cloud-functions stack before the network stack, and decide how deletion protection, final snapshots and ECR images will be handled. Never delete retained data merely to clear a stack error without approval. |
| Authorization | No approval to create resources or expose an endpoint has been recorded. | Obtain separate explicit approvals after every required check is evidenced. |

The four SAM/CloudFormation templates passed `sam validate --lint`. The local SAM image build,
HTTP health request, read-only migration plan, and worker invocation passed. The project's
`make verify` checks passed with 24 tests. These local checks do not change the gate decision.

## Calculator worksheet for Ohio

Use the [public AWS Pricing Calculator](https://calculator.aws/#/) and select **US East
(Ohio), `us-east-2`** for each regional service. Model **gross** usage before credits; the
Calculator does not know this account's live balance or all Free Tier eligibility.

| Service | Inputs to record in the saved estimate |
| --- | --- |
| RDS PostgreSQL | Single-AZ, on-demand `db.t4g.micro`, 730 hours for a full month or the approved shorter window, 20 GB gp3, one-day automated backups, possible retained snapshot and T4g Unlimited CPU credits. |
| Secrets Manager | One secret for the approved lifetime, no rotation, expected deployment-time API calls. |
| Private ECR | One repository; measured compressed image GB multiplied by retained versions and time; Basic/Enhanced scanning choice and any transfer. The old three-by-0.5-GB assumption was illustrative, not measured. |
| Lambda | Three x86_64 functions at 0.5 GB. Record API calls and average duration, worker invocation count/duration if enabled, and migration invocations. Consider the worker's 60-second timeout as a stress case. |
| API Gateway HTTP API | Zero public requests in the initial disabled state; separately model the intended public demonstration's requests and outbound transfer. |
| EventBridge Scheduler | Zero scheduled invocations while disabled; one per minute is 43,800 invocations in a 730-hour month if later enabled. |
| CloudWatch | Three log groups with seven-day retention; estimate ingestion/storage from measured or stated assumptions. No alarms exist in the template; price any proposed alarm set separately. |

Save a dated PDF/JSON or share link **privately** and record the upfront and monthly totals,
assumptions, and date checked. AWS says public Calculator share links are publicly accessible;
do not commit a link containing account or personal details. The [historical `us-east-1`
estimate](aws-cost-estimate-2026-10-11.md) is not an Ohio approval artifact.

## Account-console checks that need an authorized operator

1. In **Billing and Cost Management**, record the current plan, remaining credits, plan end
   date, each credit's applicable services, Free Tier usage, budget recipient and alert
   delivery privately. Do not assume the credit expiry extends the Free-plan end date.
2. In **RDS**, select Ohio and inspect **Create database** only through the review screen;
   do not submit it. Verify the requested PostgreSQL version, instance class, gp3 size and
   plan-specific availability.
3. In **ECR > Private registry > Scanning**, record Basic or Enhanced scanning and its rules.
4. In **AWS Pricing Calculator**, save the Ohio worksheet above and reconcile every cost line
   with the planned deployment duration and the account's credits.
5. Decide the UTC deployment/teardown window, named operator, security controls and maximum
   acceptable gross usage. Review a CloudFormation change set only after these decisions;
   do not execute it without separate approval.

Primary public sources: [AWS RDS Ohio price list](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonRDS/current/us-east-2/index.json),
[AWS Secrets Manager pricing](https://aws.amazon.com/secrets-manager/pricing/),
[AWS Pricing Calculator guidance](https://docs.aws.amazon.com/pricing-calculator/latest/userguide/getting-started.html),
[AWS estimate sharing guidance](https://docs.aws.amazon.com/pricing-calculator/latest/userguide/save-share-estimate.html),
[AWS Free-plan rules](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/free-tier-plans.html),
[RDS orderability API](https://docs.aws.amazon.com/cli/latest/reference/rds/describe-orderable-db-instance-options.html), and
[ECR scanning API](https://docs.aws.amazon.com/AmazonECR/latest/APIReference/API_GetRegistryScanningConfiguration.html).
