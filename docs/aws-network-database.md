# AWS network and database foundation

`infra/network-database.yaml` is a CloudFormation design for the first cloud infrastructure
increment. It is separate from the local `template.yaml`: SAM continues to use Docker and the
Compose database, while the cloud resources can be reviewed without changing that workflow.
This foundation has not been deployed.

## What the template defines

| Resource | Purpose |
| --- | --- |
| VPC and two subnets in distinct Availability Zones | Private address space for the future Lambda functions and RDS. |
| Private route table | Only the VPC-local route exists; there is no internet gateway, NAT gateway, or public subnet. |
| Lambda and database security groups | Lambda can send TCP 5432 to the database group; the database accepts TCP 5432 only from the Lambda group. |
| RDS subnet group | Allows RDS to choose a private subnet; the instance itself remains Single-AZ. |
| PostgreSQL 17 parameter group | Sets `rds.force_ssl=1`, requiring TLS connections. |
| RDS PostgreSQL instance | `db.t4g.micro`, 20 GiB gp3, encrypted storage, private endpoint, one-day backups, and deletion protection. |
| Secrets Manager secret | Generates the database password and holds the supplied Django signing key. |

The template requires two parameters for a future deployment: `Owner` for resource tags and
`DjangoSecretKey`, a 50–128-character URL-safe signing key supplied privately at deployment.
The template generates a 40-character database password and stores both values in one JSON
secret under `password` and `django_secret_key`, with username `ordersync_admin`. The key is a
`NoEcho` CloudFormation parameter; do not put it in a committed parameter file or CLI history.
CloudFormation resolves the database password when creating RDS. The secret is a planned
resource only: running validation does not create it. Changing its password later does not by
itself update RDS; rotation needs a coordinated change.

The stack exports both private subnet IDs, the Lambda security group ID, the private database
endpoint and port, and the secret ARN for [the cloud functions template](aws-cloud-functions.md).
Only the ARN is exported, not the secret value. The cloud functions cannot be deployed before
this stack exists; deleting this stack is also blocked while its exports remain in use.

## Local validation

With SAM CLI on `PATH`, run:

```bash
make infra-validate
make cloud-validate
make sam-validate
```

The commands lint the network, cloud application, and existing local SAM templates. They are
local checks, not a deployment or a cost estimate. They do
not verify that a particular RDS version and instance class are orderable in the account's
Region. The template pins PostgreSQL `17.10` for a reproducible review; confirm or update that
minor version before deployment. Region availability, the account's Free-plan eligibility, and
the Pricing Calculator estimate must also be checked before deployment.

## Decisions still pending

- Decide how migrations receive database access without making the instance public.
- Define the ECR publication workflow, Parameter Store configuration, logs-based alarms, and
  a teardown procedure.
- Confirm the official RDS CA bundle is present in the image and verify a real TLS connection
  in a separately approved deployment.
- Review teardown: deletion protection must be disabled deliberately, and a CloudFormation
  snapshot can continue consuming storage after the stack is removed.

No stack should be applied until the [deployment gate](adr/0003-serverless-aws-baseline.md#deployment-gate)
is complete. AWS documents the [two-AZ requirement for DB subnet groups](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-rds-dbsubnetgroup.html),
[RDS PostgreSQL TLS enforcement](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/PostgreSQL.Concepts.General.SSL.html),
and [Secrets Manager dynamic references](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/dynamic-references-secretsmanager.html).
