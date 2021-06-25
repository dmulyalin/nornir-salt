"""
netmiko_send_commands
#####################

This test plugin uses ``nornir-netmiko`` ``netmiko_send_command`` task
to send multiple commands to devices.

Dependencies:

* `nornir-netmiko module <https://pypi.org/project/nornir-netmiko/>`_ required

netmiko_send_commands sample usage
==================================

Code to invoke ``netmiko_send_commands`` task::

    from nornir_salt import netmiko_send_commands

    output = nr.run(
        task=netmiko_send_commands,
        commands=["show run", "show clock"],
        netmiko_kwargs={}
    )

netmiko_send_commands returns
=============================

Returns Nornir results object with individual tasks names set
equal to commands sent to device.

netmiko_send_commands reference
===============================

.. autofunction:: nornir_salt.plugins.tasks.netmiko_send_commands.netmiko_send_commands
"""
import time
from nornir.core.task import Result, Task
from nornir_netmiko.tasks import netmiko_send_command
from .netmiko_send_command_ps import netmiko_send_command_ps

# define connection name for RetryRunner to properly detect it using:
# connection_name = task.task.__globals__.get("CONNECTION_NAME", None)
CONNECTION_NAME = "netmiko"


def netmiko_send_commands(
    task,
    commands,
    interval=0.01,
    use_timing: bool = False,
    use_ps=False,
    enable: bool = False,
    netmiko_kwargs: dict = {},
    **kwargs
):
    """
    Nornir Task function to send show commands to devices using
    ``nornir_netmiko.tasks.netmiko_send_command`` plugin

    :param netmiko_kwargs: (dict) additional arguments to pass to send_command methods
    :param commands: (list) commands to send to device
    :param interval: (int) interval between sending commands, default 0.01s
    :param use_timing: (bool) set to True to switch to send_command_timing method
    :param use_ps: (bool or dict) set to True to switch to experimental send_command_ps method,
        if dictionary, will supply it to ps mode command run as ``**kwargs``
    :param enable: (bool) set to True to force Netmiko .enable() call
    :return result: Nornir result object with task results named after commands
    """
    # run interval sanity check
    interval = interval if isinstance(interval, (int, float)) else 0.01

    # run commands
    if use_ps:
        ps_kwargs = use_ps if isinstance(use_ps, dict) else netmiko_kwargs
        for command in commands:
            task.run(
                task=netmiko_send_command_ps,
                command_string=command,
                name=command,
                enable=enable,
                **ps_kwargs
            )
            time.sleep(interval)
    else:
        for command in commands:
            task.run(
                task=netmiko_send_command,
                command_string=command,
                name=command,
                use_timing=use_timing,
                enable=enable,
                **netmiko_kwargs
            )
            time.sleep(interval)

    # set skip_results to True, for ResultSerializer to ignore
    # results for grouped task itself, which are usually None
    return Result(host=task.host, skip_results=True)
