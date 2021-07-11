"""
netmiko_send_config
###################

This task plugin uses ``nornir-netmiko`` ``netmiko_send_config`` task
to configuration commands to devices over SSH or Telnet.

``netmiko_send_config`` exists as part of ``nornir_salt`` repository to facilitate 
per-host configuration rendering performed by SALT prior to running the task.

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


def netmiko_send_config(task, config=None, commit=True, **kwargs):
    """
    Salt-nornir Task function to send configuration to devices using
    ``nornir_netmiko.tasks.netmiko_send_config`` plugin.

    :param kwargs: (dict) any additional arguments to use with
        ``nornir_netmiko.tasks.netmiko_send_config`` task plugin
    :param config: (str or list) configuration string or list of commands to send to device
    :param commit: (bool or dict) by default commit is ``True``, as a result host
        connection commit method will be called. If ``commit`` argument is a
        dictionary, it will be supplied to commit call using ``**commit``.
    :param kwargs: any additional ``**kwargs`` for ``netmiko_send_config`` function.
    :return result: Nornir result object with task execution results

    Parameters supplied to ``netmiko_send_config`` function call that override
    Netmiko default values::

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

    # get configuration
    if "commands" in task.host.data.get("__task__", {}):
        config = task.host.data["__task__"]["commands"]
    elif "filename" in task.host.data.get("__task__", {}):
        config = task.host.data["__task__"]["filename"]

    # transform configuration to list if string given
    if isinstance(config, str):
        config = config.splitlines()

    # get connection and send bogus command to clean it from
    # HostsKeepalive or previous tasks' leftovers, this is
    # required on some platforms for Netmiko to properly match
    # propmt and commands being sent
    conn = task.host.get_connection("netmiko", task.nornir.config)
    conn.send_command("#__0\n")

    # push config to device
    task.run(
        task=nornir_netmiko_send_config,
        config_commands=config,
        name="netmiko_send_config",
        **kwargs
    )

    # check if need to commit
    if commit:
        commit = commit if isinstance(commit, dict) else {}
        try:
            conn.commit(**commit)
            conn.exit_config_mode()
            log.debug(
                "salt-nornir {} config commited, exited config mode.".format(
                    task.host.name
                )
            )
        except AttributeError:
            pass
        except:
            tb = traceback.format_exc()
            log.error("netmiko_send_config: commit error\n{}".format(tb))
            for task_result in task.results:
                task_result.failed = True
                task_result.exception = tb

    # set skip_results to True, for ResultSerializer to ignore
    # results for grouped task itself, which are usually None
    return Result(host=task.host, skip_results=True)
