"""
ToFileProcessor Plugin
######################

Processor plugin to save task execution results to file.

ToFileProcessor Sample Usage
============================

Code to demonstrate how to use ``ToFileProcessor`` plugin::

    from nornir import InitNornir
    from nornir_netmiko import netmiko_send_command
    from nornir_salt import ToFileProcessor

    nr = InitNornir(config_file="config.yaml")

    nr_with_processor = nr.with_processors([
        ToFileProcessor(tf="config", base_url="./Output/")
    ])

    nr_with_processor.run(
        task=netmiko_send_command,
        command_string="show run"
    )

ToFileProcessor reference
=========================

.. autofunction:: nornir_salt.plugins.processors.ToFileProcessor.ToFileProcessor
"""
import logging
import time
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
formatters = {"raw": _to_raw, "json": _to_json, "pprint": _to_pprint, "yaml": _to_yaml}


def _write(f, data, tf_format):
    """
    Helper function mainly to re-use code
    """
    try:
        f.write(formatters[tf_format](data) + "\n")
    except KeyError:
        log.error(
            "ToFile, unsupported format '{}'; supported '{}'".format(
                tf_format, list(formatters.keys())
            )
        )


class ToFileProcessor:
    """
    ToFileProcessor can save task execution results to file on a per host basis.
    If multiple tasks present, results of all of them saved in same file.

    :param tf: (str) alias name of the file content
    :param tf_format: (str) formatter name to use on results before saving them
    :param base_url: (str) OS path to folder where to save files, default "/var/nornir-salt/"
    :param max_files: (int) default is 5, maximum number of file for given ``tf`` alias

    Supported ``tf_format`` values:

    * ``raw`` - (default) converts data to string appending newline to the end
    * ``pprint`` - uses ``pprint.pformat`` function to format data to string
    * ``json`` - formats data to JSON format
    * ``yaml`` - formats data to YAML format

    Files saved under ``base_url`` location, where individual filename formed using
    string::

        {tf}__{timestamp}__{hostname}.{ext}

    Where:

    * timestamp - ``%d_%B_%Y_%H_%M_%S`` time formatted string, e.g. "12_June_2021_21_48_11"
    * hostname - ``name`` attribute of host
    * tf - value of ``tf`` attribute
    * ext - file extension, json, yaml or txt depending on ``tf_format``

    In addition, ``tf_aliases.json`` file created under ``base_url`` to track files created
    using dictionary structure of ``{tf: {hostname: [{filename: str, tasks: {task_name:
    file_span}}]}}``. ``tf_aliases.json`` used by ``DiffProcessor`` to retrieve previous results
    for the task.
    """

    def __init__(self, tf, tf_format="raw", base_url="/var/nornir-salt/", max_files=5):
        self.tf = tf
        self.tf_format = tf_format
        self.base_url = base_url
        self.max_files = max(1, max_files)

        self.timestamp = time.strftime("%d_%B_%Y_%H_%M_%S")
        self.aliases_file = os.path.join(base_url, "tf_aliases.json")
        self.aliases_data = (
            {}
        )  # dictionary of {tf name: {hostname: [{filename: str, tasks: {task_name: file_span}}]}}

        self._load_aliases()

    def _load_aliases(self):
        # create aliases file if does not exist
        if not os.path.exists(self.aliases_file):
            os.makedirs(os.path.dirname(self.aliases_file), exist_ok=True)
            with open(self.aliases_file, mode="w", encoding="utf-8") as f:
                f.write(json.dumps({}))

        # load aliases data
        with open(self.aliases_file, mode="r", encoding="utf-8") as f:
            self.aliases_data = json.loads(f.read())

    def _dump_aliases(self):
        # save aliases data
        with open(self.aliases_file, mode="w", encoding="utf-8") as f:
            _write(f, self.aliases_data, "json")

    def task_started(self, task: Task) -> None:
        pass  # ignore

    def task_instance_started(self, task: Task, host: Host) -> None:
        pass  # ignore

    def task_instance_completed(
        self, task: Task, host: Host, result: MultiResult
    ) -> None:
        """save to file on a per-host basis"""

        # form file name
        if self.tf_format == "json":
            ext = "json"
        elif self.tf_format == "yaml":
            ext = "yaml"
        elif self.tf_format == "pprint":
            ext = "py"
        else:
            ext = "txt"

        host_filename = "{tf}__{timestamp}__{hostname}.{ext}".format(
            timestamp=self.timestamp, hostname=host.name, tf=self.tf, ext=ext
        )
        host_filename = os.path.join(self.base_url, host_filename)

        # add aliases data
        self.aliases_data.setdefault(self.tf, {})
        self.aliases_data[self.tf].setdefault(host.name, [])

        # save data to file and populate alias details for tasks
        os.makedirs(os.path.dirname(host_filename), exist_ok=True)
        with open(host_filename, mode="w", encoding="utf-8") as f:
            self.aliases_data[self.tf][host.name].insert(
                0, {"filename": host_filename, "tasks": {}}
            )
            span_start = 0

            for i in result:
                # check if need to skip this task results
                exception = (
                    str(i.exception)
                    if i.exception != None
                    else i.host.get("exception", None)
                )
                if (
                    hasattr(i, "skip_results")
                    and i.skip_results is True
                    and not exception
                ):
                    continue
                # save results to file
                _write(f, i.result, self.tf_format)
                # add aliases data
                span = (span_start, span_start + len(str(i.result)) + 1)
                self.aliases_data[self.tf][host.name][0]["tasks"][i.name] = span
                span_start += len(str(i.result)) + 1  # _write appends \n hence +1

        # check if need to delete old files
        if len(self.aliases_data[self.tf][host.name]) > self.max_files:
            file_to_rm = self.aliases_data[self.tf][host.name].pop()
            try:
                os.remove(file_to_rm["filename"])
            except:
                log.error(
                    "nornir-salt:ToFileProcessor failed to remove file '{}':\n{}".format(
                        file_to_rm, traceback.format_exc()
                    )
                )

    def subtask_instance_started(self, task: Task, host: Host) -> None:
        pass  # ignore subtasks

    def subtask_instance_completed(
        self, task: Task, host: Host, result: MultiResult
    ) -> None:
        pass  # ignore subtasks

    def task_completed(self, task: Task, result: AggregatedResult) -> None:
        self._dump_aliases()
