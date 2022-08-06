import logging

from nornir.core.task import Task

log = logging.getLogger(__name__)


def cfg_form_commands(task: Task, config: list = None, multiline: bool = False):
    """
    Helper function to form a list of configuration commands to send to device.

    Used by:

    - netmiko_send_config with multiline=False
    - scrapli_send_config with multiline=True
    - napalm_configure with multiline=True
    - pyats_send_config with multiline=False

    Supports:

    - extracting commands from host's __task__ data
    - splitting multiline config string to a list of commands
    - replaces escaped newline - \\n - with newline - \n 

    :param task: (obj) Nornir Task object
    :param config: (str or list) configuration string or list of commands to send to device
    :param multiline: (bool) if True, returns multiline string
    :return: list of configuration commands if multiline is False, multiline string otherwise
    """
    config = config or []

    # get configuration from host data if any
    if "config" in task.host.data.get("__task__", {}):
        config = task.host.data["__task__"]["config"]
    elif "commands" in task.host.data.get("__task__", {}):
        config = task.host.data["__task__"]["commands"]
    elif "filename" in task.host.data.get("__task__", {}):
        config = task.host.data["__task__"]["filename"]

    # check f need to return multiline string
    if multiline and isinstance(config, (list, tuple)):
        config = "\n".join(config)
    # leave string as is if multiline requested
    elif multiline and isinstance(config, str):
        config = config
    # transform config to a list of commands if string given
    elif isinstance(config, str):
        config = config.splitlines()
                
    # make sure to handle \\n in config
    if isinstance(config, list):
        cfg = []
        for cfg_line in config:
            if "\\n" in cfg_line:
                cfg.extend(cfg_line.split("\\n"))
            else:
                cfg.append(cfg_line)     
        config = cfg
    elif isinstance(config, str) and "\\n" in  config:
        config = config.replace("\\n", "\n")
        
    return config
