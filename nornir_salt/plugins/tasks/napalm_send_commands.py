"""
napalm_send_commands
####################

This task plugin uses ``nornir-napalm`` ``napalm_cli`` task
to send multiple commands to devices pre-processing commands accordingly.

Pre-processing includes:

- Check and if any - retrieve per-host commands from host's inventory data
  ``task.host.data["__task__"]["commands"]`` or from ``task.host.data["__task__"]["filename"]``
- If command is a multi-line string, split it to individual lines or form a list with single command
- Iterate over commands list and remove empty strings
- Iterate over commands and replace ``new_line_char`` with ``\\n`` new line

Next, if ``interval`` argument provided commands send one by one to device using
``napalm_cli`` task plugin sleeping for given ``interval`` between commands. If
``interval`` argument is not provided, all commands sent at once.

Dependencies:

* `nornir-napalm module <https://pypi.org/project/nornir-napalm/>`_ required

napalm_send_commands sample usage
=================================

Code to invoke ``napalm_send_commands`` task::

    from nornir_salt.plugins.tasks import napalm_send_commands

    output = nr.run(
        task=napalm_send_commands,
        commands=["show run", "show clock"]
    )

Task ``napalm_send_commands`` returns Nornir results object with individual tasks
names set equal to commands sent to device.

API Reference
=============

.. autofunction:: nornir_salt.plugins.tasks.napalm_send_commands.napalm_send_commands
"""
import time
import logging
from nornir.core.task import Result, Task
from nornir_salt.utils import cli_form_commands
from nornir_salt.utils.pydantic_models import model_napalm_send_commands
from nornir_salt.utils.yangdantic import ValidateFuncArgs

try:
    from nornir_napalm.plugins.tasks import napalm_cli

    HAS_NAPALM = True
except ImportError:
    HAS_NAPALM = False

log = logging.getLogger(__name__)

# define connection name for RetryRunner to properly detect it using:
# connection_name = task.task.__globals__.get("CONNECTION_NAME", None)
CONNECTION_NAME = "napalm"


@ValidateFuncArgs(model_napalm_send_commands)
def napalm_send_commands(
    task: Task,
    commands=None,
    interval=None,
    new_line_char: str = "_br_",
    split_lines: bool = True,
):
    """
    Nornir Task function to send show commands to devices using ``napalm_cli`` task
    plugin.

    Per-host ``commands`` can be provided using host's object ``data`` attribute
    with ``__task__`` key with value set to dictionary with ``commands`` key
    containing a list of or a multiline string of commands to send to device, e.g.::

        print(host.data["__task__"]["commands"])

        ["ping 1.1.1.1 source 1.1.1.2", "show clock"]

    Alternatively, ``__task__`` can contain ``filename`` key with commands string
    to send to device.

    :param commands: (list or str) list or multiline string of commands to send to device
    :param interval: (int) interval between sending commands, default None
    :param new_line_char: (str) characters to replace in commands with new line ``\\n``
        before sending command to device, default is ``_br_``, useful to simulate enter key
    :param split_lines: (bool) if True split multiline string to commands, send multiline
        string to device as is otherwise
    :return result: Nornir result object with task results named after commands
    """
    # run sanity check
    if not HAS_NAPALM:
        return Result(
            host=task.host,
            failed=True,
            exception="No nornir-napalm found, is it installed?",
        )

    commands = cli_form_commands(
        task=task,
        commands=commands,
        split_lines=split_lines,
        new_line_char=new_line_char,
    )

    # send commands one by one
    if interval:
        for index, command in enumerate(commands):
            task.run(task=napalm_cli, commands=[command])
            # do not sleep after last command sent
            if index != len(commands) - 1:
                time.sleep(interval)
    # send all at once
    else:
        task.run(task=napalm_cli, commands=commands)

    # iterate over results and form per-command results
    per_command_results = []
    while task.results:
        res = task.results.pop()
        # check if task failed, do nothing if so
        if res.failed or res.exception:
            per_command_results.append(res)
            continue
        # iterate over dictionary result and construct per-command result
        for command, output in res.result.items():
            per_command_results.append(
                Result(host=task.host, result=output, name=command.strip())
            )
    task.results.extend(per_command_results)

    # set skip_results to True, for ResultSerializer to ignore
    # results for grouped task itself, which are usually None
    return Result(host=task.host, skip_results=True)
