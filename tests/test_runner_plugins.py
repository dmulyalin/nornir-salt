import sys
import pprint
import logging
import yaml
import pytest

sys.path.insert(0, "..")

try:
    from nornir import InitNornir
    from nornir.core.plugins.runners import RunnersPluginRegister

    HAS_NORNIR = True
except ImportError:
    HAS_NORNIR = False

from nornir_salt.plugins.functions import ResultSerializer
from nornir_salt.plugins.inventory import DictInventory
from nornir_salt.plugins.tasks import nr_test
from nornir_salt.plugins.runners import QueueRunner, RetryRunner
from nornir_salt.plugins.tasks import netmiko_send_commands


logging.basicConfig(level=logging.ERROR)


# ----------------------------------------------------------------------
# Initialize Nornir
# ----------------------------------------------------------------------


skip_if_no_nornir = pytest.mark.skipif(
    HAS_NORNIR == False,
    reason="Failed to import all required Nornir modules and plugins",
)


def init(opts, runner):
    """
    Initiate nornir by calling InitNornir()
    """
    global skip_if_no_lab

    nr = InitNornir(
        logging={"enabled": False},
        runner={"plugin": runner},
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


RunnersPluginRegister.register("QueueRunner", QueueRunner)
RunnersPluginRegister.register("RetryRunner", RetryRunner)


# ----------------------------------------------------------------------
# tests that need Nornir
# ----------------------------------------------------------------------


@skip_if_no_nornir
def test_nr_runner_QueueRunner_with_connection_name():
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
    nr = init(lab_inventory_dict, "QueueRunner")
    output = nr.run(
        task=nr_test,
        name="check ntp config",
        connection_name="netmiko",
    )
    result = ResultSerializer(output)
    pprint.pprint(result)
    # verify output does not contains connection_name k/v pair
    assert result == {
        "IOL1": {"check ntp config": {}},
        "IOL2": {"check ntp config": {}},
    }


# test_nr_runner_QueueRunner_with_connection_name()


@skip_if_no_nornir
def test_retry_runner_connection_check_failed():
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
    nr = init(lab_inventory_dict, "RetryRunner")
    output = nr.run(
        task=netmiko_send_commands,
        name="check ntp config",
        connection_name="netmiko",
        commands=["show clock"],
        run_connect_retry=0,
    )
    result = ResultSerializer(output)
    pprint.pprint(result)

    for hostname, results in result.items():
        for result_name, result_data in results.items():
            assert (
                "TCP connection error: 'timed out'" in result_data
            ), f"'{hostname}' unexpected results: {result_data}"


@skip_if_no_nornir
def test_retry_runner_connection_check_failed_custom_port():
    lab_inventory = """
hosts:
  IOL1:
    hostname: 192.168.217.10
    platform: ios
    port: 122
    groups: [lab]
  IOL2:
    hostname: 192.168.217.7
    platform: ios
    port: 321
    groups: [lab]

groups:
  lab:
    username: cisco
    password: cisco

defaults: {}
"""
    lab_inventory_dict = yaml.safe_load(lab_inventory)
    nr = init(lab_inventory_dict, "RetryRunner")
    output = nr.run(
        task=netmiko_send_commands,
        name="check ntp config",
        connection_name="netmiko",
        commands=["show clock"],
        run_connect_retry=0,
    )
    result = ResultSerializer(output)
    pprint.pprint(result)

    for hostname, results in result.items():
        for result_name, result_data in results.items():
            assert (
                "TCP connection error: 'timed out'" in result_data
            ), f"'{hostname}' unexpected results: {result_data}"
            if hostname == "IOL1":
                assert "192.168.217.10:122" in result_data
            elif hostname == "IOL2":
                assert "192.168.217.7:321" in result_data


@skip_if_no_nornir
def test_retry_runner_connection_check_failed_connection_params():
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
    connection_options:
      netmiko:
        port: 123

defaults: {}
"""
    lab_inventory_dict = yaml.safe_load(lab_inventory)
    nr = init(lab_inventory_dict, "RetryRunner")
    output = nr.run(
        task=netmiko_send_commands,
        name="check ntp config",
        connection_name="netmiko",
        commands=["show clock"],
        run_connect_retry=0,
    )
    result = ResultSerializer(output)
    pprint.pprint(result)

    for hostname, results in result.items():
        for result_name, result_data in results.items():
            assert (
                "TCP connection error: 'timed out'" in result_data
            ), f"'{hostname}' unexpected results: {result_data}"
            if hostname == "IOL1":
                assert "192.168.217.10:123" in result_data
            elif hostname == "IOL2":
                assert "192.168.217.7:123" in result_data


@skip_if_no_nornir
def test_retry_runner_connection_check():
    lab_inventory = """
hosts:
  ceos-spine-1:
    hostname: 192.168.1.130
    platform: arista_eos
    username: admin
    password: admin
    port: 2200
"""
    lab_inventory_dict = yaml.safe_load(lab_inventory)
    nr = init(lab_inventory_dict, "RetryRunner")
    output = nr.run(
        task=netmiko_send_commands,
        name="check ntp config",
        connection_name="netmiko",
        commands=["show clock"],
        run_connect_retry=1,
    )
    result = ResultSerializer(output)
    pprint.pprint(result)

    assert "error" not in result["ceos-spine-1"]["show clock"]
