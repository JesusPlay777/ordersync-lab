# AWS cost and security review — 2026-10-11

This is a **read-only review**, not approval to deploy, push to ECR, run migrations,
enable the public API or upgrade the account. The [deployment gate](aws-deployment-gate.md)
remains closed. Local validation cannot prove account eligibility or cap spending.
The [reproducible component-by-component estimate](aws-cost-estimate-2026-10-11.md) extends
this initial cost floor and records the account screenshots received later on 2026-10-11.

## Cost model before credits and taxes

The [AWS public RDS Price List for `us-east-1`](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonRDS/current/us-east-1/index.json), published 2026-10-06, lists PostgreSQL Single-AZ `db.t4g.micro` at **USD 0.016/instance-hour** (SKU `9HPEGXQTDDGH53C9`) and PostgreSQL gp3 storage at **USD 0.115/GB-month** (SKU `KYVYY29G957PKY3B`). At 730 hours and 20 GiB provisioned, that is **USD 11.68 + USD 2.30 = USD 13.98/month**. One secret adds **USD 0.40/secret-month** plus USD 0.05 per 10,000 API calls ([Secrets Manager pricing](https://aws.amazon.com/secrets-manager/pricing/)). The **USD 14.38/month subtotal is a baseline, not an all-in quote or spending limit**. It is the nominal usage value before any eligible Free Tier usage or credit offset. RDS runs and consumes storage while idle. RDS `db.t4g` Unlimited CPU can incur surplus-credit charges.

The subtotal excludes RDS backups beyond included allowance, snapshots retained after teardown,
data transfer, ECR storage/scanning, Lambda, API Gateway, Scheduler, CloudWatch logs/alarms and
other account usage. Same-Region ECR-to-Lambda transfer is listed at no charge; ECR storage
depends on the compressed image and retained versions. A new ECR customer may have 500 MB/month
private storage free for one year ([ECR pricing](https://aws.amazon.com/ecr/pricing/)).
Do not assume the USD 100 initial credits reported on 2026-09-27 remain intact, or that the
possible extra USD 100 was earned. A Free account closes when its plan ends or credits are
depleted ([AWS Free-plan terms](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/free-tier-plans.html)).

Use the following inputs in [AWS Pricing Calculator](https://calculator.aws/#/) for `us-east-1`.
Replace illustrative values with measured traffic/duration before saving:

| Service | Input to model |
| --- | --- |
| RDS PostgreSQL | Single-AZ, `db.t4g.micro`, on-demand, 730 h/month, gp3 20 GiB, one-day automated backups; separately model retained snapshots. |
| Secrets Manager | One stored secret for the deployment duration; expected calls only at deployments/updates because the template injects values then. |
| ECR private | One repository; actual compressed image GB × retained versions, and registry scanning mode. No lifecycle rule exists. |
| Lambda | Three x86_64 functions at 0.5 GiB. **Illustration:** API 1,000 requests/month × 0.5 s; worker 43,200/month × 1 s if the one-minute schedule is enabled; migration 2/month × 30 s. Total: 44,202 requests and 21,880 GB-seconds. Stress case: worker at its 60 s timeout for every scheduled invocation = 1,296,000 GB-seconds by itself. |
| API Gateway HTTP API | 1,000 requests/month for the illustrative public scenario, plus response/outbound transfer. No public calls while endpoint disabled. |
| EventBridge Scheduler | Zero while disabled; 43,200 invocations/30-day month once enabled. [AWS lists 14 million free invocations/month](https://aws.amazon.com/eventbridge/pricing/), subject to account eligibility and other usage. |
| CloudWatch | Three seven-day log groups; measured ingestion/storage and proposed alarms. The template creates no alarms. |

[Lambda pricing](https://aws.amazon.com/lambda/pricing/) is by requests and GB-seconds and
currently lists one million requests/400,000 GB-seconds free monthly;
[HTTP API pricing](https://aws.amazon.com/api-gateway/pricing/) is by requests and outbound
transfer. Free usage may be shared with other workloads. Verify the account's actual credits,
eligibility and usage in Billing; the Calculator does not know the live balance.

To save an estimate, choose **Create estimate** at [AWS Pricing Calculator](https://calculator.aws/#/),
add these services and assumptions, inspect upfront/monthly totals, then **Share** or export
PDF/JSON. AWS says the share link is public and valid for one year; omit personal/account data.
See [AWS's sharing instructions](https://docs.aws.amazon.com/pricing-calculator/latest/userguide/save-share-estimate.html).

## Security findings

1. **Before public exposure:** `infra/cloud-functions.yaml` has no explicit API Gateway route/stage throttling, authorizer or alarm. The Django REST settings and order views have no authentication or throttling. A public caller could create fictitious orders and consume database, Lambda, logs and credits. Decide whether to protect writes with an authorizer or another access model, add rate controls and alarms, and test them before `EnablePublicApi=true`. API Gateway throttles are [best-effort rather than a guaranteed cost ceiling](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-throttling.html). Reserved concurrency bounds simultaneous Lambda executions, not total requests.
2. **Before shared/long-lived deployment:** API, worker and migration all use the RDS master user. Define least-privileged application and migration roles, or explicitly accept and time-bound this demo risk. CloudFormation injects secrets into Lambda environment configuration; restrict who can read that configuration. Rotation is absent; changing a secret alone does **not** refresh all CloudFormation dynamic-reference consumers ([AWS reference behavior](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/dynamic-references-secretsmanager.html)).
3. **Before any AWS write:** review caller identity and deployment/publish/invoke permissions, especially migration invocation; inspect image contents/digest, ECR scanning mode, RDS CA checksum and CloudFormation change set. Confirm engine 17.10/class/storage orderability and Free-plan eligibility in the target account/Region. Local validation cannot establish these.
4. **Before an unattended demo:** add a minimal alarm set (Lambda errors/throttles, API 5xx, RDS CPU/storage), confirm cost-alert recipient, and rehearse teardown. The ADR intends CloudWatch alarms and Parameter Store Standard configuration; neither is implemented in the cloud template. Snapshot-on-delete, deletion protection and ECR image retention can leave billable artifacts after stack removal.

Positive controls already modeled: private VPC without NAT or public RDS route; Lambda-to-RDS
TCP 5432 only; RDS encryption and `rds.force_ssl=1`; PostgreSQL `verify-full`; digest-pinned
container image; separate execution roles; API endpoint and worker schedule initially disabled;
seven-day log retention and reserved concurrency 2/1/1.

## Account evidence and decision

The 2026-09-27 report records the initial account setup. New user-provided screenshots
viewed on **2026-10-11** now show a Free plan, USD 120 remaining credits (USD 100 initial
plus USD 20 earned), 168 days remaining, and **2027-03-26** as the *displayed plan end date*.
The active credits have a later expiry in September 2027, which does not extend the Free
plan. The Zero-Spend Budget is healthy, its actual-cost alert is above USD 0.01, and the
recipient is `Active (legacy)`. Free Tier usage alerts are enabled; the invoice still shows
USD 0.00. These are screenshots, not an independent AWS API/account check. Budget-alert
delivery has not been tested. AWS Budgets can lag and notifications are not a hard cap
([AWS Budgets documentation](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html)).

**Gate remains CLOSED.** Still needed: independent account identity check, each credit's
applicable-product list, exact recipient recorded privately and alert-delivery test, saved
dated Calculator estimate, actual ECR image size/scanning mode, target-Region service
availability, public API controls, deployment IAM review, operator/UTC window/teardown plan,
and separate explicit authorization. No account-specific CLI/API access was available for
this review; no AWS resource or account setting was changed. Do not store secrets or private
email addresses in this public repository.
