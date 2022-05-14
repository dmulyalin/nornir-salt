"""
sleep
#####

Function to sleep for given amount of time on a per-host basis.

Code to invoke ``sleep`` task::

    from nornir_salt.plugins.tasks import sleep

    output = nr.run(task=sleep, sleep_for=10)
    output = nr.run(task=sleep, sleep_random=[1,5])
    output = nr.run(task=sleep, sleep_random=3)


Returns Nornir results object with task results string "Slept for {sleep_for}s".

API Reference
=============

.. autofunction:: nornir_salt.plugins.tasks.sleep.sleep
"""
import time
import random
from nornir.core.task import Result
from nornir_salt.utils.pydantic_models import model_sleep
from nornir_salt.utils.yangdantic import ValidateFuncArgs


@ValidateFuncArgs(model_sleep)
def sleep(task, sleep_for=5, sleep_random=None):
    """
    Task to sleep for given amount of time.

    :param sleep_for: (int) time in seconds to sleep for
    :param sleep_random: (int, list or tuple) random range to sleep for e.g.
      ``sleep_random=[0,5]`` sleep random time between 0 and 5 seconds
    """
    task.name = "sleep"

    # check if need to sleep for random interval
    if sleep_random:
        if not isinstance(sleep_random, (list, tuple)):
            sleep_random = [sleep_random]
        sleep_for = random.randrange(*sleep_random)  # nosec

    time.sleep(int(sleep_for))

    return Result(host=task.host, result="Slept for {}s".format(sleep_for))
