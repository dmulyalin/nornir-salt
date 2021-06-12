"""
DiffProcessor Plugin
####################

Processor plugin to run diff against previous task's results saved
using ``ToFileProcessor``.

DiffProcessor Sample Usage
==========================

Code to demonstrate how to use ``DiffProcessor`` plugin::

    from nornir import InitNornir
    from nornir_netmiko import netmiko_send_command
    from nornir_salt import DiffProcessor

    nr = InitNornir(config_file="config.yaml")

    nr_with_processor = nr.with_processors([
        DiffProcessor(diff="config")
    ])

    nr_with_processor.run(
        task=netmiko_send_command,
        command_string="show run"
    )

DiffProcessor reference
=========================

.. autofunction:: nornir_salt.plugins.processors.DiffProcessor.DiffProcessor
"""
import logging
import os
import json
import pprint
import traceback

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

from nornir.core.inventory import Host
from nornir.core.task import AggregatedResult, MultiResult, Result, Task


log = logging.getLogger(__name__)

# --------------------------------------------------------------------------------
# formatters helper functions
# --------------------------------------------------------------------------------


def _to_json(data):
    return json.dumps(data, sort_keys=True, indent=4, separators=(",", ": "))

def _to_pprint(data):
    return pprint.pformat(data, indent=4)

def _to_yaml(data):
    if HAS_YAML:
        return yaml.dump(data, default_flow_style=False)
    else:
        return _to_pprint(data)

def _to_raw(data):
    return str(data)

# formats dispatcher dictionary
formatters = {
    "raw": _to_raw,
    "json": _to_json,
    "pprint": _to_pprint,
    "yaml": _to_yaml
}


def _format(f, data, tf_format):
    """
    Helper function mainly to re-use code
    """
    ret = ""
    try:
        ret += formatters[tf_format](data)  + "\n"
    except KeyError:
        log.error("Diff, unsupported format '{}'; supported '{}'".format(
                tf_format, list(formatters.keys())
            )
        )
    return ret


class DiffProcessor:
    """
    DiffProcessor can report difference between current task's results and previously
    saved results.

    :param diff: (str) alias name of the file content
    :param base_url: (str) OS path to folder with files, default "/var/nornir-salt/"
    :param last: (int) default is 1, file index to compare with
    :param use_deepdiff: (bool or dict) default is False, if True will use ``deepdiff``
        library to form difference between structured data, if ``use_deepdiff`` is a 
        dictionary, will pass it on to deepdiff method.
    """

    def __init__(
        self,
        diff,
        base_url="/var/nornir-salt/",
        last=1,
        use_deepdiff=False
    ):
        self.diff = diff
        self.base_url = base_url
        self.last = last
        self.use_deepdiff = use_deepdiff

        self.aliases_file = os.path.join(base_url, "tf_aliases.json")
        self.aliases_data = {} # dictionary of {diff: {hostname: [filenames]}}

        self._load_aliases()

    def _load_aliases(self):
        # load aliases data from aliases file 
        if os.path.exists(self.aliases_file):
            with open(self.aliases_file, mode="r", encoding="utf-8") as f:
                self.aliases_data = json.loads(f.read())            

    def task_started(self, task: Task) -> None:
        pass # ignore

    def task_instance_started(self, task: Task, host: Host) -> None:
        pass # ignore

    def task_instance_completed(self, task: Task, host: Host, result: MultiResult) -> None:
        """ Diff files with current task result """
        pass

    def subtask_instance_started(self, task: Task, host: Host) -> None:
        pass # ignore subtasks

    def subtask_instance_completed(self, task: Task, host: Host, result: MultiResult) -> None:
        pass # ignore subtasks

    def task_completed(self, task: Task, result: AggregatedResult) -> None:
        pass