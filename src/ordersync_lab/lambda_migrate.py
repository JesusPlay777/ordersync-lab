"""Manually invoked, one-off Django migration handler for private RDS."""

import os
from io import StringIO

import django
from django.core.management import call_command
from django.db import close_old_connections

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ordersync_lab.settings")
django.setup()

APPLY_CONFIRMATION = "APPLY_ORDERSYNC_MIGRATIONS"


def handler(event, context):
    if not isinstance(event, dict) or event.get("action") not in {"plan", "apply"}:
        raise ValueError("Choose action 'plan' or 'apply'.")

    action = event["action"]
    if action == "apply" and event.get("confirmation") != APPLY_CONFIRMATION:
        raise ValueError("Applying migrations requires the exact confirmation phrase.")

    output = StringIO()
    close_old_connections()
    try:
        call_command(
            "migrate",
            interactive=False,
            plan=action == "plan",
            stdout=output,
        )
        if action == "plan":
            return {"status": "planned", "plan": output.getvalue()}
        return {"status": "applied"}
    finally:
        close_old_connections()
