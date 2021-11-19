"""
sleep
#####

Function to sleep for given amount of time on a per-host basis.

Code to invoke ``sleep`` task::

    from nornir_salt import sleep

    output = nr.run(task=sleep, sleep_for=10)

Returns Nornir results object with task results string "Slept for {sleep_for}s".

API Reference
=============

.. autofunction:: nornir_salt.plugins.tasks.sleep.sleep
"""
import time
from nornir.core.task import Result


def sleep(task, sleep_for=5):
    """
    Task to sleep for given amount of time.

    :param sleep_for: (int) time in seconds to sleep for
    """
    task.name = "sleep"
    time.sleep(int(sleep_for))

    return Result(host=task.host, result="Slept for {}s".format(sleep_for))
