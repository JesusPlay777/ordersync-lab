import time

from django.core.management.base import BaseCommand

from ordersync_lab.orders.services import process_next_job


class Command(BaseCommand):
    help = "Process durable OrderSync jobs using the configured warehouse adapter."

    def add_arguments(self, parser):
        parser.add_argument(
            "--once",
            action="store_true",
            help="Process at most one due job and exit.",
        )
        parser.add_argument(
            "--poll-interval",
            type=float,
            default=1.0,
            help="Seconds to wait when no job is due.",
        )

    def handle(self, *args, **options):  # noqa: ARG002
        poll_interval = max(0.1, min(options["poll_interval"], 60.0))
        while True:
            outcome = process_next_job()
            if outcome:
                self.stdout.write(f"Processed job with outcome: {outcome}")
            if options["once"]:
                return
            if outcome is None:
                time.sleep(poll_interval)
