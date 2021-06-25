import sys
import os
import pprint
import logging
import yaml
import pytest
import time

sys.path.insert(0, "..")

try:
    from nornir import InitNornir
    from nornir.core.plugins.inventory import InventoryPluginRegister
    from nornir.core.task import Result

    HAS_NORNIR = True
except ImportError:
    HAS_NORNIR = False

from nornir_salt import ResultSerializer
from nornir_salt import DictInventory
from nornir_salt import nr_test
from nornir_salt.plugins.processors.ToFileProcessor import ToFileProcessor


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
            "IOL1": """
ntp server 7.7.7.8
ntp server 7.7.7.7
        """,
            "IOL2": """
ntp server 7.7.7.7
        """,
        },
        name="show run | inc ntp",
    )
    files = os.listdir("./tofile_outputs/")
    assert "tf_aliases.json" in files, "tf_aliases.json not found"
    for file in files:
        if "tf_aliases.json" in file:
            continue
        assert "config__" in file and ("__IOL1.txt" in file or "__IOL2.txt" in file)


# test_to_file()


@skip_if_no_nornir
def test_to_file_max_files():
    clean_up_folder()

    # run test
    nr_with_tf = nr.with_processors(
        [ToFileProcessor(tf="config", base_url="./tofile_outputs/", max_files=2)]
    )
    output = nr_with_tf.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": """
ntp server 7.7.7.8
ntp server 7.7.7.7
        """,
            "IOL2": """
ntp server 7.7.7.7
        """,
        },
        name="show run | inc ntp",
    )
    time.sleep(1)
    nr_with_tf = nr.with_processors(
        [ToFileProcessor(tf="config", base_url="./tofile_outputs/", max_files=2)]
    )
    output = nr_with_tf.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": """
ntp server 7.7.7.8
ntp server 7.7.7.7
        """,
            "IOL2": """
ntp server 7.7.7.7
        """,
        },
        name="show run | inc ntp",
    )
    time.sleep(1)
    nr_with_tf = nr.with_processors(
        [ToFileProcessor(tf="config", base_url="./tofile_outputs/", max_files=2)]
    )
    output = nr_with_tf.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": """
ntp server 7.7.7.8
ntp server 7.7.7.7
        """,
            "IOL2": """
ntp server 7.7.7.7
        """,
        },
        name="show run | inc ntp",
    )
    files = os.listdir("./tofile_outputs/")

    assert "tf_aliases.json" in files, "tf_aliases.json not found"
    assert len(files) == 5, "above max_files found in directory"


# test_to_file_max_files()
