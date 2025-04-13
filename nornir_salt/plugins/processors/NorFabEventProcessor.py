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

from nornir.core.inventory import Host
from nornir.core.task import AggregatedResult, MultiResult, Task

try:
    from norfab.models import NorFabEvent
except Exception as e:
    pass

log = logging.getLogger(__name__)


class NorFabEventProcessor:
    """
    NorFabEventProcessor emit events for NORFAB on task execution progress.

    :param worker: (obj) NorFab worker object
    :param tmstp_ftr: (str) timestamp formatter string, default is "%d-%b-%Y %H:%M:%S"
    :param username: (str) username who started the job
    """

    def __init__(self, worker, norfab_task_name):
        self.worker = worker
        self.norfab_task_name = norfab_task_name

    def task_started(self, task: Task) -> None:
        self.worker.event(
            NorFabEvent(
                task=f"{self.norfab_task_name}.{task.name}",
                status="started",
                resource=sorted(list(task.nornir.inventory.hosts.keys())),
                message="Task started",
                severity="INFO",
                extras={},
            )
        )

    def task_completed(self, task: Task, result: AggregatedResult) -> None:
        self.worker.event(
            NorFabEvent(
                task=f"{self.norfab_task_name}.{task.name}",
                status="completed",
                resource=sorted(list(task.nornir.inventory.hosts.keys())),
                message="Task completed",
                severity="INFO",
                extras={},
            )
        )

    def task_instance_started(self, task: Task, host: Host) -> None:
        self.worker.event(
            NorFabEvent(
                task=f"{self.norfab_task_name}.{task.name}",
                status="started",
                resource=[host.name],
                message="Host task started",
                severity="INFO",
                extras={},
            )
        )

    def task_instance_completed(
        self, task: Task, host: Host, result: MultiResult
    ) -> None:
        self.worker.event(
            NorFabEvent(
                task=f"{self.norfab_task_name}.{task.name}",
                status="failed" if task.results.failed else "completed",
                resource=[host.name],
                message="Host task completed",
                severity="INFO",
                extras={},
            )
        )

    def subtask_instance_started(self, task: Task, host: Host) -> None:
        task_name = f"{self.norfab_task_name}.{task.parent_task.name}"
        message = f"Sub-task started '{task.name}'"
        self.worker.event(
            NorFabEvent(
                task=task_name,
                status="started",
                resource=[host.name],
                message=message,
                severity="INFO",
                extras={},
            )
        )

    def subtask_instance_completed(
        self, task: Task, host: Host, result: MultiResult
    ) -> None:
        task_name = f"{self.norfab_task_name}.{task.parent_task.name}"
        if task.results.failed:
            message = f"Sub-task failed '{task.name}'"
            status = "failed"
            severity = "WARNING"
        else:
            message = f"Sub-task completed '{task.name}'"
            status = "completed"
            severity = "INFO"
        self.worker.event(
            NorFabEvent(
                task=task_name,
                status=status,
                resource=[host.name],
                message=message,
                severity=severity,
                extras={},
            )
        )
