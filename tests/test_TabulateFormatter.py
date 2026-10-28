import logging
import pprint
import sys

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

from nornir_salt.plugins.functions import ResultSerializer, TabulateFormatter
from nornir_salt.plugins.inventory import DictInventory
from nornir_salt.plugins.processors import TestsProcessor
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


def nr_test_grouped_subtasks(task, task_1, task_2):
    """
    Test grouped task
    """
    task.run(**task_1)
    task.run(**task_2)
    return Result(host=task.host, skip_results=True)


# ----------------------------------------------------------------------
# tests that need Nornir
# ----------------------------------------------------------------------


@skip_if_no_nornir
def test_tabulate_from_list():
    nr.data.reset_failed_hosts()
    output = nr.run(
        task=nr_test, ret_data="""ntp server 7.7.7.8""", name="check ntp config"
    )
    result = ResultSerializer(output, add_details=True, to_dict=False)
    table = TabulateFormatter(result)
    # print(table)
    # result              changed    diff    failed    name              exception    host
    # ------------------  ---------  ------  --------  ----------------  -----------  ------
    # ntp server 7.7.7.8  False              False     check ntp config               iol-r1
    # ntp server 7.7.7.8  False              False     check ntp config               csr1k-r1
    assert isinstance(table, str)
    assert "result" in table
    assert "host" in table
    assert len(table.splitlines()) == 4
    assert table.count("False") == 4


# test_tabulate_from_list()


@skip_if_no_nornir
def test_tabulate_from_aggregatedresult():
    nr.data.reset_failed_hosts()
    output = nr.run(
        task=nr_test, ret_data="""ntp server 7.7.7.8""", name="check ntp config"
    )
    table = TabulateFormatter(output)
    # print(table)
    assert (
        table
        == """result              changed    diff    failed    exception    name              host
------------------  ---------  ------  --------  -----------  ----------------  --------
ntp server 7.7.7.8  False              False                  check ntp config  iol-r1
ntp server 7.7.7.8  False              False                  check ntp config  csr1k-r1"""
        or table
        == """result              changed    diff    failed    name              exception    host
------------------  ---------  ------  --------  ----------------  -----------  --------
ntp server 7.7.7.8  False              False     check ntp config               iol-r1
ntp server 7.7.7.8  False              False     check ntp config               csr1k-r1"""
    )


# test_tabulate_from_aggregatedresult()


@skip_if_no_nornir
def test_tabulate_from_aggregatedresult_brief():
    nr.data.reset_failed_hosts()
    tests = [
        ["show run | inc ntp", "contains", "7.7.7.8"],
        ["show run | inc ntp", "contains", "7.7.7.7"],
    ]
    nr_with_tests = nr.with_processors(
        [TestsProcessor(tests, remove_tasks=True, build_per_host_tests=True)]
    )
    output = nr_with_tests.run(
        task=nr_test, ret_data="""ntp server 7.7.7.8""", name="show run | inc ntp"
    )
    table = TabulateFormatter(output, tabulate="brief")
    # print(table)
    assert (
        table
        == """+----+----------+---------------------------------------+----------+-----------------------+
|    | host     | name                                  | result   | exception             |
+====+==========+=======================================+==========+=======================+
|  0 | iol-r1   | show run | inc ntp contains 7.7.7.8.. | PASS     |                       |
+----+----------+---------------------------------------+----------+-----------------------+
|  1 | iol-r1   | show run | inc ntp contains 7.7.7.7.. | FAIL     | Pattern not in output |
+----+----------+---------------------------------------+----------+-----------------------+
|  2 | csr1k-r1 | show run | inc ntp contains 7.7.7.8.. | PASS     |                       |
+----+----------+---------------------------------------+----------+-----------------------+
|  3 | csr1k-r1 | show run | inc ntp contains 7.7.7.7.. | FAIL     | Pattern not in output |
+----+----------+---------------------------------------+----------+-----------------------+"""
    )


# test_tabulate_from_aggregatedresult_brief()


@skip_if_no_nornir
def test_tabulate_from_aggregatedresult_with_headers():
    nr.data.reset_failed_hosts()
    output = nr.run(
        task=nr_test,
        ret_data="""ntp server 7.7.7.8
ntp server 7.7.7.7""",
        name="check ntp config",
    )
    table = TabulateFormatter(output, headers=["host", "failed", "name", "result"])
    # print(table)
    assert table == """host      failed    name              result
--------  --------  ----------------  ------------------
iol-r1    False     check ntp config  ntp server 7.7.7.8
                                      ntp server 7.7.7.7
csr1k-r1  False     check ntp config  ntp server 7.7.7.8
                                      ntp server 7.7.7.7"""


# test_tabulate_from_aggregatedresult_with_headers()


@skip_if_no_nornir
def test_tabulate_sort_by_key_value():
    iol_r1_res_ntp = [
        {"ntp": "1.1.1.1"},
    ]
    csr1k_r1_res_ntp = [
        {"ntp": "2.2.2.2"},
    ]
    iol_r1_res_log = [
        {"log": "3.3.3.3"},
    ]
    csr1k_r1_res_log = [
        {"log": "4.4.4.4"},
    ]
    result = nr.run(
        task=nr_test_grouped_subtasks,
        task_1={
            "task": nr_test,
            "ret_data_per_host": {
                "iol-r1": iol_r1_res_ntp,
                "csr1k-r1": csr1k_r1_res_ntp,
            },
            "name": "show run | inc ntp",
        },
        task_2={
            "task": nr_test,
            "ret_data_per_host": {
                "iol-r1": iol_r1_res_log,
                "csr1k-r1": csr1k_r1_res_log,
            },
            "name": "show run | inc logging",
        },
    )
    table = TabulateFormatter(
        result, headers=["host", "failed", "name", "result"], sortby="host"
    )
    print(table)
    assert table == """host      failed    name                    result
--------  --------  ----------------------  --------------------
csr1k-r1  False     show run | inc ntp      [{'ntp': '2.2.2.2'}]
csr1k-r1  False     show run | inc logging  [{'log': '4.4.4.4'}]
iol-r1    False     show run | inc ntp      [{'ntp': '1.1.1.1'}]
iol-r1    False     show run | inc logging  [{'log': '3.3.3.3'}]"""


# test_tabulate_sort_by_key_value()


@skip_if_no_nornir
def test_tabulate_sort_by_key_value_reverse():
    iol_r1_res_ntp = [
        {"ntp": "1.1.1.1"},
    ]
    csr1k_r1_res_ntp = [
        {"ntp": "2.2.2.2"},
    ]
    iol_r1_res_log = [
        {"log": "3.3.3.3"},
    ]
    csr1k_r1_res_log = [
        {"log": "4.4.4.4"},
    ]
    result = nr.run(
        task=nr_test_grouped_subtasks,
        task_1={
            "task": nr_test,
            "ret_data_per_host": {
                "iol-r1": iol_r1_res_ntp,
                "csr1k-r1": csr1k_r1_res_ntp,
            },
            "name": "show run | inc ntp",
        },
        task_2={
            "task": nr_test,
            "ret_data_per_host": {
                "iol-r1": iol_r1_res_log,
                "csr1k-r1": csr1k_r1_res_log,
            },
            "name": "show run | inc logging",
        },
    )
    table = TabulateFormatter(
        result,
        headers=["host", "failed", "name", "result"],
        sortby="host",
        reverse=True,
    )
    # print(table)
    assert table == """host      failed    name                    result
--------  --------  ----------------------  --------------------
iol-r1    False     show run | inc ntp      [{'ntp': '1.1.1.1'}]
iol-r1    False     show run | inc logging  [{'log': '3.3.3.3'}]
csr1k-r1  False     show run | inc ntp      [{'ntp': '2.2.2.2'}]
csr1k-r1  False     show run | inc logging  [{'log': '4.4.4.4'}]"""


# test_tabulate_sort_by_key_value_reverse()
