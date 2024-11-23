"""
NorFabEventProcessor Plugin
###########################

Processor plugin to emit events on task execution progress,
used by NorFab Nornir-Worker module to track tasks flow.

NorFabEventProcessor reference
==============================

.. autofunction:: nornir_salt.plugins.processors.NorFabEventProcessor.NorFabEventProcessor
"""
import logging

from datetime import datetime
from nornir.core.inventory import Host
from nornir.core.task import AggregatedResult, MultiResult, Task

log = logging.getLogger(__name__)


class NorFabEventProcessor:
    """
    NorFabEventProcessor emit events for NORFAB on task execution progress.

    :param worker: (obj) NorFab worker object
    :param tmstp_ftr: (str) timestamp formatter string, default is "%d-%b-%Y %H:%M:%S"
    """

    def __init__(
        self, worker, tmstp_ftr="%d-%b-%Y %H:%M:%S.%f", norfab_task: str = None
    ):
        self.worker = worker
        self.tmstp_ftr = tmstp_ftr

    def _timestamp(self):
        """
        Helper function to produce event data timestamp.
        """
        return datetime.now().strftime(self.tmstp_ftr)[:-3]

    def task_started(self, task: Task) -> None:
        data = {
            "timestamp": self._timestamp(),
            "task_name": task.name,
            "parent_task": task.parent_task.name if task.parent_task else None,
            "task_event": "started",
            "task_type": "task",
            "hosts": list(task.nornir.inventory.hosts.keys()),
            "status": "RUNNING",
            "message": f"{task.name} Nornir task started",
        }
        self.worker.event(data=data)

    def task_completed(self, task: Task, result: AggregatedResult) -> None:
        data = {
            "timestamp": self._timestamp(),
            "task_name": task.name,
            "parent_task": task.parent_task.name if task.parent_task else None,
            "task_event": "completed",
            "task_type": "task",
            "hosts": list(task.nornir.inventory.hosts.keys()),
            "status": "FAILED" if task.results.failed else "COMPLETED",
            "message": f"{task.name} Nornir task completed",
        }
        self.worker.event(data=data)

    def task_instance_started(self, task: Task, host: Host) -> None:
        data = {
            "timestamp": self._timestamp(),
            "task_name": task.name,
            "parent_task": task.parent_task.name if task.parent_task else None,
            "hosts": [host.name],
            "task_event": "started",
            "task_type": "task_instance",
            "status": "RUNNING",
            "message": f"{task.name} Nornir task instance started",
        }
        self.worker.event(data=data)

    def task_instance_completed(
        self, task: Task, host: Host, result: MultiResult
    ) -> None:
        data = {
            "timestamp": self._timestamp(),
            "task_name": task.name,
            "parent_task": task.parent_task.name if task.parent_task else None,
            "hosts": [host.name],
            "task_event": "completed",
            "task_type": "task_instance",
            "status": "FAILED" if task.results.failed else "COMPLETED",
            "message": f"{task.name} Nornir task instance completed",
        }
        self.worker.event(data=data)

    def subtask_instance_started(self, task: Task, host: Host) -> None:
        data = {
            "timestamp": self._timestamp(),
            "task_name": task.name,
            "parent_task": task.parent_task.name if task.parent_task else None,
            "hosts": [host.name],
            "task_event": "started",
            "task_type": "subtask",
            "status": "RUNNING",
            "message": f"{task.name} Nornir sub-task instance started",
        }
        self.worker.event(data=data)

    def subtask_instance_completed(
        self, task: Task, host: Host, result: MultiResult
    ) -> None:
        data = {
            "timestamp": self._timestamp(),
            "task_name": task.name,
            "parent_task": task.parent_task.name if task.parent_task else None,
            "hosts": [host.name],
            "task_event": "completed",
            "task_type": "subtask",
            "status": "FAILED" if task.results.failed else "COMPLETED",
            "message": f"{task.name} Nornir sub-task instance completed",
        }
        self.worker.event(data=data)
