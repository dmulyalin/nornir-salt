"""
RetryRunner plugin
##################

RetryRunner plugin implements retry logic to improve task execution reliability.

Primary usecase for RetryRunner is to make Nornir task execution as reliable as possible
utilizing queuing, retries, connections splaying and exponential backoff mechanisms.

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

* ``run_connect_retry`` - number of connection attempts
* ``run_task_retry`` - number of attempts to run task
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

    # retry credentials if login fails but without retrying conection establishment
    result3 = NornirObj.run(
        task=netmiko_send_command,
        command_string="show clock",
        run_retry_creds=["local_creds", "dev_creds"]
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
import threading
import queue
import logging
import time
import random
from fnmatch import fnmatchcase
from typing import List
from nornir.core.task import AggregatedResult, Task, MultiResult, Result
from nornir.core.inventory import Host
from nornir_salt.plugins.tasks.connections import conn_open, conn_check

try:
    import paramiko

    HAS_PARAMIKO = True
except ImportError:
    HAS_PARAMIKO = False

log = logging.getLogger(__name__)
LOCK = threading.Lock()


def worker(
    stop_event,
    connectors_q,
    work_q,
    task_backoff: int,
    task_splay: int,
    task_retry: int,
    connect_retry: int,
    reconnect_on_fail: bool,
    stop_errors: List,
):
    while not stop_event.is_set():
        try:
            work = work_q.get(block=True, timeout=0.1)
        except queue.Empty:
            continue
        task, host, params, result = work
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
                elapsed = time.time() - params["timestamp"]
                should_wait = (params["task_retry"] * task_backoff) / 1000
                if elapsed < should_wait:
                    work_q.put(work)
                    work_q.task_done()
                    continue
            log.info(
                f"nornir_salt:RetryRunner {host.name} - running task '{task.name}'"
            )
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
                params["timestamp"] = time.time()
                # recover task results for not to count task as failed
                for r in task.results:
                    try:
                        r.failed = False
                        r.exception = None
                        r.skip_results = (
                            True  # for ResultSerializer to skip failed attempts
                        )
                    except Exception as e:
                        log.exception(f"Failed to process {task.name} task result {r}.")
                if reconnect_on_fail:
                    # close host connections to retry them
                    close_host_connection(host, params["connection_name"])
                    connectors_q.put(work)
                    params["connection_retry"] += 1
                else:
                    work_q.put(work)
                work_q.task_done()
                continue
        # en-reach result objects with runner statistics
        for result_item in work_result:
            result_item.connection_retry = params["connection_retry"]
            result_item.task_retry = params["task_retry"]
        with LOCK:
            result[host.name] = work_result
            del work_result
        work_q.task_done()
        log.info(
            "nornir_salt:RetryRunner {} - task '{}' completed".format(
                host.name, task.name
            )
        )


def connector(
    stop_event,
    connectors_q,
    work_q,
    connect_backoff: int,
    connect_splay: int,
    connect_retry: int,
    jumphosts_connections: dict,
    run_creds_retry: list,
    run_connect_timeout: int,
    run_connect_check: bool,
):
    while not stop_event.is_set():
        try:
            connection = connectors_q.get(block=True, timeout=0.1)
        except queue.Empty:
            continue
        task, host, params, result = connection
        # check if need back off connection retry for this host
        if params["connection_retry"] > 0:
            elapsed = time.time() - params["timestamp"]
            should_wait = (params["connection_retry"] * connect_backoff) / 1000
            if elapsed < should_wait:
                connectors_q.put(connection)
                connectors_q.task_done()
                continue
        try:
            # initiate connections to host
            for connection_name in params["connection_name"]:
                if connection_name in host.connections:
                    continue
                time.sleep(random.randrange(0, connect_splay) / 1000)  # nosec
                extras = host.get_connection_parameters(connection_name).extras
                if host.get("jumphost") and connection_name in ["netmiko", "ncclient"]:
                    extras["sock"] = connect_to_device_behind_jumphost(
                        host, jumphosts_connections
                    )
                # check connection
                if run_connect_check:
                    host_connection_check = conn_check(
                        task, host, connection_name, timeout=run_connect_timeout
                    )
                    if host_connection_check.failed is True:
                        raise Exception(host_connection_check.exception)
                # retry various connection parameters
                if run_creds_retry:
                    log.info(
                        f"nornir_salt:RetryRunner {host.name} - connecting with creds retry"
                    )
                    conn_open(
                        task=task,
                        host=host,
                        conn_name=connection_name,
                        reconnect=run_creds_retry,
                        raise_on_error=True,
                        extras=extras,
                    )
                # open connection to host as is
                else:
                    host.open_connection(
                        connection_name, configuration=task.nornir.config, extras=extras
                    )
                log.info(
                    "nornir_salt:RetryRunner {} - started connection: '{}'".format(
                        host.name, connection_name
                    )
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
                params["timestamp"] = time.time()
                connectors_q.put(connection)
                connectors_q.task_done()
                log.warning(err_msg)
                continue
            else:
                # record exception in params for worker thread to react on it
                params["connect_exception"] = err_msg
                log.error(err_msg)
                log.exception(e)
        connectors_q.task_done()
        work_q.put((task, host, params, result))


def close_host_connection(host, connection_names):
    """
    Helper function to close connections to host

    :param host: nornir host object
    :param connection_names: list of connection names to close
    """
    for connection_name in connection_names:
        try:
            host.close_connection(connection_name)
        except:
            _ = host.connections.pop(connection_name, None)
        if host.get("jumphost"):
            channel_name = "jumphost_{}_channel".format(host["jumphost"]["hostname"])
            try:
                host.close_connection(channel_name)
            except:
                _ = host.connections.pop(channel_name, None)


def connect_to_device_behind_jumphost(host, jumphosts_connections):
    """
    Establish connection to devices behind jumphost/bastion
    """

    jumphost = {"timeout": 3, "look_for_keys": False, "allow_agent": False}
    jumphost.update(host["jumphost"])
    # Initiate connection to jumphost if not initiated already or
    # if it failed before
    #
    # jumphosts_connections dictionary shared between threads,
    # first thread to start will detect that no connection to
    # jumphost exists and will try to establish it, while doing
    # so, jumphost key will be added to jumphosts_connections
    # dictionary with '__connecting__' value, next threads
    # will see '__connecting__' as value for jumphost and will
    # continue sleeping until either connection succeeded or
    # failed. On connection failure, first thread will set value
    # to '__failed__' to signal other threads to exit.
    if (
        jumphost["hostname"] not in jumphosts_connections
        or jumphosts_connections.get(jumphost["hostname"]) == "__failed__"
    ):
        try:
            with LOCK:
                jumphosts_connections[jumphost["hostname"]] = "__connecting__"
            jumphost_ssh_client = paramiko.client.SSHClient()
            jumphost_ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            jumphost_ssh_client.connect(**jumphost)
            with LOCK:
                jumphosts_connections[jumphost["hostname"]] = {
                    "jumphost_ssh_client": jumphost_ssh_client,
                    "jumphost_ssh_transport": jumphost_ssh_client.get_transport(),
                }
            # add jumphost to host connections to close it
            # on nornir.close_connections() call
            host.connections[
                "jumphost_{}".format(jumphost["hostname"])
            ] = jumphost_ssh_client
            log.info(
                "nornir_salt:RetryRunner Started connection to jumphost '{}' - '{}'".format(
                    jumphost["hostname"], jumphost_ssh_client
                )
            )
        except Exception as e:
            with LOCK:
                jumphosts_connections[jumphost["hostname"]] = "__failed__"
            # add exception info to host data to include in results
            error_msg = "nornir_salt:RetryRunner failed connection to jumphost '{}', error - {}".format(
                host["jumphost"]["hostname"], e
            )
            # host["exception"] = error_msg
            log.error(error_msg)
            raise RuntimeError(error_msg)
    else:
        # sleep random time waiting for connection to jumphost to establish
        while jumphosts_connections[jumphost["hostname"]] == "__connecting__":
            time.sleep(random.randrange(0, 500) / 1000)  # nosec
        if jumphosts_connections[jumphost["hostname"]] == "__failed__":
            # add exception info to host data to include in results
            error_msg = "nornir_salt:RetryRunner failed connection to jumphost '{}' in another thread".format(
                host["jumphost"]["hostname"]
            )
            # host["exception"] = error_msg
            log.error(error_msg)
            raise RuntimeError(error_msg)
    # connect to host
    channel_name = "jumphost_{}_channel".format(jumphost["hostname"])
    jconn = jumphosts_connections[jumphost["hostname"]]
    # check if connection to jumphost was closed, reconnect if so
    if not jconn["jumphost_ssh_transport"].is_active():
        log.debug(
            "nornir_salt:RetryRunner jumphost '{}' disconnected, reconnecting".format(
                jumphost["hostname"]
            )
        )
        jconn["jumphost_ssh_client"].close()
        jumphosts_connections.pop(jumphost["hostname"])
        return connect_to_device_behind_jumphost(host, jumphosts_connections)
    # proceed with openning new channel via jumphost
    if not host.connections.get(channel_name):
        host.connections[channel_name] = jconn["jumphost_ssh_transport"].open_channel(
            kind="direct-tcpip",
            dest_addr=(host.hostname, host.port or 22),
            src_addr=("localhost", 7777),
            timeout=3,
        )
        log.info(
            "nornir_salt:RetryRunner {} - started new channel via jumphost '{}' - '{}'".format(
                host.name, jumphost["hostname"], jconn["jumphost_ssh_client"]
            )
        )
    return host.connections[channel_name]


class RetryRunner:
    """
    RetryRunner is a Nornir runner plugin that strives to make task execution as reliable as possible.

    :param num_workers: number of threads for tasks execution
    :param num_connectors: number of threads for device connections
    :param connect_retry: number of connection attempts
    :param connect_backoff: exponential backoff timer in milliseconds
    :param connect_splay: random interval between 0 and splay for each connection in milliseconds
    :param task_retry: number of attempts to run task
    :param task_backoff: exponential backoff timer in milliseconds
    :param task_splay: random interval between 0 and splay before task start in milliseconds
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
        connect_check: bool = True,
        connect_timeout: int = 5,
    ) -> None:
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
            "run_task_stop_errors", self.task_stop_errors
        )
        run_task_stop_errors.append("*validation error*")
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
        # do sanity checks
        if run_num_connectors <= 0:
            raise RuntimeError("nornir-salt:RetryRunner num_connectors must be above 0")
        if run_num_workers <= 0:
            raise RuntimeError("nornir-salt:RetryRunner num_workers must be above 0")
        # enqueu hosts in connectors queue
        params = {
            "connection_retry": 0,
            "task_retry": 0,
            "connection_name": run_connection_name,
        }
        for host in hosts:
            connectors_q.put((task.copy(), host, params.copy(), result))
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
        # stop and delete connectors and workers threads
        stop_event.set()
        while connector_threads:
            _ = connector_threads.pop().join()
        while worker_threads:
            _ = worker_threads.pop().join()
        return result
