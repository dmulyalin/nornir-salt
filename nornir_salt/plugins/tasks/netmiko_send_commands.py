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

    from nornir_salt.plugins.tasks import netmiko_send_commands

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
import logging

from nornir.core.task import Result, Task
from nornir_salt.utils import cli_send_commands, cli_form_commands
from .netmiko_send_command_ps import netmiko_send_command_ps, send_command_ps

from nornir_salt.utils.pydantic_models import model_netmiko_send_commands
from nornir_salt.utils.yangdantic import ValidateFuncArgs

try:
    from nornir_netmiko.tasks import netmiko_send_command

    HAS_NETMIKO = True
except ImportError:
    HAS_NETMIKO = False
    netmiko_send_command = None

log = logging.getLogger(__name__)

# define connection name for RetryRunner to properly detect it using:
# connection_name = task.task.__globals__.get("CONNECTION_NAME", None)
CONNECTION_NAME = "netmiko"


@ValidateFuncArgs(
    model=model_netmiko_send_commands, mixins=[netmiko_send_command, send_command_ps]
)
def netmiko_send_commands(
    task: Task,
    commands: list = None,
    interval: float = 0.01,
    use_ps: bool = False,
    split_lines: bool = True,
    new_line_char: str = "_br_",
    repeat: int = 1,
    stop_pattern: str = None,
    repeat_interval: int = 1,
    return_last: int = None,
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
    :param interval: (int) interval between sending commands
    :param use_ps: (bool) set to True to switch to experimental send_command_ps method
    :param split_lines: (bool) if True split multiline string to commands, send multiline
        string to device as is otherwise
    :param new_line_char: (str) characters to replace in commands with new line ``\\n``
        before sending command to device, default is ``_br_``, useful to simulate enter key
    :param repeat: (int) - number of times to repeat the commands
    :param stop_pattern: (str) - stop commands repeat if at least one of commands output
        matches provided glob pattern
    :param repeat_interval: (int) time in seconds to wait between repeating all commands
    :param return_last: (int) if repeat greater then 1, returns requested last
        number of commands outputs
    :return result: Nornir result object with task results named after commands
    """
    # run sanity check
    if not HAS_NETMIKO:
        return Result(
            host=task.host,
            failed=True,
            exception="No nornir_netmiko found, is it installed?",
        )

    # increase read timeout to 30 from default 10 seconds
    kwargs.setdefault("read_timeout", 30)

    commands = cli_form_commands(
        task=task,
        commands=commands,
        split_lines=split_lines,
        new_line_char=new_line_char,
    )

    cli_send_commands(
        task=task,
        plugin_fun=netmiko_send_command_ps if use_ps else netmiko_send_command,
        plugin_fun_cmd_arg="command_string",
        commands=commands,
        interval=interval,
        stop_pattern=stop_pattern,
        repeat=repeat,
        kwargs=kwargs,
        repeat_interval=repeat_interval,
        return_last=return_last,
    )

    # set skip_results to True, for ResultSerializer to ignore
    # results for grouped task itself, which are usually None
    return Result(host=task.host, skip_results=True)
