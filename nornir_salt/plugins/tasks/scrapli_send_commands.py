"""
scrapli_send_commands
#####################

This plugin uses ``nornir-scrapli`` ``send_command`` task to send multiple commands
to devices pre-processing commands accordingly.

Pre-processing includes:

- Check and if any - retrieve per-host commands from host's inventory data
  ``task.host.data["__task__"]["commands"]`` or from ``task.host.data["__task__"]["filename"]``
- If command is a multi-line string, split it to individual lines or form a list with single command
- Iterate over commands list and remove empty strings
- Iterate over commands and replace ``new_line_char`` with ``\\n`` new line

Next, commands send one by one to device using ``send_command`` task plugin,
each task named after the command being sent. Sleep for given ``interval`` between
sending commands.

Dependencies:

* `nornir-scrapli module <https://pypi.org/project/nornir-scrapli/>`_ required

Sample Usage
============

Code to invoke ``scrapli_send_commands`` task::

    from nornir import InitNornir
    from nornir_salt import scrapli_send_commands

    nr = InitNornir(config_file="config.yaml")

    output = nr.run(
        task=scrapli_send_commands,
        commands=["show run", "show clock"]
    )

Task scrapli_send_commands returns Nornir results object with individual tasks
names set equal to commands sent to device.

API Reference
=============

.. autofunction:: nornir_salt.plugins.tasks.scrapli_send_commands.scrapli_send_commands
"""
import time
from nornir.core.task import Result, Task

try:
    from nornir_scrapli.tasks import send_command

    HAS_SCRAPLI = True
except ImportError:
    HAS_SCRAPLI = False

# define connection name for RetryRunner to properly detect it using:
# connection_name = task.task.__globals__.get("CONNECTION_NAME", None)
CONNECTION_NAME = "scrapli"


def scrapli_send_commands(
    task: Task, commands=None, interval=0.01, new_line_char="_br_", **kwargs
):
    """
    Nornir Task function to send show commands to devices using
    ``nornir_scrapli.tasks.send_command`` plugin

    Per-host ``commands`` can be provided using host's object ``data`` attribute
    with ``__task__`` key with value set to dictionary with ``commands`` key
    containing a list of or a multiline string of commands to send to device, e.g.::

        print(host.data["__task__"]["commands"])

        ["ping 1.1.1.1 source 1.1.1.2", "show clock"]

    :param commands: (list or str) list or multiline string of commands to send to device
    :param interval: (int) interval between sending commands, default 0.01s
    :param new_line_char: (str) characters to replace in commands with new line ``\\n``
        before sending command to device, default is ``_br_``, useful to simulate enter key
    :param kwargs: (dict) any additional arguments to pass to scrapli send_command
    :return result: Nornir result object with task execution results
    """
    # run sanity check
    if not HAS_SCRAPLI:
        return Result(
            host=task.host,
            failed=True,
            exception="No nornir_scrapli found, is it installed?",
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

    # normilize commands to a list
    if isinstance(commands, str):
        commands = commands.splitlines()

    # remove empty lines/commands that can left after rendering
    commands = [c for c in commands if c.strip()]

    # iterate over commands and see if need to add empty line - hit enter
    commands = [
        c.replace(new_line_char, "\n") if new_line_char in c else c for c in commands
    ]

    # send commands to device
    for command in commands:
        task.run(task=send_command, command=command, name=command.strip(), **kwargs)
        time.sleep(interval)

    # set skip_results to True, for ResultSerializer to ignore
    # results for grouped task itself, which are usually None
    return Result(host=task.host, skip_results=True)
