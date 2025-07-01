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

log = logging.getLogger(__name__)


class NorFabEventProcessor:
    """
    NorFabEventProcessor emit events for NORFAB on task execution progress.

    :param job: (obj) NorFab job object
    """

    def __init__(self, job: object):
        self.job = job

    def task_started(self, task: Task) -> None:
        self.job.event(
            task=f"{self.job.task}.{task.name}",
            status="started",
            resource=sorted(list(task.nornir.inventory.hosts.keys())),
            message="Task started",
            severity="INFO",
            extras={},
        )

    def task_completed(self, task: Task, result: AggregatedResult) -> None:
        self.job.event(
            task=f"{self.job.task}.{task.name}",
            status="completed",
            resource=sorted(list(task.nornir.inventory.hosts.keys())),
            message="Task completed",
            severity="INFO",
            extras={},
        )

    def task_instance_started(self, task: Task, host: Host) -> None:
        self.job.event(
            task=f"{self.job.task}.{task.name}",
            status="started",
            resource=[host.name],
            message="Host task started",
            severity="INFO",
            extras={},
        )

    def task_instance_completed(
        self, task: Task, host: Host, result: MultiResult
    ) -> None:
        self.job.event(
            task=f"{self.job.task}.{task.name}",
            status="failed" if task.results.failed else "completed",
            resource=[host.name],
            message="Host task completed",
            severity="INFO",
            extras={},
        )

    def subtask_instance_started(self, task: Task, host: Host) -> None:
        task_name = f"{self.job.task}.{task.parent_task.name}"
        message = f"Sub-task started '{task.name}'"
        self.job.event(
            task=task_name,
            status="started",
            resource=[host.name],
            message=message,
            severity="INFO",
            extras={},
        )

    def subtask_instance_completed(
        self, task: Task, host: Host, result: MultiResult
    ) -> None:
        task_name = f"{self.job.task}.{task.parent_task.name}"
        if task.results.failed:
            message = f"Sub-task failed '{task.name}'"
            status = "failed"
            severity = "WARNING"
        else:
            message = f"Sub-task completed '{task.name}'"
            status = "completed"
            severity = "INFO"
        self.job.event(
            task=task_name,
            status=status,
            resource=[host.name],
            message=message,
            severity=severity,
            extras={},
        )
