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
import traceback
import difflib
import re

from nornir.core.inventory import Host
from nornir.core.task import AggregatedResult, MultiResult, Task


log = logging.getLogger(__name__)


class DiffProcessor:
    """
    DiffProcessor can report difference between current task's results and previously
    saved results.

    :param diff: (str) filegroup name to run diff for
    :param base_url: (str) OS path to folder with files, default "/var/nornir-salt/"
    :param last: (int) default is 1, file index to compare with
    :param ignore_lines: (list) list of regular expression pattern to filter lines through,
        if line matches any of the patterns, it is ignored by removing it; by default any
        line that contains only space characters ignored
    :param remove_patterns: (list) list of regular expression pattern to remove from lines
    :param in_diff: (bool) default is False, if True uses ``Result`` object ``diff`` attribute
        to store diff results, otherwise uses task's ``Result.result`` attribute to store diffs
    :param index: (str) ``ToFileProcessor`` index file name to read files info from

    ``ignore_lines`` and ``remove_patterns`` arguments exists to clean difference results,
    for instance by ignoring timestamps, counters or other uninteresting data.
    """

    def __init__(
        self,
        diff,
        base_url="/var/nornir-salt/",
        last=1,
        in_diff=False,
        ignore_lines=None,
        remove_patterns=None,
        index=None,
    ):
        self.diff = diff
        self.base_url = base_url
        self.last = last
        self.ignore_lines = ignore_lines or [r"^\s*[\n\r]+$"]
        self.remove_patterns = remove_patterns or []
        self.in_diff = in_diff
        self.index = index or "common"

        self.aliases_file = os.path.join(
            base_url, "tf_index_{}.json".format(self.index)
        )
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
        # check if has failed tasks, do nothing in such a case
        if result.failed:
            log.error("nornir_salt:DiffProcessor do nothing, return, has failed tasks")
            return

        try:
            # get previous results data
            index = min(self.last - 1, len(self.aliases_data[self.diff][host.name]) - 1)
            prev_res_alias_data = self.aliases_data[self.diff][host.name][index]
            prev_res_filename = prev_res_alias_data["filename"]

            # open previous results file
            with open(prev_res_filename, mode="r", encoding="utf-8") as f:
                prev_result = f.read()

            # run diff for each task
            for i in result:
                # check if need to skip this task results
                if hasattr(i, "skip_results") and i.skip_results is True:
                    continue

                # check if task results exists
                if i.name not in prev_res_alias_data["tasks"]:
                    i.diff = "'{}' task results not in '{}''".format(
                        i.name, prev_res_filename
                    )
                    continue

                # form new results
                if isinstance(i.result, (str, int, float, bool)):
                    new_result = str(i.result) + "\n"
                # convert structured data to json
                else:
                    new_result = (
                        json.dumps(
                            i.result, sort_keys=True, indent=4, separators=(",", ": ")
                        )
                        + "\n"
                    )

                # run diff using portion of prev_result file with given task results only
                spans = prev_res_alias_data["tasks"][i.name]["span"]
                difference = self._run_diff(
                    prev_result=prev_result[spans[0] : spans[1]],
                    new_result=new_result,
                    fromfile=prev_res_filename,
                    tofile="current",
                )
                diff_res = "".join(difference)
                diff_res = diff_res if diff_res else True
                if self.in_diff:
                    i.diff = diff_res
                else:
                    i.result = diff_res
        except:
            log.error(
                "nornir-salt:DiffProcessor host {} error:\n{}".format(
                    host.name, traceback.format_exc()
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
