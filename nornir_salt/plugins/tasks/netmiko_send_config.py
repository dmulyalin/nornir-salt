"""
netmiko_send_config
###################

This task plugin relies on ``nornir-netmiko`` ``netmiko_send_config`` task
to send configuration commands to devices over SSH or Telnet using Netmiko.

This task plugin applies device configuration following this sequence:

- Retrieve and use, if any, per-host configuration redered by SaltStack from host's
  inventory data ``task.host.data["__task__"]["commands"]`` or 
  ``task.host.data["__task__"]["filename"]`` locations, use configuration provided
  by ``config`` argument otherwise
- If confgiuration is a multiline string, split it to a list of commands
- Push configuration commands to device using ``netmiko_send_config`` task
- If ``commit`` argument provided, perform configuration commit if device supports it
- If ``commit_final_delay`` argument provided, wait for a given timer and perform final commit
- Exit device configuration mode and return configuration results

Dependencies:

* `nornir-netmiko module <https://pypi.org/project/nornir-netmiko/>`_ required

netmiko_send_config sample usage
================================

Code to invoke ``netmiko_send_config`` task::

    from nornir_salt import netmiko_send_config

    output = nr.run(
        task=netmiko_send_config,
        commands=["sinterface loopback 0", "description 'configured by script'"]
    )

netmiko_send_config returns
===========================

Returns Nornir results object with individual tasks names set
equal to commands sent to device.

netmiko_send_config reference
=============================

.. autofunction:: nornir_salt.plugins.tasks.netmiko_send_config.netmiko_send_config
"""
import logging
import traceback
import time
from nornir.core.task import Result, Task

try:
    from nornir_netmiko.tasks import netmiko_send_config as nornir_netmiko_send_config

    HAS_NETMIKO = True
except ImportError:
    HAS_NETMIKO = False

log = logging.getLogger(__name__)


def netmiko_send_config(
    task: Task, 
    config=None, 
    commit=True, 
    commit_final_delay=0,
    **kwargs
):
    """
    Salt-nornir Task function to send configuration to devices using
    ``nornir_netmiko.tasks.netmiko_send_config`` plugin.

    :param kwargs: (dict) any additional arguments to use with
        ``nornir_netmiko.tasks.netmiko_send_config`` task plugin
    :param config: (str or list) configuration string or list of commands to send to device
    :param commit: (bool or dict) by default commit is ``True``, as a result host
        connection commit method will be called. If ``commit`` argument is a
        dictionary, it will be supplied to connection's commit method call as ``**commit``.
    :param commit_final_delay: (int) time to wait before doing final commit, can be used in
        conjunction with commit confirm feature if device supports it.
    :param kwargs: any additional ``**kwargs`` for ``netmiko_send_config`` function.
    :return result: Nornir result object with task execution results

    Default parameters supplied to ``netmiko_send_config`` function call::

        cmd_verify: False
    """
    # run sanity check
    if not HAS_NETMIKO:
        return Result(
            host=task.host,
            failed=True,
            exception="No nornir_netmiko found, is it installed?",
        )

    kwargs.setdefault("cmd_verify", False)
    commit_final_delay = int(commit_final_delay)
    
    # get configuration from host data if any
    if "commands" in task.host.data.get("__task__", {}):
        config = task.host.data["__task__"]["commands"]
    elif "filename" in task.host.data.get("__task__", {}):
        config = task.host.data["__task__"]["filename"]

    # transform configuration to list if string given
    if isinstance(config, str):
        config = config.splitlines()

    # push config to device
    task.run(
        task=nornir_netmiko_send_config,
        config_commands=config,
        name="netmiko_send_config",
        **kwargs
    )

    # get connection object to work with
    conn = task.host.get_connection("netmiko", task.nornir.config)

    # check if need to commit
    if commit:
        commit = commit if isinstance(commit, dict) else {}
        try:
            conn.commit(**commit)
            # check if need to do second commit
            if commit_final_delay:
                time.sleep(commit_final_delay)
                conn.commit()
        except AttributeError:
            pass
        except:
            tb = traceback.format_exc()
            log.error("nornir-salt:netmiko_send_config commit error\n{}".format(tb))
            for task_result in task.results:
                task_result.failed = True
                task_result.exception = tb

    # check if need to exit configuration mode
    if conn.check_config_mode():
        conn.exit_config_mode()

    # set skip_results to True, for ResultSerializer to ignore
    # results for grouped task itself, which are usually None
    return Result(host=task.host, skip_results=True)
