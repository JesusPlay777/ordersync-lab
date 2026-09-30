"""AWS Lambda entry point for API Gateway HTTP API events."""

import asyncio
import base64

from mangum import Mangum

from ordersync_lab.asgi import application


def _ensure_event_loop():
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())


def _with_content_length(event):
    """Add the body length when an HTTP API v2 event omits the header."""
    body = event.get("body")
    headers = event.get("headers") or {}
    if event.get("version") != "2.0" or body is None or "content-length" in headers:
        return event

    raw_body = base64.b64decode(body) if event.get("isBase64Encoded") else body.encode()
    return {**event, "headers": {**headers, "content-length": str(len(raw_body))}}


# Django exposes an ASGI callable but does not need ASGI lifespan events. Mangum translates
# API Gateway HTTP API payloads into ASGI requests and translates Django responses back into
# Lambda proxy responses.
_ensure_event_loop()
_adapter = Mangum(application, lifespan="off")


def handler(event, context):
    return _adapter(_with_content_length(event), context)
