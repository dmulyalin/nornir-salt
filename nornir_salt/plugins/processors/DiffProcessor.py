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
import difflib
import re

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
    :param ignore_lines: (list) list of regular expression pattern to filter lines through,
        if line matches any of the patterns, it is ignored by removing it; by default any
        line that contains only space characters ignored
    :param remove_patterns: (list) list of regular expression pattern to remove from lines
    :param diff_per_task: (bool) default is False, if True runs diff on a per-task basis,
        populating ``Results'`` object ``diff`` attribute with diff results

    ``ignore_lines`` and ``remove_patterns`` arguments exists to clean difference results,
    for instance by ignoring timestamps, counters or other uninteresting data.
    """

    def __init__(
        self,
        diff,
        base_url="/var/nornir-salt/",
        last=1,
        use_deepdiff=False,
        diff_per_task=False,
        ignore_lines=[r"^\s*[\n\r]+$"],
        remove_patterns=[],
    ):
        self.diff = diff
        self.base_url = base_url
        self.last = last
        self.use_deepdiff = use_deepdiff
        self.ignore_lines = ignore_lines
        self.remove_patterns = remove_patterns
        self.diff_per_task = diff_per_task

        self.aliases_file = os.path.join(base_url, "tf_aliases.json")
        self.aliases_data = (
            {}
        )  # dictionary of {diff name: {hostname: [{filename: str, tasks: {task_name: file_span}}]}}

        self._load_aliases()

    def _load_aliases(self):
        # load aliases data from aliases file
        if os.path.exists(self.aliases_file):
            with open(self.aliases_file, mode="r", encoding="utf-8") as f:
                self.aliases_data = json.loads(f.read())

    def _filter_ignore_lines(self, data):
        """
        Helper function to filter lines using regex from ignore_lines list

        :param data: (list) list of lines to filter
        """
        return [
            ln
            for ln in data
            if not any(
                map(lambda pt: True if re.search(pt, ln) else False, self.ignore_lines)
            )
        ]

    def _remove_patterns(self, data):
        """
        Helper function to remove patterns using regex from remove_patterns list

        :param data: (list) list of lines to remove patterns from
        """
        for index, ln in enumerate(data):
            for pattern in self.remove_patterns:
                ln = re.sub(pattern, "", ln)
            data[index] = ln
        return data

    def _run_diff(self, prev_result, new_result, fromfile, tofile):
        """
        Helper function to run diff

        :param prev_result: (str) multiline string to run diff for
        :param new_result: (str) multiline string to run diff for
        :param fromfile: (str) from file name to use with difflib
        :param tofile: (str) to file name to use with difflib
        """
        # filter data through ignore_lines patterns
        if self.ignore_lines:
            prev_result = self._filter_ignore_lines(
                prev_result.splitlines(keepends=True)
            )
            new_result = self._filter_ignore_lines(new_result.splitlines(keepends=True))

        # clean up data using remove_patterns
        if self.remove_patterns:
            prev_result = self._remove_patterns(prev_result)
            new_result = self._remove_patterns(new_result)

        return difflib.unified_diff(
            prev_result, new_result, fromfile=fromfile, tofile=tofile
        )

    def task_started(self, task: Task) -> None:
        pass  # ignore

    def task_instance_started(self, task: Task, host: Host) -> None:
        pass  # ignore

    def task_instance_completed(
        self, task: Task, host: Host, result: MultiResult
    ) -> None:
        """Diff files with current task result"""

        # get previous results data
        index = min(self.last - 1, len(self.aliases_data[self.diff][host.name]) - 1)
        prev_res_alias_data = self.aliases_data[self.diff][host.name][index]
        prev_res_filename = prev_res_alias_data["filename"]

        # decide on results formatter to use
        data_format = "raw"
        if prev_res_filename.endswith("json"):
            data_format = "json"
        elif prev_res_filename.endswith("yaml"):
            data_format = "yaml"
        elif prev_res_filename.endswith("py"):
            data_format = "pprint"

        # open previous results file
        with open(prev_res_filename, mode="r", encoding="utf-8") as f:
            prev_result = f.read()

        # run diff on a per task basis
        if self.diff_per_task:
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
                else:
                    new_result = formatters[data_format](i.result) + "\n"
                    # check if task results exists
                    if not i.name in prev_res_alias_data["tasks"]:
                        i.diff = "'{}' task results not in '{}''".format(
                            i.name, prev_res_filename
                        )
                        continue
                    # run diff using portion of prev_result file with given task results only
                    spans = prev_res_alias_data["tasks"][i.name]
                    difference = self._run_diff(
                        prev_result=prev_result[spans[0] : spans[1]],
                        new_result=new_result,
                        fromfile="old {}".format(prev_res_filename),
                        tofile="new results",
                    )
                    i.diff = "".join(difference)
        # make new task results text and run diff for whole of them
        else:
            new_result = ""
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
                else:
                    new_result += formatters[data_format](i.result) + "\n"

            # run diff
            difference = self._run_diff(
                prev_result,
                new_result,
                fromfile="old {}".format(prev_res_filename),
                tofile="new results",
            )

            # pop other results and add diff results
            while result:
                _ = result.pop()
            result.append(
                Result(
                    host, result="".join(difference), name="{}_diff".format(self.diff)
                )
            )

    def subtask_instance_started(self, task: Task, host: Host) -> None:
        pass  # ignore subtasks

    def subtask_instance_completed(
        self, task: Task, host: Host, result: MultiResult
    ) -> None:
        pass  # ignore subtasks

    def task_completed(self, task: Task, result: AggregatedResult) -> None:
        pass
