from django.core.management.base import BaseCommand, CommandError

from ordersync_lab.orders.models import WarehouseFailurePlan


class Command(BaseCommand):
    help = "Configure deterministic transient Atlas failures for a fictional external order."

    def add_arguments(self, parser):
        parser.add_argument("external_order_id")
        parser.add_argument("--failures", type=int, default=1)
        parser.add_argument("--error-code", default="atlas_unavailable")

    def handle(self, *args, **options):  # noqa: ARG002
        failures = options["failures"]
        if not 0 <= failures <= 10:
            raise CommandError("--failures must be between 0 and 10.")

        plan, _ = WarehouseFailurePlan.objects.update_or_create(
            external_order_id=options["external_order_id"],
            defaults={
                "failures_remaining": failures,
                "error_code": options["error_code"],
            },
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Atlas will fail the next {plan.failures_remaining} attempt(s) for "
                f"{plan.external_order_id}."
            )
        )
