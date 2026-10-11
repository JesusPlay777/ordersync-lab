import pytest

from ordersync_lab import lambda_migrate


def test_plan_does_not_apply_migrations(monkeypatch):
    calls = []

    def fake_call_command(name, **kwargs):
        calls.append((name, kwargs["plan"], kwargs["interactive"]))
        kwargs["stdout"].write("Planned operations: orders.0001_initial")

    monkeypatch.setattr(lambda_migrate, "call_command", fake_call_command)

    result = lambda_migrate.handler({"action": "plan"}, None)

    assert result == {"status": "planned", "plan": "Planned operations: orders.0001_initial"}
    assert calls == [("migrate", True, False)]


@pytest.mark.parametrize(
    "event", [{}, {"action": "apply"}, {"action": "apply", "confirmation": "yes"}]
)
def test_apply_rejects_missing_confirmation(monkeypatch, event):
    def unexpected_call(*args, **kwargs):
        raise AssertionError("migrate must not run")

    monkeypatch.setattr(lambda_migrate, "call_command", unexpected_call)

    with pytest.raises(ValueError):
        lambda_migrate.handler(event, None)


def test_apply_runs_only_after_exact_confirmation(monkeypatch):
    calls = []

    def fake_call_command(name, **kwargs):
        calls.append((name, kwargs["plan"], kwargs["interactive"]))

    monkeypatch.setattr(lambda_migrate, "call_command", fake_call_command)

    result = lambda_migrate.handler(
        {"action": "apply", "confirmation": lambda_migrate.APPLY_CONFIRMATION}, None
    )

    assert result == {"status": "applied"}
    assert calls == [("migrate", False, False)]
