# Cloud Lambda-to-RDS connection (review only)

`infra/cloud-functions.yaml` is a cloud SAM template. It is intentionally separate from the
local `template.yaml`: local SAM still talks to the Compose database, while this template
describes a possible AWS deployment. Neither template has been deployed by this work.

## Connection path

1. The network/database stack exports two private subnet IDs, a Lambda security group, the RDS
   hostname and port, and the application secret ARN.
2. The cloud functions stack imports those values by the `NetworkStackName` parameter. All
   three functions use the private subnets and security group. Only TCP 5432 to the database
   group is permitted by the modeled network rules; there is no NAT or public route.
3. CloudFormation resolves the JSON secret fields into the functions' environment at deployment.
   The runtime roles therefore need no `secretsmanager:GetSecretValue` permission or private
   Secrets Manager endpoint. The deployment principal does need permission to resolve the
   secret. Anyone authorized to read the Lambda configuration may also be able to see those
   environment values, so Lambda configuration access must be restricted.
4. Django passes `sslmode=verify-full` and the RDS CA bundle path to PostgreSQL. This checks both
   encryption and the server hostname; `rds.force_ssl=1` on the database rejects plaintext.

The API, worker and one-off migration runner use the same digest-pinned `LambdaImageUri`,
selecting different handlers with `ImageConfig.Command`. The image must include the official
RDS global CA bundle; the Lambda Dockerfile fetches it over HTTPS during image build and
verifies the reviewed SHA-256 digest.
If AWS updates the bundle, review and update that digest deliberately. Before publishing an
image, review the bundle provenance and the image digest. The template does not build or push
to ECR.

Each function has its own execution role and log group with seven-day retention. The only
runtime IAM grants are the EC2 network-interface permissions Lambda requires for VPC access and
write access to that function's log group. Conditional denies prevent function code from using
the EC2 permissions while leaving Lambda's VPC setup available. The worker schedule is
**disabled**. The HTTP API's public default endpoint is also disabled unless
`EnablePublicApi=true` is explicitly supplied after migrations. Reserved concurrency is two
for the API and one each for the worker and migration runner, bounding simultaneous database
connections; account concurrency quotas still need checking before deployment.

## Review locally

```bash
make infra-validate
make cloud-validate
make ecr-validate
make sam-validate
```

Validation checks syntax and CloudFormation/SAM structure. It does not prove that RDS is
orderable, that IAM and networking work in an account, that the certificate download succeeds,
or that the image has been published. No AWS credentials or cloud resources are required for
these checks.

## Remaining deployment gate

- Review the AWS Free-plan credit balance, service eligibility, pricing estimate, alert
  destinations, and exact teardown window from ADR 0003. RDS and Secrets Manager can consume
  credits while idle.
- Follow the [ECR and migration rehearsal](aws-image-and-migrations.md) and complete the
  [deployment gate](aws-deployment-gate.md). An ECR repository and manual migration runner are
  modeled, but no image has been published and no cloud migration has run.
- Define Parameter Store Standard entries for non-sensitive settings and useful alarms.
- Confirm the deployment role can resolve the secret, the chosen Region supports the RDS
  version/class, and a real connection verifies the RDS certificate and hostname.
- Decide when to enable the scheduled worker and how to add useful alarms. Validation alone is
  not authorization to deploy either stack.

AWS references: [cross-stack imports](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/intrinsic-function-reference-importvalue.html),
[Lambda VPC execution permissions](https://docs.aws.amazon.com/lambda/latest/dg/configuration-vpc.html),
[Secrets Manager dynamic references](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/dynamic-references-secretsmanager.html),
and [RDS PostgreSQL TLS verification](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/PostgreSQL.Concepts.General.SSL.html).
