"""AWS Lambda entry point for bounded scheduled job processing."""

from collections import Counter

from django.conf import settings
from django.db import close_old_connections

from ordersync_lab.orders.services import process_next_job

MAX_BATCH_SIZE = 100
OUTCOMES = ("synced", "failed", "retry_pending")


def handler(event, context):
    batch_limit = max(1, min(settings.ORDERSYNC_WORKER_BATCH_SIZE, MAX_BATCH_SIZE))
    minimum_remaining_ms = max(0, settings.ORDERSYNC_WORKER_MIN_REMAINING_MS)
    outcomes = Counter()
    stopped_reason = "batch_limit"

    close_old_connections()
    try:
        for index in range(batch_limit):
            if context.get_remaining_time_in_millis() <= minimum_remaining_ms:
                stopped_reason = "time_budget"
                break

            outcome = process_next_job(recover_stale=index == 0)
            if outcome is None:
                stopped_reason = "queue_empty"
                break
            outcomes[outcome] += 1

        return {
            "request_id": context.aws_request_id,
            "trigger": event.get("source", "eventbridge-scheduler"),
            "batch_limit": batch_limit,
            "processed": sum(outcomes.values()),
            "outcomes": {outcome: outcomes[outcome] for outcome in OUTCOMES},
            "stopped_reason": stopped_reason,
        }
    finally:
        close_old_connections()
