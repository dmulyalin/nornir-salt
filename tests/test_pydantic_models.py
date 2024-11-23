"""
Test docs code examples
"""
import sys
import pprint
import logging
import yaml
import pytest
import socket

sys.path.insert(0, "..")

try:
    from nornir import InitNornir
    from nornir.core.plugins.inventory import InventoryPluginRegister
    from nornir.core.plugins.runners import RunnersPluginRegister
    from nornir.core.task import Result

    HAS_NORNIR = True
except ImportError:
    HAS_NORNIR = False

from nornir_salt.plugins.functions import ResultSerializer
from nornir_salt.plugins.inventory import DictInventory
from nornir_salt.plugins.tasks import nr_test
from nornir_salt.plugins.processors import DataProcessor
from nornir_salt.plugins.tasks import netmiko_send_commands
from nornir_salt.plugins.runners import RetryRunner
from nornir_salt.utils.pydantic_models import modelTestsProcessorSuite

from pydantic import ValidationError

logging.basicConfig(level=logging.ERROR)
InventoryPluginRegister.register("DictInventory", DictInventory)
RunnersPluginRegister.register("RetryRunner", RetryRunner)

skip_if_no_nornir = pytest.mark.skipif(
    HAS_NORNIR == False,
    reason="Failed to import all required Nornir modules and plugins",
)

# ---------------------------------------------------
# cisco always on ios xe lab details
# ---------------------------------------------------
cisco_iosxe_always_on_router = """
hosts:
  sandbox-iosxe-latest-1:
    hostname: "sandbox-iosxe-latest-1.cisco.com"
    platform: ios
    username: developer
    password: C1sco12345
"""
s = socket.socket()
s.settimeout(1)
status = s.connect_ex(("sandbox-iosxe-latest-1.cisco.com", 22))
if status == 0:
    has_connection_to_cisco_iosxe_always_on_router = True
else:
    has_connection_to_cisco_iosxe_always_on_router = False
skip_if_has_no_cisco_iosxe_always_on_router = pytest.mark.skipif(
    has_connection_to_cisco_iosxe_always_on_router == False,
    reason="Has no connection to sandbox-iosxe-latest-1.cisco.com router",
)

cisco_iosxe_always_on_router_dict = yaml.safe_load(cisco_iosxe_always_on_router)


def init(opts):
    """
    Initiate nornir by calling InitNornir()
    """
    nr = InitNornir(
        logging={"enabled": False},
        runner={
            "plugin": "RetryRunner",
            "options": {
                "task_retry": 3,
                "connect_retry": 3,
            },
        },
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


@skip_if_has_no_cisco_iosxe_always_on_router
@skip_if_no_nornir
def test_model_netmiko_send_commands():
    nr = init(cisco_iosxe_always_on_router_dict)
    res = nr.run(
        task=netmiko_send_commands,
        commands=["show clock"],
        repeat=1.5,
    )
    ret = ResultSerializer(res, add_details=True)
    pprint.pprint(ret)
    assert ret["sandbox-iosxe-latest-1"]["netmiko_send_commands"]["failed"] == True
    assert ret["sandbox-iosxe-latest-1"]["netmiko_send_commands"]["task_retry"] == 0
    assert (
        "validation error"
        in ret["sandbox-iosxe-latest-1"]["netmiko_send_commands"]["exception"]
    )


@skip_if_no_nornir
def test_model_nr_test():
    nr = init(cisco_iosxe_always_on_router_dict)
    good_res = nr.run(
        task=nr_test,
        command="show clock",
        excpt=None,
        run_task_retry=0,
        excpt_msg="foobar",
    )
    good_ret = ResultSerializer(good_res, add_details=True)
    pprint.pprint(good_ret)

    bad_res = nr.run(
        task=nr_test, command="show clock", run_task_retry=0, excpt_msg=123
    )
    bad_ret = ResultSerializer(bad_res, add_details=True)
    pprint.pprint(bad_ret)

    assert good_ret["sandbox-iosxe-latest-1"]["nr_test"]["failed"] == False
    assert good_ret["sandbox-iosxe-latest-1"]["nr_test"]["result"] == {
        "command": "show clock"
    }

    assert bad_ret["sandbox-iosxe-latest-1"]["nr_test"]["failed"] == True
    assert "ValidationError" in bad_ret["sandbox-iosxe-latest-1"]["nr_test"]["result"]


def test_modelTestsProcessorSuite_wrong_test_name():
    tests = [
        {
            "task": "show run | inc ntp",
            "name": "Test NTP config",
            "test": "wrong_name",
        }
    ]
    with pytest.raises(ValidationError):
        _ = modelTestsProcessorSuite(tests=tests)


def test_modelTestsProcessorSuite_no_task():
    tests = [
        {
            "name": "Test NTP config",
            "test": "contains",
        }
    ]
    with pytest.raises(ValidationError) as e:
        _ = modelTestsProcessorSuite(tests=tests)
    assert "No task defined for test" in str(e.value)


def test_modelTestsProcessorSuite_no_task_but_use_all_tasks():
    tests = [
        {
            "name": "Test NTP config",
            "test": "contains",
            "pattern": "foo",
            "use_all_tasks": True,
        }
    ]
    _ = modelTestsProcessorSuite(tests=tests)


def test_modelTestsProcessorSuite_no_pattern():
    tests = [
        {
            "name": "Test NTP config",
            "task": "foo",
            "test": "contains",
        }
    ]
    with pytest.raises(ValidationError) as e:
        _ = modelTestsProcessorSuite(tests=tests)
    assert "No pattern provided for test" in str(e.value)


def test_modelTestsProcessorSuite_no_schema():
    tests = [
        {
            "name": "Test NTP config",
            "task": "foo",
            "test": "cerberus",
        }
    ]
    with pytest.raises(ValidationError) as e:
        _ = modelTestsProcessorSuite(tests=tests)
    assert "No schema provided for test" in str(e.value)


def test_modelTestsProcessorSuite_no_expr():
    tests = [
        {
            "name": "Test NTP config",
            "task": "foo",
            "test": "eval",
        }
    ]
    with pytest.raises(ValidationError) as e:
        _ = modelTestsProcessorSuite(tests=tests)
    assert "No evaluate expression provided for test" in str(e.value)
