"""
SaltEventProcessor Plugin
#########################

Processor plugin to emit events on task execution progress,
used by Nornir Proxy Runner modules to track tasks flow.

SaltEventProcessor does not work outside of SaltStack environment.

SaltEventProcessor reference
============================

.. autofunction:: nornir_salt.plugins.processors.SaltEventProcessor.SaltEventProcessor
"""
import logging
import time

from nornir.core.inventory import Host
from nornir.core.task import AggregatedResult, MultiResult, Task

log = logging.getLogger(__name__)

try:
    # starting with salt 3003 need to use loader_context to reconstruct
    # __salt__ dunder within treads:
    # details: https://github.com/saltstack/salt/issues/59962
    try:
        from salt.loader_context import loader_context

    except ImportError:
        # after salt 3004 api was updated - https://github.com/saltstack/salt/pull/60595
        from salt.loader.context import loader_context

    HAS_LOADER_CONTEXT = True
except ImportError:
    HAS_LOADER_CONTEXT = False


class SaltEventProcessor:
    """
    SaltEventProcessor can emit event on SaltStack Event bus about task execution progress.

    :param __salt__: (obj) __salt__ dunder object
    :param loader: (obj) salt loader, required to use __salt__ dunder within threads
        for SaltStack version above 3003.
    :param loader_context: (obj) salt loader context
    :param proxy_id: (str) Proxy Minion ID to form event tags
    :param tftr: (str) timestamp formatter string, default is "%d-%b-%Y %H:%M:%S"
    :param identity: (dict) task identity dictionary of uuid4, jid, function_name keys
    """

    def __init__(self, __salt__, loader, proxy_id, identity, tftr="%d-%b-%Y %H:%M:%S"):
        self.__salt__ = __salt__
        self.loader = loader
        self.proxy_id = proxy_id
        self.tftr = tftr
        self.jid = identity["jid"]
        self.function = identity["function_name"]

    def _emit_event(self, tag, data):
        """
        Helper function to emit event on SaltStack Event BUS.

        :param tag: (str) event tag string
        :param data: (any) event data content
        """
        if HAS_LOADER_CONTEXT and self.loader is not None:
            with loader_context(self.loader):
                self.__salt__["event.send"](tag=tag, data=data)
        else:
            self.__salt__["event.send"](tag=tag, data=data)

    def _timestamp(self):
        """
        Helper function to produce event data timestamp.
        """
        return time.strftime(self.tftr)

    def task_started(self, task: Task) -> None:
        tag = "nornir-proxy/{jid}/{proxy_id}/task/started/{task_name}".format(
            proxy_id=self.proxy_id, task_name=task.name, jid=self.jid
        )
        data = {
            "timestamp": self._timestamp(),
            "task_name": task.name,
            "jid": self.jid,
            "proxy_id": self.proxy_id,
            "task_event": "started",
            "task_type": "task",
            "hosts": list(task.nornir.inventory.hosts.keys()),
            "status": "RUNNING",
            "function": self.function,
        }
        self._emit_event(tag, data)

    def task_completed(self, task: Task, result: AggregatedResult) -> None:
        tag = "nornir-proxy/{jid}/{proxy_id}/task/completed/{task_name}".format(
            proxy_id=self.proxy_id, task_name=task.name, jid=self.jid
        )
        data = {
            "timestamp": self._timestamp(),
            "task_name": task.name,
            "jid": self.jid,
            "proxy_id": self.proxy_id,
            "task_event": "completed",
            "task_type": "task",
            "hosts": list(task.nornir.inventory.hosts.keys()),
            "status": "FAILED" if task.results.failed else "PASSED",
            "function": self.function,
        }
        self._emit_event(tag, data)

    def task_instance_started(self, task: Task, host: Host) -> None:
        tag = "nornir-proxy/{jid}/{proxy_id}/{host}/task/started/{task_name}".format(
            proxy_id=self.proxy_id, host=host.name, task_name=task.name, jid=self.jid
        )
        data = {
            "timestamp": self._timestamp(),
            "task_name": task.name,
            "jid": self.jid,
            "host": host.name,
            "proxy_id": self.proxy_id,
            "task_event": "started",
            "task_type": "task_instance",
            "status": "RUNNING",
            "function": self.function,
        }
        self._emit_event(tag, data)

    def task_instance_completed(
        self, task: Task, host: Host, result: MultiResult
    ) -> None:
        tag = "nornir-proxy/{jid}/{proxy_id}/{host}/task/completed/{task_name}".format(
            proxy_id=self.proxy_id, host=host.name, task_name=task.name, jid=self.jid
        )
        data = {
            "timestamp": self._timestamp(),
            "task_name": task.name,
            "jid": self.jid,
            "proxy_id": self.proxy_id,
            "host": host.name,
            "task_event": "completed",
            "task_type": "task_instance",
            "status": "FAILED" if task.results.failed else "PASSED",
            "function": self.function,
        }
        self._emit_event(tag, data)

    def subtask_instance_started(self, task: Task, host: Host) -> None:
        tag = "nornir-proxy/{jid}/{proxy_id}/{host}/subtask/started/{task_name}".format(
            proxy_id=self.proxy_id, host=host.name, task_name=task.name, jid=self.jid
        )
        data = {
            "timestamp": self._timestamp(),
            "task_name": task.name,
            "jid": self.jid,
            "proxy_id": self.proxy_id,
            "host": host.name,
            "task_event": "started",
            "task_type": "subtask",
            "status": "RUNNING",
            "function": self.function,
        }
        self._emit_event(tag, data)

    def subtask_instance_completed(
        self, task: Task, host: Host, result: MultiResult
    ) -> None:
        tag = "nornir-proxy/{jid}/{proxy_id}/{host}/subtask/completed/{task_name}".format(
            proxy_id=self.proxy_id, host=host.name, task_name=task.name, jid=self.jid
        )
        data = {
            "timestamp": self._timestamp(),
            "task_name": task.name,
            "jid": self.jid,
            "proxy_id": self.proxy_id,
            "host": host.name,
            "task_event": "completed",
            "task_type": "subtask",
            "status": "FAILED" if task.results.failed else "PASSED",
            "function": self.function,
        }
        self._emit_event(tag, data)
