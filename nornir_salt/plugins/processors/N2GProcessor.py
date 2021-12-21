"""
N2G Processor Plugin
####################

Processor plugin that uses N2G library to produce diagrams out of
network devices output.

N2GProcessor Sample Usage
=========================

Code to demonstrate how to use ``N2GProcessor`` plugin::

    TBD

N2GProcessor reference
=========================

.. autofunction:: nornir_salt.plugins.processors.N2GProcessor.N2GProcessor
"""
import logging
import traceback

from nornir.core.inventory import Host
from nornir.core.task import AggregatedResult, MultiResult, Task


log = logging.getLogger(__name__)


class N2GProcessor:
    """
    N2GProcessor can generate diagrams out network devices output.

    :param module: (str) name of diagramming module to use
    """

    def __init__(self):
        pass

    def task_started(self, task: Task) -> None:
        pass  # ignore

    def task_instance_started(self, task: Task, host: Host) -> None:
        pass  # ignore

    def task_instance_completed(
        self, task: Task, host: Host, result: MultiResult
    ) -> None:
        pass

    def subtask_instance_started(self, task: Task, host: Host) -> None:
        pass  # ignore subtasks

    def subtask_instance_completed(
        self, task: Task, host: Host, result: MultiResult
    ) -> None:
        pass  # ignore subtasks

    def task_completed(self, task: Task, result: AggregatedResult) -> None:
        pass
