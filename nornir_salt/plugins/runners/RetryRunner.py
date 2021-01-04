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


class RetryRunner:
    """
    RetryRunner is a modification of QueueRunner that strives to
    make task execution as reliable as possible.

    Arguments:
        num_workers: number of threads for tasks execution
        num_connectors: number of threads for device connections
        connect_retry: number of connection attempts
        connect_backoff: exponential backoff timer in milliseconds
        connect_splay: random splay interval for each connection
        task_retry: number of attempts to run task
        task_backoff: exponential backoff timer in milliseconds
        task_splay: random splay interval before task start
        reconnect_on_fail: boolean, default True, reconnect to host on task failure
        task_timeout: int, seconds to wait for task to complete, default 600
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

    def _connect_to_device_behind_jumphost(self, host):
        """
        Establish connection to devices behind jumphost/bastion
        """

        jumphost = {"timeout": 3, "look_for_keys": False, "allow_agent": False}
        jumphost.update(host["jumphost"])
        # Initiate connection to jumphost if not initiated already or
        # if it failed before
        #
        # self.jumphosts_connections dictionary shared between threads,
        # first thread to start will detect that no connection to
        # jumphost exists and will try to establish it, while doing
        # so, jumphost key will be added to self.jumphosts_connections
        # dictionary with '__connecting__' value, next threads
        # will see '__connecting__' as value for jumphost and will
        # continue sleeping until either connection succeeded or
        # failed. On connection failure, first thread will set value
        # to '__failed__' to signal other threads to exit.
        if (
            jumphost["hostname"] not in self.jumphosts_connections
            or self.jumphosts_connections.get(jumphost["hostname"]) == "__failed__"
        ):
            try:
                with LOCK:
                    self.jumphosts_connections[jumphost["hostname"]] = "__connecting__"
                jumphost_ssh_client = paramiko.client.SSHClient()
                jumphost_ssh_client.set_missing_host_key_policy(
                    paramiko.AutoAddPolicy()
                )
                jumphost_ssh_client.connect(**jumphost)
                with LOCK:
                    self.jumphosts_connections[jumphost["hostname"]] = {
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
                    self.jumphosts_connections[jumphost["hostname"]] = "__failed__"
                # add exception info to host data to include in results
                error_msg = "Failed connection to jumphost '{}', error - {}".format(
                    host["jumphost"]["hostname"], e
                )
                host["exception"] = error_msg
                log.error(error_msg)
                return
        else:
            # sleep random time waiting for connection to jumphost to establish
            while self.jumphosts_connections[jumphost["hostname"]] == "__connecting__":
                time.sleep(random.randrange(0, 500) / 1000)
            if self.jumphosts_connections[jumphost["hostname"]] == "__failed__":
                # add exception info to host data to include in results
                error_msg = (
                    "Failed connection to jumphost '{}' in another thread".format(
                        host["jumphost"]["hostname"]
                    )
                )
                host["exception"] = error_msg
                log.error(error_msg)
                return
        # connect to host
        channel_name = "jumphost_{}_channel".format(jumphost["hostname"])
        if not host.connections.get(channel_name):
            dest_addr = (host.hostname, host.port or 22)
            channel = self.jumphosts_connections[jumphost["hostname"]][
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
                    self.jumphosts_connections[jumphost["hostname"]][
                        "jumphost_ssh_client"
                    ],
                )
            )
        return host.connections[channel_name]

    def _close_host_connection(self, host, connection_name):
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

    def connector(self, connectors_q, work_q):
        while True:
            connection = connectors_q.get()
            if connection is None:
                connectors_q.task_done()
                break
            task, host, params, result = connection
            # check if need back off connection retry for this host
            if params["connection_retry"] > 0:
                elapsed = time.time() - params["timestamp"]
                should_wait = (params["connection_retry"] * self.connect_backoff) / 1000
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
                    time.sleep(random.randrange(0, self.connect_splay) / 1000)
                    if host.get("jumphost") and connection_name == "netmiko":
                        extras = {}
                        if host.connection_options.get("netmiko"):
                            extras = host.connection_options["netmiko"].extras
                        extras["sock"] = self._connect_to_device_behind_jumphost(host)
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
                        "{} - started connection: '{}'".format(
                            host.name, connection_name
                        )
                    )
                except Exception as e:
                    # close host connections to retry them
                    self._close_host_connection(host, connection_name)
                    log.error(
                        "{} - connection retry attempt {}, error: '{}'".format(
                            host.name, params["connection_retry"], e
                        )
                    )
                    if params["connection_retry"] < self.connect_retry:
                        params["connection_retry"] += 1
                        params["timestamp"] = time.time()
                        connectors_q.put(connection)
                        connectors_q.task_done()
                        continue
            connectors_q.task_done()
            work_q.put((task, host, params, result))

    def worker(self, connectors_q, work_q):
        while True:
            work = work_q.get()
            if work is None:
                work_q.task_done()
                break
            task, host, params, result = work
            # check if need backoff task retry for this host
            if params["task_retry"] > 0:
                elapsed = time.time() - params["timestamp"]
                should_wait = (params["task_retry"] * self.task_backoff) / 1000
                if elapsed < should_wait:
                    work_q.put(work)
                    work_q.task_done()
                    continue
            log.info("{} - running task '{}'".format(host.name, task.name))
            time.sleep(random.randrange(0, self.task_splay) / 1000)
            work_result = task.start(host)
            if task.results.failed:
                log.error(
                    "{} - task execution retry attempt {} failed: '{}'".format(
                        host.name, params["task_retry"], work_result[0].exception
                    )
                )
                if (
                    params["task_retry"] < self.task_retry
                    and params["connection_retry"] < self.connect_retry
                ):
                    params["task_retry"] += 1
                    params["timestamp"] = time.time()
                    # recover task results for not to count task as failed
                    for r in task.results:
                        r.failed = False
                    if self.reconnect_on_fail:
                        # close host connections to retry them
                        self._close_host_connection(host, params["connection_name"])
                        connectors_q.put(work)
                        params["connection_retry"] += 1
                    else:
                        work_q.put(work)
                    work_q.task_done()
                    continue
            with LOCK:
                result[host.name] = work_result
            work_q.task_done()
            log.info("{} - task '{}' completed".format(host.name, task.name))

    def run(self, task: Task, hosts: List[Host]) -> AggregatedResult:
        connectors_q = queue.Queue()
        work_q = queue.Queue()
        result = AggregatedResult(task.name)
        # enqueue hosts in connectors queue
        for host in hosts:
            connectors_q.put(
                (task.copy(), host, {"connection_retry": 0, "task_retry": 0}, result)
            )
        # start connectors threads
        connector_threads = []
        for i in range(self.num_connectors):
            t = threading.Thread(target=self.connector, args=(connectors_q, work_q))
            t.start()
            connector_threads.append(t)
        # start worker threads
        worker_threads = []
        for i in range(self.num_workers):
            t = threading.Thread(target=self.worker, args=(connectors_q, work_q))
            t.start()
            worker_threads.append(t)
        # wait until all hosts completed task or timeout reached
        start_time = time.time()
        while True:
            with LOCK:
                hosts_no_result = [h.name for h in hosts if h.name not in result]
            if hosts_no_result == []:
                break
            if time.time() - start_time > self.task_timeout:
                log.error("RetryRunner task '{}', '{}' seconds wait timeout reached, hosts that did not return results '{}'".format(
                        task.name, self.task_timeout, hosts_no_result
                    )
                )
                break
            time.sleep(0.1)
        # block until all queues empty
        connectors_q.join()
        work_q.join()
        # stop connector threads
        for i in range(self.num_connectors):
            connectors_q.put(None)
        for t in connector_threads:
            t.join()
        # stop worker threads
        for i in range(self.num_workers):
            work_q.put(None)
        for t in worker_threads:
            t.join()
        # delete queues and threads
        del(connectors_q, work_q, connector_threads, worker_threads)
        return result
