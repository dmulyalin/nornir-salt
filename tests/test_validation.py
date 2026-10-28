"""Offline checks for the shared Pydantic argument validator."""

from concurrent.futures import ThreadPoolExecutor

import pytest
from pydantic import BaseModel, ConfigDict, StrictInt, ValidationError

from nornir_salt.utils.pydantic_models import ValidateFuncArgs


class Arguments(BaseModel):
    value: StrictInt
    model_config = ConfigDict(extra="forbid")


def test_validation_preserves_arguments_and_metadata():
    @ValidateFuncArgs(Arguments)
    def command(value):
        """A task's metadata must survive wrapping."""
        return value

    assert command(1) == 1
    assert command(value=2) == 2
    assert command.__name__ == "command"
    assert command.__doc__ == command.__wrapped__.__doc__
    with pytest.raises(ValidationError):
        command("1")
    with pytest.raises(TypeError):
        command(1, value=2)
    with pytest.raises(TypeError):
        command()


def test_validation_caches_mixins_and_supports_keyword_only(monkeypatch):
    def integration(*, count: int = 1, label="ok"):
        pass

    @ValidateFuncArgs(Arguments, mixins=[None, integration])
    def command(value, **kwargs):
        return value, kwargs

    # Model composition and signature inspection must not run per task call.
    monkeypatch.setattr("nornir_salt.utils.pydantic_models.create_model", None)
    assert command(1, count=2, label="x") == (1, {"count": 2, "label": "x"})
    assert command(1) == (1, {})
    with pytest.raises(ValidationError):
        command(1, count="bad")
    with pytest.raises(ValidationError):
        command(1, unknown=True)
    with ThreadPoolExecutor(max_workers=4) as executor:
        assert list(executor.map(command, range(8))) == [(i, {}) for i in range(8)]


def test_validation_preserves_live_objects_and_passthrough():
    class LiveArguments(BaseModel):
        value: object
        model_config = ConfigDict(extra="allow")

    @ValidateFuncArgs(LiveArguments)
    def command(*, value, **kwargs):
        return value, kwargs

    live = object()
    result, extras = command(value=live, socket=live)
    assert result is live
    assert extras["socket"] is live


@pytest.mark.parametrize("ports", [[True], ["22"], [-1], [65536], "22"])
def test_tcp_ping_rejects_invalid_ports_before_socket_creation(monkeypatch, ports):
    from nornir.core.inventory import Host
    from nornir.core.task import Task
    from nornir_salt.plugins.tasks import tcp_ping

    task = Task(task=tcp_ping, nornir=None, global_dry_run=False, processors=[])
    task.host = Host(name="offline")
    monkeypatch.setattr("socket.socket", None)
    with pytest.raises(ValidationError):
        tcp_ping(task, ports=ports)


@pytest.mark.parametrize("test", ["contains", "custom", "cerberus", "eval"])
def test_test_suite_required_fields_use_model_validation(test):
    from nornir_salt.utils.pydantic_models import modelTestsProcessorTest

    with pytest.raises(ValidationError):
        modelTestsProcessorTest(test=test, task="show clock")
    with pytest.raises(ValidationError):
        modelTestsProcessorTest(task="show clock")


@pytest.mark.parametrize("last", [[1], [1, 2, 3], "1", "1,no", "²,1", True])
def test_file_diff_last_is_validated(last):
    from nornir.core.inventory import Host
    from nornir.core.task import Task
    from nornir_salt.plugins.tasks import file_diff

    task = Task(task=file_diff, nornir=None, global_dry_run=False, processors=[])
    task.host = Host(name="offline")
    with pytest.raises(ValidationError):
        file_diff(task, filegroup="config", last=last)


@pytest.mark.parametrize(
    "processor, options",
    [
        ("DataProcessor", {"dp": [1]}),
        ("DataProcessor", {"dp": [{}]}),
        ("ToFileProcessor", {"tf": "config", "max_files": 0}),
        ("DiffProcessor", {"diff": "config", "last": 0}),
        ("TestsProcessor", {"remove_tasks": "false"}),
    ],
)
def test_processor_options_use_pydantic(processor, options):
    from nornir_salt.plugins import processors

    with pytest.raises(ValidationError):
        getattr(processors, processor)(**options)


def test_connection_inputs_use_pydantic():
    from nornir_salt.plugins.connections import HTTPPlugin

    connection = HTTPPlugin()
    with pytest.raises(ValidationError):
        connection.open(None, None, None, 22, None, ["invalid"], None)


def test_inventory_update_rejects_invalid_action_before_mutation():
    from nornir_salt.plugins.functions.InventoryFun import _update_host

    with pytest.raises(ValidationError):
        _update_host(None, "offline", groups_action="invalid")


def test_mixin_cannot_override_explicit_model_fields():
    def integration(value: str = "default"):
        pass

    @ValidateFuncArgs(Arguments, mixins=[integration])
    def command(value):
        return value

    assert command(1) == 1
    with pytest.raises(ValidationError):
        command("1")
