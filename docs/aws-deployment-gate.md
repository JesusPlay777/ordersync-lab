# AWS deployment gate — not yet approved

These are **required checks**, not evidence that the AWS account is ready. Do not deploy the
ECR, network/RDS, or cloud functions templates, publish an image, or invoke a cloud migration
until the items below are completed and explicit approval is given. The locally validated
templates do not establish Free-plan eligibility or a spending cap.

| Check | Evidence to record before approval |
| --- | --- |
| Account and Region | Correct AWS account ID, `us-east-2`, Free-plan status, remaining credit balance and expiry date. |
| Alerts | Exact budget recipient, alert status, Free-tier usage alerts and their delivery test; alerts notify rather than cap spend. |
| Pricing Calculator | Saved estimate with monthly and one-time totals, assumptions and date checked. |
| RDS | `db.t4g.micro`, PostgreSQL 17.10 availability, 20 GiB gp3, 24×7 instance hours, backups, snapshots after teardown, storage and data transfer. |
| Secrets Manager | One secret, storage duration and expected API calls; no automatic rotation in this baseline. |
| ECR | Image size, number of retained versions, storage, transfer and registry scanning mode; check for enhanced scanning charges. |
| Lambda, API Gateway, Scheduler, CloudWatch | API/worker/migration invocations, execution duration, HTTP requests, schedule frequency, log volume and seven-day retention. |
| Access and security | IAM deployment/publish/invoke rights, ECR digest, secret injection, TLS verification, public API disabled for initial migration. |
| Teardown | Named operator, UTC start/end window, order of stack removal, deletion protection, snapshot and ECR image decisions. |
| Authorization | Explicit separate approval for resource creation and later public exposure; record who approved and when. |

Status: **pending; deployment not approved**. The dated
[2026-10-17 read-only gate review](aws-deployment-gate-review-2026-10-17.md) records what was
confirmed locally and through public prices, the two account API `AccessDenied` results, and
the exact remaining operator checks. The dated
[cost and security review](aws-cost-security-review-2026-10-11.md) records controls and open
security findings. The [detailed monthly estimate and eligibility matrix](aws-cost-estimate-2026-10-11.md)
records the 2026-10-11 user-provided screenshots: Free plan, USD 120 credits remaining,
plan end displayed as 2027-03-26, enabled Free Tier usage alerts, and an `Active (legacy)`
budget recipient. A 2026-10-17 account-console screenshot shows US East (Ohio), `us-east-2`,
enabled by default; the operator reports that the named CLI profile uses this Region and
`sts get-caller-identity` returns the intended IAM user. This confirms neither service-specific
orderability nor deployment permissions. The dated cost estimate uses `us-east-1` prices and
must be replaced with a saved `us-east-2` estimate before approval. The exact recipient and
alert delivery, each credit's applicable services, account/Region orderability, actual image
size/scanning, and authorization remain unverified. Close those items before any AWS write.
The [ADR deployment gate](adr/0003-serverless-aws-baseline.md#deployment-gate) remains authoritative.
