"""
Comprehensive tests for TestsProcessor plugin.

These tests cover edge cases, aliases, and code paths not covered by the
existing test_TestsProcessor_plugin.py test suite.
"""

import logging
import os
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

from nornir_salt.plugins.functions import ResultSerializer
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
    """Initiate nornir by calling InitNornir()"""
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


# ======================================================================
# Test aliases: ncontains, ncontains_re, nequal, ncontains_lines,
#   ncontains_lines_re, contains_lines_re
# ======================================================================


@skip_if_no_nornir
def test_ncontains_alias():
    """Test that 'ncontains' alias works as inverted contains."""
    tests = [
        {
            "task": "show run | inc ntp",
            "name": "Test NTP absent",
            "pattern": "ntp server 7.7.7.8",
            "test": "ncontains",
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": "ntp server 7.7.7.8\nntp server 7.7.7.7",
            "IOL2": "ntp server 7.7.7.7",
        },
        name="show run | inc ntp",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    # IOL1 has the pattern so ncontains should FAIL, IOL2 does not so PASS
    assert check_result["IOL1"]["Test NTP absent"]["result"] == "FAIL"
    assert check_result["IOL1"]["Test NTP absent"]["exception"] == "Pattern in output"
    assert check_result["IOL2"]["Test NTP absent"]["result"] == "PASS"
    assert check_result["IOL2"]["Test NTP absent"]["exception"] is None


@skip_if_no_nornir
def test_ncontains_re_alias():
    """Test that 'ncontains_re' alias works as inverted regex contains."""
    tests = [
        {
            "task": "show run | inc ntp",
            "name": "Test NTP regex absent",
            "pattern": r"ntp server 7\.7\.7\.\d+",
            "test": "ncontains_re",
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": "ntp server 7.7.7.8",
            "IOL2": "no ntp configured",
        },
        name="show run | inc ntp",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    assert check_result["IOL1"]["Test NTP regex absent"]["result"] == "FAIL"
    assert (
        check_result["IOL1"]["Test NTP regex absent"]["exception"]
        == "Regex pattern in output"
    )
    assert check_result["IOL2"]["Test NTP regex absent"]["result"] == "PASS"


@skip_if_no_nornir
def test_nequal_alias():
    """Test that 'nequal' alias works as inverted equal."""
    tests = [
        {
            "task": "show version",
            "name": "Check version differs",
            "pattern": "Version A",
            "test": "nequal",
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": "Version A",
            "IOL2": "Version B",
        },
        name="show version",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    # IOL1 is equal so nequal should FAIL
    assert check_result["IOL1"]["Check version differs"]["result"] == "FAIL"
    assert (
        check_result["IOL1"]["Check version differs"]["exception"]
        == "Pattern and output equal"
    )
    # IOL2 is not equal so nequal should PASS
    assert check_result["IOL2"]["Check version differs"]["result"] == "PASS"


@skip_if_no_nornir
def test_ncontains_lines_alias():
    """Test that 'ncontains_lines' alias works as inverted contains_lines."""
    tests = [
        {
            "task": "show run | inc logging",
            "name": "Test no bad logging",
            "pattern": ["logging host 9.9.9.9", "logging host 8.8.8.8"],
            "test": "ncontains_lines",
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": "logging host 1.1.1.1\nlogging host 2.2.2.2",
            "IOL2": "logging host 9.9.9.9\nlogging host 8.8.8.8",
        },
        name="show run | inc logging",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    # IOL1 does not have the bad lines - PASS
    assert check_result["IOL1"]["Test no bad logging"]["result"] == "PASS"
    # IOL2 has the bad lines - FAIL
    assert check_result["IOL2"]["Test no bad logging"]["result"] == "FAIL"


@skip_if_no_nornir
def test_contains_lines_re_alias():
    """Test 'contains_lines_re' alias - regex line matching."""
    tests = [
        {
            "task": "show run | inc ntp",
            "name": "Test NTP lines regex",
            "pattern": [r"ntp server \d+\.\d+\.\d+\.8", r"ntp server \d+\.\d+\.\d+\.7"],
            "test": "contains_lines_re",
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": "ntp server 7.7.7.8\nntp server 7.7.7.7",
            "IOL2": "ntp server 7.7.7.7",
        },
        name="show run | inc ntp",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    assert check_result["IOL1"]["Test NTP lines regex"]["result"] == "PASS"
    assert check_result["IOL2"]["Test NTP lines regex"]["result"] == "FAIL"
    assert (
        "Regex pattern not in output"
        in check_result["IOL2"]["Test NTP lines regex"]["exception"]
    )


@skip_if_no_nornir
def test_ncontains_lines_re_alias():
    """Test '!contains_lines_re' alias - inverted regex line matching."""
    tests = [
        {
            "task": "show run | inc ntp",
            "name": "Test no NTP lines regex",
            "pattern": [r"ntp server 7\.7\.7\.8"],
            "test": "!contains_lines_re",
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": "ntp server 7.7.7.8",
            "IOL2": "no ntp configured",
        },
        name="show run | inc ntp",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    # IOL1 has the regex match, so inverted should FAIL
    assert check_result["IOL1"]["Test no NTP lines regex"]["result"] == "FAIL"
    # IOL2 doesn't match, so inverted should PASS
    assert check_result["IOL2"]["Test no NTP lines regex"]["result"] == "PASS"


# ======================================================================
# ContainsTest edge cases
# ======================================================================


@skip_if_no_nornir
def test_contains_count_ge_and_count_le_combined():
    """Test count_ge and count_le used together for range check."""
    tests = [
        {
            "task": "show ntp",
            "name": "Test NTP count range",
            "pattern": "ntp server",
            "test": "contains",
            "count_ge": 2,
            "count_le": 4,
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": "ntp server 1\nntp server 2\nntp server 3",  # 3 - in range
            "IOL2": "ntp server 1",  # 1 - below range
        },
        name="show ntp",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    assert check_result["IOL1"]["Test NTP count range"]["result"] == "PASS"
    assert check_result["IOL2"]["Test NTP count range"]["result"] == "FAIL"
    assert (
        "between 2 and 4 times"
        in check_result["IOL2"]["Test NTP count range"]["exception"]
    )


@skip_if_no_nornir
def test_contains_count_ge_and_count_le_combined_revert():
    """Test count_ge and count_le combined with revert - should invert results."""
    tests = [
        {
            "task": "show ntp",
            "name": "Test NTP count range revert",
            "pattern": "ntp server",
            "test": "contains",
            "count_ge": 2,
            "count_le": 4,
            "revert": True,
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": "ntp server 1\nntp server 2\nntp server 3",  # 3 - in range
            "IOL2": "ntp server 1",  # 1 - below range
        },
        name="show ntp",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    # IOL1 was in range, reverted should FAIL
    assert check_result["IOL1"]["Test NTP count range revert"]["result"] == "FAIL"
    assert (
        "between 2 and 4 times"
        in check_result["IOL1"]["Test NTP count range revert"]["exception"]
    )
    # IOL2 was out of range, reverted should PASS
    assert check_result["IOL2"]["Test NTP count range revert"]["result"] == "PASS"


@skip_if_no_nornir
def test_contains_with_use_re_and_err_msg():
    """Test contains_re combined with custom err_msg."""
    tests = [
        {
            "task": "show ntp",
            "name": "Test NTP regex err_msg",
            "pattern": r"ntp server 7\.7\.7\.8",
            "test": "contains_re",
            "err_msg": "NTP 7.7.7.8 regex match failed",
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": "ntp server 7.7.7.8",
            "IOL2": "no ntp",
        },
        name="show ntp",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    assert check_result["IOL1"]["Test NTP regex err_msg"]["result"] == "PASS"
    assert check_result["IOL2"]["Test NTP regex err_msg"]["result"] == "FAIL"
    assert (
        check_result["IOL2"]["Test NTP regex err_msg"]["exception"]
        == "NTP 7.7.7.8 regex match failed"
    )


@skip_if_no_nornir
def test_contains_pattern_criteria_truncation():
    """Test that long patterns get truncated to 24 chars in criteria field."""
    long_pattern = "ntp server 7.7.7.8 configured with authentication key 12345"
    tests = [
        {
            "task": "show ntp",
            "name": "Test long pattern criteria",
            "pattern": long_pattern,
            "test": "contains",
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": long_pattern,
            "IOL2": "short",
        },
        name="show ntp",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    # Criteria should be truncated to first 24 chars
    assert len(check_result["IOL1"]["Test long pattern criteria"]["criteria"]) == 24
    assert (
        check_result["IOL1"]["Test long pattern criteria"]["criteria"]
        == long_pattern[:24]
    )


# ======================================================================
# ContainsLinesTest edge cases
# ======================================================================


@skip_if_no_nornir
def test_contains_lines_with_multiline_string_pattern():
    """Test contains_lines with a multiline string as pattern (splitlines)."""
    tests = [
        {
            "task": "show run | inc logging",
            "name": "Test logging lines string",
            "pattern": "logging host 1.1.1.1\nlogging host 2.2.2.2",
            "test": "contains_lines",
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": "logging host 1.1.1.1\nlogging host 2.2.2.2\nlogging host 3.3.3.3",
            "IOL2": "logging host 1.1.1.1",
        },
        name="show run | inc logging",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    assert check_result["IOL1"]["Test logging lines string"]["result"] == "PASS"
    assert check_result["IOL2"]["Test logging lines string"]["result"] == "FAIL"


@skip_if_no_nornir
def test_contains_lines_with_count():
    """Test contains_lines with count parameter."""
    tests = [
        {
            "task": "show ntp",
            "name": "Test NTP lines count",
            "pattern": ["ntp server"],
            "test": "contains_lines",
            "count": 2,
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": "ntp server 1\nntp server 2",  # 2 occurrences
            "IOL2": "ntp server 1",  # 1 occurrence
        },
        name="show ntp",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    assert check_result["IOL1"]["Test NTP lines count"]["result"] == "PASS"
    assert check_result["IOL2"]["Test NTP lines count"]["result"] == "FAIL"


# ======================================================================
# EqualTest edge cases
# ======================================================================


@skip_if_no_nornir
def test_equal_with_list_pattern():
    """Test the equal test function with list type pattern."""
    tests = [
        {
            "task": "get interfaces",
            "name": "Test interfaces list equal",
            "pattern": ["Gi1", "Gi2", "Gi3"],
            "test": "equal",
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": ["Gi1", "Gi2", "Gi3"],
            "IOL2": ["Gi1", "Gi2"],
        },
        name="get interfaces",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    assert check_result["IOL1"]["Test interfaces list equal"]["result"] == "PASS"
    assert check_result["IOL2"]["Test interfaces list equal"]["result"] == "FAIL"


@skip_if_no_nornir
def test_equal_with_custom_err_msg():
    """Test equal test function with custom err_msg."""
    tests = [
        {
            "task": "show version",
            "name": "Test version equal",
            "pattern": "xe1.2.3.4",
            "test": "equal",
            "err_msg": "Version mismatch detected",
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": "xe1.2.3.4",
            "IOL2": "xe4.3.2.1",
        },
        name="show version",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    assert check_result["IOL1"]["Test version equal"]["result"] == "PASS"
    assert check_result["IOL2"]["Test version equal"]["result"] == "FAIL"
    assert (
        check_result["IOL2"]["Test version equal"]["exception"]
        == "Version mismatch detected"
    )


@skip_if_no_nornir
def test_nequal_with_custom_err_msg():
    """Test nequal with custom err_msg on FAIL side."""
    tests = [
        {
            "task": "show version",
            "name": "Test version nequal",
            "pattern": "xe1.2.3.4",
            "test": "nequal",
            "err_msg": "Version should differ",
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": "xe1.2.3.4",
            "IOL2": "xe4.3.2.1",
        },
        name="show version",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    # IOL1 matches, nequal should FAIL with custom err_msg
    assert check_result["IOL1"]["Test version nequal"]["result"] == "FAIL"
    assert (
        check_result["IOL1"]["Test version nequal"]["exception"]
        == "Version should differ"
    )
    assert check_result["IOL2"]["Test version nequal"]["result"] == "PASS"


@skip_if_no_nornir
def test_equal_criteria_truncation_long_string():
    """Test that EqualTest truncates criteria for long string patterns."""
    long_pattern = "This is a very long version string that exceeds 25 characters"
    tests = [
        {
            "task": "show version",
            "name": "Test long equal criteria",
            "pattern": long_pattern,
            "test": "equal",
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={"IOL1": long_pattern, "IOL2": "short"},
        name="show version",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    assert len(check_result["IOL1"]["Test long equal criteria"]["criteria"]) == 24


@skip_if_no_nornir
def test_equal_with_dict_pattern():
    """Test equal with dict pattern."""
    tests = [
        {
            "task": "get facts",
            "name": "Test facts equal",
            "pattern": {"hostname": "router1", "model": "ISR4451"},
            "test": "equal",
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": {"hostname": "router1", "model": "ISR4451"},
            "IOL2": {"hostname": "router2", "model": "ISR4451"},
        },
        name="get facts",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    assert check_result["IOL1"]["Test facts equal"]["result"] == "PASS"
    assert check_result["IOL2"]["Test facts equal"]["result"] == "FAIL"
    # criteria should be empty for non-string patterns
    assert check_result["IOL1"]["Test facts equal"]["criteria"] == ""


@skip_if_no_nornir
def test_equal_with_integer_pattern():
    """Test equal with integer pattern."""
    tests = [
        {
            "task": "get mtu",
            "name": "Test MTU equal",
            "pattern": 9200,
            "test": "equal",
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={"IOL1": 9200, "IOL2": 1500},
        name="get mtu",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    assert check_result["IOL1"]["Test MTU equal"]["result"] == "PASS"
    assert check_result["IOL2"]["Test MTU equal"]["result"] == "FAIL"


# ======================================================================
# EvalTest edge cases
# ======================================================================


@skip_if_no_nornir
def test_eval_with_revert():
    """Test eval with revert parameter - check for inverse."""
    tests = [
        {
            "task": "show ntp",
            "name": "Test NTP eval revert",
            "expr": "'7.7.7.8' in result",
            "test": "eval",
            "revert": True,
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": "ntp server 7.7.7.8",
            "IOL2": "no ntp",
        },
        name="show ntp",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    # IOL1 matches so revert should FAIL
    assert check_result["IOL1"]["Test NTP eval revert"]["result"] == "FAIL"
    assert (
        check_result["IOL1"]["Test NTP eval revert"]["exception"]
        == "Pattern and output equal"
    )
    # IOL2 doesn't match so revert should PASS
    assert check_result["IOL2"]["Test NTP eval revert"]["result"] == "PASS"


@skip_if_no_nornir
def test_eval_with_revert_and_err_msg():
    """Test eval with revert and custom err_msg."""
    tests = [
        {
            "task": "show ntp",
            "name": "Test eval revert err_msg",
            "expr": "'7.7.7.8' in result",
            "test": "eval",
            "revert": True,
            "err_msg": "NTP should not be present",
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": "ntp server 7.7.7.8",
            "IOL2": "no ntp",
        },
        name="show ntp",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    assert check_result["IOL1"]["Test eval revert err_msg"]["result"] == "FAIL"
    assert (
        check_result["IOL1"]["Test eval revert err_msg"]["exception"]
        == "NTP should not be present"
    )


@skip_if_no_nornir
def test_eval_exec_error():
    """Test eval with expression that raises an unexpected exception."""
    tests = [
        {
            "task": "show ntp",
            "name": "Test eval exec error",
            "expr": "1/0",  # ZeroDivisionError
            "test": "eval",
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={"IOL1": "data", "IOL2": "data"},
        name="show ntp",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=False)
    for item in check_result:
        assert item["result"] == "ERROR"
        assert item["success"] is False
        assert "ZeroDivisionError" in item["exception"]


@skip_if_no_nornir
def test_eval_exec_error_with_custom_err_msg():
    """Test eval error with custom err_msg overriding traceback."""
    tests = [
        {
            "task": "show ntp",
            "name": "Test eval error msg",
            "expr": "1/0",
            "test": "eval",
            "err_msg": "Custom error message",
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={"IOL1": "data"},
        name="show ntp",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    assert check_result["IOL1"]["Test eval error msg"]["result"] == "ERROR"
    assert (
        check_result["IOL1"]["Test eval error msg"]["exception"]
        == "Custom error message"
    )


@skip_if_no_nornir
def test_eval_assert_without_message():
    """Test eval with assert that has no custom message (empty AssertionError)."""
    tests = [
        {
            "task": "show ntp",
            "name": "Test assert no msg",
            "expr": "assert False",
            "test": "eval",
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={"IOL1": "data"},
        name="show ntp",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    assert check_result["IOL1"]["Test assert no msg"]["result"] == "FAIL"
    # When assertion has no message, str(e) is empty so fallback to "AssertionError"
    assert check_result["IOL1"]["Test assert no msg"]["exception"] == "AssertionError"


@skip_if_no_nornir
def test_eval_expression_evaluates_to_true():
    """Test eval when the expression evaluates to True."""
    tests = [
        {
            "task": "show ntp",
            "name": "Test eval true",
            "expr": "True",
            "test": "eval",
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={"IOL1": "data"},
        name="show ntp",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    assert check_result["IOL1"]["Test eval true"]["result"] == "PASS"
    assert check_result["IOL1"]["Test eval true"]["success"] is True


@skip_if_no_nornir
def test_eval_with_host_reference():
    """Test eval expression that references host object."""
    tests = [
        {
            "task": "show version",
            "name": "Test eval host ref",
            "expr": "host.name in result",
            "test": "eval",
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": "Hostname: IOL1",
            "IOL2": "Hostname: IOL3",  # doesn't contain IOL2
        },
        name="show version",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    assert check_result["IOL1"]["Test eval host ref"]["result"] == "PASS"
    assert check_result["IOL2"]["Test eval host ref"]["result"] == "FAIL"


# ======================================================================
# Path traversal edge cases
# ======================================================================


@skip_if_no_nornir
def test_path_with_list_index():
    """Test path traversal using specific list index (e.g., 'interfaces.0.mtu')."""
    tests = [
        {
            "test": "eval",
            "task": "get interfaces",
            "name": "Test first interface MTU",
            "path": "interfaces.0.mtu",
            "expr": "result == 1500",
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": {"interfaces": [{"mtu": 1500}, {"mtu": 9200}]},
            "IOL2": {"interfaces": [{"mtu": 9200}]},
        },
        name="get interfaces",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    assert check_result["IOL1"]["Test first interface MTU"]["result"] == "PASS"
    assert check_result["IOL2"]["Test first interface MTU"]["result"] == "FAIL"


@skip_if_no_nornir
def test_path_with_cerberus():
    """Test path attribute combined with cerberus test function."""
    tests = [
        {
            "test": "cerberus",
            "task": "get interfaces",
            "name": "Test interface {name} MTU",
            "path": "interfaces.*",
            "schema": {"mtu": {"type": "integer", "allowed": [1500]}},
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": {
                "interfaces": [
                    {"name": "Gi1", "mtu": 1500},
                    {"name": "Gi2", "mtu": 9200},
                ]
            },
            "IOL2": {"interfaces": [{"name": "Eth1", "mtu": 1500}]},
        },
        name="get interfaces",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=False)
    # IOL1 should have one FAIL (Gi2 mtu=9200)
    iol1_results = [r for r in check_result if r["host"] == "IOL1"]
    assert len(iol1_results) == 1  # only failed results reported by default
    assert iol1_results[0]["result"] == "FAIL"
    # IOL2 should PASS
    iol2_results = [r for r in check_result if r["host"] == "IOL2"]
    assert len(iol2_results) == 1
    assert iol2_results[0]["result"] == "PASS"


@skip_if_no_nornir
def test_path_with_contains_lines():
    """Test path with contains_lines test function."""
    tests = [
        {
            "test": "contains_lines",
            "task": "show config",
            "name": "Test config section",
            "path": "config.sections.*",
            "pattern": ["enabled", "active"],
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": {
                "config": {
                    "sections": [
                        "state: enabled\nmode: active",
                        "state: disabled\nmode: inactive",
                    ]
                }
            },
            "IOL2": {"config": {"sections": ["state: enabled\nmode: active"]}},
        },
        name="show config",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=False)
    # IOL1 has one failing section, IOL2 PASS
    iol1_results = [r for r in check_result if r["host"] == "IOL1"]
    assert any(r["result"] == "FAIL" for r in iol1_results)
    iol2_results = [r for r in check_result if r["host"] == "IOL2"]
    assert all(r["result"] == "PASS" for r in iol2_results)


@skip_if_no_nornir
def test_path_with_nested_dict_traversal():
    """Test path that goes through nested dictionaries only (no lists)."""
    tests = [
        {
            "test": "equal",
            "task": "get config",
            "name": "Test hostname",
            "path": "config.system.hostname",
            "pattern": "router1",
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": {"config": {"system": {"hostname": "router1"}}},
            "IOL2": {"config": {"system": {"hostname": "router2"}}},
        },
        name="get config",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    assert check_result["IOL1"]["Test hostname"]["result"] == "PASS"
    assert check_result["IOL2"]["Test hostname"]["result"] == "FAIL"


# ======================================================================
# TestsProcessor constructor and options
# ======================================================================


@skip_if_no_nornir
def test_subset_filtering():
    """Test subset parameter to filter tests by name using glob patterns."""
    tests = [
        {
            "task": "show ntp",
            "name": "Test NTP config",
            "pattern": "ntp server",
            "test": "contains",
        },
        {
            "task": "show logging",
            "name": "Test Logging config",
            "pattern": "logging host",
            "test": "contains",
        },
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors(
        [
            TestsProcessor(
                tests, remove_tasks=True, build_per_host_tests=True, subset=["*NTP*"]
            )
        ]
    )

    def grouped_task(task):
        task.run(
            task=nr_test,
            ret_data_per_host={
                "IOL1": "ntp server 7.7.7.8",
                "IOL2": "ntp server 7.7.7.7",
            },
            name="show ntp",
        )
        task.run(
            task=nr_test,
            ret_data_per_host={
                "IOL1": "logging host 1.1.1.1",
                "IOL2": "logging host 2.2.2.2",
            },
            name="show logging",
        )
        return Result(host=task.host)

    output = nr_with_tests.run(task=grouped_task)
    check_result = ResultSerializer(output, add_details=True, to_dict=False)
    # Only NTP test should be present, Logging should be filtered out
    for item in check_result:
        assert "NTP" in item["name"]
        assert "Logging" not in item["name"]


@skip_if_no_nornir
def test_subset_filtering_comma_string():
    """Test subset parameter as comma-separated string."""
    tests = [
        {
            "task": "show ntp",
            "name": "Test NTP config",
            "pattern": "ntp server",
            "test": "contains",
        },
        {
            "task": "show logging",
            "name": "Test Logging config",
            "pattern": "logging host",
            "test": "contains",
        },
        {
            "task": "show version",
            "name": "Test Version config",
            "pattern": "Version",
            "test": "contains",
        },
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors(
        [
            TestsProcessor(
                tests,
                remove_tasks=True,
                build_per_host_tests=True,
                subset="*NTP*,*Version*",
            )
        ]
    )

    def grouped_task(task):
        task.run(
            task=nr_test,
            ret_data_per_host={
                "IOL1": "ntp server 7.7.7.8",
                "IOL2": "ntp server 7.7.7.7",
            },
            name="show ntp",
        )
        task.run(
            task=nr_test,
            ret_data_per_host={
                "IOL1": "logging host 1.1.1.1",
                "IOL2": "logging host 2.2.2.2",
            },
            name="show logging",
        )
        task.run(
            task=nr_test,
            ret_data_per_host={"IOL1": "Version 1.2.3", "IOL2": "Version 4.5.6"},
            name="show version",
        )
        return Result(host=task.host)

    output = nr_with_tests.run(task=grouped_task)
    check_result = ResultSerializer(output, add_details=True, to_dict=False)
    names = {item["name"] for item in check_result}
    assert "Test NTP config" in names
    assert "Test Version config" in names
    assert "Test Logging config" not in names


@skip_if_no_nornir
def test_render_tests_false():
    """Test render_tests=False skips Jinja2 rendering."""
    # Use a string that looks like Jinja2 but should not be rendered
    tests = [
        {
            "task": "show ntp",
            "name": "Test NTP config",
            "pattern": "ntp server",
            "test": "contains",
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors(
        [TestsProcessor(tests, remove_tasks=True, render_tests=False)]
    )
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={"IOL1": "ntp server 7.7.7.8", "IOL2": "ntp"},
        name="show ntp",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    assert check_result["IOL1"]["Test NTP config"]["result"] == "PASS"
    assert check_result["IOL2"]["Test NTP config"]["result"] == "FAIL"


# ======================================================================
# Test name auto-generation
# ======================================================================


@skip_if_no_nornir
def test_auto_generated_name_when_name_missing():
    """Test that name is auto-generated when not provided in test definition."""
    tests = [
        {
            "task": "show run | inc ntp",
            "pattern": "ntp server 7.7.7.8",
            "test": "contains",
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={"IOL1": "ntp server 7.7.7.8", "IOL2": "ntp server 7.7.7.7"},
        name="show run | inc ntp",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=False)
    for item in check_result:
        # Auto-generated name should include task name, test name, and truncated pattern
        assert "show run | inc ntp" in item["name"]
        assert "contains" in item["name"]


@skip_if_no_nornir
def test_auto_generated_name_use_all_tasks():
    """Test auto-generated name when use_all_tasks is True and no task specified."""
    custom_function = """
def run(result):
    return {"result": "PASS", "success": True}
"""
    tests = [
        {
            "test": "custom",
            "function_text": custom_function,
            "use_all_tasks": True,
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={"IOL1": "data", "IOL2": "data"},
        name="show ntp",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=False)
    for item in check_result:
        assert "Test all tasks" in item["name"]


# ======================================================================
# CustomFunctionTest edge cases
# ======================================================================


@skip_if_no_nornir
def test_custom_function_returns_none():
    """Test custom function that returns None - should be treated as PASS."""
    custom_function = """
def run(result):
    return None
"""
    tests = [
        {
            "task": "show ntp",
            "name": "Test custom None return",
            "test": "custom",
            "function_text": custom_function,
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={"IOL1": "data", "IOL2": "data"},
        name="show ntp",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=False)
    for item in check_result:
        assert item["result"] == "PASS"
        assert item["success"] is True


@skip_if_no_nornir
def test_custom_function_returns_true():
    """Test custom function that returns True - should be treated as PASS."""
    custom_function = """
def run(result):
    return True
"""
    tests = [
        {
            "task": "show ntp",
            "name": "Test custom True return",
            "test": "custom",
            "function_text": custom_function,
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={"IOL1": "data", "IOL2": "data"},
        name="show ntp",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=False)
    for item in check_result:
        assert item["result"] == "PASS"


@skip_if_no_nornir
def test_custom_function_returns_false():
    """Test custom function that returns False - should be treated as FAIL."""
    custom_function = """
def run(result):
    return False
"""
    tests = [
        {
            "task": "show ntp",
            "name": "Test custom False return",
            "test": "custom",
            "function_text": custom_function,
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={"IOL1": "data", "IOL2": "data"},
        name="show ntp",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=False)
    for item in check_result:
        assert item["result"] == "FAIL"
        assert item["success"] is False


@skip_if_no_nornir
def test_custom_function_returns_empty_list():
    """Test custom function that returns empty list - should be treated as PASS."""
    custom_function = """
def run(result):
    return []
"""
    tests = [
        {
            "task": "show ntp",
            "name": "Test custom empty list",
            "test": "custom",
            "function_text": custom_function,
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={"IOL1": "data", "IOL2": "data"},
        name="show ntp",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=False)
    for item in check_result:
        assert item["result"] == "PASS"


@skip_if_no_nornir
def test_custom_function_returns_empty_dict():
    """Test custom function that returns empty dict - should be treated as PASS."""
    custom_function = """
def run(result):
    return {}
"""
    tests = [
        {
            "task": "show ntp",
            "name": "Test custom empty dict",
            "test": "custom",
            "function_text": custom_function,
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={"IOL1": "data", "IOL2": "data"},
        name="show ntp",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=False)
    for item in check_result:
        assert item["result"] == "PASS"


@skip_if_no_nornir
def test_custom_function_with_function_kwargs():
    """Test custom function with function_kwargs parameter."""
    custom_function = """
def run(result, threshold=0):
    if len(result.result.splitlines()) < threshold:
        return {"result": "FAIL", "success": False, "exception": "Not enough lines"}
    return {"result": "PASS", "success": True}
"""
    tests = [
        {
            "task": "show ntp",
            "name": "Test custom kwargs",
            "test": "custom",
            "function_text": custom_function,
            "function_kwargs": {"threshold": 3},
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": "line1\nline2\nline3\nline4",  # 4 lines >= 3
            "IOL2": "line1",  # 1 line < 3
        },
        name="show ntp",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    assert check_result["IOL1"]["Test custom kwargs"]["result"] == "PASS"
    assert check_result["IOL2"]["Test custom kwargs"]["result"] == "FAIL"
    assert check_result["IOL2"]["Test custom kwargs"]["exception"] == "Not enough lines"


@skip_if_no_nornir
def test_custom_function_with_add_host():
    """Test custom function with add_host=True parameter."""
    custom_function = """
def run(result, host=None):
    if host and host.name == 'IOL1':
        return {"result": "PASS", "success": True}
    return {"result": "FAIL", "success": False, "exception": "Host is not IOL1"}
"""
    tests = [
        {
            "task": "show ntp",
            "name": "Test custom add_host",
            "test": "custom",
            "function_text": custom_function,
            "add_host": True,
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={"IOL1": "data", "IOL2": "data"},
        name="show ntp",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    assert check_result["IOL1"]["Test custom add_host"]["result"] == "PASS"
    assert check_result["IOL2"]["Test custom add_host"]["result"] == "FAIL"


@skip_if_no_nornir
def test_custom_function_run_error():
    """Test custom function that raises an exception during execution."""
    custom_function = """
def run(result):
    raise ValueError("Something went wrong")
"""
    tests = [
        {
            "task": "show ntp",
            "name": "Test custom run error",
            "test": "custom",
            "function_text": custom_function,
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={"IOL1": "data", "IOL2": "data"},
        name="show ntp",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=False)
    for item in check_result:
        assert item["result"] == "ERROR"
        assert "function run error" in item["exception"]
        assert "ValueError" in item["exception"]


@skip_if_no_nornir
def test_custom_function_with_globals_dictionary():
    """Test custom function with globals_dictionary parameter."""
    custom_function = """
def run(result):
    import re
    if re.search(EXPECTED_PATTERN, result.result):
        return {"result": "PASS", "success": True}
    return {"result": "FAIL", "success": False}
"""
    tests = [
        {
            "task": "show ntp",
            "name": "Test custom globals",
            "test": "custom",
            "function_text": custom_function,
            "globals_dictionary": {"EXPECTED_PATTERN": r"ntp server \d+"},
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": "ntp server 1",
            "IOL2": "no ntp",
        },
        name="show ntp",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    assert check_result["IOL1"]["Test custom globals"]["result"] == "PASS"
    assert check_result["IOL2"]["Test custom globals"]["result"] == "FAIL"


@skip_if_no_nornir
def test_custom_function_no_function_provided():
    """Test pydantic validation catches custom test with no function provided."""
    tests = [
        {
            "task": "show ntp",
            "name": "Test no function",
            "test": "custom",
            # no function_text, function_file, function_call, or function_import
        }
    ]
    # Pydantic validation catches missing function at construction time
    with pytest.raises(Exception) as exc_info:
        TestsProcessor(tests, remove_tasks=True)
    assert "No function provided" in str(exc_info.value)


@skip_if_no_nornir
def test_custom_function_bad_function_import():
    """Test CustomFunctionTest with invalid function_import format."""
    tests = [
        {
            "task": "show ntp",
            "name": "Test bad import",
            "test": "custom",
            "function_import": "no_dot_in_path",  # invalid format
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={"IOL1": "data", "IOL2": "data"},
        name="show ntp",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=False)
    for item in check_result:
        assert item["result"] == "ERROR"
        assert "module.function" in item["exception"]


@skip_if_no_nornir
def test_custom_function_with_task_as_list():
    """Test custom function when task is a list of task names."""
    custom_function = """
def run(results):
    # results should be a list of Result objects
    for r in results:
        if "error" in r.result:
            return {"result": "FAIL", "success": False, "exception": "Found error"}
    return {"result": "PASS", "success": True}
"""
    tests = [
        {
            "task": ["show ntp", "show logging"],
            "name": "Test multi-task custom",
            "test": "custom",
            "function_text": custom_function,
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])

    def grouped_task(task):
        task.run(
            task=nr_test,
            ret_data_per_host={"IOL1": "ntp ok", "IOL2": "ntp ok"},
            name="show ntp",
        )
        task.run(
            task=nr_test,
            ret_data_per_host={"IOL1": "logging ok", "IOL2": "logging error found"},
            name="show logging",
        )
        return Result(host=task.host)

    output = nr_with_tests.run(task=grouped_task)
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    assert check_result["IOL1"]["Test multi-task custom"]["result"] == "PASS"
    assert check_result["IOL2"]["Test multi-task custom"]["result"] == "FAIL"


# ======================================================================
# CerberusTest edge cases
# ======================================================================


@skip_if_no_nornir
def test_cerberus_unsupported_result_type():
    """Test CerberusTest with unsupported result type (string instead of dict/list)."""
    tests = [
        {
            "task": "show ntp",
            "name": "Test cerberus string",
            "test": "cerberus",
            "schema": {"field": {"type": "string"}},
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={"IOL1": "just a string", "IOL2": "another string"},
        name="show ntp",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=False)
    for item in check_result:
        assert item["result"] == "ERROR"
        assert "unsupported results type" in item["exception"]


@skip_if_no_nornir
def test_cerberus_allow_unknown_false():
    """Test CerberusTest with allow_unknown=False."""
    tests = [
        {
            "task": "get facts",
            "name": "Test strict schema",
            "test": "cerberus",
            "schema": {"hostname": {"type": "string"}},
            "allow_unknown": False,
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": {"hostname": "router1"},  # passes - only known field
            "IOL2": {"hostname": "router2", "model": "ISR"},  # fails - unknown field
        },
        name="get facts",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    assert check_result["IOL1"]["Test strict schema"]["result"] == "PASS"
    assert check_result["IOL2"]["Test strict schema"]["result"] == "FAIL"


# ======================================================================
# Error handling and edge cases
# ======================================================================


@skip_if_no_nornir
def test_unsupported_test_function_name():
    """Test that pydantic validation catches unsupported test function name at construction."""
    tests = [
        {
            "task": "show ntp",
            "name": "Test bad function",
            "pattern": "ntp server",
            "test": "nonexistent_test_function",
        }
    ]
    # Pydantic validation catches invalid test name at construction time
    with pytest.raises(Exception) as exc_info:
        TestsProcessor(tests, remove_tasks=True)
    assert "nonexistent_test_function" in str(exc_info.value)


@skip_if_no_nornir
def test_no_matching_task_results():
    """Test when test task name doesn't match any task in results.

    Uses two tests so the single-test + single-task auto-match logic
    doesn't kick in.
    """
    tests = [
        {
            "task": "nonexistent task name",
            "name": "Test no results",
            "pattern": "data",
            "test": "contains",
        },
        {
            "task": "show ntp",
            "name": "Test NTP",
            "pattern": "ntp",
            "test": "contains",
        },
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={"IOL1": "ntp data", "IOL2": "ntp data"},
        name="show ntp",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    # "Test no results" should get ERROR because its task name doesn't match
    for host in ["IOL1", "IOL2"]:
        assert check_result[host]["Test no results"]["result"] == "ERROR"
        assert (
            "Found no results to test"
            in check_result[host]["Test no results"]["exception"]
        )
        # The second test should still work fine
        assert check_result[host]["Test NTP"]["result"] == "PASS"


@skip_if_no_nornir
def test_single_test_single_task_auto_match():
    """Test that single test + single task auto-matches even without matching task name."""
    tests = [
        {
            "task": "wrong task name",
            "name": "Test auto match",
            "pattern": "data",
            "test": "contains",
        }
    ]
    nr.data.reset_failed_hosts()
    # With grouped tasks, there are multiple sub-tasks, so auto match shouldn't work
    # But with single nr_test, there's one task, so it should auto-match
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={"IOL1": "data", "IOL2": "data"},
        name="show ntp",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=False)
    # Single test + single task should auto-match
    for item in check_result:
        assert item["result"] == "PASS"


@skip_if_no_nornir
def test_multiple_tests_on_same_task():
    """Test running multiple tests against the same task output."""
    tests = [
        {
            "task": "show ntp",
            "name": "Test NTP server 8",
            "pattern": "ntp server 7.7.7.8",
            "test": "contains",
        },
        {
            "task": "show ntp",
            "name": "Test NTP server 7",
            "pattern": "ntp server 7.7.7.7",
            "test": "contains",
        },
        {
            "task": "show ntp",
            "name": "Test NTP count",
            "pattern": "ntp server",
            "test": "contains",
            "count": 2,
        },
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": "ntp server 7.7.7.8\nntp server 7.7.7.7",
            "IOL2": "ntp server 7.7.7.7",
        },
        name="show ntp",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    # IOL1: all three should pass
    assert check_result["IOL1"]["Test NTP server 8"]["result"] == "PASS"
    assert check_result["IOL1"]["Test NTP server 7"]["result"] == "PASS"
    assert check_result["IOL1"]["Test NTP count"]["result"] == "PASS"
    # IOL2: first fails, second passes, third fails (count 1 != 2)
    assert check_result["IOL2"]["Test NTP server 8"]["result"] == "FAIL"
    assert check_result["IOL2"]["Test NTP server 7"]["result"] == "PASS"
    assert check_result["IOL2"]["Test NTP count"]["result"] == "FAIL"


@skip_if_no_nornir
def test_list_of_lists_format_with_auto_name():
    """Test list-of-lists format with 3 items (no name, auto-generated).

    List-of-lists format requires build_per_host_tests=True.
    """
    tests = [
        ["show ntp", "contains", "ntp server 7.7.7.8"],
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors(
        [TestsProcessor(tests, remove_tasks=True, build_per_host_tests=True)]
    )
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": "ntp server 7.7.7.8",
            "IOL2": "no ntp",
        },
        name="show ntp",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=False)
    assert len(check_result) == 2
    iol1 = [r for r in check_result if r["host"] == "IOL1"][0]
    iol2 = [r for r in check_result if r["host"] == "IOL2"][0]
    assert iol1["result"] == "PASS"
    assert iol2["result"] == "FAIL"
    # Name should be auto-generated
    assert iol1["name"] is not None


@skip_if_no_nornir
def test_list_of_lists_eval_format():
    """Test list-of-lists format with eval test converts pattern to expr automatically.

    List-of-lists format requires build_per_host_tests=True.
    """
    tests = [
        ["show ntp", "eval", "'ntp' in result", "Test NTP eval"],
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors(
        [TestsProcessor(tests, remove_tasks=True, build_per_host_tests=True)]
    )
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={"IOL1": "ntp server 7.7.7.8", "IOL2": "no data"},
        name="show ntp",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    assert check_result["IOL1"]["Test NTP eval"]["result"] == "PASS"
    assert check_result["IOL2"]["Test NTP eval"]["result"] == "FAIL"


# ======================================================================
# Jinja2 template rendering edge cases
# ======================================================================


@skip_if_no_nornir
def test_jinja2_template_renders_empty():
    """Test Jinja2 template that renders to empty string for a host."""
    tests = [
        """
{% if host.interfaces is defined %}
{% for interface in host.interfaces %}
- task: "show interface {{ interface.name }}"
  name: "Test {{ host.name }} {{ interface.name }} MTU"
  test: contains
  pattern: "{{ interface.mtu }}"
{% endfor %}
{% endif %}
    """,
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors(
        [TestsProcessor(tests, remove_tasks=True, build_per_host_tests=True)]
    )

    def grouped_task(task):
        task.run(
            task=nr_test,
            ret_data_per_host={
                "IOL1": "Interface mtu 1500",
            },
            name="show interface Eth1",
        )
        return Result(host=task.host)

    output = nr_with_tests.run(task=grouped_task)
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    # IOL1 has interfaces defined, so tests should run
    assert "IOL1" in check_result
    assert "Test IOL1 Eth1 MTU" in check_result["IOL1"]
    # IOL2 has no interfaces, template should render empty => no tests
    assert check_result.get("IOL2", {}) == {}


# ======================================================================
# build_per_host_tests with various test item types
# ======================================================================


@skip_if_no_nornir
def test_build_per_host_tests_with_dict_items():
    """Test build_per_host_tests mode with dict test items."""
    tests = [
        {
            "task": "show ntp",
            "name": "Test NTP config",
            "pattern": "ntp server",
            "test": "contains",
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors(
        [TestsProcessor(tests, remove_tasks=True, build_per_host_tests=True)]
    )
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={"IOL1": "ntp server 7.7.7.8", "IOL2": "no ntp"},
        name="show ntp",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    assert check_result["IOL1"]["Test NTP config"]["result"] == "PASS"
    assert check_result["IOL2"]["Test NTP config"]["result"] == "FAIL"


@skip_if_no_nornir
def test_build_per_host_tests_with_list_items():
    """Test build_per_host_tests mode with list-of-lists test items."""
    tests = [
        ["show ntp", "contains", "ntp server", "Test NTP config"],
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors(
        [TestsProcessor(tests, remove_tasks=True, build_per_host_tests=True)]
    )
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={"IOL1": "ntp server 7.7.7.8", "IOL2": "no ntp"},
        name="show ntp",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    assert check_result["IOL1"]["Test NTP config"]["result"] == "PASS"
    assert check_result["IOL2"]["Test NTP config"]["result"] == "FAIL"


@skip_if_no_nornir
def test_build_per_host_tests_with_eval_list():
    """Test build_per_host_tests with eval test in list-of-lists format."""
    tests = [
        ["show ntp", "eval", "'ntp' in result", "Test NTP eval"],
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors(
        [TestsProcessor(tests, remove_tasks=True, build_per_host_tests=True)]
    )
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={"IOL1": "ntp server", "IOL2": "no data"},
        name="show ntp",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    assert check_result["IOL1"]["Test NTP eval"]["result"] == "PASS"
    assert check_result["IOL2"]["Test NTP eval"]["result"] == "FAIL"


# ======================================================================
# Pydantic validation tests
# ======================================================================


@skip_if_no_nornir
def test_pydantic_validation_missing_test_field():
    """Test that pydantic validation catches missing 'test' field."""
    tests = [
        {
            "task": "show ntp",
            "name": "Test missing test field",
            "pattern": "ntp server",
            # "test" field is missing
        }
    ]
    with pytest.raises(Exception):
        TestsProcessor(tests, remove_tasks=True)


@skip_if_no_nornir
def test_pydantic_validation_invalid_test_name():
    """Test that pydantic validation catches invalid test function name."""
    tests = [
        {
            "task": "show ntp",
            "name": "Test invalid test name",
            "pattern": "ntp server",
            "test": "invalid_test_name",  # not a valid test function
        }
    ]
    with pytest.raises(Exception):
        TestsProcessor(tests, remove_tasks=True)


@skip_if_no_nornir
def test_pydantic_validation_eval_missing_expr():
    """Test pydantic validation fails when eval test misses expr field."""
    tests = [
        {
            "task": "show ntp",
            "name": "Test eval no expr",
            "test": "eval",
            # "expr" is missing for eval test
        }
    ]
    with pytest.raises(Exception):
        TestsProcessor(tests, remove_tasks=True)


# ======================================================================
# task_completed cleanup and failed_only
# ======================================================================


@skip_if_no_nornir
def test_failed_only_all_pass():
    """Test failed_only when all tests pass - should return empty results."""
    tests = [
        {
            "task": "show ntp",
            "name": "Test NTP config",
            "pattern": "ntp server",
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
            "IOL1": "ntp server 7.7.7.8",
            "IOL2": "ntp server 7.7.7.7",
        },
        name="show ntp",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    # Both pass, so with failed_only=True there should be no results
    assert check_result == {}


@skip_if_no_nornir
def test_failed_only_mixed_results():
    """Test failed_only with mix of pass and fail results."""
    tests = [
        {
            "task": "show ntp",
            "name": "Test NTP 8",
            "pattern": "7.7.7.8",
            "test": "contains",
        },
        {
            "task": "show ntp",
            "name": "Test NTP 9",
            "pattern": "7.7.7.9",
            "test": "contains",
        },
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors(
        [TestsProcessor(tests, remove_tasks=True, failed_only=True)]
    )
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": "ntp 7.7.7.8",  # passes test 1, fails test 2
            "IOL2": "ntp 7.7.7.7",  # fails both
        },
        name="show ntp",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    # IOL1 should only have failing test (Test NTP 9)
    assert "Test NTP 8" not in check_result.get("IOL1", {})
    assert check_result["IOL1"]["Test NTP 9"]["result"] == "FAIL"
    # IOL2 should have both failing tests
    assert check_result["IOL2"]["Test NTP 8"]["result"] == "FAIL"
    assert check_result["IOL2"]["Test NTP 9"]["result"] == "FAIL"


@skip_if_no_nornir
def test_remove_tasks_true_removes_original_output():
    """Verify remove_tasks=True removes original task results."""
    tests = [
        {
            "task": "show ntp",
            "name": "Test NTP",
            "pattern": "ntp",
            "test": "contains",
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={"IOL1": "ntp configured", "IOL2": "ntp configured"},
        name="show ntp",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    # Only test results should be present, no original task output
    for host, results in check_result.items():
        assert "show ntp" not in results
        assert "Test NTP" in results


@skip_if_no_nornir
def test_remove_tasks_false_keeps_original_output():
    """Verify remove_tasks=False keeps original task results alongside test results."""
    tests = [
        {
            "task": "show ntp",
            "name": "Test NTP",
            "pattern": "ntp",
            "test": "contains",
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=False)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={"IOL1": "ntp configured", "IOL2": "ntp configured"},
        name="show ntp",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    # Both test results and original task output should be present
    for host, results in check_result.items():
        assert "show ntp" in results
        assert "Test NTP" in results


# ======================================================================
# Test calling by global function name
# ======================================================================


@skip_if_no_nornir
def test_calling_by_global_name_EqualTest():
    """Test calling test by global function name 'EqualTest'."""
    tests = [
        {
            "task": "show version",
            "name": "Test version",
            "pattern": "1.0",
            "test": "EqualTest",
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={"IOL1": "1.0", "IOL2": "2.0"},
        name="show version",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    assert check_result["IOL1"]["Test version"]["result"] == "PASS"
    assert check_result["IOL1"]["Test version"]["test"] == "EqualTest"
    assert check_result["IOL2"]["Test version"]["result"] == "FAIL"


@skip_if_no_nornir
def test_calling_by_global_name_ContainsLinesTest():
    """Test calling test by global function name 'ContainsLinesTest'."""
    tests = [
        {
            "task": "show ntp",
            "name": "Test NTP lines",
            "pattern": ["server 1", "server 2"],
            "test": "ContainsLinesTest",
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": "server 1\nserver 2\nserver 3",
            "IOL2": "server 1\nserver 3",
        },
        name="show ntp",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    assert check_result["IOL1"]["Test NTP lines"]["result"] == "PASS"
    assert check_result["IOL2"]["Test NTP lines"]["result"] == "FAIL"


@skip_if_no_nornir
def test_calling_by_global_name_EvalTest():
    """Test calling test by global function name 'EvalTest'."""
    tests = [
        {
            "task": "show ntp",
            "name": "Test NTP eval",
            "expr": "'ntp' in result",
            "test": "EvalTest",
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={"IOL1": "ntp server", "IOL2": "no data"},
        name="show ntp",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    assert check_result["IOL1"]["Test NTP eval"]["result"] == "PASS"
    assert check_result["IOL2"]["Test NTP eval"]["result"] == "FAIL"


@skip_if_no_nornir
def test_calling_by_global_name_CerberusTest():
    """Test calling test by global function name 'CerberusTest'."""
    tests = [
        {
            "task": "get facts",
            "name": "Test facts schema",
            "test": "CerberusTest",
            "schema": {"hostname": {"type": "string"}},
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": {"hostname": "router1"},
            "IOL2": {"hostname": 123},  # wrong type
        },
        name="get facts",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    assert check_result["IOL1"]["Test facts schema"]["result"] == "PASS"
    assert check_result["IOL2"]["Test facts schema"]["result"] == "FAIL"


# ======================================================================
# ResultSerializer format tests
# ======================================================================


@skip_if_no_nornir
def test_result_serializer_to_dict_false():
    """Test ResultSerializer with to_dict=False returns list format."""
    tests = [
        {
            "task": "show ntp",
            "name": "Test NTP",
            "pattern": "ntp",
            "test": "contains",
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={"IOL1": "ntp server", "IOL2": "no data"},
        name="show ntp",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=False)
    assert isinstance(check_result, list)
    assert len(check_result) == 2
    for item in check_result:
        assert "host" in item
        assert "name" in item
        assert "result" in item


@skip_if_no_nornir
def test_result_serializer_add_details_false():
    """Test ResultSerializer with add_details=False returns minimal fields."""
    tests = [
        {
            "task": "show ntp",
            "name": "Test NTP",
            "pattern": "ntp",
            "test": "contains",
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={"IOL1": "ntp server", "IOL2": "no data"},
        name="show ntp",
    )
    check_result = ResultSerializer(output, add_details=False, to_dict=False)
    assert isinstance(check_result, list)
    for item in check_result:
        assert "host" in item
        assert "name" in item
        assert "result" in item


# ======================================================================
# Newline handling in criteria
# ======================================================================


@skip_if_no_nornir
def test_contains_pattern_with_newlines_in_criteria():
    """Test that newlines in pattern are escaped in criteria field."""
    tests = [
        {
            "task": "show ntp",
            "name": "Test newline pattern",
            "pattern": "line1\nline2",
            "test": "contains",
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={"IOL1": "line1\nline2", "IOL2": "line1"},
        name="show ntp",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    # Criteria should have escaped newlines
    assert "\\n" in check_result["IOL1"]["Test newline pattern"]["criteria"]
    assert "\n" not in check_result["IOL1"]["Test newline pattern"]["criteria"]


# ======================================================================
# Contains with regex count interaction
# ======================================================================


@skip_if_no_nornir
def test_contains_re_regex_match():
    """Test contains_re with complex regex pattern."""
    tests = [
        {
            "task": "show bgp",
            "name": "Test BGP state regex",
            "pattern": r"(Idle|Active|Connect)",
            "test": "contains_re",
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": "10.0.0.1  Active  0  0  0  0",
            "IOL2": "10.0.0.1  Established  100  200  50  0",
        },
        name="show bgp",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    assert check_result["IOL1"]["Test BGP state regex"]["result"] == "PASS"
    assert check_result["IOL2"]["Test BGP state regex"]["result"] == "FAIL"


@skip_if_no_nornir
def test_ncontains_with_err_msg():
    """Test ncontains (inverted) with custom err_msg."""
    tests = [
        {
            "task": "show ntp",
            "name": "Test no bad server",
            "pattern": "bad_server",
            "test": "ncontains",
            "err_msg": "Bad server found in config",
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": "ntp bad_server",  # has it - FAIL
            "IOL2": "ntp good_server",  # doesn't have it - PASS
        },
        name="show ntp",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    assert check_result["IOL1"]["Test no bad server"]["result"] == "FAIL"
    assert (
        check_result["IOL1"]["Test no bad server"]["exception"]
        == "Bad server found in config"
    )
    assert check_result["IOL2"]["Test no bad server"]["result"] == "PASS"


# ======================================================================
# Test with integer/boolean result data
# ======================================================================


@skip_if_no_nornir
def test_contains_pattern_coerced_to_string():
    """Test that ContainsTest coerces pattern to string via str(pattern)."""
    tests = [
        {
            "task": "show mtu",
            "name": "Test MTU contains int",
            "pattern": 9200,  # integer pattern - should be coerced to "9200"
            "test": "contains",
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": "Interface MTU 9200",
            "IOL2": "Interface MTU 1500",
        },
        name="show mtu",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    assert check_result["IOL1"]["Test MTU contains int"]["result"] == "PASS"
    assert check_result["IOL2"]["Test MTU contains int"]["result"] == "FAIL"


# ======================================================================
# EqualTest with newlines in pattern
# ======================================================================


@skip_if_no_nornir
def test_equal_pattern_newlines_escaped_in_criteria():
    """Test EqualTest escapes newlines in criteria for short patterns."""
    short_pattern_with_newline = "line1\nline2"
    tests = [
        {
            "task": "show data",
            "name": "Test equal newline",
            "pattern": short_pattern_with_newline,
            "test": "equal",
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={"IOL1": "line1\nline2"},
        name="show data",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    assert "\\n" in check_result["IOL1"]["Test equal newline"]["criteria"]


# ======================================================================
# Test report_all with path (non-eval)
# ======================================================================


@skip_if_no_nornir
def test_path_with_contains_report_all():
    """Test path with contains test and report_all=True."""
    tests = [
        {
            "test": "contains",
            "task": "get config",
            "name": "Test config entries",
            "path": "config.*",
            "pattern": "enabled",
            "report_all": True,
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": {"config": ["state: enabled", "mode: enabled"]},
            "IOL2": {"config": ["state: disabled", "mode: enabled"]},
        },
        name="get config",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=False)
    # With report_all=True, all results (PASS and FAIL) should be reported
    iol1_results = [r for r in check_result if r["host"] == "IOL1"]
    iol2_results = [r for r in check_result if r["host"] == "IOL2"]
    # IOL1 both pass
    assert len(iol1_results) == 2
    assert all(r["result"] == "PASS" for r in iol1_results)
    # IOL2 one fails, one passes
    assert len(iol2_results) == 2
    assert any(r["result"] == "FAIL" for r in iol2_results)
    assert any(r["result"] == "PASS" for r in iol2_results)


# ======================================================================
# Jinja2 name rendering from result data
# ======================================================================


@skip_if_no_nornir
def test_cerberus_name_format_from_data():
    """Test that cerberus formats test name using validated data keys."""
    tests = [
        {
            "task": "get interfaces",
            "name": "Test {interface} config",
            "test": "cerberus",
            "schema": {"mtu": {"type": "integer", "allowed": [1500]}},
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": {"interface": "Gi1", "mtu": 1500},
            "IOL2": {"interface": "Gi2", "mtu": 9200},
        },
        name="get interfaces",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    # Names should be formatted with data values
    assert "Test Gi1 config" in check_result["IOL1"]
    assert "Test Gi2 config" in check_result["IOL2"]


# ======================================================================
# Contains revert with use_re combined
# ======================================================================


@skip_if_no_nornir
def test_contains_re_revert_using_exclamation_alias():
    """Test !contains_re alias with exclamation mark."""
    tests = [
        {
            "task": "show ntp",
            "name": "Test no NTP regex",
            "pattern": r"ntp server \d+\.\d+",
            "test": "!contains_re",
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": "ntp server 7.7.7.8",
            "IOL2": "no ntp configured",
        },
        name="show ntp",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    assert check_result["IOL1"]["Test no NTP regex"]["result"] == "FAIL"
    assert (
        check_result["IOL1"]["Test no NTP regex"]["exception"]
        == "Regex pattern in output"
    )
    assert check_result["IOL2"]["Test no NTP regex"]["result"] == "PASS"


@skip_if_no_nornir
def test_contains_lines_revert_using_exclamation_alias():
    """Test !contains_lines alias with exclamation mark."""
    tests = [
        {
            "task": "show ntp",
            "name": "Test no bad lines",
            "pattern": ["Idle", "Active"],
            "test": "!contains_lines",
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": "Idle\nActive\nEstablished",  # has them - inverted FAIL
            "IOL2": "Established\nEstablished",  # no bad lines - inverted PASS
        },
        name="show ntp",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    assert check_result["IOL1"]["Test no bad lines"]["result"] == "FAIL"
    assert check_result["IOL2"]["Test no bad lines"]["result"] == "PASS"


@skip_if_no_nornir
def test_contains_revert_using_exclamation_alias():
    """Test !contains alias with exclamation mark syntax."""
    tests = [
        {
            "task": "show ntp",
            "name": "Test no pattern",
            "pattern": "bad_config",
            "test": "!contains",
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": "bad_config present",
            "IOL2": "good_config only",
        },
        name="show ntp",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    assert check_result["IOL1"]["Test no pattern"]["result"] == "FAIL"
    assert check_result["IOL2"]["Test no pattern"]["result"] == "PASS"


@skip_if_no_nornir
def test_nequal_using_exclamation_alias():
    """Test !equal alias with exclamation mark."""
    tests = [
        {
            "task": "show version",
            "name": "Test version not equal",
            "pattern": "oldversion",
            "test": "!equal",
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": "oldversion",  # equal, inverted -> FAIL
            "IOL2": "newversion",  # not equal, inverted -> PASS
        },
        name="show version",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    assert check_result["IOL1"]["Test version not equal"]["result"] == "FAIL"
    assert check_result["IOL2"]["Test version not equal"]["result"] == "PASS"


# ======================================================================
# Extra attributes pass-through
# ======================================================================


@skip_if_no_nornir
def test_extra_attributes_in_contains_test():
    """Test that extra kwargs in test definition are passed through to results."""
    tests = [
        {
            "task": "show ntp",
            "name": "Test NTP extra attrs",
            "pattern": "ntp server",
            "test": "contains",
            "description": "Verify NTP configuration",
            "severity": "critical",
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={"IOL1": "ntp server 7.7.7.8", "IOL2": "no ntp"},
        name="show ntp",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    # Extra attributes should be present in results
    assert (
        check_result["IOL1"]["Test NTP extra attrs"]["description"]
        == "Verify NTP configuration"
    )
    assert check_result["IOL1"]["Test NTP extra attrs"]["severity"] == "critical"
    assert (
        check_result["IOL2"]["Test NTP extra attrs"]["description"]
        == "Verify NTP configuration"
    )
    assert check_result["IOL2"]["Test NTP extra attrs"]["severity"] == "critical"


@skip_if_no_nornir
def test_extra_attributes_in_eval_test():
    """Test that extra kwargs work with eval test."""
    tests = [
        {
            "task": "show ntp",
            "name": "Test eval extra",
            "expr": "'ntp' in result",
            "test": "eval",
            "category": "network",
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={"IOL1": "ntp server"},
        name="show ntp",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    assert check_result["IOL1"]["Test eval extra"]["category"] == "network"


# ======================================================================
# Test with None result data
# ======================================================================


@skip_if_no_nornir
def test_contains_with_none_result_data():
    """Test behavior when host result data is None (not in ret_data_per_host)."""
    tests = [
        {
            "task": "show ntp",
            "name": "Test NTP none data",
            "pattern": "ntp",
            "test": "contains",
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": "ntp configured",
            # IOL2 not in ret_data_per_host, gets None
        },
        name="show ntp",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    assert check_result["IOL1"]["Test NTP none data"]["result"] == "PASS"
    # IOL2 gets None result - ContainsTest calls str(pattern) on pattern and checks
    # pattern in result.result but result.result is None, should error
    assert "IOL2" in check_result
    iol2_test = check_result["IOL2"]["Test NTP none data"]
    # When result data is None, ContainsTest will try "ntp" in None which raises TypeError
    assert iol2_test["result"] in ("FAIL", "ERROR")


# ======================================================================
# Contains with exact count
# ======================================================================


@skip_if_no_nornir
def test_contains_count_exact_zero():
    """Test contains with count=0 - pattern should appear exactly 0 times to pass."""
    tests = [
        {
            "task": "show ntp",
            "name": "Test NTP count 0",
            "pattern": "bad_server",
            "test": "contains",
            "count": 0,
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": "ntp good_server",  # 0 occurrences of bad_server - PASS
            "IOL2": "ntp bad_server",  # 1 occurrence - FAIL
        },
        name="show ntp",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    # IOL1: 0 occurrences == count(0) -> PASS
    assert check_result["IOL1"]["Test NTP count 0"]["result"] == "PASS"
    assert check_result["IOL1"]["Test NTP count 0"]["success"] is True
    # IOL2: 1 occurrence != count(0) -> FAIL
    assert check_result["IOL2"]["Test NTP count 0"]["result"] == "FAIL"
    assert check_result["IOL2"]["Test NTP count 0"]["success"] is False
    assert "0 times" in check_result["IOL2"]["Test NTP count 0"]["exception"]


@skip_if_no_nornir
def test_contains_count_zero_with_revert():
    """Test contains with count=0 and revert=True - inverts the result."""
    tests = [
        {
            "task": "show ntp",
            "name": "Test count 0 revert",
            "pattern": "bad_server",
            "test": "contains",
            "count": 0,
            "revert": True,
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": "ntp good_server",  # 0 occurrences -> normally PASS, reverted -> FAIL
            "IOL2": "ntp bad_server",  # 1 occurrence -> normally FAIL, reverted -> PASS
        },
        name="show ntp",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    assert check_result["IOL1"]["Test count 0 revert"]["result"] == "FAIL"
    assert "0 times" in check_result["IOL1"]["Test count 0 revert"]["exception"]
    assert check_result["IOL2"]["Test count 0 revert"]["result"] == "PASS"
    assert check_result["IOL2"]["Test count 0 revert"]["exception"] is None


@skip_if_no_nornir
def test_contains_count_zero_reported_in_result():
    """Test that count=0 is included in the result dict."""
    tests = [
        {
            "task": "show ntp",
            "name": "Test count 0 in result",
            "pattern": "ntp",
            "test": "contains",
            "count": 0,
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={"IOL1": "no match here"},
        name="show ntp",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    # count=0 should appear in the result metadata
    assert check_result["IOL1"]["Test count 0 in result"]["count"] == 0


@skip_if_no_nornir
def test_contains_count_ge_zero():
    """Test contains with count_ge=0 - any count >= 0 should pass (always true)."""
    tests = [
        {
            "task": "show ntp",
            "name": "Test count_ge 0",
            "pattern": "nonexistent_pattern",
            "test": "contains",
            "count_ge": 0,
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": "ntp server 7.7.7.8",  # 0 occurrences of pattern, 0 >= 0 -> PASS
            "IOL2": "some other data",  # 0 occurrences, 0 >= 0 -> PASS
        },
        name="show ntp",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    # count_ge=0 means pattern must appear >= 0 times, which is always true
    assert check_result["IOL1"]["Test count_ge 0"]["result"] == "PASS"
    assert check_result["IOL2"]["Test count_ge 0"]["result"] == "PASS"
    # count_ge=0 should be reported in result
    assert check_result["IOL1"]["Test count_ge 0"]["count_ge"] == 0


@skip_if_no_nornir
def test_contains_count_le_zero():
    """Test contains with count_le=0 - pattern must appear 0 or fewer times (i.e. absent)."""
    tests = [
        {
            "task": "show ntp",
            "name": "Test count_le 0",
            "pattern": "bad_server",
            "test": "contains",
            "count_le": 0,
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": "ntp good_server",  # 0 occurrences <= 0 -> PASS
            "IOL2": "bad_server is here",  # 1 occurrence > 0 -> FAIL
        },
        name="show ntp",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    assert check_result["IOL1"]["Test count_le 0"]["result"] == "PASS"
    assert check_result["IOL1"]["Test count_le 0"]["success"] is True
    assert check_result["IOL2"]["Test count_le 0"]["result"] == "FAIL"
    assert check_result["IOL2"]["Test count_le 0"]["success"] is False
    assert (
        "lower or equal 0 times" in check_result["IOL2"]["Test count_le 0"]["exception"]
    )
    # count_le=0 should be reported in result
    assert check_result["IOL1"]["Test count_le 0"]["count_le"] == 0


@skip_if_no_nornir
def test_contains_count_ge_zero_and_count_le_zero_combined():
    """Test count_ge=0 and count_le=0 combined - pattern must appear exactly 0 times."""
    tests = [
        {
            "task": "show ntp",
            "name": "Test range 0-0",
            "pattern": "bad_server",
            "test": "contains",
            "count_ge": 0,
            "count_le": 0,
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": "ntp good_server",  # 0 in [0,0] -> PASS
            "IOL2": "bad_server configured",  # 1 not in [0,0] -> FAIL
        },
        name="show ntp",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    assert check_result["IOL1"]["Test range 0-0"]["result"] == "PASS"
    assert check_result["IOL2"]["Test range 0-0"]["result"] == "FAIL"
    assert (
        "between 0 and 0 times" in check_result["IOL2"]["Test range 0-0"]["exception"]
    )


# ======================================================================
# Mixed test suite with different test types
# ======================================================================


@skip_if_no_nornir
def test_mixed_test_suite():
    """Test a suite combining contains, equal, eval, and contains_lines tests."""
    tests = [
        {
            "task": "show ntp",
            "name": "Test NTP contains",
            "pattern": "ntp server",
            "test": "contains",
        },
        {
            "task": "show version",
            "name": "Test version equal",
            "pattern": "v1.0",
            "test": "equal",
        },
        {
            "task": "show ntp",
            "name": "Test NTP eval",
            "expr": "len(result) > 5",
            "test": "eval",
        },
        {
            "task": "show logging",
            "name": "Test logging lines",
            "pattern": ["syslog", "enabled"],
            "test": "contains_lines",
        },
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])

    def grouped_task(task):
        task.run(
            task=nr_test,
            ret_data_per_host={"IOL1": "ntp server 1", "IOL2": "ntp server 2"},
            name="show ntp",
        )
        task.run(
            task=nr_test,
            ret_data_per_host={"IOL1": "v1.0", "IOL2": "v2.0"},
            name="show version",
        )
        task.run(
            task=nr_test,
            ret_data_per_host={
                "IOL1": "syslog enabled\nlogging active",
                "IOL2": "syslog disabled",
            },
            name="show logging",
        )
        return Result(host=task.host)

    output = nr_with_tests.run(task=grouped_task)
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    # IOL1: all should PASS
    assert check_result["IOL1"]["Test NTP contains"]["result"] == "PASS"
    assert check_result["IOL1"]["Test version equal"]["result"] == "PASS"
    assert check_result["IOL1"]["Test NTP eval"]["result"] == "PASS"
    assert check_result["IOL1"]["Test logging lines"]["result"] == "PASS"
    # IOL2: version and logging should FAIL
    assert check_result["IOL2"]["Test NTP contains"]["result"] == "PASS"
    assert check_result["IOL2"]["Test version equal"]["result"] == "FAIL"
    assert check_result["IOL2"]["Test NTP eval"]["result"] == "PASS"
    assert check_result["IOL2"]["Test logging lines"]["result"] == "FAIL"


# ======================================================================
# Groups filtering tests
# ======================================================================


def _groups_suite():
    """Helper: returns a test suite with groups assigned to each test."""
    return [
        {
            "task": "show ntp",
            "name": "Test NTP contains",
            "pattern": "ntp server",
            "test": "contains",
            "groups": ["NTP", "SYS"],
        },
        {
            "task": "show version",
            "name": "Test version equal",
            "pattern": "v1.0",
            "test": "equal",
            "groups": ["SYS"],
        },
        {
            "task": "show ntp",
            "name": "Test NTP eval",
            "expr": "len(result) > 5",
            "test": "eval",
            "groups": ["NTP"],
        },
        {
            "task": "show logging",
            "name": "Test logging lines",
            "pattern": ["syslog", "enabled"],
            "test": "contains_lines",
            "groups": ["LOG", "SYS"],
        },
    ]


def _groups_grouped_task(task):
    """Helper: runs the four tasks expected by _groups_suite."""
    task.run(
        task=nr_test,
        ret_data_per_host={"IOL1": "ntp server 1", "IOL2": "ntp server 2"},
        name="show ntp",
    )
    task.run(
        task=nr_test,
        ret_data_per_host={"IOL1": "v1.0", "IOL2": "v2.0"},
        name="show version",
    )
    task.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": "syslog enabled\nlogging active",
            "IOL2": "syslog disabled",
        },
        name="show logging",
    )
    return Result(host=task.host)


@skip_if_no_nornir
def test_groups_filter_single_group_sys():
    """Filter by groups=['SYS'] - only tests with SYS in their groups should run."""
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors(
        [
            TestsProcessor(
                _groups_suite(),
                remove_tasks=True,
                build_per_host_tests=True,
                groups=["SYS"],
            )
        ]
    )
    output = nr_with_tests.run(task=_groups_grouped_task)
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    # SYS group includes: "Test NTP contains" (NTP,SYS), "Test version equal" (SYS),
    #                      "Test logging lines" (LOG,SYS)
    # Should exclude:     "Test NTP eval" (NTP only)
    for host in ["IOL1", "IOL2"]:
        assert (
            "Test NTP contains" in check_result[host]
        ), f"Missing NTP contains for {host}"
        assert (
            "Test version equal" in check_result[host]
        ), f"Missing version equal for {host}"
        assert (
            "Test logging lines" in check_result[host]
        ), f"Missing logging lines for {host}"
        assert (
            "Test NTP eval" not in check_result[host]
        ), f"NTP eval should be excluded for {host}"


@skip_if_no_nornir
def test_groups_filter_single_group_ntp():
    """Filter by groups=['NTP'] - only tests with NTP in their groups should run."""
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors(
        [
            TestsProcessor(
                _groups_suite(),
                remove_tasks=True,
                build_per_host_tests=True,
                groups=["NTP"],
            )
        ]
    )
    output = nr_with_tests.run(task=_groups_grouped_task)
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    # NTP group includes: "Test NTP contains" (NTP,SYS), "Test NTP eval" (NTP)
    # Should exclude:     "Test version equal" (SYS), "Test logging lines" (LOG,SYS)
    for host in ["IOL1", "IOL2"]:
        assert "Test NTP contains" in check_result[host]
        assert "Test NTP eval" in check_result[host]
        assert "Test version equal" not in check_result[host]
        assert "Test logging lines" not in check_result[host]


@skip_if_no_nornir
def test_groups_filter_single_group_log():
    """Filter by groups=['LOG'] - only tests with LOG in their groups should run."""
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors(
        [
            TestsProcessor(
                _groups_suite(),
                remove_tasks=True,
                build_per_host_tests=True,
                groups=["LOG"],
            )
        ]
    )
    output = nr_with_tests.run(task=_groups_grouped_task)
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    # LOG group includes only: "Test logging lines" (LOG,SYS)
    for host in ["IOL1", "IOL2"]:
        assert "Test logging lines" in check_result[host]
        assert "Test NTP contains" not in check_result[host]
        assert "Test version equal" not in check_result[host]
        assert "Test NTP eval" not in check_result[host]


@skip_if_no_nornir
def test_groups_filter_multiple_groups():
    """Filter by groups=['NTP', 'LOG'] - tests with NTP OR LOG should run."""
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors(
        [
            TestsProcessor(
                _groups_suite(),
                remove_tasks=True,
                build_per_host_tests=True,
                groups=["NTP", "LOG"],
            )
        ]
    )
    output = nr_with_tests.run(task=_groups_grouped_task)
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    # NTP|LOG includes: "Test NTP contains" (NTP,SYS), "Test NTP eval" (NTP),
    #                   "Test logging lines" (LOG,SYS)
    # Should exclude:   "Test version equal" (SYS only)
    for host in ["IOL1", "IOL2"]:
        assert "Test NTP contains" in check_result[host]
        assert "Test NTP eval" in check_result[host]
        assert "Test logging lines" in check_result[host]
        assert "Test version equal" not in check_result[host]


@skip_if_no_nornir
def test_groups_filter_comma_separated_string():
    """Filter by groups as comma-separated string 'NTP,LOG'."""
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors(
        [
            TestsProcessor(
                _groups_suite(),
                remove_tasks=True,
                build_per_host_tests=True,
                groups="NTP,LOG",
            )
        ]
    )
    output = nr_with_tests.run(task=_groups_grouped_task)
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    # Same as multiple groups list: NTP|LOG
    for host in ["IOL1", "IOL2"]:
        assert "Test NTP contains" in check_result[host]
        assert "Test NTP eval" in check_result[host]
        assert "Test logging lines" in check_result[host]
        assert "Test version equal" not in check_result[host]


@skip_if_no_nornir
def test_groups_filter_no_groups_runs_all():
    """When no groups filter is specified, all tests should run."""
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors(
        [
            TestsProcessor(
                _groups_suite(),
                remove_tasks=True,
                build_per_host_tests=True,
                # no groups parameter
            )
        ]
    )
    output = nr_with_tests.run(task=_groups_grouped_task)
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    for host in ["IOL1", "IOL2"]:
        assert "Test NTP contains" in check_result[host]
        assert "Test version equal" in check_result[host]
        assert "Test NTP eval" in check_result[host]
        assert "Test logging lines" in check_result[host]


@skip_if_no_nornir
def test_groups_filter_nonexistent_group():
    """Filter by a group name that no test has - all tests should be filtered out."""
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors(
        [
            TestsProcessor(
                _groups_suite(),
                remove_tasks=True,
                build_per_host_tests=True,
                groups=["NONEXISTENT"],
            )
        ]
    )
    output = nr_with_tests.run(task=_groups_grouped_task)
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    # No tests match, result should be empty
    assert check_result == {}


@skip_if_no_nornir
def test_groups_filter_results_correctness():
    """Verify groups filtering still produces correct PASS/FAIL results."""
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors(
        [
            TestsProcessor(
                _groups_suite(),
                remove_tasks=True,
                build_per_host_tests=True,
                groups=["SYS"],
            )
        ]
    )
    output = nr_with_tests.run(task=_groups_grouped_task)
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    # IOL1: ntp server present -> PASS, v1.0 matches -> PASS, syslog+enabled -> PASS
    assert check_result["IOL1"]["Test NTP contains"]["result"] == "PASS"
    assert check_result["IOL1"]["Test version equal"]["result"] == "PASS"
    assert check_result["IOL1"]["Test logging lines"]["result"] == "PASS"
    # IOL2: ntp server present -> PASS, v2.0 != v1.0 -> FAIL, "syslog disabled" missing "enabled" -> FAIL
    assert check_result["IOL2"]["Test NTP contains"]["result"] == "PASS"
    assert check_result["IOL2"]["Test version equal"]["result"] == "FAIL"
    assert check_result["IOL2"]["Test logging lines"]["result"] == "FAIL"


# ======================================================================
# Jinja2 template with tests_data using host-specific data
# ======================================================================


@skip_if_no_nornir
def test_jinja2_with_job_data():
    """Test Jinja2 template using host's job_data for rendering."""
    tests = [
        """
- task: "show version"
  name: "Test {{ host.name }} version"
  pattern: "{{ host.version }}"
  test: contains
    """,
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors(
        [TestsProcessor(tests, remove_tasks=True, build_per_host_tests=True)]
    )
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": "Software version: xe1.2.3.4",
            "IOL2": "Software version: xe1.2.3.4",
        },
        name="show version",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    # Both hosts have version xe1.2.3.4 in inventory data
    assert check_result["IOL1"]["Test IOL1 version"]["result"] == "PASS"
    assert check_result["IOL2"]["Test IOL2 version"]["result"] == "PASS"


# ======================================================================
# Test task_completed cleanup
# ======================================================================


@skip_if_no_nornir
def test_task_completed_cleans_up_host_data():
    """Verify that task_completed removes tests_suite and commands from host data."""
    tests = [
        {
            "task": "show ntp",
            "name": "Test NTP",
            "pattern": "ntp",
            "test": "contains",
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors(
        [TestsProcessor(tests, remove_tasks=True, build_per_host_tests=True)]
    )
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={"IOL1": "ntp server", "IOL2": "ntp server"},
        name="show ntp",
    )
    # After task completion, __task__ should not contain tests_suite or commands
    for host in nr.inventory.hosts.values():
        task_data = host.data.get("__task__", {})
        assert "tests_suite" not in task_data
        assert "commands" not in task_data


# ======================================================================
# Test with skip_results attribute
# ======================================================================


@skip_if_no_nornir
def test_skip_results_attribute():
    """Test that results with skip_results=True are skipped during test matching."""
    tests = [
        {
            "task": "show ntp",
            "name": "Test NTP",
            "pattern": "ntp",
            "test": "contains",
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])

    def task_with_skip(task):
        r = task.run(
            task=nr_test,
            ret_data_per_host={
                "IOL1": "should be skipped",
                "IOL2": "should be skipped",
            },
            name="setup task",
        )
        # Mark the first result to be skipped
        r[0].skip_results = True

        task.run(
            task=nr_test,
            ret_data_per_host={
                "IOL1": "ntp server 7.7.7.8",
                "IOL2": "ntp server 7.7.7.7",
            },
            name="show ntp",
        )
        return Result(host=task.host)

    output = nr_with_tests.run(task=task_with_skip)
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    # The test should match "show ntp" task, not the skipped "setup task"
    assert check_result["IOL1"]["Test NTP"]["result"] == "PASS"
    assert check_result["IOL2"]["Test NTP"]["result"] == "PASS"


# ======================================================================
# Eval test with structured data
# ======================================================================


@skip_if_no_nornir
def test_eval_with_structured_data():
    """Test eval expression against structured data (dict result)."""
    tests = [
        {
            "task": "get facts",
            "name": "Test uptime eval",
            "expr": "result['uptime'] > 3600",
            "test": "eval",
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": {"uptime": 7200, "hostname": "r1"},
            "IOL2": {"uptime": 1800, "hostname": "r2"},
        },
        name="get facts",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    assert check_result["IOL1"]["Test uptime eval"]["result"] == "PASS"
    assert check_result["IOL2"]["Test uptime eval"]["result"] == "FAIL"


# ======================================================================
# Test with empty pattern
# ======================================================================


@skip_if_no_nornir
def test_contains_empty_pattern():
    """Test contains with empty string pattern - empty string is in every string."""
    tests = [
        {
            "task": "show ntp",
            "name": "Test empty pattern",
            "pattern": "",
            "test": "contains",
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={"IOL1": "any output", "IOL2": "any output"},
        name="show ntp",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=False)
    # Empty string is always in any string, so all should PASS
    for item in check_result:
        assert item["result"] == "PASS"


# ======================================================================
# Test single test kwargs constructor mode
# ======================================================================


@skip_if_no_nornir
def test_single_test_kwargs_with_eval():
    """Test passing single test as kwargs to TestsProcessor constructor."""
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors(
        [
            TestsProcessor(
                remove_tasks=True,
                task="show ntp",
                name="Test NTP eval kwargs",
                expr="'ntp' in result",
                test="eval",
            )
        ]
    )
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={"IOL1": "ntp server", "IOL2": "no data"},
        name="show ntp",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    assert check_result["IOL1"]["Test NTP eval kwargs"]["result"] == "PASS"
    assert check_result["IOL2"]["Test NTP eval kwargs"]["result"] == "FAIL"


# ======================================================================
# Test contains count with revert and err_msg
# ======================================================================


@skip_if_no_nornir
def test_contains_count_revert_with_err_msg():
    """Test contains with count and revert and custom err_msg."""
    tests = [
        {
            "task": "show ntp",
            "name": "Test count revert err_msg",
            "pattern": "ntp server",
            "test": "contains",
            "count": 2,
            "revert": True,
            "err_msg": "Found exactly 2 NTP servers",
        }
    ]
    nr.data.reset_failed_hosts()
    nr_with_tests = nr.with_processors([TestsProcessor(tests, remove_tasks=True)])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": "ntp server 1\nntp server 2",  # 2 matches - pass reversed to FAIL
            "IOL2": "ntp server 1",  # 1 match - fail reversed to PASS
        },
        name="show ntp",
    )
    check_result = ResultSerializer(output, add_details=True, to_dict=True)
    assert check_result["IOL1"]["Test count revert err_msg"]["result"] == "FAIL"
    assert (
        check_result["IOL1"]["Test count revert err_msg"]["exception"]
        == "Found exactly 2 NTP servers"
    )
    assert check_result["IOL2"]["Test count revert err_msg"]["result"] == "PASS"
