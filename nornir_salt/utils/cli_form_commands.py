import logging

from nornir.core.task import Task

log = logging.getLogger(__name__)


def cli_form_commands(
    task: Task,
    commands: list = None,
    split_lines: bool = True,
    new_line_char: str = "_br_",
):
    """
    Helper function to form a list of commands to send to device.

    Used by:

    - netmiko_send_commands
    - scrapli_send_commands
    - napalm_send_commands
    - pyats_send_commands

    Support:

    - extracting commands from host's __task__ data
    - splitting multiline commands string to a list of commands
    - removing empty command items
    - replacing new line patter within the lines

    :param task: (obj) Nornir task object
    :param commands: (list or str) list or multiline string of commands to be send to device
    :param split_lines: (bool) if True split multiline string to commands, uses multiline
        string as is otherwise
    :param new_line_char: (str) characters to replace in commands with new line ``\\n``
        while forming commands to be send to device, default is ``_br_``, useful to simulate
        enter key
    """
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
    if split_lines:
        if isinstance(commands, str):
            commands = commands.splitlines()
        # handle a list of multiline command strings
        elif isinstance(commands, list):
            temp = []
            for i in commands:
                temp.extend(i.splitlines())
            commands = temp
    elif isinstance(commands, str) and not split_lines:
        commands = [commands]

    # remove empty lines/commands that can left after rendering
    commands = [c for c in commands if c.strip()]

    # iterate over commands and see if need to add empty line - hit enter
    commands = [
        c.replace(new_line_char, "\n") if new_line_char in c else c for c in commands
    ]

    return commands
