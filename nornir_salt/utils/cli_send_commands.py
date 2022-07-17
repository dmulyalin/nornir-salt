import time
import logging

from fnmatch import fnmatchcase
from nornir.core.task import Task

log = logging.getLogger(__name__)


def cli_send_commands(
    task: Task,
    plugin_fun,
    commands: list,
    kwargs: dict,
    plugin_fun_cmd_arg: str = "command",
    interval: int = 0.01,
    repeat: int = 1,
    repeat_interval: int = 1,
    stop_pattern: str = None,
    return_last: int = None,
):
    """
    Helper function to send commands to device.

    Used by:

    - netmiko_send_commands
    - scrapli_send_commands

    Supports:
    - repeating commands given amount of time
    - searching command outputs for pattern and on match stop repeating commands
    - inter-command/commands timers

    :param task: (obj) task object
    :param plugin_fun: (obj) callable plugin function to use
    :param plugin_fun_cmd_arg: (str) command argument to use with plugin function,
        different ``plugin_fun`` expect different argument for command string,
        ``plugin_fun_cmd_arg`` indicates what is the command argument name to use
    :param commands: (list) commands list to send
    :param kwargs: (dict) arguments to use with task plugin
    :param repeat: (int) number of times to repeat commands
    :param interval: (int) time to in between sending commands
    :param stop_pattern: (str) glob pattern to check in output
    :param return_last: (int) if repeat greater then 1, returns requested last
        number of commands outputs
    :return: (bool) True if given stop_pattern is in output, False otherwise
    """
    stop_patern_matched = False
    len_before = len(task.results) - 1  # record task results length

    for seq in range(repeat):
        for index, command in enumerate(commands):
            name = command.strip().splitlines()[0]
            name = "{}:{}".format(seq + 1, name) if repeat > 1 else name
            kwargs[plugin_fun_cmd_arg] = command
            res = task.run(task=plugin_fun, name=name, **kwargs)
            # check if results contain pattern
            if stop_pattern and repeat > 1:
                # do not overwrite pattern_match if its already True
                stop_patern_matched = (
                    True
                    if stop_patern_matched is True
                    else any(fnmatchcase(str(r.result), stop_pattern) for r in res)
                )
            # do not wait after last command sent
            if index + 1 < len(commands):
                time.sleep(interval)

        if stop_patern_matched:
            break
        # do not wait after last repeat done
        if seq + 1 < repeat:
            time.sleep(repeat_interval)

    # trim task results if requested so
    if repeat > 1 and return_last is not None:
        len_after = len(task.results) - 1
        remove_count = len_after - len_before - return_last * len(commands)
        # do nothing if asked to return more tasks then have
        if remove_count > 0:
            for _ in range(remove_count):
                _ = task.results.pop(len_before + 1)
