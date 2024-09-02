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

from nornir_salt.plugins.functions import ResultSerializer
from nornir_salt.plugins.inventory import DictInventory
from nornir_salt.plugins.tasks import nr_test
from nornir_salt.plugins.processors import ToFileProcessor
from nornir_salt.plugins.processors import DiffProcessor

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
def test_diff_processor():
    clean_up_folder()

    # run test to generate the file
    nr_with_tests = nr.with_processors(
        [ToFileProcessor(tf="config_for_diff", base_url="./tofile_outputs/")]
    )
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": """
Timestamp 12:12:12

ntp server 7.7.7.8
ntp server 7.7.7.7
        """,
            "IOL2": """
ntp server 7.7.7.7
        """,
        },
        name="show run | inc ntp",
    )

    # run the test to make difference
    nr_with_tests = nr.with_processors(
        [DiffProcessor(diff="config_for_diff", base_url="./tofile_outputs/")]
    )
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": """
Timestamp 14:14:14

ntp server 7.7.7.8
        """,
            "IOL2": """
ntp server 7.7.7.7
ntp server 9.9.9.9
        """,
        },
        name="show run | inc ntp",
    )

    res = ResultSerializer(output, add_details=True)

    pprint.pprint(res)
    # {'IOL1': {'show run | inc ntp': {'changed': False,
    #                                  'diff': '',
    #                                  'exception': None,
    #                                  'failed': False,
    #                                  'result': '--- old '
    #                                            './tofile_outputs/config_for_diff__23_August_2021_22_12_40__634__IOL1.txt\n'
    #                                            '+++ new results\n'
    #                                            '@@ -1,3 +1,2 @@\n'
    #                                            '-Timestamp 12:12:12\n'
    #                                            '+Timestamp 14:14:14\n'
    #                                            ' ntp server 7.7.7.8\n'
    #                                            '-ntp server 7.7.7.7\n'}},
    #  'IOL2': {'show run | inc ntp': {'changed': False,
    #                                  'diff': '',
    #                                  'exception': None,
    #                                  'failed': False,
    #                                  'result': '--- old '
    #                                            './tofile_outputs/config_for_diff__23_August_2021_22_12_40__397__IOL2.txt\n'
    #                                            '+++ new results\n'
    #                                            '@@ -1 +1,2 @@\n'
    #                                            ' ntp server 7.7.7.7\n'
    #                                            '+ntp server 9.9.9.9\n'}}}

    assert (
        """-Timestamp 12:12:12
+Timestamp 14:14:14
 ntp server 7.7.7.8
-ntp server 7.7.7.7"""
        in res["IOL1"]["show run | inc ntp"]["result"]
    )
    assert (
        """
 ntp server 7.7.7.7
+ntp server 9.9.9.9"""
        in res["IOL2"]["show run | inc ntp"]["result"]
    )


test_diff_processor()


@skip_if_no_nornir
def test_diff_processor_in_diff_is_true():
    clean_up_folder()

    # run test to generate the file
    nr_with_tests = nr.with_processors(
        [ToFileProcessor(tf="config_for_diff", base_url="./tofile_outputs/")]
    )
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": """
Timestamp 12:12:12

ntp server 7.7.7.8
ntp server 7.7.7.7
        """,
            "IOL2": """
ntp server 7.7.7.7
        """,
        },
        name="show run | inc ntp",
    )

    # run the test to make difference
    nr_with_tests = nr.with_processors(
        [DiffProcessor(diff="config_for_diff", base_url="./tofile_outputs/", in_diff=True)]
    )
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": """
Timestamp 14:14:14

ntp server 7.7.7.8
        """,
            "IOL2": """
ntp server 7.7.7.7
ntp server 9.9.9.9
        """,
        },
        name="show run | inc ntp",
    )

    res = ResultSerializer(output, add_details=True)

    # pprint.pprint(res)
    # {'IOL1': {'show run | inc ntp': {'changed': False,
    #                                  'diff': '--- old '
    #                                          './tofile_outputs/config_for_diff__22_August_2021_20_44_04__IOL1.txt\n'
    #                                          '+++ new results\n'
    #                                          '@@ -1,3 +1,2 @@\n'
    #                                          '-Timestamp 12:12:12\n'
    #                                          '+Timestamp 14:14:14\n'
    #                                          ' ntp server 7.7.7.8\n'
    #                                          '-ntp server 7.7.7.7\n',
    #                                  'exception': None,
    #                                  'failed': False,
    #                                  'result': '\n'
    #                                            'Timestamp 14:14:14\n'
    #                                            '\n'
    #                                            'ntp server 7.7.7.8\n'
    #                                            '        '}},
    #  'IOL2': {'show run | inc ntp': {'changed': False,
    #                                  'diff': '--- old '
    #                                          './tofile_outputs/config_for_diff__22_August_2021_20_44_04__IOL2.txt\n'
    #                                          '+++ new results\n'
    #                                          '@@ -1 +1,2 @@\n'
    #                                          ' ntp server 7.7.7.7\n'
    #                                          '+ntp server 9.9.9.9\n',
    #                                  'exception': None,
    #                                  'failed': False,
    #                                  'result': '\n'
    #                                            'ntp server 7.7.7.7\n'
    #                                            'ntp server 9.9.9.9\n'
    #                                            '        '}}}
    assert (
        """-Timestamp 12:12:12
+Timestamp 14:14:14
 ntp server 7.7.7.8
-ntp server 7.7.7.7"""
        in res["IOL1"]["show run | inc ntp"]["diff"]
    )
    assert (
        """
 ntp server 7.7.7.7
+ntp server 9.9.9.9"""
        in res["IOL2"]["show run | inc ntp"]["diff"]
    )

# test_diff_processor_in_diff_is_true()
