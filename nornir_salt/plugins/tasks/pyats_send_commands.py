"""
pyats_send_commands
#########################

This task plugin uses PyATS devices ``execute`` method
to send multiple commands to devices pre-processing commands accordingly.

Pre-processing includes:

- Check and if any - retrieve per-host commands from host's inventory data
  ``task.host.data["__task__"]["commands"]`` or from ``task.host.data["__task__"]["filename"]``
- If command is a multi-line string, split it to individual lines or form a list with single command
- Iterate over commands list and remove empty strings
- Iterate over commands and replace ``new_line_char`` with ``\\n`` new line

Tere are several modes that ``pyats_send_commands`` task plugin can operate in:

1. If ``parse`` is true and device platform supports it, send commands one by one parsing
   their output waiting for ``interval`` in betwen commands if ``interval`` provided, if
   no parser available for this platofrm to parse command output, exception message returned
   for such a command
2. If ``interval`` argument provided, commands send one by one to device using
   ``execute`` method sleeping for given ``interval`` between commands
3. If ``via`` argument refers to connections pool object, send commands in parallel,
   commands excution order not guaranteed
4. By default, all commands supplied to device's connection ``execute`` method as is

Dependencies:

* `PyATS library <https://pypi.org/project/pyats/>`_ required
* `Genie library <https://pypi.org/project/genie/>`_ required

Useful links:

- `Genie parsers <https://pubhub.devnetcloud.com/media/genie-feature-browser/docs/#/parsers>`_

Sample Usage
============

Given this inventory::

    host-1:
      connection_options:
        pyats:
          extras:
            devices:
              host-1:
                os: iosxe
                credentials:
                  default:
                    username: nornir
                    password: nornir
                connections:
                  default:
                    protocol: ssh
                    ip: 10.0.1.4
                    port: 22
                  vty_1:
                    protocol: ssh
                    ip: 10.0.1.4
                    pool: 3

Code to invoke ``pyats_send_commands`` task::

    from nornir_salt import pyats_send_commands

    # send via "default" connection
    output_via_default = nr.run(
        task=pyats_send_commands,
        commands=["show run", "show clock"]
    )

    # send via vty_1 connection pool of 3 SSH connections
    output_via_pool = nr.run(
        task=pyats_send_commands,
        commands=["show run", "show clock"],
        via="vty_1"
    )

    # send via "default" connection with 5s interval between commands
    output_with_interval = nr.run(
        task=pyats_send_commands,
        commands=["show run", "show clock"],
        interval=5
    )

    # send commands and parse output
    output_parse = nr.run(
        task=pyats_send_commands,
        commands=["show hostname", "show clock"],
        parse=True
    )

Returns Nornir results object with individual tasks names set
equal to commands sent to device.

Reference
=========

.. autofunction:: nornir_salt.plugins.tasks.pyats_send_commands.pyats_send_commands
"""
import time
import logging
import traceback

from nornir.core.task import Result, Task
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from pyats.connections.pool import ConnectionPool
    from genie.libs.parser.utils.common import ParserNotFound
    from genie.libs.parser.utils import get_parser

    HAS_PYATS = True
except ImportError:
    HAS_PYATS = False

log = logging.getLogger(__name__)

# define connection name for RetryRunner to properly detect it using:
# connection_name = task.task.__globals__.get("CONNECTION_NAME", None)
CONNECTION_NAME = "pyats"


def _form_results(task, res, command):
    """
    Helper function to save code on forming results out of PyATS output

    :param task: (obj) Nornir task object
    :param res: (str, dict) PyATS command execution results
    :param command: (str, list) command string or list of commands sent
    """
    # if non-multiline or single command was provided res is a string
    if isinstance(res, str):
        cmd = ", ".join(command) if isinstance(command, list) else command.strip()
        task.results.append(Result(host=task.host, result=res, name=cmd))
    # if multiline command provided or a list of commands res is a dictionary
    elif isinstance(res, dict):
        for cmd, output in res.items():
            task.results.append(Result(host=task.host, result=output, name=cmd.strip()))


def pyats_send_commands(
    task: Task,
    commands: list = None,
    interval: int = None,
    new_line_char: str = "_br_",
    via: str = "default",
    parse: bool = False,
    **kwargs
):
    """
    Nornir Task function to send show commands to devices using PyATS Unicon module.

    Per-host ``commands`` can be provided using host's object ``data`` attribute
    with ``__task__`` key with value set to dictionary with ``commands`` key
    containing a list of or a multiline string of commands to send to device, e.g.::

        print(host.data["__task__"]["commands"])

        ["ping 1.1.1.1 source 1.1.1.2", "show clock"]

    Alternatively, ``__task__`` can contain ``filename`` key with commands string
    to send to device.

    :param kwargs: (dict) used with connection's ``execute`` or testbed's ``parse`` method as ``**kwargs``
    :param commands: (list or str) list or multiline string of commands to send to device
    :param interval: (int) interval between sending commands, default is None - commands send simelteniously
    :param new_line_char: (str) characters to replace in commands with new line ``\\n``
        before sending command to device, default is ``_br_``, useful to simulate enter key
    :param via: (str) testbed inventory connection name, default is ``default``
    :param parse: (bool) if True, parses command output and returns structured data
    :return result: Nornir result object with task results named after commands
    """
    # run sanity check
    if not HAS_PYATS:
        return Result(
            host=task.host,
            failed=True,
            exception="Failed to import PyATS library, is it installed?",
        )

    commands = commands or []

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
    if isinstance(commands, str):
        commands = commands.splitlines()
    elif isinstance(commands, str):
        commands = [commands]

    # remove empty lines/commands that can left after rendering
    commands = [c for c in commands if c.strip()]

    # iterate over commands and see if need to add empty line - hit enter
    commands = [
        c.replace(new_line_char, "\n") if new_line_char in c else c for c in commands
    ]

    # get PyATS testbed, device and connection objects
    testbed = task.host.get_connection(CONNECTION_NAME, task.nornir.config)
    device = testbed.devices[task.host.name]
    if hasattr(device, via):
        connection = getattr(device, via)
    else:
        raise RuntimeError("{} has no connection '{}'".format(task.host.name, via))

    # check if nee to parse output
    if parse:
        log.debug(
            "nornir-salt:pyats_send_commands sending commands one by one and parsing output"
        )
        for command in commands:
            try:
                get_parser(command, device)  # raises exception if no parse available
                output = connection.execute(command, **kwargs)
                result = device.parse(command, output=output)
                result = result.q.reconstruct()  # result is PyATS Dq Dict object
                exception = None
            except ParserNotFound as e:
                result = str(e)
                exception = traceback.format_exc()
            task.results.append(
                Result(
                    host=task.host,
                    result=result,
                    exception=exception,
                    name=command.strip(),
                )
            )
            if isinstance(interval, (int, float)):
                time.sleep(interval)
    # send commands one by one with interval
    elif isinstance(interval, (int, float)):
        log.debug(
            "nornir-salt:pyats_send_commands connection '{}', sending commands with '{}s' interval".format(
                via, interval
            )
        )
        for command in commands:
            _form_results(task, connection.execute(command, **kwargs), command)
            time.sleep(interval)
    # make use of PyATS connections pool to send commands in parrallel
    elif isinstance(connection, ConnectionPool):
        size = connection._pool_size if hasattr(connection, "_pool_size") else 5
        log.debug(
            "nornir-salt:pyats_send_commands connections pool '{}', size '{}', sending commands in parrallel".format(
                via, size
            )
        )
        # execute threads to send commands across multiple connections
        with ThreadPoolExecutor(size) as pool:
            cmd_futures = {
                pool.submit(lambda cmd: connection.execute(cmd, **kwargs), cmd): cmd
                for cmd in commands
            }
            for future in as_completed(cmd_futures):
                _form_results(task, future.result(), cmd_futures[future])
    # send all commands at once
    else:
        log.debug(
            "nornir-salt:pyats_send_commands connection '{}', sending commands all at once".format(
                via
            )
        )
        _form_results(task, connection.execute(commands, **kwargs), commands)

    # set skip_results to True, for ResultSerializer to ignore
    # results for grouped task itself, which are usually None
    return Result(host=task.host, skip_results=True)
