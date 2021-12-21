"""
files
#####

Collection of task plugins to work with files saved by ``TofileProcessor``.

Files Plugin Sample usage
=========================

Code to invoke ``files`` task plugins::

    from nornir import InitNornir

    from nornir_salt.plugins.processors.ToFileProcessor import ToFileProcessor
    from nornir_salt.plugins.tasks import file_read, file_remove, file_list, file_diff, files
    from nornir_netmiko import netmiko_send_command

    nr = InitNornir(config_file="config.yaml")

    # save results to files
    nr_with_tf = nr.with_processors(
        [ToFileProcessor(tf="config_for_read", base_url="./tofile_outputs/")]
    )
    nr_with_tf.run(
        task=netmiko_send_command,
        command_string="show run"
    )

    # retrieve saved files content on demand
    res = nr.run(
        task=file_read,
        filegroup="config_for_read",
        base_url="./tofile_outputs/",
    )

Files Plugin API reference
==========================

file_read
+++++++++
.. autofunction:: nornir_salt.plugins.tasks.files.file_read

file_list
+++++++++
.. autofunction:: nornir_salt.plugins.tasks.files.file_list

file_remove
+++++++++++
.. autofunction:: nornir_salt.plugins.tasks.files.file_remove

file_diff
+++++++++
.. autofunction:: nornir_salt.plugins.tasks.files.file_diff

files dispatcher function
+++++++++++++++++++++++++
.. autofunction:: nornir_salt.plugins.tasks.files.files
"""
import os
import json
import difflib
import logging

from nornir.core.task import Result

log = logging.getLogger(__name__)


def _read_content(
    task, task_name: str, task_details: dict, data: str, timestamp: str, group: str
) -> None:
    """
    Helper function to re-use code. Gets subset of task results from
    overall data and adds it to task.results

    :param task: (obj) Nornir task object
    :param task_name: (str) Name of the task to process
    :param task_details: (dict) details of task from ToFileProcessor index file
    :param data: (str) content of file with previous results
    :param group: (str) ``tf`` files group name
    :returns: None
    """
    start, end = task_details["span"]
    # "end - 1" to account for ToFileProcessor adds "+\n" to the end
    content = data[start : end - 1]
    if task_details["content_type"] == "json":
        content = json.loads(content)
    task.results.append(
        Result(
            host=task.host,
            result=content,
            name=task_name,
            timestamp=timestamp,
            filegroup=group,
        )
    )


def _load_index_data(base_url, index):
    """
    Helper function to load json index file and return python dictionary.

    :param base_url: (str) OS path to folder where to save files, default "/var/nornir-salt/"
    :param index: (str) ``ToFileProcessor`` index filename to read files information from
    :return: Dictionary of index data
    """
    index_file = os.path.join(base_url, "tf_index_{}.json".format(index))
    with open(index_file, mode="r", encoding="utf-8") as f:
        index_data = json.loads(f.read())
    return index_data


def file_read(
    task,
    filegroup,
    base_url: str = "/var/nornir-salt/",
    task_name: str = None,
    last: int = 1,
    index: str = "common",
    **kwargs
):
    """
    Function to read text files content saved by ``ToFileProcessor``.

    This task reconstructs previously saved results and returns Nornir
    Result objects.

    :param filegroup: (str or list) ``tf`` group or list of ``tf`` file group names of files to load
    :param base_url: (str) OS path to folder with saved files, default "/var/nornir-salt/"
    :param last: (int) what file to read, default is 1 - the most current one
    :param task_name: (str) name of task to read previous results for, returns all results
        if ``task_name`` is empty.
    :param index: (str) ``ToFileProcessor`` index filename to read files information from
    :return: Result object with file read content
    """
    # run sanity checks
    if not filegroup:
        raise RuntimeError("nornir-salt:file_read bad filegroup '{}'".format(filegroup))

    # load index data
    index_data = _load_index_data(base_url, index)

    filegrous = [filegroup] if isinstance(filegroup, str) else filegroup

    for group in filegrous:
        # do sanity check
        if group not in index_data:
            task.results.append(
                Result(
                    host=task.host,
                    result=None,
                    exception="nornir-salt:file_read '{}' files not found".format(
                        group
                    ),
                )
            )
            continue
        if task.host.name not in index_data[group]:
            task.results.append(
                Result(
                    host=task.host,
                    result=None,
                    filegroup=group,
                    exception="nornir-salt:file_read '{}' host, '{}' files not found".format(
                        task.host.name, group
                    ),
                )
            )
            continue

        # get previous results metadata
        res_index = min(last - 1, len(index_data[group][task.host.name]) - 1)
        prev_res_details = index_data[group][task.host.name][res_index]
        timestamp = prev_res_details["timestamp"]

        # load file content
        with open(prev_res_details["filename"], mode="r", encoding="utf-8") as f:
            data = f.read()

        # check if need to load results for certain task only
        if task_name:
            task_details = prev_res_details["tasks"][task_name]
            _read_content(task, task_name, task_details, data, timestamp, group)
        # load content of all tasks reconstructing them in Nornir result objects
        else:
            for _task_name, task_details in prev_res_details["tasks"].items():
                _read_content(task, _task_name, task_details, data, timestamp, group)

    return Result(host=task.host, skip_results=True)


def file_list(
    task,
    filegroup=None,
    base_url: str = "/var/nornir-salt/",
    index: str = "common",
    **kwargs
):
    """
    Function to produce a list of text files saved by ``ToFileProcessor``

    :param filegroup: (str or list) ``tf`` group or list of ``tf`` file group names of files to list
    :param base_url: (str) OS path to folder where to save files, default "/var/nornir-salt/"
    :param index: (str) ``ToFileProcessor`` index filename to read files information from
    :return: Nornir Result object with files list
    """
    filegroup = filegroup or []
    ret = []

    # load index data
    index_data = _load_index_data(base_url, index)

    if filegroup:
        filegroups = [filegroup] if isinstance(filegroup, str) else filegroup
    else:
        filegroups = list(index_data.keys())

    for group in filegroups:
        # do sanity check
        if group not in index_data:
            task.results.append(
                Result(
                    host=task.host,
                    result=None,
                    exception="nornir-salt:file_list '{}' files group not found".format(
                        group
                    ),
                )
            )
            continue

        # iterate over previous results
        for index, file_details in enumerate(index_data[group].get(task.host.name, [])):
            tasks = file_details.pop("tasks")
            ret.append(
                {
                    "host": task.host.name,
                    "filegroup": group,
                    "last": index + 1,
                    "tasks": "\n".join(list(tasks.keys())),
                    **file_details,
                }
            )

    return Result(host=task.host, result=ret)


def file_remove(
    task,
    filegroup,
    base_url: str = "/var/nornir-salt/",
    index: str = "common",
    **kwargs
):
    """
    Function to remove files saved by ``ToFileProcessor``

    :param filegroup: (str or list or bool) ``tf`` or list of ``tf`` file group names of files
        to remove. If set to True will remove all files
    :param base_url: (str) OS path to folder with saved files, default "/var/nornir-salt/"
    :param index: (str) ``ToFileProcessor`` index filename to read files information from
    :return: Result object with removed files summary
    """
    ret = []

    # load index data
    index_data = _load_index_data(base_url, index)

    # check if need to remove files for all filegroups
    if filegroup is True:
        filegroups = list(index_data.keys())
    else:
        filegroups = filegroup if isinstance(filegroup, list) else [filegroup]

    for group in filegroups:
        # do sanity check
        if group not in index_data:
            task.results.append(
                Result(
                    host=task.host,
                    result=None,
                    exception="nornir-salt:file_remove '{}' files group not found".format(
                        group
                    ),
                )
            )
            continue

        # iterate over previous results
        for file_details in index_data[group].get(task.host.name, []):
            filename = file_details["filename"]
            tasks = file_details.pop("tasks")
            if os.path.exists(filename):
                os.remove(filename)
                ret.append(
                    {
                        "host": task.host.name,
                        "filegroup": group,
                        "tasks": "\n".join(list(tasks.keys())),
                        **file_details,
                    }
                )

        # clean up index data
        _ = index_data[group].pop(task.host.name, None)

    # save new index data
    index_file = os.path.join(base_url, "tf_index_{}.json".format(index))
    with open(index_file, mode="w", encoding="utf-8") as f:
        f.write(
            json.dumps(index_data, sort_keys=True, indent=4, separators=(",", ": "))
        )

    return Result(host=task.host, result=ret)


def file_diff(
    task,
    filegroup,
    base_url: str = "/var/nornir-salt/",
    task_name: str = None,
    last=None,
    index: str = "common",
    **kwargs
):
    """
    Function to read text files content saved by ``ToFileProcessor`` and
    return difference.

    :param filegroup: (str or list) ``tf`` file group name of files to use for diff, if list,
        runs difference for each filegroup
    :param base_url: (str) OS path to folder with saved files, default "/var/nornir-salt/"
    :param last: (int or list or str) files to diff, default is - [1, 2] - last 1 and last 2
    :param task_name: (str) name of task to read previous results for, diffs all results
        if ``task_name`` is empty.
    :param index: (str) ``ToFileProcessor`` index filename to read files information from
    :return: Result object with files difference, if files are identical reslt is True
    """
    last = last or [1, 2]

    # load index data
    index_data = _load_index_data(base_url, index)

    # get indexes of files to diff
    if isinstance(last, int):
        new = 1
        old = last
    elif isinstance(last, list) and len(last) == 2:
        new, old = last
    elif isinstance(last, str) and "," in last:
        new, old = [int(i.strip()) for i in last.split(",")][:2]
    else:
        raise TypeError(
            "nornir_data:files:diff last is not list or int or string but {}, last: {}".format(
                type(last), last
            )
        )

    filegroups = filegroup if isinstance(filegroup, list) else [filegroup]

    # iterate over filegroups and produce diffs
    for group in filegroups:
        # run sanity checks
        if group not in index_data:
            task.results.append(
                Result(
                    host=task.host,
                    result=None,
                    exception="nornir-salt:files:diff {} files not found".format(group),
                    name=group,
                )
            )
            continue
        if task.host.name not in index_data[group]:
            task.results.append(
                Result(
                    host=task.host,
                    result=None,
                    exception="nornir-salt:files:diff {} host, {} files not found".format(
                        task.host.name, group
                    ),
                    name=group,
                )
            )
            continue
        # get previous results metadata
        new_res_index = min(new - 1, len(index_data[group][task.host.name]) - 1)
        old_res_index = min(old - 1, len(index_data[group][task.host.name]) - 1)

        # check if new and old reference same file
        if new_res_index == old_res_index:
            task.results.append(
                Result(
                    host=task.host,
                    result=None,
                    exception="nornir-salt:files:diff new and old files are same - last {}, last {}".format(
                        new_res_index + 1, old_res_index + 1
                    ),
                    name=group,
                )
            )
            continue

        new_res_details = index_data[group][task.host.name][new_res_index]
        old_res_details = index_data[group][task.host.name][old_res_index]

        # load files content
        with open(new_res_details["filename"], mode="r", encoding="utf-8") as f:
            new_res_data = f.read()
        with open(old_res_details["filename"], mode="r", encoding="utf-8") as f:
            old_res_data = f.read()

        # if task_name given, retrieve task results content
        if task_name:
            # get task details
            new_task_details = new_res_details["tasks"][task_name]
            old_task_details = old_res_details["tasks"][task_name]
            # get task span
            new_start, new_end = new_task_details["span"]
            old_start, old_end = old_task_details["span"]
            # get task text results to diff
            new_todiff_data = new_res_data[new_start : new_end - 1]
            old_todiff_data = old_res_data[old_start : old_end - 1]
        # use all data for diff
        else:
            new_todiff_data = new_res_data
            old_todiff_data = old_res_data

        # run diff
        difference = difflib.unified_diff(
            a=old_todiff_data.splitlines(keepends=True),
            b=new_todiff_data.splitlines(keepends=True),
            fromfile=old_res_details["filename"],
            tofile=new_res_details["filename"],
        )

        res = "".join(difference)
        res = res if res else True
        task.results.append(Result(host=task.host, result=res, name=group))

    return Result(host=task.host, skip_results=True)


def files(task, call, *args, **kwargs):
    """
    Dispatcher function to call one of the functions.

    :param call: (str) nickname of function to call
    :param arg: (list) function arguments
    :param kwargs: (dict) function key-word arguments
    :return: function execution results

    Call function nicknames:

    * ``ls`` - calls `file_list`_
    * ``rm`` - calls `file_remove`_
    * ``read`` - calls `file_read`_
    * ``diff`` - calls `file_diff`_
    """
    dispatcher = {
        "ls": file_list,
        "rm": file_remove,
        "read": file_read,
        "diff": file_diff,
    }
    return dispatcher[call](task, *args, **kwargs)
