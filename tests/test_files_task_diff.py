"""
For some reason tests test_file_diff_certain_task_name and
test_file_diff_whole_result_non_exist_filegroup if run from
test_files_task_plugins.py file, produce error with due to
output folder contains no files. If move these two tests in
separate file all works fine. ALso running tests individually
also works fine even if theu are part of test_files_task_plugins.py
file.
"""

import sys
import os
import pprint
import logging
import yaml
import pytest
import time
import json

sys.path.insert(0, "..")

try:
    from nornir import InitNornir
    from nornir.core.plugins.inventory import InventoryPluginRegister
    from nornir.core.task import Result

    HAS_NORNIR = True
except ImportError:
    HAS_NORNIR = False

from nornir_salt.plugins.functions import ResultSerializer
from nornir_salt.plugins.inventory import DictInventory
from nornir_salt.plugins.tasks import nr_test
from nornir_salt.plugins.processors import ToFileProcessor
from nornir_salt.plugins.processors import DataProcessor
from nornir_salt.plugins.tasks import file_read, file_remove, file_list, file_diff, files

logging.basicConfig(level=logging.ERROR)


# ----------------------------------------------------------------------
# Initialize Nornir
# ----------------------------------------------------------------------


skip_if_no_nornir = pytest.mark.skipif(
    HAS_NORNIR == False,
    reason="Failed to import all required Nornir modules and plugins",
)
skip_if_no_lab = None

lab_inventory = """
hosts:
  IOL1:
    hostname: 192.168.217.10
    platform: ios
    groups: [lab]
  IOL2:
    hostname: 192.168.217.7
    platform: ios
    groups: [lab]

groups:
  lab:
    username: cisco
    password: cisco

defaults: {}
"""
lab_inventory_dict = yaml.safe_load(lab_inventory)


def init(opts):
    """
    Initiate nornir by calling InitNornir()
    """
    global skip_if_no_lab

    nr = InitNornir(
        logging={"enabled": False},
        runner={"plugin": "serial"},
        inventory={
            "plugin": "DictInventory",
            "options": {
                "hosts": opts["hosts"],
                "groups": opts.get("groups", {}),
                "defaults": opts.get("defaults", {}),
            },
        },
    )

    return nr


InventoryPluginRegister.register("DictInventory", DictInventory)

nr = init(lab_inventory_dict)


def clean_up_folder():
    # remove previous files and folder
    if os.path.exists("./tofile_outputs/"):
        for filen in os.listdir("./tofile_outputs/"):
            os.remove("./tofile_outputs/" + filen)
        os.rmdir("./tofile_outputs/")

def nr_test_grouped_subtasks(task, task_1, task_2):
    """
    Test grouped task
    """
    task.run(**task_1)
    task.run(**task_2)
    return Result(host=task.host, skip_results=True)

def generate_files(tf):
    """
    Helper function to generate files by running task
    """
    iol1_res_ntp = [
{"ntp": "1.1.1.1"},
    ]
    iol2_res_ntp = [
{"ntp": "2.2.2.2"},
    ]
    iol1_res_log = [
{"log": "3.3.3.3"},
    ]
    iol2_res_log = [
{"log": "4.4.4.4"},
    ]

    # run test to generate the file
    nr_with_tf = nr.with_processors(
        [ToFileProcessor(tf=tf, base_url="./tofile_outputs/")]
    )

    # first task run
    nr_with_tf.run(
        task=nr_test_grouped_subtasks,
        task_1={
            "task": nr_test,
            "ret_data_per_host": {
                "IOL1": iol1_res_ntp,
                "IOL2": iol2_res_ntp,
            },
            "name": "show run | inc ntp",
        },
        task_2={
            "task": nr_test,
            "ret_data_per_host": {
                "IOL1": iol1_res_log,
                "IOL2": iol2_res_log,
            },
            "name": "show run | inc logging",
        },
    )

# ----------------------------------------------------------------------
# tests that need Nornir
# ----------------------------------------------------------------------


@skip_if_no_nornir
def test_file_diff_certain_task_name():
    clean_up_folder()

    # generate text files
    iol1_res_old_ntp = """
ntp server 7.7.7.8
ntp server 7.7.7.7
        """
    iol1_res_new_ntp = """
ntp server 7.7.6.8
ntp server 7.7.7.7
ntp server 1.1.1.1
        """
    iol2_res_old_ntp = """
ntp server 7.7.7.7
        """
    iol2_res_new_ntp = """
ntp server 7.7.7.9
        """
    nr_with_tf1 = nr.with_processors(
        [ToFileProcessor(tf="device_config", base_url="./tofile_outputs/")]
    )

    # first task run
    _ = nr_with_tf1.run(
        task=nr_test_grouped_subtasks,
        task_1={
            "task": nr_test,
            "ret_data_per_host": {
                "IOL1": iol1_res_old_ntp,
                "IOL2": iol2_res_old_ntp,
            },
            "name": "show run | inc ntp",
        },
        task_2={
            "task": nr_test,
            "ret_data_per_host": {
                "IOL1": "old logging results",
                "IOL2": "old logging results",
            },
            "name": "show run | inc logging",
        },
    )

    # second task run
    _ = nr_with_tf1.run(
        task=nr_test_grouped_subtasks,
        task_1={
            "task": nr_test,
            "ret_data_per_host": {
                "IOL1": iol1_res_new_ntp,
                "IOL2": iol2_res_new_ntp,
            },
            "name": "show run | inc ntp",
        },
        task_2={
            "task": nr_test,
            "ret_data_per_host": {
                "IOL1": "new logging results",
                "IOL2": "new logging results",
            },
            "name": "show run | inc logging",
        },
    )

    # run task to diff
    output = nr.run(
        task=file_diff,
        base_url="./tofile_outputs/",
        filegroup="device_config",
        task_name="show run | inc ntp"
    )

    res_task_diff = ResultSerializer(output, add_details=True)

    pprint.pprint(res_task_diff, width=150)

    assert """-ntp server 7.7.7.8
+ntp server 7.7.6.8
 ntp server 7.7.7.7
+ntp server 1.1.1.1""" in res_task_diff["IOL1"]["device_config"]["result"]
    assert res_task_diff["IOL1"]["device_config"]["result"].count("device_config") == 2

    assert """-ntp server 7.7.7.7
+ntp server 7.7.7.9""" in res_task_diff["IOL2"]["device_config"]["result"]
    assert res_task_diff["IOL2"]["device_config"]["result"].count("device_config") == 2

# test_file_diff_certain_task_name()

@skip_if_no_nornir
def test_file_diff_whole_result_non_exist_filegroup():
    clean_up_folder()

    # generate text files
    iol1_res_old = """
ntp server 7.7.7.8
ntp server 7.7.7.7
        """
    iol1_res_new = """
ntp server 7.7.6.8
ntp server 7.7.7.7
ntp server 1.1.1.1
        """
    iol2_res_old = """
ntp server 7.7.7.7
        """
    iol2_res_new = """
ntp server 7.7.7.9
        """

    # run test to generate the file
    nr_with_tf = nr.with_processors(
        [ToFileProcessor(tf="ntp_config", base_url="./tofile_outputs/")]
    )
    _ = nr_with_tf.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": iol1_res_old,
            "IOL2": iol2_res_old,
        },
        name="show run | inc ntp",
    )
    _ = nr_with_tf.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": iol1_res_new,
            "IOL2": iol2_res_new,
        },
        name="show run | inc ntp",
    )

    # run task to diff
    output = nr.run(
        task=file_diff,
        base_url="./tofile_outputs/",
        filegroup="non_existing",
    )
    res = ResultSerializer(output, add_details=True)

    # pprint.pprint(res, width=150)

    assert res["IOL1"]["non_existing"]["failed"] == True
    assert "non_existing files not found" in res["IOL1"]["non_existing"]["exception"]
    assert res["IOL2"]["non_existing"]["failed"] == True
    assert "non_existing files not found" in res["IOL2"]["non_existing"]["exception"]

# test_file_diff_whole_result_non_exist_filegroup()
