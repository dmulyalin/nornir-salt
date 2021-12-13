"""
DumpResults
###########

Function to take data and save it to the file, adding details to
``ToFileProcessor`` and ``files`` task text database index.

``DumpResults`` does not perform any formatting on data supplied,
if it is string, it is saved as is, if it is anything but string
data converted to string using ``str(data)`` prior to saving it.

Primary use case for ``DumpResults`` is mainly related to Salt Stack
restriction on Event Bus maximum data transmission size, as a result in
certain cases need to save full results to local file system instead.

DumpResults sample usage
========================

Code to invoke ``DumpResults`` function ::

    from nornir import InitNornir
    from nornir_salt import TabulateFormatter
    from nornir_netmiko import netmiko_send_command
    from nornir_salt import DumpResults

    nr = InitNornir(config_file="config.yaml")

    result = NornirObj.run(
        task=netmiko_send_command,
        command_string="show clock"
    )

    serialized_output = ResultSerializer(result)
    DumpResults(serialized_output, filegroup="running_config", base_url="./tofile_outputs/")

DumpResults reference
=====================

.. autofunction:: nornir_salt.plugins.functions.DumpResults.DumpResults
"""

import logging
import json
import random
import os
import pprint
import time
import traceback

log = logging.getLogger(__name__)


def _load_index_data(base_url, index):
    """
    Helper function to load json index file and return python dictionary.

    :param base_url: (str) OS path to folder where to save files, default "/var/nornir-salt/"
    :param index: (str) ``ToFileProcessor`` index filename to read files information from
    :return: Dictionary of index data
    """
    index_file = os.path.join(base_url, "tf_index_{}.json".format(index))

    if not os.path.exists(index_file):
        os.makedirs(os.path.dirname(index_file), exist_ok=True)
        with open(index_file, mode="w", encoding="utf-8") as f:
            f.write(json.dumps({}))

    with open(index_file, mode="r", encoding="utf-8") as f:
        index_data = json.loads(f.read())

    return index_data


def _save_index_data(index_data, base_url, index):
    """
    Helper function to save json index file.

    :param index_data: (dict) index data to save
    :param base_url: (str) OS path to folder where to save files, default "/var/nornir-salt/"
    :param index: (str) index filename to save files information into, default is "common"
    :return: Dictionary of index data
    """
    # save new index data
    index_file = os.path.join(base_url, "tf_index_{}.json".format(index))
    with open(index_file, mode="w", encoding="utf-8") as f:
        f.write(
            json.dumps(index_data, sort_keys=True, indent=4, separators=(",", ": "))
        )


def DumpResults(
    results,
    filegroup,
    base_url="/var/nornir-salt/",
    max_files=50,
    index="common",
    proxy_id="untitled",
):
    """
    Function to save results to local file system and update ``ToFileProcessor``
    and ``files`` task text database index.

    :param results: (str, any) data to save
    :param filegroup: (str) ``tf`` file group name of files to save
    :param base_url: (str) OS path to folder where to save files, default "/var/nornir-salt/"
    :param index: (str) index name to read files index data from
    :param proxy_id: (str) filename identifier, usually equal to Proxy Minion ID
    :param max_files: (int) maximum number of files to save, older files deleted once limit reached
    :return: None

    Filename to save results formed using this formatter::

        /{base_url}/{filegroup}__{timestamp}__{rand}__{proxy_id}.txt

    Where:

    * ``base_url`` - OS path to folder where to save files
    * ``filegroup`` - ``tf`` file group name of files
    * ``timestamp`` - formed using "%d_%B_%Y_%H_%M_%S" time.strftime formatter
    * ``rand`` - random integer from 0-1000 range
    * ``proxy_id`` - Name of Proxy Minion ID
    """
    index_data = _load_index_data(base_url, index)

    # form filename
    dump_filename = "{filegroup}__{timestamp}__{rand}__{proxy_id}.txt".format(
        timestamp=time.strftime("%d_%B_%Y_%H_%M_%S"),
        rand=random.randint(0, 1000),  # nosec
        proxy_id=proxy_id,
        filegroup=filegroup,
    )
    dump_filename = os.path.join(base_url, dump_filename)

    # update index data
    index_data.setdefault(filegroup, {})
    index_data[filegroup].setdefault(proxy_id, [])

    # save data to file and populate alias details for tasks
    os.makedirs(os.path.dirname(dump_filename), exist_ok=True)
    with open(dump_filename, mode="w", encoding="utf-8") as f:
        index_data[filegroup][proxy_id].insert(
            0,
            {
                "filename": dump_filename,
                "tasks": {"full_results": {}},
                "timestamp": time.strftime("%d %b %Y %H:%M:%S %Z"),
                "content_type": "pprint",
            },
        )

        # save results to file
        if isinstance(results, str):
            result_to_save = results
        else:
            result_to_save = pprint.pformat(results, indent=2, width=150)
        f.write(result_to_save + "\n")

        # update index data with span
        span = (0, len(result_to_save) + 1)
        index_data[filegroup][proxy_id][0]["tasks"]["full_results"]["span"] = span

    # check if need to delete old files
    if len(index_data[filegroup][proxy_id]) > max_files:
        file_to_rm = index_data[filegroup][proxy_id].pop(-1)
        try:
            os.remove(file_to_rm["filename"])
        except:
            log.error(
                "nornir-salt:DumpResults failed to remove file '{}':\n{}".format(
                    file_to_rm, traceback.format_exc()
                )
            )

    _save_index_data(index_data, base_url, index)
