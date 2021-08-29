import sys
import pprint
import logging
import yaml
import pytest

sys.path.insert(0, "..")

try:
    from nornir import InitNornir
    from nornir.core.task import Result, Task
    from nornir_netmiko import netmiko_send_command, netmiko_send_config
    from nornir.core.plugins.inventory import InventoryPluginRegister

    HAS_NORNIR = True
except ImportError:
    HAS_NORNIR = False

from nornir_salt import ResultSerializer
from nornir_salt import DictInventory
from nornir_salt import tcp_ping
from nornir_salt import nr_test

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

    ping_check = ResultSerializer(nr.run(tcp_ping))
    HAS_LAB = True
    for hostname, result in ping_check.items():
        if result["tcp_ping"][22] == False:
            HAS_LAB = False

    skip_if_no_lab = pytest.mark.skipif(
        HAS_LAB == False, reason="Failed connect to LAB"
    )

    return nr


InventoryPluginRegister.register("DictInventory", DictInventory)

nr = init(lab_inventory_dict)


# ----------------------------------------------------------------------
# tests that need Nornir
# ----------------------------------------------------------------------

@skip_if_no_nornir
def test_result_serializer_to_dict_with_details():
    output = nr.run(
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
        name="check ntp config",
    )
    serialized_output = ResultSerializer(output, add_details=True)
    assert serialized_output == {
        "IOL1": {
            "check ntp config": {
                "changed": False,
                "diff": "",
                "exception": None,
                "failed": False,
                "result": "\n" "ntp server 7.7.7.8\n" "ntp server 7.7.7.7\n" "        ",
            }
        },
        "IOL2": {
            "check ntp config": {
                "changed": False,
                "diff": "",
                "exception": None,
                "failed": False,
                "result": "\nntp server 7.7.7.7\n        ",
            }
        },
    }


# test_result_serializer_to_dict_with_details()


@skip_if_no_nornir
def test_result_serializer_to_dict_no_details():
    output = nr.run(
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
        name="check ntp config",
    )
    serialized_output = ResultSerializer(output, add_details=False)
    assert serialized_output == {
        "IOL1": {
            "check ntp config": "\n"
            "ntp server 7.7.7.8\n"
            "ntp server 7.7.7.7\n"
            "        "
        },
        "IOL2": {"check ntp config": "\nntp server 7.7.7.7\n        "},
    }


# test_result_serializer_to_dict_no_details()


@skip_if_no_nornir
def test_result_serializer_to_list_with_details():
    output = nr.run(
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
        name="check ntp config",
    )
    serialized_output = ResultSerializer(output, add_details=True, to_dict=False)
    # pprint.pprint(serialized_output)
    assert serialized_output == [
        {
            "changed": False,
            "diff": "",
            "exception": None,
            "failed": False,
            "host": "IOL1",
            "name": "check ntp config",
            "result": "\nntp server 7.7.7.8\nntp server 7.7.7.7\n        ",
        },
        {
            "changed": False,
            "diff": "",
            "exception": None,
            "failed": False,
            "host": "IOL2",
            "name": "check ntp config",
            "result": "\nntp server 7.7.7.7\n        ",
        },
    ]


# test_result_serializer_to_list_with_details()


@skip_if_no_nornir
def test_result_serializer_to_list_no_details():
    output = nr.run(
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
        name="check ntp config",
    )
    serialized_output = ResultSerializer(output, add_details=False, to_dict=False)
    # pprint.pprint(serialized_output)
    assert serialized_output == [
        {
            "host": "IOL1",
            "name": "check ntp config",
            "result": "\nntp server 7.7.7.8\nntp server 7.7.7.7\n        ",
        },
        {
            "host": "IOL2",
            "name": "check ntp config",
            "result": "\nntp server 7.7.7.7\n        ",
        },
    ]


# test_result_serializer_to_list_no_details()
