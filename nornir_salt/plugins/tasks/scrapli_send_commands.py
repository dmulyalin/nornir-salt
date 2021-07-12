"""
scrapli_send_commands
#####################

This test plugin uses ``nornir-scrapli`` ``send_command`` task
to send multiple commands to devices.

Dependencies:

* `nornir-scrapli module <https://pypi.org/project/nornir-scrapli/>`_ required

scrapli_send_commands sample usage
==================================

Code to invoke ``scrapli_send_commands`` task::

    from nornir import InitNornir
    from nornir_salt import scrapli_send_commands

    nr = InitNornir(config_file="config.yaml")

    output = nr.run(
        task=scrapli_send_commands,
        commands=["show run", "show clock"],
        scrapli_kwargs={}
    )

scrapli_send_commands returns
=============================

Returns Nornir results object with individual tasks names set
equal to commands sent to device.

scrapli_send_commands reference
===============================

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


def scrapli_send_commands(task, commands=[], interval=0.01, **kwargs):
    """
    Nornir Task function to send show commands to devices using
    ``nornir_scrapli.tasks.send_command`` plugin

    Per-host ``commands`` can be provided using host's object ``data`` attribute
    with ``__task__`` key with value set to dictionary with ``commands`` key
    containing a list of or a multiline string of commands to send to device, e.g.::

        print(host.data["__task__"]["commands"])

        ["ping 1.1.1.1 source 1.1.1.2", "show clock"]

    :param commands: (list) commands list to send to device(s)
    :param interval: (int) interval between sending commands, default 0.01s
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

    # run interval sanity check
    interval = interval if isinstance(interval, (int, float)) else 0.01

    # get per-host commands if any
    if "commands" in task.host.data.get("__task__", {}):
        commands = task.host.data["__task__"]["commands"]
    elif "filename" in task.host.data.get("__task__", {}):
        commands = task.host.data["__task__"]["filename"]

    # prep commands by splitting them
    if isinstance(commands, str):
        commands = commands.splitlines()

    # send commands to device
    for command in commands:
        task.run(task=send_command, command=command, name=command, **kwargs)
        time.sleep(interval)

    # set skip_results to True, for ResultSerializer to ignore
    # results for grouped task itself, which are usually None
    return Result(host=task.host, skip_results=True)
