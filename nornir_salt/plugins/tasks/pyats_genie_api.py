"""
pyats_genie_api
###############

This task can call one of Genie device ``api`` methods.

Full list of api methods available for your device platform can be found
`in Genie docs <https://pubhub.devnetcloud.com/media/genie-feature-browser/docs/#/apis>`_

Dependencies:

* `PyATS library <https://pypi.org/project/pyats/>`_ required
* `Genie library <https://pypi.org/project/genie/>`_ required

Sample Usage
============

Code to invoke ``pyats_genie_api`` task::

    from nornir_salt import pyats_genie_api

    output = nr.run(
        task=pyats_genie_api,
        api="ping",
        address="127.0.0.1",
        timeout=1,
        count=1,
    )

``pyats_genie_api`` returns Nornir results object with results containing
api call output.

API Reference
=============

.. autofunction:: nornir_salt.plugins.tasks.pyats_genie_api.pyats_genie_api
"""
import logging
from nornir.core.task import Result, Task

log = logging.getLogger(__name__)

# define connection name for RetryRunner to properly detect it using:
# connection_name = task.task.__globals__.get("CONNECTION_NAME", None)
CONNECTION_NAME = "pyats"


def pyats_genie_api(task: Task, api: str, **kwargs):
    """
    Salt-nornir task function to call Genie device's api methods.

    :param api: (str) api name to call
    :param kwargs: (dict) any additional arguments to use with api call
    :return result: Nornir result object with task execution results
    """
    task.name = "pyats_genie_api"

    # get PyATS testbed, device object
    testbed = task.host.get_connection(CONNECTION_NAME, task.nornir.config)
    device = testbed.devices[task.host.name]

    # call api
    result = getattr(device.api, api)(**kwargs)

    return Result(host=task.host, result=result)
