"""
netmiko_send_commands
#####################

This task plugin uses ``nornir-netmiko`` ``netmiko_send_command`` task
to send multiple commands to devices.

Dependencies:

* `nornir-netmiko module <https://pypi.org/project/nornir-netmiko/>`_ required

netmiko_send_commands sample usage
==================================

Code to invoke ``netmiko_send_commands`` task::

    from nornir_salt import netmiko_send_commands

    output = nr.run(
        task=netmiko_send_commands,
        commands=["show run", "show clock"]
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
import logging
from nornir.core.task import Result, Task
from .netmiko_send_command_ps import netmiko_send_command_ps

try:
    from nornir_netmiko.tasks import netmiko_send_command

    HAS_NETMIKO = True
except ImportError:
    HAS_NETMIKO = False

log = logging.getLogger(__name__)

# define connection name for RetryRunner to properly detect it using:
# connection_name = task.task.__globals__.get("CONNECTION_NAME", None)
CONNECTION_NAME = "netmiko"


def netmiko_send_commands(
    task: Task,
    commands=None,
    interval=0.01,
    use_ps: bool = False,
    split_lines: bool = True,
    new_line_char: str = "_br_",
    **kwargs
):
    """
    Nornir Task function to send show commands to devices using
    ``nornir_netmiko.tasks.netmiko_send_command`` plugin

    Per-host ``commands`` can be provided using host's object ``data`` attribute
    with ``__task__`` key with value set to dictionary with ``commands`` key
    containing a list of or a multiline string of commands to send to device, e.g.::

        print(host.data["__task__"]["commands"])

        ["ping 1.1.1.1 source 1.1.1.2", "show clock"]

    Alternatively, ``__task__`` can contain ``filename`` key with commands string
    to send to device.

    :param kwargs: (dict) any additional arguments to pass to ``netmiko_send_command``
        ``nornir-netmiko`` task
    :param commands: (list or str) list or multiline string of commands to send to device
    :param interval: (int) interval between sending commands, default 0.01s
    :param use_ps: (bool) set to True to switch to experimental send_command_ps method
    :param split_lines: (bool) if True (default) - split multiline string to commands,
        if False, send multiline string to device as is; honored only when ``use_ps`` is
        True, ``split_lines`` ignored if ``use_ps`` is False
    :param new_line_char: (str) characters to replace in commands with new line ``\\n``
        before sending command to device, default is ``_br_``, useful to simulate enter key
    :return result: Nornir result object with task results named after commands
    """
    # run sanity check
    if not HAS_NETMIKO:
        return Result(
            host=task.host,
            failed=True,
            exception="No nornir_netmiko found, is it installed?",
        )

    commands = commands or []

    # run interval sanity check
    interval = interval if isinstance(interval, (int, float)) else 0.01

    # get per-host commands if any
    if "commands" in task.host.data.get("__task__", {}):
        if commands:
            for c in task.host.data["__task__"]["commands"]:
                if c not in commands:
                    commands.append(c)
        else:
            commands = task.host.data["__task__"]["commands"]
    elif "filename" in task.host.data.get("__task__", {}):
        commands = task.host.data["__task__"]["filename"]

    # normalize commands to a list
    if isinstance(commands, str) and split_lines:
        commands = commands.splitlines()
    elif isinstance(commands, str) and not split_lines:
        commands = [commands]

    # remove empty lines/commands that can left after rendering
    commands = [c for c in commands if c.strip()]

    # iterate over commands and see if need to add empty line - hit enter
    commands = [
        c.replace(new_line_char, "\n") if new_line_char in c else c for c in commands
    ]

    # run commands
    if use_ps:
        # send commands
        for index, command in enumerate(commands):
            task.run(
                task=netmiko_send_command_ps,
                command_string=command,
                name=command.strip().splitlines()[0],
                **kwargs
            )
            # do not sleep after last command sent
            if index != len(commands) - 1:
                time.sleep(interval)
    else:
        # send commands
        for command in commands:
            task.run(
                task=netmiko_send_command,
                command_string=command,
                name=command.strip(),
                **kwargs
            )
            time.sleep(interval)

    # set skip_results to True, for ResultSerializer to ignore
    # results for grouped task itself, which are usually None
    return Result(host=task.host, skip_results=True)
