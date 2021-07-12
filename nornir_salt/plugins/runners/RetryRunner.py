"""
RetryRunner plugin
##################

RetryRunner plugin implements retry logic to improve task execution reliability.

.. warning:: For grouped tasks need to explicitly provide `connection_name` attribute
    such as `netmiko`, `napalm`, `scrapli`. Specifying `connection_name` attribute for
    standalone tasks not required. Lack of `connection_name` attribute will result in skipping
    connection retry logic and connections to all hosts initiated simultaneously up to the
    number of `num_workers`

RetryRunner Architecture
========================

.. image:: ./_images/RetryRunner_v0.png

RetryRunner Sample Usage
========================

Need to instruct Nornir to use RetryRunner on instantiation::

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

RetryRunner - Connect to hosts behind jumphost
==============================================

RetryRunner implements logic to connect with hosts behind bastion/jumphosts.

.. note:: Only Netmiko tasks, `connection_name="netmiko"`, support connecting via Jumphosts.

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

RetryRunner Reference
=====================

.. autoclass:: nornir_salt.plugins.runners.RetryRunner.RetryRunner
"""
import threading
import queue
import logging
import time
import random
import paramiko
from typing import List
from nornir.core.task import AggregatedResult, Task
from nornir.core.inventory import Host


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
):
    while not stop_event.is_set():
        try:
            work = work_q.get(block=True, timeout=0.1)
        except queue.Empty:
            continue
        task, host, params, result = work
        # check if need backoff task retry for this host
        if params["task_retry"] > 0:
            elapsed = time.time() - params["timestamp"]
            should_wait = (params["task_retry"] * task_backoff) / 1000
            if elapsed < should_wait:
                work_q.put(work)
                work_q.task_done()
                continue
        log.info("{} - running task '{}'".format(host.name, task.name))
        time.sleep(random.randrange(0, task_splay) / 1000)
        work_result = task.start(host)
        if task.results.failed:
            log.error(
                "{} - task execution retry attempt {} failed: '{}'".format(
                    host.name, params["task_retry"], work_result[0].exception
                )
            )
            if (
                params["task_retry"] < task_retry
                and params["connection_retry"] < connect_retry
            ):
                params["task_retry"] += 1
                params["timestamp"] = time.time()
                # recover task results for not to count task as failed
                for r in task.results:
                    r.failed = False
                    r.exception = None
                    r.skip_results = True # for ResultSerializer to skip failed attempts
                if reconnect_on_fail:
                    # close host connections to retry them
                    close_host_connection(host, params["connection_name"])
                    connectors_q.put(work)
                    params["connection_retry"] += 1
                else:
                    work_q.put(work)
                work_q.task_done()
                continue
        # enreach result objects with runner statistics
        for result_item in work_result:
            result_item.connection_retry = params["connection_retry"]
            result_item.task_retry = params["task_retry"]
        with LOCK:
            result[host.name] = work_result
            del work_result
        work_q.task_done()
        log.info("{} - task '{}' completed".format(host.name, task.name))


def connector(
    stop_event,
    connectors_q,
    work_q,
    connect_backoff: int,
    connect_splay: int,
    connect_retry: int,
    jumphosts_connections,
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
        # initiate connection to host
        connection_name = task.task.__globals__.get("CONNECTION_NAME", None)
        connection_name = task.params.pop("connection_name", connection_name)
        # on connect retry get connection name from params
        connection_name = params.get("connection_name", connection_name)
        params.setdefault("connection_name", connection_name)
        if connection_name and connection_name not in host.connections:
            try:
                time.sleep(random.randrange(0, connect_splay) / 1000)
                if host.get("jumphost") and connection_name in ["netmiko", "ncclient"]:
                    extras = host.get_connection_parameters(connection_name).extras
                    extras["sock"] = connect_to_device_behind_jumphost(
                        host, jumphosts_connections
                    )
                    host.open_connection(
                        connection_name,
                        configuration=task.nornir.config,
                        extras=extras,
                    )
                else:
                    host.open_connection(
                        connection_name, configuration=task.nornir.config
                    )
                log.info(
                    "{} - started connection: '{}'".format(host.name, connection_name)
                )
            except Exception as e:
                # close host connections to retry them
                close_host_connection(host, connection_name)
                log.error(
                    "{} - connection retry attempt {}, error: '{}'".format(
                        host.name, params["connection_retry"], e
                    )
                )
                if params["connection_retry"] < connect_retry:
                    params["connection_retry"] += 1
                    params["timestamp"] = time.time()
                    connectors_q.put(connection)
                    connectors_q.task_done()
                    continue
        connectors_q.task_done()
        work_q.put((task, host, params, result))


def close_host_connection(host, connection_name):
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
                "Started connection to jumphost '{}' - '{}'".format(
                    jumphost["hostname"], jumphost_ssh_client
                )
            )
        except Exception as e:
            with LOCK:
                jumphosts_connections[jumphost["hostname"]] = "__failed__"
            # add exception info to host data to include in results
            error_msg = "Failed connection to jumphost '{}', error - {}".format(
                host["jumphost"]["hostname"], e
            )
            host["exception"] = error_msg
            log.error(error_msg)
            return
    else:
        # sleep random time waiting for connection to jumphost to establish
        while jumphosts_connections[jumphost["hostname"]] == "__connecting__":
            time.sleep(random.randrange(0, 500) / 1000)
        if jumphosts_connections[jumphost["hostname"]] == "__failed__":
            # add exception info to host data to include in results
            error_msg = "Failed connection to jumphost '{}' in another thread".format(
                host["jumphost"]["hostname"]
            )
            host["exception"] = error_msg
            log.error(error_msg)
            return
    # connect to host
    channel_name = "jumphost_{}_channel".format(jumphost["hostname"])
    if not host.connections.get(channel_name):
        dest_addr = (host.hostname, host.port or 22)
        channel = jumphosts_connections[jumphost["hostname"]][
            "jumphost_ssh_transport"
        ].open_channel(
            kind="direct-tcpip",
            dest_addr=dest_addr,
            src_addr=("localhost", 7777),
            timeout=3,
        )
        host.connections[channel_name] = channel
        log.info(
            "{} - started new channel via jumphost '{}' - '{}'".format(
                host.name,
                jumphost["hostname"],
                jumphosts_connections[jumphost["hostname"]]["jumphost_ssh_client"],
            )
        )
    return host.connections[channel_name]


class RetryRunner:
    """
    RetryRunner is a modification of QueueRunner that strives to
    make task execution as reliable as possible.

    Arguments:
        num_workers: number of threads for tasks execution
        num_connectors: number of threads for device connections
        connect_retry: number of connection attempts
        connect_backoff: exponential backoff timer in milliseconds
        connect_splay: random interval between 0 and splay for each connection in milliseconds
        task_retry: number of attempts to run task
        task_backoff: exponential backoff timer in milliseconds
        task_splay: random interval between 0 and splay before task start in milliseconds
        reconnect_on_fail: boolean, default True, perform reconnect to host on task failure
        task_timeout: int, seconds to wait for task to complete before closing all queues
            and stopping connectors and workers threads, default 600
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
        # enqueue hosts in connectors queue
        for host in hosts:
            connectors_q.put(
                (task.copy(), host, {"connection_retry": 0, "task_retry": 0}, result)
            )
        # start connectors threads
        for i in range(self.num_connectors):
            t = threading.Thread(
                target=connector,
                args=(
                    stop_event,
                    connectors_q,
                    work_q,
                    self.connect_backoff,
                    self.connect_splay,
                    self.connect_retry,
                    self.jumphosts_connections,
                ),
            )
            t.start()
            connector_threads.append(t)
        # start worker threads
        for i in range(self.num_workers):
            t = threading.Thread(
                target=worker,
                args=(
                    stop_event,
                    connectors_q,
                    work_q,
                    self.task_backoff,
                    self.task_splay,
                    self.task_retry,
                    self.connect_retry,
                    self.reconnect_on_fail,
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
                "RetryRunner task '{}', '{}'s task_timeout reached, hosts no results '{}'".format(
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
