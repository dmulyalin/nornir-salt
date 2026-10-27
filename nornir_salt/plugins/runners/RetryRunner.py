"""
RetryRunner plugin
##################

RetryRunner plugin implements retry logic to improve task execution reliability.

Primary usecase for RetryRunner is to make Nornir task execution as reliable as possible
utilizing queuing, retries, connections splaying and linear backoff mechanisms.

RetryRunner Architecture
========================

RetryRunner helps to control the rate of connections establishment by limiting the number of
connector workers.

For example, if ``num_connectors`` is 5, meaning at any point in time there are only 5 workers
establishing connections to devices, even if there are 100 devices, RetryRunner will connect
only with 5 of them at a time. This is very helpful when connections rate need to be limited
due to operations restrictions like AAA (TACACS, RADIUS) servers load.

When new task started and if no connection exist to device that this task makes the use of,
RetryRunner attempts to connect to device retrying up to ``connect_retry`` times.

Once connection established, task handed over to worker threads for execution, workers
will retry the task up to ``task_retry`` times if task fails.

Connection parameters such as timeouts or usage of SSH keys handled by Nornir Connection plugins.
RetryRunner calls Nornir to start the connection, further connection establishment details
controlled by Connection plugin itself.

.. image:: ../_images/RetryRunner_v0.png

Sample Usage
============

Instruct Nornir to use RetryRunner on instantiation and run your tasks::

    from nornir import InitNornir

    NornirObj = InitNornir(
        runner={
            "plugin": "RetryRunner",
            "options": {
                "num_workers": 100,
                "num_connectors": 10,
                "connect_retry": 3,
                "connect_backoff": 1000,
                "connect_splay": 100,
                "task_retry": 3,
                "task_backoff": 1000,
                "task_splay": 100
            }
        }
    )

Sample code to demonstrate usage of ``RetryRunner``, ``DictInventory`` and ``ResultSerializer`` plugins::

    import yaml
    import pprint
    from nornir import InitNornir
    from nornir.core.task import Result, Task
    from nornir_netmiko import netmiko_send_command, netmiko_send_config
    from nornir_salt.plugins.functions import ResultSerializer

    inventory_data = '''
    hosts:
      R1:
        hostname: 192.168.1.151
        platform: ios
        groups: [lab]
      R2:
        hostname: 192.168.1.153
        platform: ios
        groups: [lab]
      R3:
        hostname: 192.168.1.154
        platform: ios
        groups: [lab]

    groups:
      lab:
        username: cisco
        password: cisco
    '''

    inventory_dict = yaml.safe_load(inventory_data)

    NornirObj = InitNornir(
        runner={
            "plugin": "RetryRunner",
            "options": {
                "num_workers": 100,
                "num_connectors": 10,
                "connect_retry": 3,
                "connect_backoff": 1000,
                "connect_splay": 100,
                "task_retry": 3,
                "task_backoff": 1000,
                "task_splay": 100
            }
        },
        inventory={
            "plugin": "DictInventory",
            "options": {
                "hosts": inventory_dict["hosts"],
                "groups": inventory_dict["groups"],
                "defaults": inventory_dict.get("defaults", {})
            }
        },
    )

    def _task_group_netmiko_send_commands(task, commands):
        # run commands
        for command in commands:
            task.run(
                task=netmiko_send_command,
                command_string=command,
                name=command
            )
        return Result(host=task.host)

    # run single task
    result1 = NornirObj.run(
        task=netmiko_send_command,
        command_string="show clock"
    )

    # run grouped tasks
    result2 = NornirObj.run(
        task=_task_group_netmiko_send_commands,
        commands=["show clock", "show run | inc hostname"],
        connection_name="netmiko"
    )

    # run another single task
    result3 = NornirObj.run(
        task=netmiko_send_command,
        command_string="show run | inc hostname"
    )

    NornirObj.close_connections()

    # Print results
    formed_result1 = ResultSerializer(result1, add_details=True)
    pprint.pprint(formed_result1, width=100)

    formed_result2 = ResultSerializer(result2, add_details=True)
    pprint.pprint(formed_result2, width=100)

    formed_result3 = ResultSerializer(result3, add_details=True)
    pprint.pprint(formed_result3, width=100)

Connections handling
====================

.. warning::  For parent or grouped tasks need to explicitly provide connection plugin
    ``connection_name`` task parameter such as ``netmiko, napalm, scrapli, scrapli_netconf``,
    etc. Specifying ``connection_name`` attribute for parent or grouped tasks not required if that
    task has ``CONNECTION_NAME`` global variable defined within it. Lack of ``connection_name``
    attribute will result in skipping connections retry logic, jumphost connection logic or credentials
    retry logic and connections to all hosts initiated simultaneously up to the number of ``num_workers``
    option.

Above restriction stems from the fact that Nornir tasks does not have built-in way to communicate
the set of connection plugins that task will use. By convention, task may contain ``CONNECTION_NAME``
global parameter to identify the name(s) of connection plugin(s) task uses.

``CONNECTION_NAME`` global parameter can be a single connection name or a comma separated list of
connection plugin names that task and its subtask uses. RetryRunner honors this parameter and tries
to establish all specified connections before starting the task.

Alternatively, inline task parameter ``connection_name`` can be provided on task run.

However, only parent/main/grouped task supports task parameters, subtasks does not support them.
As a result, if subtask uses connection plugin different from specified in parent task ``connection_name``
parameter or ``CONNECTION_NAME`` variable, subtask connection does not handled by RetryRunner
connections establishment logic and connection established on subtask start simultaneously in parallel
up to the number of ``num_workers`` option.

Sample task that uses different connection plugins for subtasks::

    from nornir.core.task import Result, Task
    from nornir_scrapli.tasks import netconf_get_config
    from nornir_scrapli.tasks import send_command as scrapli_send_command
    from nornir_netmiko.tasks import netmiko_send_command

    # inform RetryRunner to establish these connections
    CONNECTION_NAME = "scrapli_netconf, netmiko, scrapli"

    def task(task: Task) -> Result:

        task.run(
            name="Pull Configuration Using Scrapli Netconf",
            task=netconf_get_config,
            source="running"
        )

        task.run(
            name="Pull Configuration using Netmiko",
            task=netmiko_send_command,
            command_string="show run",
            enable=True
        )

        task.run(
            name="Pull Configuration using Scrapli",
            task=scrapli_send_command,
            command="show run"
        )

        return Result(host=task.host)


RetryRunner task parameters
===========================

RetryRunner supports a number of task parameters to influence its behavior on a per-task
basis. These parameters can be supplied to the task as key/value arguments to override
RetryRunner options supplied on Nornir object instantiation.

RetryRunner task parameters description:

* ``run_connect_retry`` - maximum number of additional connection retries. Zero allows only the initial attempt
* ``run_task_retry`` - maximum number of additional task retries. Zero allows only the initial attempt
* ``run_creds_retry`` - list of connection credentials and parameters to retry while connecting to device
* ``run_num_workers`` - number of threads for tasks execution
* ``run_num_connectors`` - number of threads for device connections
* ``run_reconnect_on_fail`` - if True, re-establish connection on task failure
* ``run_task_stop_errors`` - list of glob patterns to stop retrying if seen in task exception string
* ``connection_name`` - name of connection plugin to use to initiate connection to device

.. note:: Tasks retry count is the smallest of ``run_connect_retry`` and ``run_task_retry`` counters,
    i.e. ``task_retry`` set to ``min(run_connect_retry, run_task_retry)`` value.

.. warning:: only main/parent tasks support RetryRunner task parameters, subtasks does not support them.

Sample code to use RetryRunner task parameters::

    import yaml
    from nornir import InitNornir
    from nornir.core.task import Result, Task
    from nornir_netmiko import netmiko_send_command

    inventory_data = '''
    hosts:
      R1:
        hostname: 192.168.1.151
        platform: ios
        groups: [lab]

    groups:
      lab:
        username: foo
        password: bar

    defaults:
      data:
        credentials:
          local_creds:
            username: nornir
            password: nornir
          dev_creds:
            username: devops
            password: foobar
    '''

    inventory_dict = yaml.safe_load(inventory_data)

    NornirObj = InitNornir(
        runner={
            "plugin": "RetryRunner"
        },
        inventory={
            "plugin": "DictInventory",
            "options": {
                "hosts": inventory_dict["hosts"],
                "groups": inventory_dict["groups"],
                "defaults": inventory_dict.get("defaults", {})
            }
        },
    )

    # run task without retrying - simulate QueueRunner behavior
    result1 = NornirObj.run(
        task=netmiko_send_command,
        command_string="show clock",
        run_connect_retry=0,
        run_task_retry=0,
    )

    # run task one by one - simulate SerialRunner behavior but with retrying
    result2 = NornirObj.run(
        task=netmiko_send_command,
        command_string="show clock",
        run_num_workers=1,
        run_num_connectors=1,
    )

    # retry credentials if login fails but without retrying connection establishment
    result3 = NornirObj.run(
        task=netmiko_send_command,
        command_string="show clock",
        run_creds_retry=["local_creds", "dev_creds"],
        run_connect_retry=0,
    )

Connecting to hosts behind jumphost
===================================

RetryRunner implements logic to connect with hosts behind bastion/jumphosts.

To connect to devices behind jumphost, need to define jumphost parameters in host's inventory data::

    hosts:
      R1:
        hostname: 192.168.1.151
        platform: ios
        username: test
        password: test
        data:
          jumphost:
            hostname: 10.1.1.1
            port: 22
            password: jump_host_password
            username: jump_host_user

Set ``hostkey_policy: reject`` in ``jumphost`` to reject unknown SSH host keys.
System known-hosts keys are loaded automatically. Set ``known_hosts`` to a file
path to load additional trusted keys. ``hostkey_policy`` also accepts ``warning``
and ``autoadd``. The default is ``autoadd`` for compatibility. It trusts unknown
keys. Known keys that do not match are rejected regardless of policy.

Jumphost sessions are shared only when their connection and trust settings match.
Session creation and replacement are synchronized independently for each session.

.. note:: Only Netmiko ``connection_name="netmiko"`` and Ncclient ``connection_name="ncclient"``
    tasks, support connecting to hosts behind Jumphosts using above inventory data.

Retrying different credentials
==============================

RetryRunner is capable of trying several credentials while connecting to device.
Credentials tried in a sequence starting with host's inventory username and
password parameters moving on to connection parameters supplied in ``creds_retry``
RetryRunner option.

Credentials retry logic implemented using ``conn_open`` task plugin in a way that
``creds_retry`` list content passed as ``reconnect`` argument to ``conn_open`` task.
Each fallback attempt receives fresh jitter controlled by ``connect_splay``.
The existing 100 ms delay after a failed credential attempt is retained.

Items of ``creds_retry`` list tried sequentially until connection successfully established,
or list runs out of items. If no connection established after all ``creds_retry`` items tried,
this connection attempt considered unsuccessful, hosts queued back to connectors queue and
process repeats on next try.

Sample inventory with retry credentials::

    hosts:
      R1:
        hostname: 192.168.1.151
        platform: ios
        groups: [lab]
        data:
          credentials:
            local_creds:
              username: admin
              password: admin

    groups:
      lab:
        username: foo
        password: bar

    defaults:
      data:
        credentials:
          local_creds:
            username: nornir
            password: nornir
            extras:
              optional_args:
                key_file: False
          dev_creds:
            username: devops
            password: foobar

``credentials`` defined within ``default`` data section, but can be defined
inside host or groups data. Credentials definitions does not merged across
different data sections but searched in a ``host -> groups -> defaults`` order
and first one encountered used.

Sample code to use ``creds_retry``::

    from nornir import InitNornir

    NornirObj = InitNornir(
        runner={
            "plugin": "RetryRunner",
            "options": {
                "creds_retry": ["local_creds", "dev_creds"]
            }
        }
    )

``creds_retry`` items parameters used as Nornir ``host.open_connection`` kwargs,
as a result all arguments of
`open_connection <https://nornir.readthedocs.io/en/latest/api/nornir/core/inventory.html#nornir.core.inventory.Host.open_connection>`_
method are supported such as ``username``, ``password``, ``port``, ``extras`` etc.

API Reference
=============

.. autoclass:: nornir_salt.plugins.runners.RetryRunner.RetryRunner
"""

import logging
import hashlib
import queue
import random
import threading
import time
from fnmatch import fnmatchcase
from typing import Any, Dict, List

from nornir.core.inventory import Host
from nornir.core.task import AggregatedResult, MultiResult, Result, Task

from nornir_salt.plugins.tasks.connections import conn_check, conn_open
from nornir_salt.utils.pydantic_models import model_RetryRunner

try:
    import paramiko

    HAS_PARAMIKO = True
except ImportError:
    HAS_PARAMIKO = False

log = logging.getLogger(__name__)
LOCK = threading.Lock()


def worker(
    stop_event: threading.Event,
    connectors_q: queue.Queue,
    work_q: queue.Queue,
    task_backoff: int,
    task_splay: int,
    task_retry: int,
    connect_retry: int,
    reconnect_on_fail: bool,
    stop_errors: List[str],
) -> None:
    """
    Worker thread function that executes tasks with retry logic, linear backoff, and splaying.
    Handles task failures by retrying or reconnecting as configured.
    """
    while not stop_event.is_set():
        try:
            work = work_q.get(block=True, timeout=0.1)
        except queue.Empty:
            continue
        task, host, params, result = work
        try:
            # check if has exception recorded in params by connector thread
            if params.get("connect_exception"):
                work_result = MultiResult(task.name)
                work_result.append(
                    Result(
                        host,
                        result=params["connect_exception"],
                        failed=True,
                        exception=params["connect_exception"],
                        name=task.name,
                    )
                )
            else:
                # check if need backoff task retry for this host
                if params["task_retry"] > 0:
                    elapsed = time.monotonic() - params["timestamp"]
                    should_wait = (params["task_retry"] * task_backoff) / 1000
                    if elapsed < should_wait:
                        work_q.put(work)
                        stop_event.wait(0.1)
                        continue
                log.info(
                    f"nornir_salt:RetryRunner {host.name} - running task '{task.name}'"
                )
                if task_splay:
                    time.sleep(random.randrange(0, task_splay) / 1000)  # nosec

                work_result = task.start(host)
            # check if need to run task retry logic
            if task.results.failed:
                log.error(
                    f"nornir_salt:RetryRunner {host.name} - task execution retry "
                    f"attempt {params['task_retry']} failed: '{work_result[0].exception}'"
                )
                # check if need to stop because of this error
                stop_error_found = False
                for i in stop_errors:
                    if fnmatchcase(str(work_result[0].exception), i):
                        log.warning(
                            f"nornir_salt:RetryRunner {host.name} - task exception "
                            f"matched stop pattern '{i}', stopping"
                        )
                        stop_error_found = True
                if (
                    not stop_error_found
                    and params["task_retry"] < task_retry
                    and params["connection_retry"] < connect_retry
                ):
                    params["task_retry"] += 1
                    params["timestamp"] = time.monotonic()
                    # recover task results for not to count task as failed
                    for r in task.results:
                        try:
                            r.failed = False
                            r.exception = None
                            r.skip_results = (
                                True  # for ResultSerializer to skip failed attempts
                            )
                        except Exception:
                            log.exception(
                                f"Failed to process {task.name} task result {r}."
                            )
                    if reconnect_on_fail:
                        # close host connections to retry them
                        close_host_connection(host, params["connection_name"])
                        params["connection_retry"] += 1
                        connectors_q.put(work)
                    else:
                        work_q.put(work)
                    continue
            # en-reach result objects with runner statistics
            for result_item in work_result:
                result_item.connection_retry = params["connection_retry"]
                result_item.task_retry = params["task_retry"]
            with LOCK:
                result[host.name] = work_result
                del work_result
            log.info(
                "nornir_salt:RetryRunner {} - task '{}' completed".format(
                    host.name, task.name
                )
            )
        except Exception as exc:
            log.exception(
                "nornir_salt:RetryRunner %s - unexpected %s error", host.name, "worker"
            )
            failure = MultiResult(task.name)
            failure.append(
                Result(host=host, name=task.name, failed=True, exception=exc)
            )
            with LOCK:
                result[host.name] = failure
        finally:
            work_q.task_done()


def connector(
    stop_event: threading.Event,
    connectors_q: queue.Queue,
    work_q: queue.Queue,
    connect_backoff: int,
    connect_splay: int,
    connect_retry: int,
    jumphosts_connections: Dict[str, Any],
    run_creds_retry: List[str],
    run_connect_timeout: int,
    run_connect_check: bool,
    job: object,
) -> None:
    """
    Connector thread function that establishes connections to hosts with retry logic,
    linear backoff, splaying, and support for jumphosts and credential retry.
    """
    while not stop_event.is_set():
        try:
            connection = connectors_q.get(block=True, timeout=0.1)
        except queue.Empty:
            continue
        task, host, params, result = connection
        try:
            # check if need back off connection retry for this host
            if params["connection_retry"] > 0:
                elapsed = time.monotonic() - params["timestamp"]
                should_wait = (params["connection_retry"] * connect_backoff) / 1000
                if elapsed < should_wait:
                    connectors_q.put(connection)
                    stop_event.wait(
                        0.01
                    )  # avoid busy polling during connection backoff
                    continue
            try:
                # initiate connections to host
                for connection_name in params["connection_name"]:
                    if connection_name in host.connections:
                        continue
                    if connect_splay:
                        time.sleep(random.randrange(0, connect_splay) / 1000)  # nosec
                    extras = host.get_connection_parameters(connection_name).extras
                    if host.get("jumphost") and connection_name in [
                        "netmiko",
                        "ncclient",
                    ]:
                        if job is not None:
                            job.event(
                                task="nornir.retrun",
                                resource=[host.name],
                                message=(
                                    "Connecting via jumphost "
                                    f"'{host['jumphost']['hostname']}'"
                                ),
                                severity="INFO",
                            )
                        extras["sock"] = connect_to_device_behind_jumphost(
                            host, jumphosts_connections
                        )
                    # check connection
                    if run_connect_check:
                        if job is not None:
                            job.event(
                                task="nornir.retrun",
                                resource=[host.name],
                                message=(
                                    f"Checking connection '{connection_name}' "
                                    f"with timeout {run_connect_timeout}s"
                                ),
                                severity="INFO",
                            )
                        host_connection_check = conn_check(
                            task, host, connection_name, timeout=run_connect_timeout
                        )
                        if host_connection_check.failed is True:
                            raise Exception(host_connection_check.exception)
                        time.sleep(1)  # sleep a bit to not hit devices SSH rate limit
                    # retry various connection parameters
                    if run_creds_retry:
                        log.info(
                            f"nornir_salt:RetryRunner {host.name} - connecting with creds retry"
                        )
                        if job is not None:
                            job.event(
                                task=f"{job.task}.retryrunner",
                                resource=[host.name],
                                message=(
                                    f"Connecting using '{connection_name}' "
                                    "with credentials retry"
                                ),
                                severity="INFO",
                            )
                        conn_open(
                            task=task,
                            host=host,
                            conn_name=connection_name,
                            reconnect=run_creds_retry,
                            raise_on_error=True,
                            reconnect_splay=connect_splay,
                            extras=extras,
                        )
                    # open connection to host as is
                    else:
                        if job is not None:
                            job.event(
                                task=f"{job.task}.retryrunner",
                                resource=[host.name],
                                message=(
                                    f"Connecting using '{connection_name}', attempt "
                                    f"{params['connection_retry'] + 1} of {connect_retry + 1}"
                                ),
                                severity="INFO",
                            )
                        host.open_connection(
                            connection_name,
                            configuration=task.nornir.config,
                            extras=extras,
                        )
                    log.info(
                        "nornir_salt:RetryRunner {} - started connection: '{}'".format(
                            host.name, connection_name
                        )
                    )
                    if job is not None:
                        job.event(
                            task=f"{job.task}.retryrunner",
                            resource=[host.name],
                            message=f"Connection '{connection_name}' established",
                            severity="INFO",
                        )
            except Exception as e:
                # close host connections to retry it
                close_host_connection(host, [connection_name])
                err_msg = "nornir_salt:RetryRunner {} - connection {}, retry attempt {}, error: '{}'".format(
                    host.name,
                    connection_name,
                    params["connection_retry"],
                    " ".join([i.strip() for i in str(e).splitlines()]),
                )
                if params["connection_retry"] < connect_retry:
                    params["connection_retry"] += 1
                    params["timestamp"] = time.monotonic()
                    log.warning(err_msg)
                    if job is not None:
                        job.event(
                            task=f"{job.task}.retryrunner",
                            resource=[host.name],
                            message=(
                                f"Connection '{connection_name}' failed, "
                                f"retrying attempt {params['connection_retry']} "
                                f"of {connect_retry}: '{e}'"
                            ),
                            severity="WARNING",
                        )
                    connectors_q.put(connection)
                    continue
                else:
                    # record exception in params for worker thread to react on it
                    params["connect_exception"] = err_msg
                    log.error(err_msg)
                    log.exception(e)
                    if job is not None:
                        job.event(
                            task=f"{job.task}.retryrunner",
                            resource=[host.name],
                            message=err_msg,
                            severity="ERROR",
                        )
            work_q.put((task, host, params, result))
        except Exception as exc:
            log.exception(
                "nornir_salt:RetryRunner %s - unexpected %s error",
                host.name,
                "connector",
            )
            failure = MultiResult(task.name)
            failure.append(
                Result(host=host, name=task.name, failed=True, exception=exc)
            )
            with LOCK:
                result[host.name] = failure
        finally:
            connectors_q.task_done()


def close_host_connection(host: Host, connection_names: List[str]) -> None:
    """
    Helper function to close connections to host

    :param host: nornir host object
    :param connection_names: list of connection names to close
    """
    for connection_name in connection_names:
        try:
            host.close_connection(connection_name)
        except Exception:
            _ = host.connections.pop(connection_name, None)
        if host.get("jumphost"):
            channel_name = "jumphost_{}_channel".format(host["jumphost"]["hostname"])
            try:
                host.close_connection(channel_name)
            except Exception:
                _ = host.connections.pop(channel_name, None)


def connect_to_device_behind_jumphost(
    host: Host, jumphosts_connections: Dict[str, Any]
) -> Any:
    """
    Establish connection to devices behind jumphost/bastion
    """

    jumphost = {"timeout": 3, "look_for_keys": False, "allow_agent": False, "port": 22}
    jumphost.update(host["jumphost"])
    policy = jumphost.pop("hostkey_policy", "autoadd")
    known_hosts = jumphost.pop("known_hosts", None)
    policies = {
        "autoadd": paramiko.AutoAddPolicy,
        "reject": paramiko.RejectPolicy,
        "warning": paramiko.WarningPolicy,
    }
    if policy not in policies:
        raise ValueError("jumphost hostkey_policy must be autoadd, reject, or warning")
    # Include credentials and SSH/trust options without putting secrets in cache keys.
    identity = repr((sorted(jumphost.items()), policy, known_hosts)).encode()
    cache_key = hashlib.sha256(identity).hexdigest()
    with LOCK:
        session = jumphosts_connections.setdefault(
            cache_key, {"lock": threading.Lock()}
        )
    # Serialize creation and replacement for this session only. Never remove an entry
    # another connector may already be using.
    with session["lock"]:
        transport = session.get("jumphost_ssh_transport")
        if transport is None or not transport.is_active():
            previous = session.pop("jumphost_ssh_client", None)
            session.pop("jumphost_ssh_transport", None)
            if previous is not None:
                previous.close()
            client = paramiko.client.SSHClient()
            try:
                client.load_system_host_keys()
                if known_hosts is not None:
                    client.load_host_keys(known_hosts)
                client.set_missing_host_key_policy(policies[policy]())
                client.connect(**jumphost)
                transport = client.get_transport()
                if transport is None or not transport.is_active():
                    raise RuntimeError("jumphost transport is not active")
            except Exception as exc:
                client.close()
                raise RuntimeError(
                    f"RetryRunner failed connection to jumphost '{jumphost['hostname']}'"
                ) from exc
            session["jumphost_ssh_client"] = client
            session["jumphost_ssh_transport"] = transport
            # Retain Nornir's close_connections lifecycle for shared clients.
            host.connections[f"jumphost_{jumphost['hostname']}_{cache_key}"] = client
            log.info(
                "RetryRunner started connection to jumphost '%s'", jumphost["hostname"]
            )
        channel_name = f"jumphost_{jumphost['hostname']}_channel"
        channel = host.connections.get(channel_name)
        if channel is not None and (
            channel.closed or channel.get_transport() is not transport
        ):
            channel.close()
            host.connections.pop(channel_name, None)
            channel = None
        if channel is None:
            channel = transport.open_channel(
                kind="direct-tcpip",
                dest_addr=(host.hostname, host.port or 22),
                src_addr=("localhost", 7777),
                timeout=3,
            )
            host.connections[channel_name] = channel
            log.info(
                "RetryRunner %s opened channel via jumphost '%s'",
                host.name,
                jumphost["hostname"],
            )
        return channel


class RetryRunner:
    """
    RetryRunner is a Nornir runner plugin that strives to make task execution as reliable as possible.

    :param num_workers: number of threads for tasks execution
    :param num_connectors: number of threads for device connections
    :param connect_retry: maximum number of additional connection retries. Zero allows only the initial attempt
    :param connect_backoff: linear backoff timer in milliseconds
    :param connect_splay: random delay below splay for each connection in milliseconds. Zero disables jitter
    :param task_retry: maximum number of additional task retries. Zero allows only the initial attempt.
        Also limited by the remaining connection retry budget
    :param task_backoff: linear backoff timer in milliseconds
    :param task_splay: random delay below splay before task start in milliseconds. Zero disables jitter
    :param reconnect_on_fail: boolean, default True, perform reconnect to host on task failure
    :param task_timeout: int, seconds to wait for task to complete before closing all queues
        and stopping connectors and workers threads, default 600
    :param creds_retry: list of connection credentials and parameters to retry while connecting
        to device
    :param task_stop_errors: list of glob patterns to stop retrying if seen in task exception string,
        these patterns not applicable to errors encountered during connection establishment. Error
        ``*validation error*`` pattern always included in these list.
    :param connect_check: if True tries to open test TCP connection with hostname before opening actual
        connection, raises error if fails. This is mechanism to fail fast hosts that are not reachable.
    :param connect_timeout: timeout in seconds to wait for test TCP connection to establish
    """

    def __init__(
        self,
        num_workers: int = 100,
        num_connectors: int = 20,
        connect_retry: int = 3,
        connect_backoff: int = 5000,
        connect_splay: int = 100,
        task_retry: int = 1,
        task_backoff: int = 5000,
        task_splay: int = 100,
        reconnect_on_fail: bool = True,
        task_timeout: int = 600,
        creds_retry: list = None,
        task_stop_errors: list = None,
        connect_check: bool = False,
        connect_timeout: int = 5,
    ) -> None:
        model_RetryRunner(
            num_workers=num_workers,
            num_connectors=num_connectors,
            connect_retry=connect_retry,
            task_retry=task_retry,
            connect_backoff=connect_backoff,
            task_backoff=task_backoff,
            connect_splay=connect_splay,
            task_splay=task_splay,
            task_timeout=task_timeout,
            connect_timeout=connect_timeout,
            reconnect_on_fail=reconnect_on_fail,
            creds_retry=creds_retry,
            task_stop_errors=task_stop_errors,
            connect_check=connect_check,
        )
        self.num_workers = num_workers
        self.num_connectors = num_connectors
        self.connect_retry = connect_retry
        self.connect_backoff = connect_backoff
        self.connect_splay = connect_splay
        self.task_retry = task_retry
        self.task_backoff = task_backoff
        self.task_splay = task_splay
        self.jumphosts_connections = {}
        self.reconnect_on_fail = reconnect_on_fail
        self.task_timeout = task_timeout
        self.creds_retry = creds_retry or []
        self.task_stop_errors = task_stop_errors or []
        self.connect_timeout = connect_timeout
        self.connect_check = connect_check
        self.job = None

    def run(self, task: Task, hosts: List[Host]) -> AggregatedResult:
        connectors_q = queue.Queue()
        work_q = queue.Queue()
        stop_event = threading.Event()
        task_timeout_event = threading.Event()
        task_timeout_timer = threading.Timer(
            self.task_timeout, lambda: task_timeout_event.set()
        )
        result = AggregatedResult(task.name)
        connector_threads = []
        worker_threads = []
        # extract runner parameters from task
        run_connect_retry = task.params.pop("run_connect_retry", self.connect_retry)
        run_task_retry = task.params.pop("run_task_retry", self.task_retry)
        run_creds_retry = task.params.pop("run_creds_retry", self.creds_retry)
        run_num_workers = task.params.pop("run_num_workers", self.num_workers)
        run_num_connectors = task.params.pop("run_num_connectors", self.num_connectors)
        run_connect_timeout = task.params.pop(
            "run_connect_timeout", self.connect_timeout
        )
        run_connect_check = task.params.pop("run_connect_check", self.connect_check)
        run_reconnect_on_fail = task.params.pop(
            "run_reconnect_on_fail", self.reconnect_on_fail
        )
        # form a list of exception patterns to stop task retries
        run_task_stop_errors = task.params.pop(
            "run_task_stop_errors", list(self.task_stop_errors)
        )
        # attempt to extract a list of connections names this task uses
        if task.params.get("connection_name"):  # use task connection_name argument
            run_connection_name = task.params.pop("connection_name")
        elif getattr(task.task, "__wrapped__", None):  # task function has decorator
            run_connection_name = task.task.__wrapped__.__globals__.get(
                "CONNECTION_NAME", ""
            )
        else:  # use task global CONNECTION_NAME varibale
            run_connection_name = task.task.__globals__.get("CONNECTION_NAME", "")
        run_connection_name = [
            i.strip() for i in run_connection_name.split(",") if i.strip()
        ]
        model_RetryRunner(
            run_num_workers=run_num_workers,
            run_num_connectors=run_num_connectors,
            run_connect_retry=run_connect_retry,
            run_task_retry=run_task_retry,
            run_connect_timeout=run_connect_timeout,
            run_reconnect_on_fail=run_reconnect_on_fail,
            run_creds_retry=run_creds_retry,
            run_task_stop_errors=run_task_stop_errors,
            run_connect_check=run_connect_check,
        )
        run_task_stop_errors.append("*validation error*")
        # enqueu hosts in connectors queue
        params = {
            "connection_retry": 0,
            "task_retry": 0,
            "connection_name": list(run_connection_name),
            "timestamp": 0,
        }
        for host in hosts:
            connectors_q.put((task.copy(), host, params.copy(), result))
        try:
            # start connectors threads
            for _ in range(int(run_num_connectors)):
                t = threading.Thread(
                    target=connector,
                    args=(
                        stop_event,
                        connectors_q,
                        work_q,
                        self.connect_backoff,
                        self.connect_splay,
                        int(run_connect_retry),
                        self.jumphosts_connections,
                        run_creds_retry,
                        run_connect_timeout,
                        run_connect_check,
                        self.job,
                    ),
                )
                t.start()
                connector_threads.append(t)
            # start worker threads
            for _ in range(int(run_num_workers)):
                t = threading.Thread(
                    target=worker,
                    args=(
                        stop_event,
                        connectors_q,
                        work_q,
                        self.task_backoff,
                        self.task_splay,
                        int(run_task_retry),
                        int(run_connect_retry),
                        run_reconnect_on_fail,
                        run_task_stop_errors,
                    ),
                )
                t.start()
                worker_threads.append(t)
            # wait until all hosts completed task or timeout reached
            task_timeout_timer.start()
            while not task_timeout_event.is_set():
                with LOCK:
                    hosts_no_result = [h.name for h in hosts if h.name not in result]
                if hosts_no_result == []:
                    task_timeout_timer.cancel()
                    break
                time.sleep(0.1)
            else:
                log.warning(
                    "nornir_salt:RetryRunner task '{}', '{}'s task_timeout reached, hosts no results '{}'".format(
                        task.name, self.task_timeout, hosts_no_result
                    )
                )
            # block until all queues empty
            connectors_q.join()
            work_q.join()
        finally:
            task_timeout_timer.cancel()
            stop_event.set()
            for thread in connector_threads + worker_threads:
                thread.join()
            self.job = None  # delete job reference
        return result
