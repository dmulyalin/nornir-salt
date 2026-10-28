import json
import logging
import os
import pprint
import sys
import time

import pytest
import yaml

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
from nornir_salt.plugins.processors import ToFileProcessor
from nornir_salt.plugins.tasks import nr_test

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
  iol-r1:
    hostname: containerlab.lab
    platform: ios
    port: 2206
    groups: [lab]
  csr1k-r1:
    hostname: containerlab.lab
    platform: ios
    port: 2207
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


# ----------------------------------------------------------------------
# tests that need Nornir
# ----------------------------------------------------------------------


@skip_if_no_nornir
def test_to_file():
    clean_up_folder()

    # run test
    nr_with_tf = nr.with_processors(
        [ToFileProcessor(tf="config", base_url="./tofile_outputs/")]
    )
    output = nr_with_tf.run(
        task=nr_test,
        ret_data_per_host={
            "iol-r1": """
ntp server 7.7.7.8
ntp server 7.7.7.7
        """,
            "csr1k-r1": """
ntp server 7.7.7.7
        """,
        },
        name="show run | inc ntp",
    )
    files = os.listdir("./tofile_outputs/")
    assert "tf_index_common.json" in files, "tf_index_common.json not found"
    for file in files:
        if "tf_index_common.json" in file:
            continue
        assert "config__" in file and ("__iol-r1.txt" in file or "__csr1k-r1.txt" in file)


# test_to_file()


@skip_if_no_nornir
def test_to_file_max_files(tmp_path):
    # run test
    nr_with_tf = nr.with_processors(
        [ToFileProcessor(tf="config", base_url=str(tmp_path), max_files=2)]
    )
    output = nr_with_tf.run(
        task=nr_test,
        ret_data_per_host={
            "iol-r1": """
ntp server 7.7.7.8
ntp server 7.7.7.7
        """,
            "csr1k-r1": """
ntp server 7.7.7.7
        """,
        },
        name="show run | inc ntp",
    )
    time.sleep(1)
    nr_with_tf = nr.with_processors(
        [ToFileProcessor(tf="config", base_url=str(tmp_path), max_files=2)]
    )
    output = nr_with_tf.run(
        task=nr_test,
        ret_data_per_host={
            "iol-r1": """
ntp server 7.7.7.8
ntp server 7.7.7.7
        """,
            "csr1k-r1": """
ntp server 7.7.7.7
        """,
        },
        name="show run | inc ntp",
    )
    time.sleep(1)
    nr_with_tf = nr.with_processors(
        [ToFileProcessor(tf="config", base_url=str(tmp_path), max_files=2)]
    )
    output = nr_with_tf.run(
        task=nr_test,
        ret_data_per_host={
            "iol-r1": """
ntp server 7.7.7.8
ntp server 7.7.7.7
        """,
            "csr1k-r1": """
ntp server 7.7.7.7
        """,
        },
        name="show run | inc ntp",
    )
    files = os.listdir(tmp_path)

    assert "tf_index_common.json" in files, "tf_index_common.json not found"
    assert len(files) == 5, "above max_files found in directory"
    index = json.loads((tmp_path / "tf_index_common.json").read_text())
    assert {host: len(entries) for host, entries in index["config"].items()} == {
        "iol-r1": 2,
        "csr1k-r1": 2,
    }


# test_to_file_max_files()


@skip_if_no_nornir
def test_to_file_struct_data():
    """test that structured data saves as a json"""
    clean_up_folder()

    iol_r1_res = [
        {"ip": "1.2.3.4", "interface": "Gi123"},
        {"ip": "2.2.2.2", "interface": "Gi2"},
        {"ip": "3.3.3.3", "interface": "Gi3"},
    ]
    csr1k_r1_res = [
        {"ip": "4.4.4.4", "interface": "Gi2"},
    ]

    # run test to generate the file
    nr_with_tf = nr.with_processors(
        [ToFileProcessor(tf="config_for_read", base_url="./tofile_outputs/")]
    )
    output = nr_with_tf.run(
        task=nr_test,
        ret_data_per_host={
            "iol-r1": iol_r1_res,
            "csr1k-r1": csr1k_r1_res,
        },
        name="show run | inc ntp",
    )

    files = os.listdir("./tofile_outputs/")
    assert "tf_index_common.json" in files, "tf_index_common.json not found"
    for file in files:
        filname = "./tofile_outputs/{}".format(file)
        if "tf_index_common.json" in filname:
            with open(filname, "r") as f:
                tf_index_common_content = f.read()
                assert (
                    tf_index_common_content.count('"content_type": "json"') == 2
                ), "Not all files converted to json"
        elif "iol-r1" in filname:
            with open(filname, "r") as f:
                content = json.loads(f.read())
                assert content == iol_r1_res
        elif "csr1k-r1" in filname:
            with open(filname, "r") as f:
                content = json.loads(f.read())
                assert content == csr1k_r1_res


# test_to_file_struct_data()
