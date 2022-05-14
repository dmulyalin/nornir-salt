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
    from nornir_salt.plugins.tasks import scrapli_send_commands

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
from nornir.core.task import Result, Task
from nornir_salt.utils import cli_send_commands, cli_form_commands
from nornir_salt.utils.pydantic_models import model_scrapli_send_commands
from nornir_salt.utils.yangdantic import ValidateFuncArgs

try:
    from nornir_scrapli.tasks import send_command

    HAS_SCRAPLI = True
except ImportError:
    HAS_SCRAPLI = False
    send_command = None

# define connection name for RetryRunner to properly detect it using:
# connection_name = task.task.__globals__.get("CONNECTION_NAME", None)
CONNECTION_NAME = "scrapli"


@ValidateFuncArgs(model_scrapli_send_commands, mixins=[send_command])
def scrapli_send_commands(
    task: Task,
    commands: list = None,
    interval: int = 0.01,
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
    :param kwargs: (dict) arguments for nornir-scrapli ``send_command`` plugin
    :param split_lines: (bool) if True split multiline string to commands, send multiline
        string to device as is otherwise
    :param repeat: (int) - number of times to repeat the commands
    :param stop_pattern: (str) - stop commands repeat if at least one of commands output
        matches provided glob pattern
    :param repeat_interval: (int) time in seconds to wait between repeating all commands
    :param return_last: (int) if repeat greater then 1, returns requested last
        number of commands outputs
    :return result: Nornir result object with task results named after commands
    """
    # run sanity check
    if not HAS_SCRAPLI:
        return Result(
            host=task.host,
            failed=True,
            exception="No nornir_scrapli found, is it installed?",
        )

    commands = cli_form_commands(
        task=task,
        commands=commands,
        split_lines=split_lines,
        new_line_char=new_line_char,
    )

    cli_send_commands(
        task=task,
        plugin_fun=send_command,
        plugin_fun_cmd_arg="command",
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
