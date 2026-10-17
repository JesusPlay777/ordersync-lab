# OrderSync Lab AWS cost estimate and Free-plan eligibility — 2026-10-11

**Status:** public-price estimate and public-documentation check; **not** a saved AWS
Pricing Calculator quote, account-specific service authorization, or deployment approval.
No AWS resources were created for this review. Region: `us-east-1`. The estimate describes
the resources in `infra/ecr-repository.yaml`, `infra/network-database.yaml`, and
`infra/cloud-functions.yaml`, not every service mentioned as a future possibility in ADR 0003.

**Historical Region notice (2026-10-17):** The deployment target changed to `us-east-2`.
The dollar amounts below remain an `us-east-1` historical model, not an Ohio estimate or
deployment approval. Obtain a new saved estimate for `us-east-2` before opening the gate.

## Evidence from the account screenshots

User-provided AWS console screenshots viewed on 2026-10-11 show a **Free** plan, **USD 120**
remaining credits, **168 days** remaining, and **2027-03-26** as the displayed plan end date.
They also show USD 0.00 month-to-date and an OK budget monitor. Earlier screenshots show
two active credits (USD 100 initial Free Tier and USD 20 earned through an AWS Budgets
activity), both with USD 0 used; the credit-detail pages show 2027-09-26 as their expiry.
The screenshots show Free Tier usage alerts enabled and the zero-spend budget recipient as
`Active (legacy)` with an actual-cost alert above USD 0.01. The address and account ID are
intentionally not copied into this public repository. A delivery test was not performed.

**The plan and credits have different end dates.** The Free plan ends on the displayed date
or earlier if Free Tier credits run out; credit expiry in September 2027 does not extend the
Free plan. Do not treat the USD 0.00 invoice or budget OK status as a future cost ceiling.
[AWS Free Tier FAQ](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/free-tier-FAQ.html).

## Reproducible monthly model, before free allowances and credits

This is a *gross usage-value* model for a 730-hour average month with the API and worker
enabled throughout. It intentionally does not subtract Free Tier allowances or credits;
account-wide usage and credit applicability are not yet known. Values are USD, rounded only
for display. The monthly model is not a spending cap.

| Component | Assumption and calculation | Gross USD/month |
| --- | --- | ---: |
| RDS PostgreSQL instance | Single-AZ `db.t4g.micro`, 730 h × USD 0.016/h | 11.68 |
| RDS gp3 storage | 20 GiB × USD 0.115/GiB-month | 2.30 |
| Secrets Manager | One secret × USD 0.40/secret-month; low deployment-time API usage rounds below USD 0.01 | 0.40 |
| ECR private storage | **Illustrative, not measured:** three retained 0.5-GB compressed images = 1.5 GB × USD 0.10/GB-month | 0.15 |
| Lambda | Three 512-MiB x86 functions: API 1,000 × 0.5 s; worker 43,800 × 1 s (every minute for 730 h); migration 2 × 30 s. Total 44,802 requests and 22,180 GB-s. At USD 0.20/million requests and USD 0.0000166667/GB-s | 0.38 |
| API Gateway HTTP API | 1,000 requests × USD 1/million; small outbound transfer not priced | <0.01 |
| EventBridge Scheduler | 43,800 invocations × USD 1/million gross; schedule currently **disabled** | 0.04 |
| CloudWatch Logs | **Illustrative, not measured:** 1 GB ingested × USD 0.50/GB plus ~7 days average retention × USD 0.03/GB-month | 0.51 |
| **Current-template scenario** | Sum of unrounded rows; **zero alarms are created by the template** | **~15.46** |
| Four standard-resolution alarms | **Proposed only, not in template:** 4 × USD 0.10/alarm-month | +0.40 |
| **Target with proposed alarms** | Illustrative total, if those alarms are implemented | **~15.86** |

At initial deployment, with the public API and scheduler both disabled, RDS + its storage +
the secret + illustrative ECR storage still total **~USD 14.53/month** if retained for a full
month. This explains why an idle deployment is not zero-cost even though the invoice can be
zero while Free-plan credits apply. At the worker's 60-second timeout on *every* scheduled
invocation, worker compute alone would be 1,314,000 GB-s, about **USD 21.90 gross/month**
before Lambda's applicable monthly allowance, API usage, RDS, and other costs.

**Not priced:** backups beyond the included RDS allowance, retained snapshots after deletion,
RDS T4g Unlimited surplus CPU credits, cross-AZ/Internet transfer, ECR enhanced scanning,
CloudWatch custom metrics or high-resolution alarms, taxes, other workloads in this account,
and extra logs or requests caused by failures/abuse. Automated backups within the account's
same-Region provisioned database-storage allowance are included, but retained snapshots after
teardown need a fresh check. The model assumes no NAT gateway, ALB, RDS Proxy, Multi-AZ,
public IPv4 address, or paid KMS key because the templates do not create them.

The RDS rates are from the [AWS public RDS price list for `us-east-1`](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonRDS/current/us-east-1/index.json),
as captured in the [dated cost/security review](aws-cost-security-review-2026-10-11.md).
Other rates and allowances: [Secrets Manager](https://aws.amazon.com/secrets-manager/pricing/),
[ECR](https://aws.amazon.com/ecr/pricing/), [Lambda](https://aws.amazon.com/lambda/pricing/),
[API Gateway](https://aws.amazon.com/api-gateway/pricing/),
[EventBridge Scheduler](https://aws.amazon.com/eventbridge/pricing/), and
[CloudWatch](https://aws.amazon.com/cloudwatch/pricing/). Prices should be refreshed in the
AWS Pricing Calculator immediately before any approval.

## What is and is not confirmed about the Free plan

AWS says that Free-plan accounts have **Always Free** offers, whereas short-term trial offers
are for paid-plan accounts. Other selected services may consume Free-plan credits, but that
is different from having a zero-price monthly allowance. See the
[Free Tier offer rules](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/free-tier.html)
and [plan comparison](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/free-tier-plans.html).

| Service in current templates | Public evidence | Account-specific status |
| --- | --- | --- |
| RDS PostgreSQL, `db.t4g.micro`, gp3 | AWS describes a Free-plan RDS creation option. For accounts created after 2025-07-15, **do not assume** the legacy 750 instance-hours/20-GB RDS allowance; price its usage and check credit applicability. PostgreSQL 17.10 is a published RDS release. | **Pending for the amended target:** exact `17.10` + `db.t4g.micro` + gp3 orderability in `us-east-2`, Free-plan access, and credit applicability. |
| Lambda | An [Always Free allowance](https://aws.amazon.com/lambda/pricing/) of 1 million requests and 400,000 GB-s/month is published; the modeled 44,802/22,180 is below it before other account usage. | Published allowance supports this design; account-wide consumption/quotas not checked. |
| API Gateway HTTP API | [Pricing](https://aws.amazon.com/api-gateway/pricing/) names API Gateway as credit-eligible; HTTP API is usage-priced. Do **not** assume its older 12-month new-customer promotion applies to this 2026 Free-plan account. | Pending credit/product applicability and API quota check. |
| EventBridge Scheduler | [14 million free invocations/month](https://aws.amazon.com/eventbridge/pricing/) are published, well above the modeled 43,800 before other account usage. | Published allowance supports this design; account-wide use and access not checked. |
| ECR private repository | [Pricing](https://aws.amazon.com/ecr/pricing/) names ECR as credit-eligible and advertises 500 MB/month for new ECR customers for a year. Do not subtract that introductory allowance until its applicability to this Free-plan account is confirmed. | Pending private-repository access, actual compressed image size, registry scanning mode and credit/product applicability. |
| Secrets Manager | [USD 0.40/secret-month](https://aws.amazon.com/secrets-manager/pricing/) plus API calls; no zero-price allowance is assumed. | Pending Free-plan access and whether each active credit covers it. |
| CloudWatch Logs and alarms | [Published Always Free limits](https://aws.amazon.com/cloudwatch/pricing/) include 5 GB Logs and 10 standard-resolution alarm metrics monthly; no alarms are currently implemented. | Account-wide use and future alarm design not checked. |
| VPC, CloudFormation, IAM | The current VPC has private subnets but no NAT or public IPv4. [VPC](https://docs.aws.amazon.com/vpc/latest/userguide/what-is-amazon-vpc.html) and [CloudFormation](https://aws.amazon.com/cloudformation/pricing/) do not add a charge for the basic modeled constructs, but deployed resources do. | Templates reviewed only; no stack or permission test. |

The [RDS FAQ](https://aws.amazon.com/rds/faqs/) specifically distinguishes customers who
signed up before July 2025 from those using the newer credit-based plan. A service's pricing
page, or the fact that it appears in a USD 0.00 Billing graph, does **not** prove that a
specific account can create it or that a particular promotional credit covers it.

## Read-only account verification still required

1. In **Billing > Credits**, open **each** active credit and select **View full list of
   applicable services**. Confirm at least RDS, ECR, Lambda, API Gateway, EventBridge,
   Secrets Manager and CloudWatch for the credit that would cover them. The USD 20 activity
   credit may have different applicable products than the USD 100 initial credit. Record the
   result privately; do not publish IDs, addresses or full account screenshots.
2. In **Billing > Free Tier**, inspect **Explore our offers** with **Always Free** selected
   for Lambda, CloudWatch and EventBridge Scheduler. This checks offer type, not service
   authorization or remaining account-wide usage.
3. Select **Ohio (`us-east-2`)** in the RDS console and inspect the *Create database*
   form **without clicking Create**. Confirm PostgreSQL 17.10, Single-AZ, `db.t4g.micro`,
   gp3 20 GiB and the displayed Free-plan option. The read-only RDS API
   [`DescribeOrderableDBInstanceOptions`](https://docs.aws.amazon.com/cli/latest/reference/rds/describe-orderable-db-instance-options.html)
   can independently confirm the engine/version/class/storage combination if the deployment
   identity is granted read-only RDS access. No account-level API call was made in the original
   2026-10-11 review; a CLI login configured later does not by itself grant RDS permissions.
4. In **ECR > Private registry > Scanning**, inspect whether the registry is on **Basic** or
   **Enhanced** scanning. [Enhanced scanning](https://docs.aws.amazon.com/AmazonECR/latest/userguide/image-scanning.html)
   uses Amazon Inspector and can add cost. Measure the
   compressed image bytes and retained-image count before a final estimate.
5. Create a dated, **saved** estimate in the [public AWS Pricing Calculator](https://calculator.aws/#/)
   using the table above; export PDF or keep its share link **privately**. The public
   Calculator does not know this account's credits or other usage. Reconcile its line items
   with this model and add missing transfer/backups/alarms. Its estimate is not a hard cap.

Until those checks, service eligibility is **plausible from public AWS documentation but not
confirmed for this account**. The [deployment gate](aws-deployment-gate.md) remains **closed**.
