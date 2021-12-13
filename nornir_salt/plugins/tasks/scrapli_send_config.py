"""
scrapli_send_config
###################

This task plugin uses ``nornir-scrapli`` ``scrapli_send_config`` task
to send configuration commands to devices over SSH or Telnet.

``scrapli_send_config`` exists as part of ``nornir_salt`` repository to facilitate
per-host configuration rendering performed by SALT prior to running the task.

Dependencies:

* `nornir-scrapli module <https://pypi.org/project/nornir-scrapli/>`_ required

scrapli_send_config sample usage
================================

Code to invoke ``scrapli_send_config`` task::

    from nornir import InitNornir
    from nornir_salt import scrapli_send_config

    nr = InitNornir(config_file="config.yaml")

    output = nr.run(
        task=scrapli_send_config,
        commands=["sinterface loopback 0", "description 'configured by script'"]
    )

scrapli_send_config returns
===========================

Returns Nornir results object with individual tasks names set
equal to commands sent to device.

scrapli_send_config reference
=============================

.. autofunction:: nornir_salt.plugins.tasks.scrapli_send_config.scrapli_send_config
"""
import logging
from nornir.core.task import Result, Task

try:
    from nornir_scrapli.tasks import send_config as nornir_scrapli_send_config

    HAS_SCRAPLI = True
except ImportError:
    HAS_SCRAPLI = False

log = logging.getLogger(__name__)


def scrapli_send_config(task: Task, config=None, **kwargs):
    """
    Nornir Task function to send confgiuration to devices using
    ``nornir_scrapli.tasks.send_config`` plugin

    :param kwargs: arguments for ``file.apply_template_on_contents`` salt function
        for configuration rendering as well as for ``task.run`` method
    :param config: (str or list) configuration string or list of commands to send to device
    :param commit: not implemented yet
    :return result: Nornir result object with task execution results
    """
    # run sanity check
    if not HAS_SCRAPLI:
        return Result(
            host=task.host,
            failed=True,
            exception="No nornir_scrapli found, is it installed?",
        )

    # get configuration
    if "commands" in task.host.data.get("__task__", {}):
        config = task.host.data["__task__"]["commands"]
    elif "filename" in task.host.data.get("__task__", {}):
        config = task.host.data["__task__"]["filename"]

    # transform configuration to string if list/tuple given
    if isinstance(config, (list, tuple)):
        config = "\n".join(config)

    # push config to device
    task.run(
        task=nornir_scrapli_send_config,
        config=config,
        name="scrapli_send_config",
        **kwargs
    )

    # set skip_results to True, for ResultSerializer to ignore
    # results for grouped task itself, which are usually None
    return Result(host=task.host, skip_results=True)
