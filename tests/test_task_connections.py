"""
At the moment this does not tests apat from testing import of PyGNMI library and gNMI
connecton and task plugins.

Was not able to find always-on endpoints that can test using gNMI, Cisco sandboxes has gRPC
API available but that is different.
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
    from nornir.core.task import Result

    HAS_NORNIR = True
except ImportError:
    HAS_NORNIR = False

from nornir_salt.plugins.functions import ResultSerializer
from nornir_salt.plugins.inventory import DictInventory
from nornir_salt.plugins.tasks import connections

logging.basicConfig(level=logging.ERROR)
InventoryPluginRegister.register("DictInventory", DictInventory)

skip_if_no_nornir = pytest.mark.skipif(
    HAS_NORNIR == False,
    reason="Failed to import all required Nornir modules and plugins",
)

# ---------------------------------------------------
# cisco always on ios xr lab details
# ---------------------------------------------------
cisco_iosxr_always_on_router = """
hosts:
  sandbox-iosxr-1.cisco.com:
    hostname: "sandbox-iosxr-1.cisco.com"
    platform: iosxr
    username: admin
    password: C1sco12345
    port: 57777
    connection_options:
      conn_test:
        port: 1234
"""
try:
    s = socket.socket()
    s.settimeout(1)
    s.connect(("sandbox-iosxr-1.cisco.com", 22))
    has_connection_to_cisco_iosxr_always_on_router = True
except:
    has_connection_to_cisco_iosxr_always_on_router = False

skip_if_has_no_cisco_iosxr_always_on_router = pytest.mark.skipif(
    has_connection_to_cisco_iosxr_always_on_router == False,
    reason="Has no connection to sandbox-iosxr-1.cisco.com router",
)

cisco_iosxr_always_on_router_dict = yaml.safe_load(cisco_iosxr_always_on_router)


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


@skip_if_no_nornir
@skip_if_has_no_cisco_iosxr_always_on_router
def test_connection_check():
    nr = init(cisco_iosxr_always_on_router_dict)
    output = nr.run(
        task=connections,
        call="check",
        connection_name=None,
        name="check base connection",
    )
    result = ResultSerializer(output, add_details=True)

    pprint.pprint(result)

    assert (
        result["sandbox-iosxr-1.cisco.com"]["connections"]["result"] == True
    ), "Unexpected connection check result"


@skip_if_no_nornir
@skip_if_has_no_cisco_iosxr_always_on_router
def test_connection_check_with_conn_name():
    nr = init(cisco_iosxr_always_on_router_dict)
    output = nr.run(
        task=connections,
        call="check",
        connection_name="conn_test",
        name="check connection by name",
    )
    result = ResultSerializer(output, add_details=True)

    pprint.pprint(result)

    assert (
        result["sandbox-iosxr-1.cisco.com"]["connections"]["result"] == False
    ), "Connection check should have failed"


@skip_if_no_nornir
@skip_if_has_no_cisco_iosxr_always_on_router
def test_connection_check_non_existing_conn_name():
    nr = init(cisco_iosxr_always_on_router_dict)
    output = nr.run(
        task=connections,
        call="check",
        connection_name="non_exist",
        name="check non existing connection",
    )
    result = ResultSerializer(output, add_details=True)

    pprint.pprint(result)

    assert (
        result["sandbox-iosxr-1.cisco.com"]["connections"]["result"] == True
    ), "Connection check should not have failed"
