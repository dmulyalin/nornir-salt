"""
pyats_send_config
#######################

This task plugin relies on Genie device conection ``config`` method
to send configuration commands to devices over SSH or Telnet.

This task plugin applies device configuration following this sequence:

- Retrieve and use, if any, per-host configuration rendered by SaltStack from host's
  inventory data ``task.host.data["__task__"]["commands"]`` or
  ``task.host.data["__task__"]["filename"]`` locations, use configuration provided
  by ``config`` argument otherwise
- If configuration is a multi-line string, split it to a list of commands
- Check if device in enable mode, if not enter device enabled mode if device supports it
- Push configuration commands to device using ``send_config_set`` Netmiko connection's method,
  if ``batch`` argument given, pushes commands in batches
- If ``commit`` argument provided, perform configuration commit if device supports it
- If ``commit_final_delay`` argument provided, wait for a given timer and perform final commit
- Exit device configuration mode and return configuration results

Dependencies:

* `PyATS library <https://pypi.org/project/pyats/>`_ required
* `Genie library <https://pypi.org/project/genie/>`_ required

Sample Usage
============

Code to invoke ``pyats_send_config`` task::

    from nornir_salt import pyats_send_config

    output = nr.run(
        task=pyats_send_config,
        commands=["sinterface loopback 0", "description 'configured by script'"]
    )

``pyats_send_config`` returns Nornir results object with task name set
to ``pyats_send_config`` and results containing configuration commands
applied to device.

API Reference
=============

.. autofunction:: nornir_salt.plugins.tasks.pyats_send_config.pyats_send_config
"""
import logging
import traceback
from nornir.core.task import Result, Task

log = logging.getLogger(__name__)

# define connection name for RetryRunner to properly detect it using:
# connection_name = task.task.__globals__.get("CONNECTION_NAME", None)
CONNECTION_NAME = "pyats"


def pyats_send_config(task: Task, config: str = None, **kwargs):
    """
    Salt-nornir Task function to send configuration to devices using
    ``nornir_netmiko.tasks.pyats_send_config`` plugin.

    Device ``configure`` method does not support specifying connection to use to
    send configuration via.

    :param config: (str or list) configuration string or list of commands to send to device
    :param kwargs: (dict) any additional ``**kwargs`` for device connection ``configure`` method
    :return result: Nornir result object with task execution results

    Device ``configure`` method supports below additional arguments that can be passed
    via ``**kwargs``:

    :param reply: Addition Dialogs for interactive config commands.
    :param timeout: Timeout value in sec, Default Value is 30 sec
    :param error_pattern: list of regex to detect command errors
    :param target: Target RP where to execute service, for DualRp only
    :param lock_retries: retry times if config mode is locked, default is 0
    :param lock_retry_sleep: sleep between retries, default is 2 sec
    :param bulk: If False, send all commands in one sendline,
        If True, send commands in chunked mode, default is False
    :param bulk_chunk_lines: maximum number of commands to send per chunk,
        default is 50, 0 means to send all commands in a single chunk
    :param bulk_chunk_sleep: sleep between sending command chunks, default is 0.5 sec
    """
    # run sanity check
    if kwargs.get("dry_run"):
        raise ValueError("pyats_send_config does not support dry_run")

    task.name = "pyats_send_config"
    task_result = Result(host=task.host, result=[], changed=True)

    # get PyATS testbed, device object
    testbed = task.host.get_connection(CONNECTION_NAME, task.nornir.config)
    device = testbed.devices[task.host.name]

    # get configuration from host data if any
    if "commands" in task.host.data.get("__task__", {}):
        config = task.host.data["__task__"]["commands"]
    elif "filename" in task.host.data.get("__task__", {}):
        config = task.host.data["__task__"]["filename"]

    # transform configuration to a list if string given
    if isinstance(config, str):
        config = config.splitlines()

    # send config
    try:
        task_result.result = device.configure(config, **kwargs)
    except:
        log.exception("nornir-salt:pyats_send_config configure error")
        task_result.failed = True
        task_result.exception = traceback.format_exc()
        task_result.changed = False

    return task_result
