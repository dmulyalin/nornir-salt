import sys
import pprint
import logging
import yaml
import pytest

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
from nornir_salt.plugins.processors import TestsProcessor


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
    data:
      interfaces:
        - name: Eth1
          description: Circuit CX54DF323
          mtu: 1500
          line: line protocol is up
          admin: admin up
        - name: Eth2
          description: OOB Connection
          mtu: 9200
          line: line protocol is up
          admin: admin up
      version: xe1.2.3.4
  IOL2:
    hostname: 192.168.217.7
    platform: ios
    groups: [lab]
    data:
      version: xe1.2.3.4
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


# ----------------------------------------------------------------------
# tests that need Nornir
# ----------------------------------------------------------------------


@skip_if_no_nornir
def test_contains_check_list_of_dict_tests():
    tests = [
        {
            "task": "show run | inc ntp",
            "name": "Test NTP config",
            "pattern": "ntp server 7.7.7.8",
            "test": "contains",
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
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
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    # pprint.pprint(check_result)
    assert check_result == {
        "IOL1": {
            "Test NTP config": {
                "changed": False,
                "criteria": "ntp server 7.7.7.8",
                "diff": "",
                "exception": None,
                "failed": False,
                "result": "PASS",
                "success": True,
                "task": "show run | inc ntp",
                "test": "contains",
            }
        },
        "IOL2": {
            "Test NTP config": {
                "changed": False,
                "criteria": "ntp server 7.7.7.8",
                "diff": "",
                "exception": "Pattern not in output",
                "failed": True,
                "result": "FAIL",
                "success": False,
                "task": "show run | inc ntp",
                "test": "contains",
            }
        },
    }


# test_contains_check_list_of_dict_tests()


@skip_if_no_nornir
def test_contains_check_single_test_kwargs():
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors(
        [
            TestsProcessor(
                remove_tasks=True,
                task="show run | inc ntp",
                name="Test NTP config",
                pattern="ntp server 7.7.7.8",
                test="contains",
            )
        ]
    )
    output = nr_with_tests.run(
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
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    # pprint.pprint(check_result)
    assert check_result == {
        "IOL1": {
            "Test NTP config": {
                "changed": False,
                "criteria": "ntp server 7.7.7.8",
                "diff": "",
                "exception": None,
                "failed": False,
                "result": "PASS",
                "success": True,
                "task": "show run | inc ntp",
                "test": "contains",
            }
        },
        "IOL2": {
            "Test NTP config": {
                "changed": False,
                "criteria": "ntp server 7.7.7.8",
                "diff": "",
                "exception": "Pattern not in output",
                "failed": True,
                "result": "FAIL",
                "success": False,
                "task": "show run | inc ntp",
                "test": "contains",
            }
        },
    }


# test_contains_check_single_test_kwargs()


@skip_if_no_nornir
def test_contains_check_list_of_lists():
    tests = [
        [
            "show run | inc ntp",
            "contains",
            "ntp server 7.7.7.8",
            "test ntp configuration",
        ],
        ["show run | inc ntp", "contains", "ntp server 7.7.7.7"],
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors(
        [TestsProcessor(tests, remove_tasks=True, build_per_host_tests=True)]
    )
    output = nr_with_tests.run(
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
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    # pprint.pprint(check_result, width=150)
    assert check_result == {
        "IOL1": {
            "show run | inc ntp contains ntp serve..": {
                "changed": False,
                "criteria": "ntp server 7.7.7.7",
                "diff": "",
                "exception": None,
                "failed": False,
                "result": "PASS",
                "success": True,
                "task": "show run | inc ntp",
                "test": "contains",
            },
            "test ntp configuration": {
                "changed": False,
                "criteria": "ntp server 7.7.7.8",
                "diff": "",
                "exception": None,
                "failed": False,
                "result": "PASS",
                "success": True,
                "task": "show run | inc ntp",
                "test": "contains",
            },
        },
        "IOL2": {
            "show run | inc ntp contains ntp serve..": {
                "changed": False,
                "criteria": "ntp server 7.7.7.7",
                "diff": "",
                "exception": None,
                "failed": False,
                "result": "PASS",
                "success": True,
                "task": "show run | inc ntp",
                "test": "contains",
            },
            "test ntp configuration": {
                "changed": False,
                "criteria": "ntp server 7.7.7.8",
                "diff": "",
                "exception": "Pattern not in output",
                "failed": True,
                "result": "FAIL",
                "success": False,
                "task": "show run | inc ntp",
                "test": "contains",
            },
        },
    }


# test_contains_check_list_of_lists()


@skip_if_no_nornir
def test_contains_re_check():
    tests = [
        {
            "task": "show run | inc ntp",
            "name": "Test NTP config",
            "pattern": ".* server 7.7.7.8",
            "test": "contains_re",
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
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
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    # pprint.pprint(check_result)
    assert check_result == {
        "IOL1": {
            "Test NTP config": {
                "changed": False,
                "criteria": ".* server 7.7.7.8",
                "diff": "",
                "exception": None,
                "failed": False,
                "result": "PASS",
                "success": True,
                "task": "show run | inc ntp",
                "test": "contains_re",
            }
        },
        "IOL2": {
            "Test NTP config": {
                "changed": False,
                "criteria": ".* server 7.7.7.8",
                "diff": "",
                "exception": "Regex pattern not in output",
                "failed": True,
                "result": "FAIL",
                "success": False,
                "task": "show run | inc ntp",
                "test": "contains_re",
            }
        },
    }


# test_contains_re_check()


@skip_if_no_nornir
def test_contains_count_check():
    tests = [
        {
            "task": "show run | inc ntp",
            "name": "Test NTP config",
            "pattern": "ntp server 7.7.7.",
            "test": "contains",
            "count": 2,
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
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
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    # pprint.pprint(check_result)
    assert check_result == {
        "IOL1": {
            "Test NTP config": {
                "changed": False,
                "count": 2,
                "criteria": "ntp server 7.7.7.",
                "diff": "",
                "exception": None,
                "failed": False,
                "result": "PASS",
                "success": True,
                "task": "show run | inc ntp",
                "test": "contains",
            }
        },
        "IOL2": {
            "Test NTP config": {
                "changed": False,
                "count": 2,
                "criteria": "ntp server 7.7.7.",
                "diff": "",
                "exception": "Pattern not in output 2 times",
                "failed": True,
                "result": "FAIL",
                "success": False,
                "task": "show run | inc ntp",
                "test": "contains",
            }
        },
    }


# test_contains_count_check()


@skip_if_no_nornir
def test_contains_check_revert():
    tests = [
        {
            "task": "show run | inc ntp",
            "name": "Test NTP config",
            "pattern": "ntp server 7.7.7.8",
            "test": "!contains",
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
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
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    # pprint.pprint(check_result)
    assert check_result == {
        "IOL1": {
            "Test NTP config": {
                "changed": False,
                "criteria": "ntp server 7.7.7.8",
                "diff": "",
                "exception": "Pattern in output",
                "failed": True,
                "result": "FAIL",
                "success": False,
                "task": "show run | inc ntp",
                "test": "!contains",
            }
        },
        "IOL2": {
            "Test NTP config": {
                "changed": False,
                "criteria": "ntp server 7.7.7.8",
                "diff": "",
                "exception": None,
                "failed": False,
                "result": "PASS",
                "success": True,
                "task": "show run | inc ntp",
                "test": "!contains",
            }
        },
    }


# test_contains_check_revert()


@skip_if_no_nornir
def test_contains_re_check_revert():
    tests = [
        {
            "task": "show run | inc ntp",
            "name": "Test NTP config",
            "pattern": ".* server 7.7.7.8",
            "test": "!contains_re",
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
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
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    # pprint.pprint(check_result)
    assert check_result == {
        "IOL1": {
            "Test NTP config": {
                "changed": False,
                "criteria": ".* server 7.7.7.8",
                "diff": "",
                "exception": "Regex pattern in output",
                "failed": True,
                "result": "FAIL",
                "success": False,
                "task": "show run | inc ntp",
                "test": "!contains_re",
            }
        },
        "IOL2": {
            "Test NTP config": {
                "changed": False,
                "criteria": ".* server 7.7.7.8",
                "diff": "",
                "exception": None,
                "failed": False,
                "result": "PASS",
                "success": True,
                "task": "show run | inc ntp",
                "test": "!contains_re",
            }
        },
    }


# test_contains_re_check_revert()


@skip_if_no_nornir
def test_contains_count_check_revert():
    tests = [
        {
            "task": "show run | inc ntp",
            "name": "Test NTP config",
            "pattern": "ntp server 7.7.7.",
            "test": "!contains",
            "count": 2,
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
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
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    # pprint.pprint(check_result)
    assert check_result == {
        "IOL1": {
            "Test NTP config": {
                "changed": False,
                "count": 2,
                "criteria": "ntp server 7.7.7.",
                "diff": "",
                "exception": "Pattern in output 2 times",
                "failed": True,
                "result": "FAIL",
                "success": False,
                "task": "show run | inc ntp",
                "test": "!contains",
            }
        },
        "IOL2": {
            "Test NTP config": {
                "changed": False,
                "count": 2,
                "criteria": "ntp server 7.7.7.",
                "diff": "",
                "exception": None,
                "failed": False,
                "result": "PASS",
                "success": True,
                "task": "show run | inc ntp",
                "test": "!contains",
            }
        },
    }


# test_contains_count_check_revert()


@skip_if_no_nornir
def test_contains_check_contains_lines():
    tests = [
        {
            "task": "show run | inc ntp",
            "name": "Test NTP config",
            "pattern": ["ntp server 7.7.7.8", "ntp server 7.7.7.7"],
            "test": "contains_lines",
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
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
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    # pprint.pprint(check_result)
    assert check_result == {
        "IOL1": {
            "Test NTP config": {
                "changed": False,
                "criteria": "",
                "diff": "",
                "exception": None,
                "failed": False,
                "result": "PASS",
                "success": True,
                "task": "show run | inc ntp",
                "test": "contains_lines",
            }
        },
        "IOL2": {
            "Test NTP config": {
                "changed": False,
                "criteria": "ntp server 7.7.7.8",
                "diff": "",
                "exception": "Pattern not in output",
                "failed": True,
                "result": "FAIL",
                "success": False,
                "task": "show run | inc ntp",
                "test": "contains_lines",
            }
        },
    }


# test_contains_check_contains_lines()


@skip_if_no_nornir
def test_contains_check_contains_lines_revert():
    tests = [
        {
            "task": "show run | inc ntp",
            "name": "Test NTP config",
            "pattern": ["ntp server 7.7.7.8", "ntp server 7.7.7.7"],
            "test": "!contains_lines",
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": """
ntp server 7.7.7.8
ntp server 7.7.7.7
        """,
            "IOL2": """
ntp server 7.7.7.9
        """,
        },
        name="show run | inc ntp",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    # pprint.pprint(check_result)
    assert check_result == {
        "IOL1": {
            "Test NTP config": {
                "changed": False,
                "criteria": "ntp server 7.7.7.8",
                "diff": "",
                "exception": "Pattern in output",
                "failed": True,
                "result": "FAIL",
                "success": False,
                "task": "show run | inc ntp",
                "test": "!contains_lines",
            }
        },
        "IOL2": {
            "Test NTP config": {
                "changed": False,
                "criteria": "",
                "diff": "",
                "exception": None,
                "failed": False,
                "result": "PASS",
                "success": True,
                "task": "show run | inc ntp",
                "test": "!contains_lines",
            }
        },
    }


# test_contains_check_contains_lines_revert()


@skip_if_no_nornir
def test_equal_check():
    tests = [
        {
            "task": "show run | inc ntp",
            "name": "Test NTP config",
            "pattern": "ntp server 7.7.7.7",
            "test": "equal",
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": """
ntp server 7.7.7.8
ntp server 7.7.7.7
        """,
            "IOL2": """ntp server 7.7.7.7""",
        },
        name="show run | inc ntp",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    # pprint.pprint(check_result)
    assert check_result == {
        "IOL1": {
            "Test NTP config": {
                "changed": False,
                "criteria": "ntp server 7.7.7.7",
                "diff": "",
                "exception": "Pattern and output not equal",
                "failed": True,
                "result": "FAIL",
                "success": False,
                "task": "show run | inc ntp",
                "test": "equal",
            }
        },
        "IOL2": {
            "Test NTP config": {
                "changed": False,
                "criteria": "ntp server 7.7.7.7",
                "diff": "",
                "exception": None,
                "failed": False,
                "result": "PASS",
                "success": True,
                "task": "show run | inc ntp",
                "test": "equal",
            }
        },
    }


# test_equal_check()


@skip_if_no_nornir
def test_not_equal_check():
    tests = [
        {
            "task": "show run | inc ntp",
            "name": "Test NTP config",
            "pattern": "ntp server 7.7.7.7",
            "test": "!equal",
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": """
ntp server 7.7.7.8
ntp server 7.7.7.7
        """,
            "IOL2": """ntp server 7.7.7.7""",
        },
        name="show run | inc ntp",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    # pprint.pprint(check_result)
    assert check_result == {
        "IOL1": {
            "Test NTP config": {
                "changed": False,
                "criteria": "ntp server 7.7.7.7",
                "diff": "",
                "exception": None,
                "failed": False,
                "result": "PASS",
                "success": True,
                "task": "show run | inc ntp",
                "test": "!equal",
            }
        },
        "IOL2": {
            "Test NTP config": {
                "changed": False,
                "criteria": "ntp server 7.7.7.7",
                "diff": "",
                "exception": "Pattern and output equal",
                "failed": True,
                "result": "FAIL",
                "success": False,
                "task": "show run | inc ntp",
                "test": "!equal",
            }
        },
    }


# test_not_equal_check()


@skip_if_no_nornir
def test_custom_function_text():
    custom_function = """
def run(result):
    ret =[]
    if "7.7.7.8" not in result.result:
        ret.append({
            "exception": "Server 7.7.7.8 not in config",
            "result": "FAIL",
            "success": False,
            "description": "check ntp config"
        })
    else:
        ret.append({
            "exception": "",
            "result": "PASS",
            "success": True
        })
    return ret
    """
    tests = [
        {
            "task": "show run | inc ntp",
            "name": "Test NTP config",
            "test": "custom",
            "function_text": custom_function,
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
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
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    # pprint.pprint(check_result)
    assert check_result == {
        "IOL1": {
            "Test NTP config": {
                "changed": False,
                "criteria": "",
                "diff": "",
                "exception": "",
                "failed": False,
                "result": "PASS",
                "success": True,
                "task": "show run | inc ntp",
                "test": "custom",
            }
        },
        "IOL2": {
            "Test NTP config": {
                "changed": False,
                "criteria": "",
                "description": "check ntp config",
                "diff": "",
                "exception": "Server 7.7.7.8 not in config",
                "failed": True,
                "result": "FAIL",
                "success": False,
                "task": "show run | inc ntp",
                "test": "custom",
            }
        },
    }


# test_custom_function_text()


@skip_if_no_nornir
def test_custom_function_file():
    tests = [
        {
            "task": "show run | inc ntp",
            "name": "Test NTP config",
            "test": "custom",
            "function_file": "./assets/custom_check_function_fun_1.txt",
            "function_name": "fun_1",
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
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
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    # pprint.pprint(check_result)
    assert check_result == {
        "IOL1": {
            "Test NTP config": {
                "changed": False,
                "criteria": "",
                "diff": "",
                "exception": None,
                "failed": False,
                "result": "PASS",
                "success": True,
                "task": "show run | inc ntp",
                "test": "custom",
            }
        },
        "IOL2": {
            "Test NTP config": {
                "changed": False,
                "criteria": "",
                "diff": "",
                "error": "Server 7.7.7.8 not in config",
                "exception": None,
                "failed": False,
                "result": "FAIL",
                "success": False,
                "task": "show run | inc ntp",
                "test": "custom",
            }
        },
    }


# test_custom_function_file()


def _custom_fun_run(result):
    ret = []
    if "7.7.7.8" not in result.result:
        ret.append(
            {
                "exception": "Server 7.7.7.8 not in config",
                "result": "FAIL",
                "success": False,
                "description": "check ntp config",
            }
        )
    else:
        ret.append({"exception": "", "result": "PASS", "success": True})
    return ret


@skip_if_no_nornir
def test_custom_function_call():
    tests = [
        {
            "task": "show run | inc ntp",
            "name": "Test NTP config",
            "test": "custom",
            "function_call": _custom_fun_run,
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
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
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    # pprint.pprint(check_result)
    assert check_result == {
        "IOL1": {
            "Test NTP config": {
                "changed": False,
                "criteria": "",
                "diff": "",
                "exception": "",
                "failed": False,
                "result": "PASS",
                "success": True,
                "task": "show run | inc ntp",
                "test": "custom",
            }
        },
        "IOL2": {
            "Test NTP config": {
                "changed": False,
                "criteria": "",
                "description": "check ntp config",
                "diff": "",
                "exception": "Server 7.7.7.8 not in config",
                "failed": True,
                "result": "FAIL",
                "success": False,
                "task": "show run | inc ntp",
                "test": "custom",
            }
        },
    }


# test_custom_function_call()


@skip_if_no_nornir
def grouped_task_for_use_all_tasks_test(task):
    # run first subtask
    task.run(
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
    # run second subtask
    task.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": """
logging host 1.1.1.1
        """,
            "IOL2": """
logging host 2.2.2.2
""",
        },
        name="show run | inc logging",
    )
    return Result(
        host=task.host,
    )


def custom_fun_for_use_all_tasks_test(multiresult):
    ret = []
    for item in multiresult:
        if not item.result:
            continue
        if "1.1.1.1" in item.result or "7.7.7.8" in item.result:
            ret.append({"exception": None, "success": True, "result": "PASS"})
        else:
            ret.append(
                {
                    "exception": "Logging or NTP cfg incorrect",
                    "success": False,
                    "result": "FAIL",
                }
            )

    return ret


@skip_if_no_nornir
def test_custom_function_text_use_all_tasks():
    tests = [
        {
            "name": "Test NTP and logging config",
            "test": "custom",
            "function_call": custom_fun_for_use_all_tasks_test,
            "use_all_tasks": True,
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(task=grouped_task_for_use_all_tasks_test)
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    pprint.pprint(check_result, width=150)
    assert check_result == {
        "IOL1": {
            "Test NTP and logging config": {
                "changed": False,
                "criteria": "",
                "diff": "",
                "exception": None,
                "failed": False,
                "result": "PASS",
                "success": True,
                "task": "",
                "test": "custom",
                "use_all_tasks": True,
            }
        },
        "IOL2": {
            "Test NTP and logging config": {
                "changed": False,
                "criteria": "",
                "diff": "",
                "exception": "Logging or NTP cfg incorrect",
                "failed": True,
                "result": "FAIL",
                "success": False,
                "task": "",
                "test": "custom",
                "use_all_tasks": True,
            }
        },
    }


# test_custom_function_text_use_all_tasks()


@skip_if_no_nornir
def test_custom_function_text_dictionary_return():
    """test case when custom function returns dictionary"""
    custom_function = """
def run(result):
    if "7.7.7.8" not in result.result:
        ret = {
            "exception": "Server 7.7.7.8 not in config",
            "result": "FAIL",
            "success": False,
            "description": "check ntp config"
        }
    else:
        ret = {
            "exception": "",
            "result": "PASS",
            "success": True
        }
    return ret
    """
    tests = [
        {
            "task": "show run | inc ntp",
            "name": "Test NTP config",
            "test": "custom",
            "function_text": custom_function,
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
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
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    # pprint.pprint(check_result)
    assert check_result == {
        "IOL1": {
            "Test NTP config": {
                "changed": False,
                "criteria": "",
                "diff": "",
                "exception": "",
                "failed": False,
                "result": "PASS",
                "success": True,
                "task": "show run | inc ntp",
                "test": "custom",
            }
        },
        "IOL2": {
            "Test NTP config": {
                "changed": False,
                "criteria": "",
                "description": "check ntp config",
                "diff": "",
                "exception": "Server 7.7.7.8 not in config",
                "failed": True,
                "result": "FAIL",
                "success": False,
                "task": "show run | inc ntp",
                "test": "custom",
            }
        },
    }


# test_custom_function_text_dictionary_return()


@skip_if_no_nornir
def test_custom_function_not_found_in_function_text():
    custom_function = """
def non_exist(result):
    pass
    """
    tests = [
        {
            "task": "show run | inc ntp",
            "name": "Test NTP config",
            "test": "custom",
            "function_text": custom_function,
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
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
    check_result = ResultSerializer(output, add_details=True, to_dict=False)
    # pprint.pprint(check_result, width=150)
    for item in check_result:
        assert item["result"] == "ERROR"
        assert "RuntimeError" in item["exception"]
        assert item["success"] == False
        assert item["failed"] == True


# test_custom_function_not_found_in_function_text()


@skip_if_no_nornir
def test_custom_function_returns_wrong_results_type():
    custom_function = """
def run(result):
    return set()
    """
    tests = [
        {
            "task": "show run | inc ntp",
            "name": "Test NTP config",
            "test": "custom",
            "function_text": custom_function,
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
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
    check_result = ResultSerializer(output, add_details=True, to_dict=False)
    # pprint.pprint(check_result, width=150)
    for item in check_result:
        assert item["failed"] == True
        assert "test function returned unsupported results type" in item["exception"]


# test_custom_function_returns_wrong_results_type()


@skip_if_no_nornir
def test_cerberus_dict():
    tests = [
        {
            "task": "interfaces MTU",
            "name": "Test {interface} MTU config",
            "test": "cerberus",
            "schema": {"mtu": {"type": "integer", "allowed": [1500]}},
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": {"interface": "Gig1", "mtu": 1200},
            "IOL2": {"mtu": 1500},
        },
        name="interfaces MTU",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    # pprint.pprint(check_result)
    assert check_result == {
        "IOL1": {
            "Test Gig1 MTU config": {
                "changed": False,
                "criteria": "",
                "diff": "",
                "exception": "{'mtu': ['unallowed value " "1200']}",
                "failed": True,
                "result": "FAIL",
                "success": False,
                "task": "interfaces MTU",
                "test": "cerberus",
            }
        },
        "IOL2": {
            "Test {interface} MTU config": {
                "changed": False,
                "criteria": "",
                "diff": "",
                "exception": None,
                "failed": False,
                "result": "PASS",
                "success": True,
                "task": "interfaces MTU",
                "test": "cerberus",
            }
        },
    }


# test_cerberus_dict()


@skip_if_no_nornir
def test_cerberus_list_of_dict():
    tests = [
        {
            "task": "interfaces MTU",
            "name": "Test {interface} MTU config",
            "test": "cerberus",
            "schema": {"mtu": {"type": "integer", "allowed": [1500]}},
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": [
                {"interface": "Gi1", "mtu": 1200},
                {"interface": "Gi2", "mtu": 1500},
                {"interface": "Gi2", "mtu": 1505},
            ],
            "IOL2": [{"interface": "Gi6", "mtu": 9600}],
        },
        name="interfaces MTU",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=False)
    # pprint.pprint(check_result)
    assert check_result == [
        {
            "changed": False,
            "criteria": "",
            "diff": "",
            "exception": "{'mtu': ['unallowed value 1200']}",
            "failed": True,
            "host": "IOL1",
            "name": "Test Gi1 MTU config",
            "result": "FAIL",
            "success": False,
            "task": "interfaces MTU",
            "test": "cerberus",
        },
        {
            "changed": False,
            "criteria": "",
            "diff": "",
            "exception": None,
            "failed": False,
            "host": "IOL1",
            "name": "Test Gi2 MTU config",
            "result": "PASS",
            "success": True,
            "task": "interfaces MTU",
            "test": "cerberus",
        },
        {
            "changed": False,
            "criteria": "",
            "diff": "",
            "exception": "{'mtu': ['unallowed value 1505']}",
            "failed": True,
            "host": "IOL1",
            "name": "Test Gi2 MTU config",
            "result": "FAIL",
            "success": False,
            "task": "interfaces MTU",
            "test": "cerberus",
        },
        {
            "changed": False,
            "criteria": "",
            "diff": "",
            "exception": "{'mtu': ['unallowed value 9600']}",
            "failed": True,
            "host": "IOL2",
            "name": "Test Gi6 MTU config",
            "result": "FAIL",
            "success": False,
            "task": "interfaces MTU",
            "test": "cerberus",
        },
    ]


# test_cerberus_list_of_dict()


@skip_if_no_nornir
def test_contains_check_remove_tasks_false():
    tests = [
        {
            "task": "show run | inc ntp",
            "name": "Test NTP config",
            "pattern": "ntp server 7.7.7.8",
            "test": "contains",
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=False)])
    output = nr_with_tests.run(
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
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    # pprint.pprint(check_result)
    assert check_result == {
        "IOL1": {
            "Test NTP config": {
                "changed": False,
                "criteria": "ntp server 7.7.7.8",
                "diff": "",
                "exception": None,
                "failed": False,
                "result": "PASS",
                "success": True,
                "task": "show run | inc ntp",
                "test": "contains",
            },
            "show run | inc ntp": {
                "changed": False,
                "diff": "",
                "exception": None,
                "failed": False,
                "result": "\n" "ntp server 7.7.7.8\n" "ntp server 7.7.7.7\n" "        ",
            },
        },
        "IOL2": {
            "Test NTP config": {
                "changed": False,
                "criteria": "ntp server 7.7.7.8",
                "diff": "",
                "exception": "Pattern not in output",
                "failed": True,
                "result": "FAIL",
                "success": False,
                "task": "show run | inc ntp",
                "test": "contains",
            },
            "show run | inc ntp": {
                "changed": False,
                "diff": "",
                "exception": None,
                "failed": False,
                "result": "\nntp server 7.7.7.7\n        ",
            },
        },
    }


# test_contains_check_remove_tasks_false()


@skip_if_no_nornir
def test_contains_check_calling_by_globals_name():
    tests = [
        {
            "task": "show run | inc ntp",
            "name": "Test NTP config",
            "pattern": "ntp server 7.7.7.8",
            "test": "ContainsTest",
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
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
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    # pprint.pprint(check_result)
    assert check_result == {
        "IOL1": {
            "Test NTP config": {
                "changed": False,
                "criteria": "ntp server 7.7.7.8",
                "diff": "",
                "exception": None,
                "failed": False,
                "result": "PASS",
                "success": True,
                "task": "show run | inc ntp",
                "test": "ContainsTest",
            }
        },
        "IOL2": {
            "Test NTP config": {
                "changed": False,
                "criteria": "ntp server 7.7.7.8",
                "diff": "",
                "exception": "Pattern not in output",
                "failed": True,
                "result": "FAIL",
                "success": False,
                "task": "show run | inc ntp",
                "test": "ContainsTest",
            }
        },
    }


# test_contains_check_calling_by_globals_name()


def _test_docs_sample_code():
    from nornir_salt.plugins.tasks import netmiko_send_commands

    tests = [
        {
            "name": "Test NTP config",
            "task": "show run | inc ntp",
            "test": "contains",
            "pattern": "ntp server 7.7.7.8",
        },
        {
            "name": "Test Logging config",
            "task": "show run | inc logging",
            "test": "contains_lines",
            "pattern": ["logging host 1.1.1.1", "logging host 1.1.1.2"],
        },
        {
            "name": "Test BGP peers state",
            "task": "show bgp ipv4 un summary",
            "test": "!contains_lines",
            "pattern": ["Idle", "Active", "Connect"],
        },
    ]

    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])

    # netmiko_send_commands maps commands to sub-task names
    results = nr_with_tests.run(
        task=netmiko_send_commands,
        commands=[
            "show run | inc ntp",
            "show run | inc logging",
            "show bgp ipv4 un summary",
        ],
    )

    results_dictionary = ResultSerializer(results, to_dict=False, add_details=False)

    pprint.pprint(results_dictionary)
    # should print something like:
    #
    # [{'host': 'IOL1', 'name': 'Test NTP config', 'result': 'PASS'},
    # {'host': 'IOL1', 'name': 'Test Logging config', 'result': 'PASS'},
    # {'host': 'IOL1', 'name': 'Test BGP peers state', 'result': 'FAIL'},
    # {'host': 'IOL2', 'name': 'Test NTP config', 'result': 'PASS'},
    # {'host': 'IOL2', 'name': 'Test Logging config', 'result': 'PASS'},
    # {'host': 'IOL2', 'name': 'Test BGP peers state', 'result': 'PASS'}]


# _test_docs_sample_code()


@skip_if_no_nornir
def test_contains_check_failed_only_to_dict():
    tests = [
        {
            "task": "show run | inc ntp",
            "name": "Test NTP config",
            "pattern": "ntp server 7.7.7.8",
            "test": "contains",
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors(
        [TestsProcessor(tests, remove_tasks=True, failed_only=True)]
    )
    output = nr_with_tests.run(
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
    check_result_to_dict = ResultSerializer(output, add_details=True, to_dict=True)
    check_result_to_list = ResultSerializer(output, add_details=True, to_dict=False)
    # pprint.pprint(check_result_to_list)
    assert check_result_to_dict == {
        "IOL2": {
            "Test NTP config": {
                "changed": False,
                "criteria": "ntp server 7.7.7.8",
                "diff": "",
                "exception": "Pattern not in output",
                "failed": True,
                "result": "FAIL",
                "success": False,
                "task": "show run | inc ntp",
                "test": "contains",
            }
        }
    }
    assert check_result_to_list == [
        {
            "changed": False,
            "criteria": "ntp server 7.7.7.8",
            "diff": "",
            "exception": "Pattern not in output",
            "failed": True,
            "host": "IOL2",
            "name": "Test NTP config",
            "result": "FAIL",
            "success": False,
            "task": "show run | inc ntp",
            "test": "contains",
        }
    ]


# test_contains_check_failed_only()


@skip_if_no_nornir
def test_custom_function_text_failed_only_ret_is_list():
    custom_function = """
def run(result):
    ret =[]
    if "7.7.7.8" not in result.result:
        ret.append({
            "exception": "Server 7.7.7.8 not in config",
            "result": "FAIL",
            "success": False,
            "description": "check ntp config"
        })
    else:
        ret.append({
            "exception": "",
            "result": "PASS",
            "success": True
        })
    return ret
    """
    tests = [
        {
            "task": "show run | inc ntp",
            "name": "Test NTP config",
            "test": "custom",
            "function_text": custom_function,
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors(
        [TestsProcessor(tests, remove_tasks=True, failed_only=True)]
    )
    output = nr_with_tests.run(
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
    check_result_to_dict = ResultSerializer(output, add_details=True, to_dict=True)
    check_result_to_list = ResultSerializer(output, add_details=True, to_dict=False)
    # pprint.pprint(check_result_to_dict)
    # pprint.pprint(check_result_to_list)
    assert check_result_to_dict == {
        "IOL2": {
            "Test NTP config": {
                "changed": False,
                "criteria": "",
                "description": "check ntp config",
                "diff": "",
                "exception": "Server 7.7.7.8 not in config",
                "failed": True,
                "result": "FAIL",
                "success": False,
                "task": "show run | inc ntp",
                "test": "custom",
            }
        }
    }
    assert check_result_to_list == [
        {
            "changed": False,
            "criteria": "",
            "description": "check ntp config",
            "diff": "",
            "exception": "Server 7.7.7.8 not in config",
            "failed": True,
            "host": "IOL2",
            "name": "Test NTP config",
            "result": "FAIL",
            "success": False,
            "task": "show run | inc ntp",
            "test": "custom",
        }
    ]


# test_custom_function_text_failed_only_ret_is_list()


@skip_if_no_nornir
def test_contains_custom_err_msg():
    tests = [
        {
            "task": "show run | inc ntp",
            "name": "Test NTP config",
            "pattern": "ntp server 7.7.7.8",
            "test": "contains",
            "err_msg": "NTP server 7.7.7.8 not in config",
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
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
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    # pprint.pprint(check_result)
    assert check_result == {
        "IOL1": {
            "Test NTP config": {
                "changed": False,
                "criteria": "ntp server 7.7.7.8",
                "diff": "",
                "exception": None,
                "failed": False,
                "result": "PASS",
                "success": True,
                "task": "show run | inc ntp",
                "test": "contains",
            }
        },
        "IOL2": {
            "Test NTP config": {
                "changed": False,
                "criteria": "ntp server 7.7.7.8",
                "diff": "",
                "exception": "NTP server 7.7.7.8 not in config",
                "failed": True,
                "result": "FAIL",
                "success": False,
                "task": "show run | inc ntp",
                "test": "contains",
            }
        },
    }


# test_contains_custom_err_msg()


def test_eval_function_simple_expression():
    tests = [
        {
            "task": "show run | inc ntp",
            "name": "Test NTP config",
            "expr": "'7.7.7.8' in result",
            "test": "eval",
            "err_msg": "NTP server 7.7.7.8 not in config",
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
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
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    # pprint.pprint(check_result)
    assert check_result == {
        "IOL1": {
            "Test NTP config": {
                "changed": False,
                "criteria": "",
                "diff": "",
                "exception": None,
                "failed": False,
                "result": "PASS",
                "success": True,
                "task": "show run | inc ntp",
                "test": "eval",
            }
        },
        "IOL2": {
            "Test NTP config": {
                "changed": False,
                "criteria": "",
                "diff": "",
                "exception": "NTP server 7.7.7.8 not in config",
                "failed": True,
                "result": "FAIL",
                "success": False,
                "task": "show run | inc ntp",
                "test": "eval",
            }
        },
    }


# test_eval_function_simple_expression()


def test_eval_function_assert_statement():
    tests = [
        {
            "task": "show run | inc ntp",
            "name": "Test NTP config",
            "expr": "assert '7.7.7.8' in result, 'NTP server 7.7.7.8 not in config'",
            "test": "eval",
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
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
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    # pprint.pprint(check_result)
    assert check_result == {
        "IOL1": {
            "Test NTP config": {
                "changed": False,
                "criteria": "",
                "diff": "",
                "exception": None,
                "failed": False,
                "result": "PASS",
                "success": True,
                "task": "show run | inc ntp",
                "test": "eval",
            }
        },
        "IOL2": {
            "Test NTP config": {
                "changed": False,
                "criteria": "",
                "diff": "",
                "exception": "NTP server 7.7.7.8 not in config",
                "failed": True,
                "result": "FAIL",
                "success": False,
                "task": "show run | inc ntp",
                "test": "eval",
            }
        },
    }


# test_eval_function_assert_statement()


@skip_if_no_nornir
def test_eval_when_tests_are_list_of_lists():
    tests = [
        [
            "show run | inc ntp",
            "eval",
            "assert 'ntp server 7.7.7.8' in result, 'NTP config is wrong'",
            "test ntp configuration",
        ],
        ["show run | inc ntp", "eval", "'7.7.7.7' in result"],
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors(
        [TestsProcessor(tests, remove_tasks=True, build_per_host_tests=True)]
    )
    output = nr_with_tests.run(
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
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    # pprint.pprint(check_result, width=150)
    assert check_result == {
        "IOL1": {
            "show run | inc ntp eval ..": {
                "changed": False,
                "criteria": "",
                "diff": "",
                "exception": None,
                "failed": False,
                "result": "PASS",
                "success": True,
                "task": "show run | inc ntp",
                "test": "eval",
            },
            "test ntp configuration": {
                "changed": False,
                "criteria": "",
                "diff": "",
                "exception": None,
                "failed": False,
                "result": "PASS",
                "success": True,
                "task": "show run | inc ntp",
                "test": "eval",
            },
        },
        "IOL2": {
            "show run | inc ntp eval ..": {
                "changed": False,
                "criteria": "",
                "diff": "",
                "exception": None,
                "failed": False,
                "result": "PASS",
                "success": True,
                "task": "show run | inc ntp",
                "test": "eval",
            },
            "test ntp configuration": {
                "changed": False,
                "criteria": "",
                "diff": "",
                "exception": "NTP config is wrong",
                "failed": True,
                "result": "FAIL",
                "success": False,
                "task": "show run | inc ntp",
                "test": "eval",
            },
        },
    }


# test_eval_when_tests_are_list_of_lists()


def test_eval_kwargs_to_globals_vars_usage():
    tests = [
        {
            "test": "eval",
            "task": "show run | inc logging",
            "name": "Test Syslog config",
            "expr": "all(map(lambda line: line in result, lines))",
            "globs": {"lines": ["logging host 1.1.1.1", "logging host 2.2.2.2"]},
            "err_msg": "Syslog config is wrong",
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": """
logging host 1.1.1.1
logging host 2.2.2.2
        """,
            "IOL2": """
logging host 3.3.3.3
        """,
        },
        name="show run | inc logging",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    # pprint.pprint(check_result)
    assert check_result == {
        "IOL1": {
            "Test Syslog config": {
                "changed": False,
                "criteria": "",
                "diff": "",
                "exception": None,
                "failed": False,
                "result": "PASS",
                "success": True,
                "task": "show run | inc logging",
                "test": "eval",
            }
        },
        "IOL2": {
            "Test Syslog config": {
                "changed": False,
                "criteria": "",
                "diff": "",
                "exception": "Syslog config is wrong",
                "failed": True,
                "result": "FAIL",
                "success": False,
                "task": "show run | inc logging",
                "test": "eval",
            }
        },
    }


# test_eval_kwargs_to_globals_vars_usage()


def test_path_with_eval():
    tests = [
        {
            "test": "eval",
            "task": "show run | inc logging",
            "name": "Test Syslog config",
            "path": "config.system.syslog.*.remote_host",
            "expr": "result == '1.1.1.1'",
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": {
                "config": {
                    "system": {
                        "syslog": [
                            {"remote_host": "1.1.1.1"},
                            {"remote_host": "1.1.1.1"},
                        ]
                    }
                }
            },
            "IOL2": {"config": {"system": {"syslog": [{"remote_host": "1.1.1.2"}]}}},
        },
        name="show run | inc logging",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=False)
    # pprint.pprint(check_result)
    assert check_result == [
        {
            "changed": False,
            "criteria": "",
            "diff": "",
            "exception": None,
            "failed": False,
            "host": "IOL1",
            "name": "Test Syslog config",
            "result": "PASS",
            "success": True,
            "task": "show run | inc logging",
            "test": "eval",
        },
        {
            "changed": False,
            "criteria": "",
            "diff": "",
            "exception": "Expression evaluated to False",
            "failed": True,
            "host": "IOL2",
            "name": "Test Syslog config",
            "result": "FAIL",
            "success": False,
            "task": "show run | inc logging",
            "test": "eval",
        },
    ]


# test_path_with_eval()


def test_path_with_equal():
    tests = [
        {
            "test": "equal",
            "task": "show run | inc logging",
            "name": "Test Syslog config",
            "path": "config.system.syslog.*",
            "pattern": {"remote_host": "1.1.1.1"},
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": {
                "config": {
                    "system": {
                        "syslog": [
                            {"remote_host": "1.1.1.1"},
                            {"remote_host": "1.1.1.3"},
                        ]
                    }
                }
            },
            "IOL2": {"config": {"system": {"syslog": [{"remote_host": "1.1.1.2"}]}}},
        },
        name="show run | inc logging",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=False)
    # pprint.pprint(check_result)
    assert check_result == [
        {
            "changed": False,
            "criteria": "",
            "diff": "",
            "exception": "Pattern and output not equal",
            "failed": True,
            "host": "IOL1",
            "name": "Test Syslog config",
            "result": "FAIL",
            "success": False,
            "task": "show run | inc logging",
            "test": "equal",
        },
        {
            "changed": False,
            "criteria": "",
            "diff": "",
            "exception": "Pattern and output not equal",
            "failed": True,
            "host": "IOL2",
            "name": "Test Syslog config",
            "result": "FAIL",
            "success": False,
            "task": "show run | inc logging",
            "test": "equal",
        },
    ]


# test_path_with_equal()


def test_path_with_contains():
    tests = [
        {
            "test": "contains",
            "task": "show run | inc logging",
            "name": "Test Syslog config",
            "path": "config.system.syslog.*",
            "pattern": "remote_host",
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": {
                "config": {
                    "system": {
                        "syslog": [
                            {"remote_host": "1.1.1.1"},
                            {"remote_host": "1.1.1.3"},
                        ]
                    }
                }
            },
            "IOL2": {
                "config": {"system": {"syslog": [{"remote_host_bla": "1.1.1.2"}]}}
            },
        },
        name="show run | inc logging",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=False)
    # pprint.pprint(check_result)
    assert check_result == [
        {
            "changed": False,
            "criteria": "",
            "diff": "",
            "exception": None,
            "failed": False,
            "host": "IOL1",
            "name": "Test Syslog config",
            "pattern": "remote_host",
            "result": "PASS",
            "success": True,
            "task": "show run | inc logging",
            "test": "contains",
        },
        {
            "changed": False,
            "criteria": "remote_host",
            "diff": "",
            "exception": "Pattern not in output",
            "failed": True,
            "host": "IOL2",
            "name": "Test Syslog config",
            "result": "FAIL",
            "success": False,
            "task": "show run | inc logging",
            "test": "contains",
        },
    ]


# test_path_with_contains()


def test_path_with_eval_assert():
    tests = [
        {
            "test": "eval",
            "task": "show run interface",
            "name": "Test MTU config",
            "path": "interfaces.*",
            "expr": "assert result['mtu'] > 9000, '{} MTU less then 9000'.format(result['interface'])",
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": {
                "interfaces": [
                    {"interface": "Gi1", "mtu": 1500},
                    {"interface": "Gi2", "mtu": 9200},
                ]
            },
            "IOL2": {"interfaces": [{"interface": "Eth1/9", "mtu": 9600}]},
        },
        name="show run interface",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=False)
    # pprint.pprint(check_result)
    assert check_result == [
        {
            "changed": False,
            "criteria": "",
            "diff": "",
            "exception": "Gi1 MTU less then 9000",
            "failed": True,
            "host": "IOL1",
            "name": "Test MTU config",
            "result": "FAIL",
            "success": False,
            "task": "show run interface",
            "test": "eval",
        },
        {
            "changed": False,
            "criteria": "",
            "diff": "",
            "exception": None,
            "failed": False,
            "host": "IOL2",
            "name": "Test MTU config",
            "result": "PASS",
            "success": True,
            "task": "show run interface",
            "test": "eval",
        },
    ]


# test_path_with_eval_assert()


def test_path_with_eval_list_of_lists():
    tests = [
        {
            "test": "eval",
            "task": "show ospf neighbors",
            "name": "Test OSPF peers",
            "path": "ospf_processes.*.peers.*",
            "expr": "assert result['state'] == 'up', '{} peer is {}'.format(result['peer'], result['state'])",
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": {
                "ospf_processes": [
                    {
                        "pid": 1,
                        "peers": [
                            {"state": "up", "peer": "1.1.1.1"},
                            {"state": "init", "peer": "1.1.1.2"},
                        ],
                    },
                    {"pid": 2, "peers": [{"state": "up", "peer": "3.3.3.3"}]},
                ]
            },
            "IOL2": {
                "ospf_processes": [
                    {"pid": 3, "peers": [{"state": "init", "peer": "1.1.1.2"}]}
                ]
            },
        },
        name="show ospf neighbors",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=False)
    # pprint.pprint(check_result)
    assert check_result == [
        {
            "changed": False,
            "criteria": "",
            "diff": "",
            "exception": "1.1.1.2 peer is init",
            "failed": True,
            "host": "IOL1",
            "name": "Test OSPF peers",
            "result": "FAIL",
            "success": False,
            "task": "show ospf neighbors",
            "test": "eval",
        },
        {
            "changed": False,
            "criteria": "",
            "diff": "",
            "exception": "1.1.1.2 peer is init",
            "failed": True,
            "host": "IOL2",
            "name": "Test OSPF peers",
            "result": "FAIL",
            "success": False,
            "task": "show ospf neighbors",
            "test": "eval",
        },
    ]


# test_path_with_eval_list_of_lists()


def test_path_with_eval_list_of_lists_report_all():
    tests = [
        {
            "test": "eval",
            "task": "show ospf neighbors",
            "name": "Test OSPF peers",
            "path": "ospf_processes.*.peers.*",
            "expr": "assert result['state'] == 'up', '{} peer is {}'.format(result['peer'], result['state'])",
            "report_all": True,
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": {
                "ospf_processes": [
                    {
                        "pid": 1,
                        "peers": [
                            {"state": "up", "peer": "1.1.1.1"},
                            {"state": "init", "peer": "1.1.1.2"},
                        ],
                    },
                    {"pid": 2, "peers": [{"state": "up", "peer": "3.3.3.3"}]},
                ]
            },
            "IOL2": {
                "ospf_processes": [
                    {"pid": 3, "peers": [{"state": "init", "peer": "1.1.1.2"}]}
                ]
            },
        },
        name="show ospf neighbors",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=False)
    # pprint.pprint(check_result)
    assert check_result == [
        {
            "changed": False,
            "criteria": "",
            "diff": "",
            "exception": None,
            "failed": False,
            "host": "IOL1",
            "name": "Test OSPF peers",
            "result": "PASS",
            "success": True,
            "task": "show ospf neighbors",
            "test": "eval",
        },
        {
            "changed": False,
            "criteria": "",
            "diff": "",
            "exception": "1.1.1.2 peer is init",
            "failed": True,
            "host": "IOL1",
            "name": "Test OSPF peers",
            "result": "FAIL",
            "success": False,
            "task": "show ospf neighbors",
            "test": "eval",
        },
        {
            "changed": False,
            "criteria": "",
            "diff": "",
            "exception": None,
            "failed": False,
            "host": "IOL1",
            "name": "Test OSPF peers",
            "result": "PASS",
            "success": True,
            "task": "show ospf neighbors",
            "test": "eval",
        },
        {
            "changed": False,
            "criteria": "",
            "diff": "",
            "exception": "1.1.1.2 peer is init",
            "failed": True,
            "host": "IOL2",
            "name": "Test OSPF peers",
            "result": "FAIL",
            "success": False,
            "task": "show ospf neighbors",
            "test": "eval",
        },
    ]


# test_path_with_eval_list_of_lists_report_all()


@skip_if_no_nornir
def test_contains_count_ge_check():
    tests = [
        {
            "task": "show run | inc ntp",
            "name": "Test NTP config",
            "pattern": "ntp server 7.7.7.",
            "test": "contains",
            "count_ge": 2,
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": """
ntp server 7.7.7.8
ntp server 7.7.7.7
ntp server 7.7.7.6
        """,
            "IOL2": """
ntp server 7.7.7.7
        """,
        },
        name="show run | inc ntp",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    pprint.pprint(check_result)
    assert check_result == {
        "IOL1": {
            "Test NTP config": {
                "changed": False,
                "count_ge": 2,
                "criteria": "ntp server 7.7.7.",
                "diff": "",
                "exception": None,
                "failed": False,
                "result": "PASS",
                "success": True,
                "task": "show run | inc ntp",
                "test": "contains",
            }
        },
        "IOL2": {
            "Test NTP config": {
                "changed": False,
                "count_ge": 2,
                "criteria": "ntp server 7.7.7.",
                "diff": "",
                "exception": "Pattern not in output greater or " "equal 2 times",
                "failed": True,
                "result": "FAIL",
                "success": False,
                "task": "show run | inc ntp",
                "test": "contains",
            }
        },
    }


@skip_if_no_nornir
def test_contains_count_ge_check_revert():
    tests = [
        {
            "task": "show run | inc ntp",
            "name": "Test NTP config",
            "pattern": "ntp server 7.7.7.",
            "test": "contains",
            "count_ge": 2,
            "revert": True,
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": """
ntp server 7.7.7.8
ntp server 7.7.7.7
ntp server 7.7.7.6
        """,
            "IOL2": """
ntp server 7.7.7.7
        """,
        },
        name="show run | inc ntp",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    pprint.pprint(check_result)
    assert check_result == {
        "IOL1": {
            "Test NTP config": {
                "changed": False,
                "count_ge": 2,
                "criteria": "ntp server 7.7.7.",
                "diff": "",
                "exception": "Pattern in output greater or equal " "2 times",
                "failed": True,
                "result": "FAIL",
                "success": False,
                "task": "show run | inc ntp",
                "test": "contains",
            }
        },
        "IOL2": {
            "Test NTP config": {
                "changed": False,
                "count_ge": 2,
                "criteria": "ntp server 7.7.7.",
                "diff": "",
                "exception": None,
                "failed": False,
                "result": "PASS",
                "success": True,
                "task": "show run | inc ntp",
                "test": "contains",
            }
        },
    }


@skip_if_no_nornir
def test_contains_count_le_check():
    tests = [
        {
            "task": "show run | inc ntp",
            "name": "Test NTP config",
            "pattern": "ntp server 7.7.7.",
            "test": "contains",
            "count_le": 2,
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": """
ntp server 7.7.7.8
ntp server 7.7.7.7
ntp server 7.7.7.6
        """,
            "IOL2": """
ntp server 7.7.7.7
        """,
        },
        name="show run | inc ntp",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    pprint.pprint(check_result)
    assert check_result == {
        "IOL1": {
            "Test NTP config": {
                "changed": False,
                "count_le": 2,
                "criteria": "ntp server 7.7.7.",
                "diff": "",
                "exception": "Pattern not in output lower or " "equal 2 times",
                "failed": True,
                "result": "FAIL",
                "success": False,
                "task": "show run | inc ntp",
                "test": "contains",
            }
        },
        "IOL2": {
            "Test NTP config": {
                "changed": False,
                "count_le": 2,
                "criteria": "ntp server 7.7.7.",
                "diff": "",
                "exception": None,
                "failed": False,
                "result": "PASS",
                "success": True,
                "task": "show run | inc ntp",
                "test": "contains",
            }
        },
    }


@skip_if_no_nornir
def test_contains_count_le_check_revert():
    tests = [
        {
            "task": "show run | inc ntp",
            "name": "Test NTP config",
            "pattern": "ntp server 7.7.7.",
            "test": "contains",
            "count_le": 2,
            "revert": True,
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": """
ntp server 7.7.7.8
ntp server 7.7.7.7
ntp server 7.7.7.6
        """,
            "IOL2": """
ntp server 7.7.7.7
        """,
        },
        name="show run | inc ntp",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    pprint.pprint(check_result)
    assert check_result == {
        "IOL1": {
            "Test NTP config": {
                "changed": False,
                "count_le": 2,
                "criteria": "ntp server 7.7.7.",
                "diff": "",
                "exception": None,
                "failed": False,
                "result": "PASS",
                "success": True,
                "task": "show run | inc ntp",
                "test": "contains",
            }
        },
        "IOL2": {
            "Test NTP config": {
                "changed": False,
                "count_le": 2,
                "criteria": "ntp server 7.7.7.",
                "diff": "",
                "exception": "Pattern in output lower or equal 2 " "times",
                "failed": True,
                "result": "FAIL",
                "success": False,
                "task": "show run | inc ntp",
                "test": "contains",
            }
        },
    }


def grouped_task_for_test_jinja2_suite(task):
    # run first subtask
    task.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": """
Interface description Circuit CX54DF323
Interface mtu 1500
Interface line protocol is up
Interface admin state - admin up
        """
        },
        name="show interface Eth1",
    )
    # run second subtask
    task.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": """
Interface description OOB Connection
Interface mtu 9200
Interface line protocol is up
Interface admin state - admin up
        """
        },
        name="show interface Eth2",
    )
    # run third subtask
    task.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": "Version: xe1.2.3.4",
            "IOL2": "Version: xe4.3.2.1",
        },
        name="show version",
    )
    return Result(host=task.host)


@skip_if_no_nornir
def test_jinja2_suite():
    """
    IOL1 inventory has this data:
    data:
      interfaces:
        - name: Eth1
          description: Circuit CX54DF323
          mtu: 1500
          line: line protocol is up
          admin: admin up
        - name: Eth2
          description: OOB Connection
          mtu: 9200
          line: line protocol is up
          admin: admin up
      version: xe1.2.3.4
    IOL2 inventory has this data:
    data:
      version: xe1.2.3.4
    """
    tests = [
        """
- task: "show version"
  name: "Test {{ host.name }} version"
  pattern: "{{ host.version }}"
  test: contains
{% for interface in host.interfaces %}
- task: "show interface {{ interface.name }}"
  name: "Test {{ host.name }} interface {{ interface.name }} MTU"
  test: contains
  pattern: {{ interface.mtu }}
- task: "show interface {{ interface.name }}"
  name: "Test {{ host.name }} interface {{ interface.name }} description"
  test: contains
  pattern: {{ interface.description }}
{% endfor %}
    """,
        """
{% for interface in host.interfaces %}
- task: "show interface {{ interface.name }}"
  name: "Test {{ host.name }} interface {{ interface.name }} status"
  test: contains_lines
  pattern: 
  - {{ interface.line }}
  - {{ interface.admin }}
{% endfor %}
    """,
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors(
        [TestsProcessor(tests, remove_tasks=True, build_per_host_tests=True)]
    )
    output = nr_with_tests.run(task=grouped_task_for_test_jinja2_suite)
    res = ResultSerializer(output, add_details=True, to_dict=True)
    pprint.pprint(res, width=150)
    assert res["IOL1"]["Test IOL1 interface Eth1 MTU"]["result"] == "PASS"
    assert res["IOL1"]["Test IOL1 interface Eth2 MTU"]["result"] == "PASS"
    assert res["IOL1"]["Test IOL1 interface Eth1 description"]["result"] == "PASS"
    assert res["IOL1"]["Test IOL1 interface Eth2 description"]["result"] == "PASS"
    assert res["IOL1"]["Test IOL1 interface Eth1 status"]["result"] == "PASS"
    assert res["IOL1"]["Test IOL1 interface Eth2 status"]["result"] == "PASS"
    assert res["IOL1"]["Test IOL1 version"]["result"] == "PASS"
    assert res["IOL2"]["Test IOL2 version"]["result"] == "FAIL"


@skip_if_no_nornir
def test_jinja2_suite_tests_data():
    """
    This tes add tests_data to testsprovessor, that data used to render tests suite
    """
    tests_data = {
        "IOL1": {
            "interfaces": [
                {
                    "name": "Eth1",
                    "description": "Circuit CX54DF323",
                    "mtu": 1500,
                    "line": "line protocol is up",
                    "admin": "admin up",
                },
                {
                    "name": "Eth2",
                    "description": "OOB Connection",
                    "mtu": 9200,
                    "line": "line protocol is up",
                    "admin": "admin up",
                },
            ],
            "version": "xe1.2.3.4",
        },
        "IOL2": {"version": "xe1.2.3.4"},
    }
    tests = [
        """
- task: "show version"
  name: "Test {{ host.name }} version"
  pattern: "{{ tests_data[host.name]['version'] }}"
  test: contains
{% if host.name == 'IOL1' %}
{% for interface in tests_data[host.name]['interfaces'] %}
- task: "show interface {{ interface.name }}"
  name: "Test {{ host.name }} interface {{ interface.name }} MTU"
  test: contains
  pattern: {{ interface.mtu }}
- task: "show interface {{ interface.name }}"
  name: "Test {{ host.name }} interface {{ interface.name }} description"
  test: contains
  pattern: {{ interface.description }}
{% endfor %}
{% endif %}
    """,
        """
{% if host.name == 'IOL1' %}
{% for interface in tests_data[host.name]['interfaces'] %}
- task: "show interface {{ interface.name }}"
  name: "Test {{ host.name }} interface {{ interface.name }} status"
  test: contains_lines
  pattern: 
  - {{ interface.line }}
  - {{ interface.admin }}
{% endfor %}
{% endif %}
    """,
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors(
        [
            TestsProcessor(
                tests,
                remove_tasks=True,
                build_per_host_tests=True,
                tests_data=tests_data,
            )
        ]
    )
    output = nr_with_tests.run(task=grouped_task_for_test_jinja2_suite)
    res = ResultSerializer(output, add_details=True, to_dict=True)
    pprint.pprint(res, width=150)
    assert res["IOL1"]["Test IOL1 interface Eth1 MTU"]["result"] == "PASS"
    assert res["IOL1"]["Test IOL1 interface Eth2 MTU"]["result"] == "PASS"
    assert res["IOL1"]["Test IOL1 interface Eth1 description"]["result"] == "PASS"
    assert res["IOL1"]["Test IOL1 interface Eth2 description"]["result"] == "PASS"
    assert res["IOL1"]["Test IOL1 interface Eth1 status"]["result"] == "PASS"
    assert res["IOL1"]["Test IOL1 interface Eth2 status"]["result"] == "PASS"
    assert res["IOL1"]["Test IOL1 version"]["result"] == "PASS"
    assert res["IOL2"]["Test IOL2 version"]["result"] == "FAIL"
