# ECR image and private RDS migrations (preparation only)

Nothing in this guide has been deployed. `infra/ecr-repository.yaml` describes one private,
immutable-tag ECR repository, with S3-managed encryption and scan-on-push. It deliberately has
no lifecycle rule and `EmptyOnDelete: false`: an image cannot be silently removed while a
function still uses its digest. Review the account's registry scanning mode before deployment;
enhanced scanning can incur additional charges.

## Local rehearsal, with no AWS calls

```bash
make ecr-validate cloud-validate sam-validate
make cloud-image-build
docker image inspect ordersync-lab:cloud-candidate --format '{{.Os}}/{{.Architecture}}'
make sam-local-migration-plan
```

The image must be `linux/amd64` to match the cloud functions. The build disables provenance
attestations so Docker exports a single-platform image manifest, not an image index that Lambda
cannot consume. Verify the manifest type again in ECR after the future push. The plan event is
read-only: it calls Django's `migrate --plan` against the **local Compose database** through
SAM. It does not apply migrations. The migration Lambda has no trigger; even in AWS it only runs
when an authorized operator invokes it with an explicit event.

## Future sequence, only after the deployment gate is approved

1. Review a clean Git commit, image contents, architecture, RDS CA checksum, ECR scanning mode,
   estimated costs, exact account/Region, and teardown plan. Use one immutable tag based on
   that commit; do not label an image built from uncommitted changes as that commit.
2. Deploy the ECR repository stack in `us-east-2`, then log in to that account's ECR registry,
   tag the locally tested image, and push it. Confirm the pushed image digest and manifest type.
   The publishing identity needs `ecr:GetAuthorizationToken` plus repository-scoped upload
   permissions. No push command is automated by this repository.
3. Deploy the private network/RDS stack, then the cloud functions stack with
   `LambdaImageUri=<repository-uri>@sha256:<verified-digest>` and
   `EnablePublicApi=false`. The worker schedule is also disabled. The ECR repository, RDS and
   Secrets Manager may consume credits as soon as they exist.
4. Invoke only the migration function with `{"action":"plan"}` and review its proposed
   operations. Then, after a separate human check, invoke it with
   `{"action":"apply","confirmation":"APPLY_ORDERSYNC_MIGRATIONS"}`. Invoke `plan` again to
   verify no operations remain. Migration output must not contain credentials.
5. After a healthy database/schema check, explicitly update the cloud stack to
   `EnablePublicApi=true`. Enable the worker schedule only after an end-to-end order test.

The future publication commands, **not to run until that gate is approved**, are:

```bash
aws sts get-caller-identity
aws ecr get-login-password --region us-east-2 | docker login --username AWS --password-stdin <reviewed-registry-uri>
docker tag ordersync-lab:cloud-candidate <reviewed-repository-uri>:git-<reviewed-commit>
docker push <reviewed-repository-uri>:git-<reviewed-commit>
aws ecr describe-images --region us-east-2 --repository-name ordersync-lab --image-ids imageTag=git-<reviewed-commit>
```

Confirm the account ID, repository URI, pushed `imageDigest`, and single-image
`imageManifestMediaType` from that last command before passing the digest to the cloud stack.
The placeholders are intentionally not executable as written; this repository does not contain
account identifiers or credentials.

The migration function runs in the same private subnets and uses the same container image,
TLS settings and database secret as the API/worker. This first demo uses the RDS master user
for all three; a dedicated least-privileged application user and migration user are a future
hardening task. The function has no API or scheduler event. Restrict `lambda:InvokeFunction` on
it to the approved deployment operator. PostgreSQL migration atomicity depends on the
particular operations; if invocation times out, inspect `plan` and the migration table before
any retry. Never run `migrate` in the API or worker startup path.

Before teardown, disable the public API and schedule, then delete the cloud functions stack.
Only then consider removing the network stack; RDS deletion protection must be deliberately
disabled first and retained snapshots can still cost money. An ECR repository with images will
not be deleted automatically; inspect which digests are still referenced before removing any.

References: [Lambda container images and same-Region ECR](https://docs.aws.amazon.com/lambda/latest/dg/images-create.html),
[ECR push procedure](https://docs.aws.amazon.com/AmazonECR/latest/userguide/docker-push-ecr-image.html),
[ECR repository properties](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-ecr-repository.html),
and [Django `migrate --plan`](https://docs.djangoproject.com/en/5.2/ref/django-admin/#migrate).
