# AWS deployment gate — not yet approved

These are **required checks**, not evidence that the AWS account is ready. Do not deploy the
ECR, network/RDS, or cloud functions templates, publish an image, or invoke a cloud migration
until the items below are completed and explicit approval is given. The locally validated
templates do not establish Free-plan eligibility or a spending cap.

| Check | Evidence to record before approval |
| --- | --- |
| Account and Region | Correct AWS account ID, `us-east-1`, Free-plan status, remaining credit balance and expiry date. |
| Alerts | Exact budget recipient, alert status, Free-tier usage alerts and their delivery test; alerts notify rather than cap spend. |
| Pricing Calculator | Saved estimate with monthly and one-time totals, assumptions and date checked. |
| RDS | `db.t4g.micro`, PostgreSQL 17.10 availability, 20 GiB gp3, 24×7 instance hours, backups, snapshots after teardown, storage and data transfer. |
| Secrets Manager | One secret, storage duration and expected API calls; no automatic rotation in this baseline. |
| ECR | Image size, number of retained versions, storage, transfer and registry scanning mode; check for enhanced scanning charges. |
| Lambda, API Gateway, Scheduler, CloudWatch | API/worker/migration invocations, execution duration, HTTP requests, schedule frequency, log volume and seven-day retention. |
| Access and security | IAM deployment/publish/invoke rights, ECR digest, secret injection, TLS verification, public API disabled for initial migration. |
| Teardown | Named operator, UTC start/end window, order of stack removal, deletion protection, snapshot and ECR image decisions. |
| Authorization | Explicit separate approval for resource creation and later public exposure; record who approved and when. |

Status: **pending**. No account-specific prices, credit balances, recipient addresses, or
authorization have been verified in this repository. Fill this gate with current account data
and a saved [AWS Pricing Calculator](https://calculator.aws/) estimate before making any AWS
write. The [ADR deployment gate](adr/0003-serverless-aws-baseline.md#deployment-gate) remains
authoritative.
