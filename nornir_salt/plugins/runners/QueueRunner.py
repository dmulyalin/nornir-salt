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
        self.work_q = None

    def worker(self):
        while True:
            work_to_do = self.work_q.get()
            if work_to_do is None:
                break
            task, host, result = work_to_do
            work_result = task.copy().start(host)
            with LOCK:
                result[host.name] = work_result
            self.work_q.task_done()

    def run(self, task: Task, hosts: List[Host]) -> AggregatedResult:
        self.work_q = queue.Queue()
        result = AggregatedResult(task.name)
        # enqueue hosts in work queue
        for host in hosts:
            self.work_q.put((task, host, result))
        # start threads
        threads = []
        for i in range(self.num_workers):
            t = threading.Thread(target=self.worker, args=(), daemon=True)
            t.start()
            threads.append(t)
        # block until all tasks are done
        self.work_q.join()
        # stop workers:
        for i in range(self.num_workers):
            self.work_q.put(None)
        for t in threads:
            t.join()
        return result
