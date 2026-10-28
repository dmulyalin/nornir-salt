import importlib
import logging
import pprint
import queue
import socket
import sys
import threading
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import yaml

sys.path.insert(0, "..")

try:
    from nornir import InitNornir
    from nornir.core.plugins.runners import RunnersPluginRegister

    HAS_NORNIR = True
except ImportError:
    HAS_NORNIR = False

from nornir_salt.plugins.functions import ResultSerializer
from nornir_salt.plugins.inventory import DictInventory
from nornir_salt.plugins.runners import RetryRunner
from nornir_salt.plugins.tasks import netmiko_send_commands, nr_test

logging.basicConfig(level=logging.ERROR)


# ----------------------------------------------------------------------
# Initialize Nornir
# ----------------------------------------------------------------------


skip_if_no_nornir = pytest.mark.skipif(
    HAS_NORNIR == False,
    reason="Failed to import all required Nornir modules and plugins",
)


def init(opts, runner):
    """
    Initiate nornir by calling InitNornir()
    """
    global skip_if_no_lab

    nr = InitNornir(
        logging={"enabled": False},
        runner={"plugin": runner},
        inventory={
            "plugin": "DictInventory",
            "options": {
                "hosts": opts["hosts"],
                "groups": opts.get("groups", {}),
                "defaults": opts.get("defaults", {}),
            },
        },
    )

    return nr


RunnersPluginRegister.register("RetryRunner", RetryRunner)


# ----------------------------------------------------------------------
# tests that need Nornir
# ----------------------------------------------------------------------


@skip_if_no_nornir
@pytest.mark.parametrize(
    "port, connection_port", [(2206, None), (122, None), (2206, 123)]
)
def test_retry_runner_connection_check_failed(monkeypatch, port, connection_port):
    lab_inventory = yaml.safe_load("""
hosts:
  iol-r1:
    hostname: containerlab.lab
    platform: ios
    port: 2206
    groups: [lab]

groups:
  lab:
    username: cisco
    password: cisco

defaults: {}
""")
    lab_inventory["hosts"]["iol-r1"]["port"] = port
    if connection_port is not None:
        lab_inventory["hosts"]["iol-r1"].setdefault("connection_options", {})["netmiko"] = {
            "port": connection_port
        }
    connection = Mock()
    connection.connect.side_effect = socket.timeout("timed out")
    monkeypatch.setattr(socket, "socket", Mock(return_value=connection))
    nr = init(lab_inventory, "RetryRunner")
    # Explicitly enable TCP preflight; its default is now False.
    output = nr.run(
        task=netmiko_send_commands,
        commands=["show clock"],
        connection_name="netmiko",
        run_connect_check=True,
        run_connect_retry=0,
    )
    result = ResultSerializer(output)
    assert set(result) == {"iol-r1"}
    for result_data in result["iol-r1"].values():
        assert "TCP connection error: 'timed out'" in result_data
        assert f"containerlab.lab:{connection_port or port}" in result_data
    connection.connect.assert_called_once_with(
        ("containerlab.lab", connection_port or port)
    )
    assert output.failed


@skip_if_no_nornir
def test_retry_runner_connection_check():
    lab_inventory = yaml.safe_load("""
hosts:
  ceos-spine-1:
    hostname: containerlab.lab
    platform: arista_eos
    username: admin
    password: admin
    port: 2200
""")
    host = lab_inventory["hosts"]["ceos-spine-1"]
    try:
        with socket.create_connection((host["hostname"], host["port"]), timeout=1):
            pass
    except OSError as exc:
        pytest.skip(f"cEOS lab unavailable: {exc}")
    nr = init(lab_inventory, "RetryRunner")
    output = nr.run(
        task=netmiko_send_commands,
        commands=["show clock"],
        connection_name="netmiko",
        run_connect_check=True,
        run_connect_retry=1,
    )
    nr.close_connections()
    assert not output.failed, ResultSerializer(output, add_details=True)
    assert ResultSerializer(output)["ceos-spine-1"]["show clock"].strip()


@skip_if_no_nornir
@pytest.mark.parametrize("connect_retry", [0, 2])
@pytest.mark.parametrize("always_fail", [False, True])
def test_retry_runner_offline_connection_attempts(
    monkeypatch, connect_retry, always_fail
):
    runner = importlib.import_module("nornir_salt.plugins.runners.RetryRunner")
    stop_event = threading.Event()
    connectors_q, work_q = queue.Queue(), queue.Queue()
    clock, events = [0.0], []
    delays = iter([10, 20, 30])

    def now():
        clock[0] += 0.25
        return clock[0]

    def sleep(seconds):
        events.append(("sleep", seconds))
        clock[0] += seconds

    def jitter(start, stop):
        assert (start, stop) == (0, 100)
        return next(delays)

    def open_connection(*args, **kwargs):
        events.append(("open", clock[0]))
        if always_fail or host.open_connection.call_count == 1:
            raise RuntimeError("offline connection failure")

    host = Mock(name="host", connections={})
    host.name = "offline-host"
    host.get.return_value = None
    host.get_connection_parameters.return_value.extras = {}
    host.open_connection.side_effect = open_connection
    task = Mock(name="task")
    params = {"connection_retry": 0, "timestamp": 0, "connection_name": ["netmiko"]}
    connectors_q.put((task, host, params, {}))
    # Stop once the connector hands the host to the worker, even on exhaustion.
    original_put = work_q.put

    def completed(work):
        original_put(work)
        stop_event.set()

    monkeypatch.setattr(work_q, "put", completed)
    monkeypatch.setattr(runner, "time", SimpleNamespace(monotonic=now, sleep=sleep))
    monkeypatch.setattr(runner, "random", SimpleNamespace(randrange=jitter))
    runner.connector(
        stop_event,
        connectors_q,
        work_q,
        1000,
        100,
        connect_retry,
        {},
        [],
        5,
        False,
        None,
    )

    attempts = connect_retry + 1 if always_fail else min(connect_retry + 1, 2)
    assert host.open_connection.call_count == attempts
    assert [kind for kind, _ in events] == ["sleep", "open"] * attempts
    assert [value for kind, value in events if kind == "sleep"] == [
        (index + 1) / 100 for index in range(attempts)
    ]
    starts = [value for kind, value in events if kind == "open"]
    for retry, (previous, current) in enumerate(zip(starts, starts[1:]), 1):
        assert current - previous >= retry  # linear backoff in seconds
    assert params["connection_retry"] == attempts - 1
    assert ("connect_exception" in params) == (always_fail or connect_retry == 0)
    assert work_q.qsize() == 1
    assert connectors_q.unfinished_tasks == 0


@skip_if_no_nornir
@pytest.mark.parametrize("connect_splay", [0, 100])
@pytest.mark.parametrize("existing", [[], ["netmiko"], ["netmiko", "ncclient"]])
def test_retry_runner_offline_reuses_connections(monkeypatch, existing, connect_splay):
    runner = importlib.import_module("nornir_salt.plugins.runners.RetryRunner")
    stop_event = threading.Event()
    connectors_q, work_q = queue.Queue(), queue.Queue()
    host = Mock(connections=dict.fromkeys(existing))
    host.name = "offline-host"
    host.get.return_value = None
    host.get_connection_parameters.return_value.extras = {}
    sleep = Mock()
    jitter = Mock(return_value=25)
    monkeypatch.setattr(runner, "time", SimpleNamespace(sleep=sleep))
    monkeypatch.setattr(runner, "random", SimpleNamespace(randrange=jitter))
    monkeypatch.setattr(work_q, "put", lambda work: stop_event.set())
    params = {
        "connection_retry": 0,
        "timestamp": 0,
        "connection_name": ["netmiko", "ncclient"],
    }
    connectors_q.put((Mock(), host, params, {}))
    runner.connector(
        stop_event, connectors_q, work_q, 1000, connect_splay, 2, {}, [], 5, False, None
    )

    missing = [name for name in params["connection_name"] if name not in existing]
    assert [call.args[0] for call in host.open_connection.call_args_list] == missing
    assert (
        jitter.call_count == sleep.call_count == (len(missing) if connect_splay else 0)
    )
    assert all(call.args == (0.025,) for call in sleep.call_args_list)
    assert connectors_q.unfinished_tasks == 0


@skip_if_no_nornir
@pytest.mark.parametrize("reconnect_on_fail", [False, True])
def test_retry_runner_offline_task_retry(monkeypatch, reconnect_on_fail):
    from nornir.core.task import MultiResult, Result

    runner = importlib.import_module("nornir_salt.plugins.runners.RetryRunner")
    stop_event = threading.Event()
    connectors_q, work_q = queue.Queue(), queue.Queue()
    task, host = Mock(), Mock()
    task.name, host.name = "offline-task", "offline-host"
    failed = MultiResult(task.name)
    failed.append(Result(host=host, failed=True, exception=RuntimeError("retry me")))
    task.results = failed
    task.start.return_value = failed
    params = {
        "connection_retry": 0,
        "task_retry": 0,
        "timestamp": 0,
        "connection_name": ["netmiko"],
    }
    work_q.put((task, host, params, {}))
    original_put = work_q.put

    def requeued(work):
        original_put(work)
        stop_event.set()

    monkeypatch.setattr(work_q, "put", requeued)
    original_connector_put = connectors_q.put

    def reconnect(work):
        assert work[2]["connection_retry"] == 1
        original_connector_put(work)
        stop_event.set()

    monkeypatch.setattr(connectors_q, "put", reconnect)
    close = Mock()
    monkeypatch.setattr(runner, "close_host_connection", close)
    monkeypatch.setattr(
        runner, "time", SimpleNamespace(monotonic=lambda: 10, sleep=Mock())
    )
    monkeypatch.setattr(runner, "random", SimpleNamespace(randrange=lambda a, b: 25))
    runner.worker(
        stop_event, connectors_q, work_q, 1000, 100, 1, 2, reconnect_on_fail, []
    )

    task.start.assert_called_once_with(host)
    assert params["task_retry"] == 1
    assert params["connection_retry"] == int(reconnect_on_fail)
    assert params["timestamp"] == 10
    assert close.call_count == int(reconnect_on_fail)
    if reconnect_on_fail:
        close.assert_called_once_with(host, ["netmiko"])
    assert connectors_q.qsize() == int(reconnect_on_fail)
    assert work_q.qsize() == int(not reconnect_on_fail)
    assert work_q.unfinished_tasks == int(not reconnect_on_fail)


@pytest.mark.parametrize(
    "setting",
    [
        "num_workers",
        "num_connectors",
        "connect_retry",
        "task_retry",
        "connect_backoff",
        "task_backoff",
        "connect_splay",
        "task_splay",
        "task_timeout",
        "connect_timeout",
    ],
)
@pytest.mark.parametrize("value", [-1, True, "1", float("nan"), float("inf")])
def test_retry_runner_offline_invalid_settings(setting, value):
    with pytest.raises((TypeError, ValueError), match=setting):
        RetryRunner(**{setting: value})


@pytest.mark.parametrize(
    "setting",
    [
        "run_num_workers",
        "run_num_connectors",
        "run_connect_retry",
        "run_task_retry",
        "run_connect_timeout",
    ],
)
@pytest.mark.parametrize("value", [-1, True, "1", float("nan"), float("inf")])
def test_retry_runner_offline_invalid_run_settings(monkeypatch, setting, value):
    runner = importlib.import_module("nornir_salt.plugins.runners.RetryRunner")
    thread = Mock()
    monkeypatch.setattr(runner.threading, "Thread", thread)
    task = Mock(params={setting: value, "connection_name": "netmiko"})
    with pytest.raises((TypeError, ValueError), match=setting):
        RetryRunner().run(task, [])
    thread.assert_not_called()


@pytest.mark.parametrize("raises", [False, True])
def test_retry_runner_offline_zero_task_jitter_and_exception(monkeypatch, raises):
    from nornir.core.task import MultiResult, Result

    runner = importlib.import_module("nornir_salt.plugins.runners.RetryRunner")
    stop_event = threading.Event()
    connectors_q, work_q = queue.Queue(), queue.Queue()
    host, task = Mock(), Mock()
    host.name, task.name = "offline-host", "offline-task"
    results = {}
    params = {
        "connection_retry": 0,
        "task_retry": 0,
        "timestamp": 0,
        "connection_name": [],
    }

    def start(host):
        stop_event.set()
        if raises:
            raise RuntimeError("unexpected task error")
        result = MultiResult(task.name)
        result.append(Result(host=host, result="done"))
        return result

    task.start.side_effect = start
    task.results.failed = False
    jitter = Mock(side_effect=AssertionError("zero jitter must not call randrange"))
    monkeypatch.setattr(runner, "random", SimpleNamespace(randrange=jitter))
    work_q.put((task, host, params, results))
    runner.worker(stop_event, connectors_q, work_q, 0, 0, 0, 0, False, [])
    task.start.assert_called_once_with(host)
    assert work_q.unfinished_tasks == 0
    assert results[host.name].failed == raises
    if raises:
        assert "unexpected task error" in str(results[host.name][0].exception)


def test_retry_runner_offline_connector_exception_accounting(monkeypatch):
    runner = importlib.import_module("nornir_salt.plugins.runners.RetryRunner")
    stop_event = threading.Event()
    connectors_q, work_q = queue.Queue(), queue.Queue()
    host, task = Mock(connections={}), Mock()
    host.name, task.name = "offline-host", "offline-task"
    host.get.return_value = None
    host.open_connection.side_effect = RuntimeError("connection failed")
    results = {}
    params = {"connection_retry": 0, "timestamp": 0, "connection_name": ["netmiko"]}

    def close(*args):
        stop_event.set()
        raise RuntimeError("unexpected cleanup error")

    monkeypatch.setattr(runner, "close_host_connection", close)
    connectors_q.put((task, host, params, results))
    runner.connector(stop_event, connectors_q, work_q, 0, 0, 0, {}, [], 5, False, None)
    assert connectors_q.unfinished_tasks == 0
    assert work_q.empty()
    assert results[host.name].failed
    assert "unexpected cleanup error" in str(results[host.name][0].exception)


@pytest.mark.parametrize(
    "setting", ["num_workers", "num_connectors", "task_timeout", "connect_timeout"]
)
@pytest.mark.parametrize("value", [0, 1.5])
def test_retry_runner_offline_positive_settings(setting, value):
    if value == 1.5 and setting.endswith("timeout"):
        assert getattr(RetryRunner(**{setting: value}), setting) == value
    else:
        with pytest.raises((TypeError, ValueError), match=setting):
            RetryRunner(**{setting: value})


def test_retry_runner_offline_thread_start_cleanup(monkeypatch):
    runner = importlib.import_module("nornir_salt.plugins.runners.RetryRunner")
    first, second, timer = Mock(), Mock(), Mock()
    second.start.side_effect = RuntimeError("thread start failed")
    monkeypatch.setattr(runner.threading, "Thread", Mock(side_effect=[first, second]))
    monkeypatch.setattr(runner.threading, "Timer", Mock(return_value=timer))
    task = Mock(params={"connection_name": "netmiko"})
    instance = RetryRunner(num_connectors=2, num_workers=1)
    instance.job = Mock()
    with pytest.raises(RuntimeError, match="thread start failed"):
        instance.run(task, [])
    first.join.assert_called_once()
    second.join.assert_not_called()
    timer.cancel.assert_called_once()
    assert instance.job is None


@pytest.mark.parametrize("raises", [False, True])
def test_retry_runner_offline_run_zero_jitter(monkeypatch, raises):
    from nornir.core.task import Task

    nr = init({"hosts": {"offline-host": {"hostname": "127.0.0.1"}}}, "RetryRunner")
    nr.runner.connect_splay = 0
    nr.runner.task_splay = 0
    if raises:
        monkeypatch.setattr(
            Task, "start", Mock(side_effect=RuntimeError("task crashed"))
        )
    result = nr.run(
        task=nr_test,
        run_num_workers=1,
        run_num_connectors=1,
        run_task_retry=0,
        run_connect_retry=0,
    )
    assert result["offline-host"].failed == raises
    if raises:
        assert "task crashed" in str(result["offline-host"][0].exception)


@pytest.mark.parametrize(
    "setting,value",
    [
        ("connect_check", "yes"),
        ("reconnect_on_fail", 1),
        ("creds_retry", "credentials"),
        ("task_stop_errors", [1]),
    ],
)
@pytest.mark.parametrize("per_run", [False, True])
def test_retry_runner_offline_pydantic_settings(monkeypatch, setting, value, per_run):
    from pydantic import ValidationError

    runner = importlib.import_module("nornir_salt.plugins.runners.RetryRunner")
    thread = Mock()
    monkeypatch.setattr(runner.threading, "Thread", thread)
    name = f"run_{setting}" if per_run else setting
    with pytest.raises(ValidationError, match=name):
        if per_run:
            RetryRunner().run(
                Mock(params={name: value, "connection_name": "netmiko"}), []
            )
        else:
            RetryRunner(**{name: value})
    thread.assert_not_called()


def test_retry_runner_offline_pydantic_defaults():
    import inspect
    from nornir_salt.utils.pydantic_models import model_RetryRunner

    defaults = model_RetryRunner().model_dump()
    assert defaults == {
        name: parameter.default
        for name, parameter in inspect.signature(RetryRunner).parameters.items()
    }
    settings = model_RetryRunner(
        run_num_workers=1,
        run_connect_retry=0,
        connect_splay=0,
        task_splay=0,
        creds_retry=["alternate", {"username": "user"}],
    )
    assert settings.num_workers == 1
    assert settings.connect_retry == settings.connect_splay == settings.task_splay == 0


@pytest.mark.parametrize(
    "changed",
    [
        {},
        {"port": 2222},
        {"username": "other"},
        {"password": "other"},
        {"hostkey_policy": "reject"},
    ],
)
def test_retry_runner_offline_jumphost_identity(monkeypatch, changed):
    from nornir.core.inventory import Host

    runner = importlib.import_module("nornir_salt.plugins.runners.RetryRunner")
    clients = [Mock(), Mock()]
    for client in clients:
        client.get_transport.return_value.is_active.return_value = True
    ssh = Mock(
        client=SimpleNamespace(SSHClient=Mock(side_effect=clients)),
        AutoAddPolicy=Mock(),
        RejectPolicy=Mock(),
        WarningPolicy=Mock(),
    )
    monkeypatch.setattr(runner, "paramiko", ssh, raising=False)
    cache = {}
    config = {"hostname": "gateway", "username": "user", "password": "secret"}
    first = Host("first", hostname="target1", data={"jumphost": config})
    second = Host(
        "second", hostname="target2", data={"jumphost": dict(config, **changed)}
    )
    runner.connect_to_device_behind_jumphost(first, cache)
    runner.connect_to_device_behind_jumphost(second, cache)
    assert ssh.client.SSHClient.call_count == (2 if changed else 1)
    assert len(cache) == (2 if changed else 1)
    assert "secret" not in repr(list(cache))


def test_retry_runner_offline_jumphost_concurrent_replacement(monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from nornir.core.inventory import Host

    runner = importlib.import_module("nornir_salt.plugins.runners.RetryRunner")
    old, new = Mock(), Mock()
    for client in (old, new):
        client.get_transport.return_value.is_active.return_value = True
    ssh = Mock(
        client=SimpleNamespace(SSHClient=Mock(side_effect=[old, new])),
        AutoAddPolicy=Mock(),
        RejectPolicy=Mock(),
        WarningPolicy=Mock(),
    )
    monkeypatch.setattr(runner, "paramiko", ssh, raising=False)
    config = {"hostname": "gateway"}
    hosts = [
        Host(str(i), hostname="target", data={"jumphost": config}) for i in range(3)
    ]
    cache = {}
    runner.connect_to_device_behind_jumphost(hosts[0], cache)
    old.get_transport.return_value.is_active.return_value = False
    entered, release = threading.Event(), threading.Event()

    def connect(**kwargs):
        entered.set()
        assert release.wait(2)

    new.connect.side_effect = connect
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(runner.connect_to_device_behind_jumphost, hosts[1], cache)
        assert entered.wait(2)
        second = pool.submit(runner.connect_to_device_behind_jumphost, hosts[2], cache)
        release.set()
        first.result(timeout=2)
        second.result(timeout=2)
    assert ssh.client.SSHClient.call_count == 2
    old.close.assert_called_once()
    new.close.assert_not_called()
    assert new.get_transport.return_value.open_channel.call_count == 2
    # The original host must not reuse its channel from the dead transport.
    channel = hosts[0].connections["jumphost_gateway_channel"]
    runner.connect_to_device_behind_jumphost(hosts[0], cache)
    channel.close.assert_called_once()
    assert new.get_transport.return_value.open_channel.call_count == 3


@pytest.mark.parametrize("policy", ["autoadd", "reject", "warning", "invalid"])
def test_retry_runner_offline_jumphost_hostkeys(monkeypatch, policy):
    from nornir.core.inventory import Host

    runner = importlib.import_module("nornir_salt.plugins.runners.RetryRunner")
    client = Mock()
    ssh = Mock(
        client=SimpleNamespace(SSHClient=Mock(return_value=client)),
        AutoAddPolicy=Mock(),
        RejectPolicy=Mock(),
        WarningPolicy=Mock(),
    )
    monkeypatch.setattr(runner, "paramiko", ssh, raising=False)
    host = Host(
        "host",
        hostname="target",
        data={
            "jumphost": {
                "hostname": "gateway",
                "hostkey_policy": policy,
                "known_hosts": "known_hosts",
            }
        },
    )
    if policy == "invalid":
        with pytest.raises(ValueError, match="hostkey_policy"):
            runner.connect_to_device_behind_jumphost(host, {})
        ssh.client.SSHClient.assert_not_called()
        return
    runner.connect_to_device_behind_jumphost(host, {})
    client.load_system_host_keys.assert_called_once_with()
    client.load_host_keys.assert_called_once_with("known_hosts")
    factory = {
        "autoadd": ssh.AutoAddPolicy,
        "reject": ssh.RejectPolicy,
        "warning": ssh.WarningPolicy,
    }[policy]
    client.set_missing_host_key_policy.assert_called_once_with(factory.return_value)
    assert "hostkey_policy" not in client.connect.call_args.kwargs
    assert "known_hosts" not in client.connect.call_args.kwargs


@pytest.mark.parametrize("splay", [None, 0, 100])
def test_retry_runner_offline_credential_jitter(monkeypatch, splay):
    from nornir.core.inventory import Host
    from nornir.core.task import Task

    connections = importlib.import_module("nornir_salt.plugins.tasks.connections")
    host = Host("host")
    monkeypatch.setattr(
        Host,
        "open_connection",
        Mock(side_effect=[RuntimeError(), RuntimeError(), None]),
    )
    task = Mock(spec=Task)
    task.host = host
    task.nornir = Mock()
    sleep, jitter = Mock(), Mock(side_effect=[10, 20])
    monkeypatch.setattr(connections, "time", SimpleNamespace(sleep=sleep))
    monkeypatch.setattr(
        connections, "random", SimpleNamespace(randrange=jitter), raising=False
    )
    kwargs = {} if splay is None else {"reconnect_splay": splay}
    result = connections.conn_open(
        task=task, conn_name="netmiko", reconnect=[{}, {}], **kwargs
    )
    assert not result.failed
    assert jitter.call_count == (2 if splay else 0)
    assert [call.args[0] for call in sleep.call_args_list] == (
        [0.1, 0.01, 0.1, 0.02] if splay else [0.1, 0.1]
    )


@pytest.mark.parametrize("failure", ["load_host_keys", "connect"])
def test_retry_runner_offline_jumphost_failed_handshake(monkeypatch, failure):
    from nornir.core.inventory import Host

    runner = importlib.import_module("nornir_salt.plugins.runners.RetryRunner")
    failed, good = Mock(), Mock()
    getattr(failed, failure).side_effect = RuntimeError("untrusted or unavailable")
    ssh = Mock(
        client=SimpleNamespace(SSHClient=Mock(side_effect=[failed, good])),
        AutoAddPolicy=Mock(),
        RejectPolicy=Mock(),
        WarningPolicy=Mock(),
    )
    monkeypatch.setattr(runner, "paramiko", ssh, raising=False)
    host = Host(
        "host",
        hostname="target",
        data={
            "jumphost": {
                "hostname": "gateway",
                "hostkey_policy": "reject",
                "known_hosts": "keys",
            }
        },
    )
    cache = {}
    with pytest.raises(RuntimeError, match="failed connection to jumphost") as exc:
        runner.connect_to_device_behind_jumphost(host, cache)
    assert "untrusted or unavailable" in str(exc.value.__cause__)
    failed.close.assert_called_once()
    assert "jumphost_ssh_client" not in next(iter(cache.values()))
    runner.connect_to_device_behind_jumphost(host, cache)
    good.connect.assert_called_once()
    assert next(iter(cache.values()))["jumphost_ssh_client"] is good


def test_retry_runner_offline_credential_jitter_forwarding(monkeypatch):
    runner = importlib.import_module("nornir_salt.plugins.runners.RetryRunner")
    stop_event = threading.Event()
    connectors_q, work_q = queue.Queue(), queue.Queue()
    host = Mock(connections={})
    host.name = "host"
    host.get.return_value = None
    params = {"connection_retry": 0, "timestamp": 0, "connection_name": ["netmiko"]}
    task = Mock()
    connectors_q.put((task, host, params, {}))
    open_connection = Mock()
    monkeypatch.setattr(runner, "conn_open", open_connection)
    monkeypatch.setattr(runner, "time", SimpleNamespace(sleep=Mock()))
    monkeypatch.setattr(runner, "random", SimpleNamespace(randrange=lambda a, b: 25))
    monkeypatch.setattr(work_q, "put", lambda work: stop_event.set())
    runner.connector(
        stop_event, connectors_q, work_q, 0, 100, 0, {}, ["alternate"], 5, False, None
    )
    assert open_connection.call_args.kwargs["reconnect_splay"] == 100
    assert open_connection.call_args.kwargs["reconnect"] == ["alternate"]
    assert connectors_q.unfinished_tasks == 0


@pytest.mark.parametrize("closed", [False, True])
def test_retry_runner_offline_jumphost_channel_reuse(monkeypatch, closed):
    from nornir.core.inventory import Host

    runner = importlib.import_module("nornir_salt.plugins.runners.RetryRunner")
    client = Mock()
    transport = client.get_transport.return_value
    first_channel, second_channel = Mock(closed=closed), Mock(closed=False)
    first_channel.get_transport.return_value = transport
    transport.open_channel.side_effect = [first_channel, second_channel]
    ssh = Mock(
        client=SimpleNamespace(SSHClient=Mock(return_value=client)),
        AutoAddPolicy=Mock(),
        RejectPolicy=Mock(),
        WarningPolicy=Mock(),
    )
    monkeypatch.setattr(runner, "paramiko", ssh, raising=False)
    config = {"hostname": "gateway", "hostkey_policy": "reject"}
    host = Host("host", hostname="target", data={"jumphost": config})
    cache = {}
    assert runner.connect_to_device_behind_jumphost(host, cache) is first_channel
    channel = runner.connect_to_device_behind_jumphost(host, cache)
    assert channel is (second_channel if closed else first_channel)
    assert transport.open_channel.call_count == (2 if closed else 1)
    assert first_channel.close.call_count == int(closed)
    client.connect.assert_called_once()
    assert config == {"hostname": "gateway", "hostkey_policy": "reject"}
