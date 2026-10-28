import logging
import pprint
import sys

import pytest
import yaml

sys.path.insert(0, "..")

try:
    from nornir import InitNornir
    from nornir.core.plugins.inventory import InventoryPluginRegister

    HAS_NORNIR = True
except ImportError:
    HAS_NORNIR = False

from nornir_salt.plugins.functions import ResultSerializer
from nornir_salt.plugins.inventory import DictInventory
from nornir_salt.plugins.tasks import nr_test, sleep

logging.basicConfig(level=logging.ERROR)


# ----------------------------------------------------------------------
# Initialize Nornir
# ----------------------------------------------------------------------


skip_if_no_nornir = pytest.mark.skipif(
    HAS_NORNIR == False,
    reason="Failed to import all required Nornir modules and plugins",
)

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


# ----------------------------------------------------------------------
# tests that need Nornir
# ----------------------------------------------------------------------


@skip_if_no_nornir
def test_nr_test_ret_data():
    output = nr.run(
        task=nr_test,
        ret_data="""
ntp server 7.7.7.8
ntp server 7.7.7.7
        """,
        name="check ntp config",
    )
    result = ResultSerializer(output)
    # pprint.pprint(result)
    assert result == {
        "iol-r1": {
            "check ntp config": "\n"
            "ntp server 7.7.7.8\n"
            "ntp server 7.7.7.7\n"
            "        "
        },
        "csr1k-r1": {
            "check ntp config": "\n"
            "ntp server 7.7.7.8\n"
            "ntp server 7.7.7.7\n"
            "        "
        },
    }


# test_nr_test_ret_data()


@skip_if_no_nornir
def test_nr_test_kwargs():
    output = nr.run(task=nr_test, a="b", c="d", name="check ntp config")
    result = ResultSerializer(output)
    # pprint.pprint(result)
    assert result == {
        "iol-r1": {"check ntp config": {"a": "b", "c": "d"}},
        "csr1k-r1": {"check ntp config": {"a": "b", "c": "d"}},
    }


# test_nr_test_kwargs()


@skip_if_no_nornir
def test_nr_test_ret_data_per_host():
    output = nr.run(
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
        name="check ntp config",
    )
    result = ResultSerializer(output)
    # pprint.pprint(result)
    assert result == {
        "iol-r1": {
            "check ntp config": "\n"
            "ntp server 7.7.7.8\n"
            "ntp server 7.7.7.7\n"
            "        "
        },
        "csr1k-r1": {"check ntp config": "\nntp server 7.7.7.7\n        "},
    }


# test_nr_test_ret_data_per_host()


@skip_if_no_nornir
def test_task_sleep_random_two_digits():
    output = nr.run(
        task=sleep,
        sleep_random=[0, 2],
    )
    result = ResultSerializer(output)
    pprint.pprint(result)
    assert "Slept for" in result["iol-r1"]["sleep"]
    assert "Slept for" in result["csr1k-r1"]["sleep"]


# test_task_sleep_random_two_digits()


@skip_if_no_nornir
def test_task_sleep_random_digit():
    output = nr.run(
        task=sleep,
        sleep_random=2,
    )
    result = ResultSerializer(output)
    pprint.pprint(result)
    assert "Slept for" in result["iol-r1"]["sleep"]
    assert "Slept for" in result["csr1k-r1"]["sleep"]


# test_task_sleep_random_digit()


@skip_if_no_nornir
def test_nr_test_ret_task_data():
    # add __task__data
    for host_name, host_object in nr.inventory.hosts.items():
        _ = host_object.data.pop("__task__", None)  # rewrite task data
        host_object.data["__task__"] = {"cmds": ["foo", "bar"]}
    output = nr.run(task=nr_test, use_task_data=True)
    result = ResultSerializer(output)
    pprint.pprint(result)
    assert result == {
        "iol-r1": {"nr_test": {"cmds": ["foo", "bar"]}},
        "csr1k-r1": {"nr_test": {"cmds": ["foo", "bar"]}},
    }


@skip_if_no_nornir
def test_nr_test_ret_task_data_key():
    # add __task__data
    for host_name, host_object in nr.inventory.hosts.items():
        _ = host_object.data.pop("__task__", None)  # rewrite task data
        host_object.data["__task__"] = {"cmds": ["foo", "bar"]}
    output = nr.run(task=nr_test, use_task_data="cmds")
    result = ResultSerializer(output)
    pprint.pprint(result)
    assert result == {
        "iol-r1": {"nr_test": ["foo", "bar"]},
        "csr1k-r1": {"nr_test": ["foo", "bar"]},
    }
