"""
netmiko_send_config
###################

This task plugin relies on ``Netmiko`` conection ``send_config_set`` method
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

* `nornir-netmiko module <https://pypi.org/project/nornir-netmiko/>`_ required

netmiko_send_config sample usage
================================

Code to invoke ``netmiko_send_config`` task::

    from nornir_salt.plugins.tasks import netmiko_send_config

    output = nr.run(
        task=netmiko_send_config,
        commands=["interface loopback 0", "description 'configured by script'"]
    )

netmiko_send_config returns
===========================

Returns Nornir results object with task name set to ``netmiko_send_config``
and results containing commands execution CLI output.

netmiko_send_config reference
=============================

.. autofunction:: nornir_salt.plugins.tasks.netmiko_send_config.netmiko_send_config
"""
import logging
import traceback
import time
from nornir.core.task import Result, Task
from nornir_salt.utils import cfg_form_commands
from nornir_salt.utils.pydantic_models import model_netmiko_send_config
from nornir_salt.utils.yangdantic import ValidateFuncArgs

try:
    from nornir_netmiko.tasks import (  # noqa
        netmiko_send_config as nornir_netmiko_send_config,
    )

    HAS_NETMIKO = True
except ImportError:
    HAS_NETMIKO = False

log = logging.getLogger(__name__)

# define connection name for RetryRunner to properly detect it using:
# connection_name = task.task.__globals__.get("CONNECTION_NAME", None)
CONNECTION_NAME = "netmiko"


@ValidateFuncArgs(model_netmiko_send_config)
def netmiko_send_config(
    task: Task,
    config=None,
    commit=True,
    commit_final_delay=0,
    batch=0,
    enable=True,
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
    :param batch: (int) commands count to send in batches, sends all at once by default
    :param enable: (bool) if True (default), attempts to enter enable-mode
    :return result: Nornir result object with task execution results

    Default parameters supplied to ``netmiko_send_config`` function call::

        cmd_verify: False
        exit_config_mode: False if batch provided or commit is True else unmodified

    Batch mode controlled by ``batch`` parameter, by default all configuration commands send
    at once, but that approach might lead to Netmiko timeout errors if device takes too long
    to respond, sending commands in batches helps to overcome that problem.
    """
    # run sanity check
    if not HAS_NETMIKO:
        return Result(
            host=task.host,
            failed=True,
            exception="No nornir_netmiko found, is it installed?",
        )
    if kwargs.get("dry_run"):
        raise ValueError("netmiko_send_config does not support dry_run")

    task.name = "netmiko_send_config"
    kwargs.setdefault("cmd_verify", False)
    commit_final_delay = int(commit_final_delay)
    batch = max(0, int(batch))
    result = []
    task_result = Result(host=task.host, result=None, changed=True)
    conn = task.host.get_connection(CONNECTION_NAME, task.nornir.config)
    config = cfg_form_commands(task=task, config=config)

    # make sure netmiko has prompt, some devices fail to enter
    # enable mode because of is_alive called by keepalive function
    _ = conn.find_prompt()
    # enter enable mode
    if enable and conn.check_enable_mode() is False:
        conn.enable()

    if batch or commit:
        kwargs["exit_config_mode"] = False

    # push config to device in batches
    if batch:
        for i in range(0, len(config), batch):
            chunk = config[i : i + batch]
            result.append(conn.send_config_set(config_commands=chunk, **kwargs))
    # push config all at once
    else:
        result.append(conn.send_config_set(config_commands=config, **kwargs))

    # check if need to commit
    if commit:
        commit = commit if isinstance(commit, dict) else {}
        try:
            result.append(conn.commit(**commit))
            # check if need to do second commit
            if commit_final_delay:
                time.sleep(commit_final_delay)
                result.append(conn.commit())
        except AttributeError:
            pass
        except:
            tb = traceback.format_exc()
            log.error("nornir-salt:netmiko_send_config commit error\n{}".format(tb))
            task_result.failed = True
            task_result.exception = tb
            task_result.changed = False

    # check if need to exit configuration mode
    if conn.check_config_mode():
        result.append(conn.exit_config_mode())

    task_result.result = "\n".join(str(i) for i in result)

    return task_result
