"""
QueueRunner plugin
##################

QueueRunner plugin implements simple queue for task execution instead of starting
threads for ongoing tasks.

For example, if number of threads 10, but task need to be executed on 20 hosts,
threaded runner will start first 10 threads to run task for first 10 hosts,
after that start another 10 threads to run task for remaining 10 hosts.

Above process works well for majority of cases, but using QueueRunner might be
beneficial in certain situations, e.g. QueueRunner pros:

- worker threads started only once saving some negligible CPU cycles
- even if one of the hosts takes longer time to complete the task, threads will
  not stay idle and continue serving other hosts, that might reveal better
  execution time

QueueRunner Architecture
========================

.. image:: ../_images/QueueRunner_v0.png

QueueRunner Sample Usage
========================

Need to instruct Nornir to use QueueRunner on instantiation::

    from nornir import InitNornir

    NornirObj = InitNornir(
        runner={
            "plugin": "QueueRunner",
            "options": {
                "num_workers": 100
            }
        }
    )

QueueRunner Reference
=====================

.. autoclass:: nornir_salt.plugins.runners.QueueRunner.QueueRunner
"""
import threading
import queue
from typing import List
from nornir.core.task import AggregatedResult, Task
from nornir.core.inventory import Host


LOCK = threading.Lock()


class QueueRunner:
    """
    QueueRunner run tasks over each host using queue together
    with workers threads consuming work from work queue.

    Instead of firing up num_workes threads for each batch of hosts,
    QueueRunner starts num_workes threads once and uses queue to
    submit tasks and obtain results.

    Arguments:
        num_workers: number of threads to use
    """

    def __init__(self, num_workers: int = 20) -> None:
        self.num_workers = num_workers

    def worker(self, work_q):
        while True:
            work_to_do = work_q.get()
            if work_to_do is None:
                break
            task, host, result = work_to_do
            work_result = task.copy().start(host)
            with LOCK:
                result[host.name] = work_result
            work_q.task_done()

    def run(self, task: Task, hosts: List[Host]) -> AggregatedResult:
        work_q = queue.Queue()
        result = AggregatedResult(task.name)
        # enqueue hosts in work queue
        for host in hosts:
            work_q.put((task, host, result))
        # start threads
        threads = []
        for i in range(self.num_workers):
            t = threading.Thread(target=self.worker, args=(work_q,), daemon=True)
            t.start()
            threads.append(t)
        # block until all tasks are done
        work_q.join()
        # stop workers:
        for i in range(self.num_workers):
            work_q.put(None)
        for t in threads:
            t.join()
        return result
