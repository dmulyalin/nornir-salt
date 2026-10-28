"""
Test docs code examples
"""

import logging
import pprint
import socket
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
from nornir_salt.plugins.processors import DataProcessor
from nornir_salt.plugins.tasks import netmiko_send_commands, nr_test

logging.basicConfig(level=logging.ERROR)
InventoryPluginRegister.register("DictInventory", DictInventory)

skip_if_no_nornir = pytest.mark.skipif(
    HAS_NORNIR == False,
    reason="Failed to import all required Nornir modules and plugins",
)

lab_inventory = yaml.safe_load("""
hosts:
  csr1k-r1:
    hostname: containerlab.lab
    platform: ios
    username: admin
    password: admin
    port: 2207
""")


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
def test_run_ttp_docs():
    host = lab_inventory["hosts"]["csr1k-r1"]
    try:
        with socket.create_connection((host["hostname"], host["port"]), timeout=1):
            pass
    except OSError as exc:
        pytest.skip(f"IOS XE lab unavailable: {exc}")
    nr = init(lab_inventory)

    # define TTP template with inputs having commands attributes
    template = """
<input name="arp">
commands = ["show arp"]
</input>

<input name="version">
commands = ["show version"]
</input>

<group name="arp_cache*" input="arp">
Internet  {{ ip }}   {{ age }}   {{ mac }}  ARPA   {{ interface }}
</group>

<group name="facts.version" input="version">
Cisco IOS XE Software, Version {{ ios_xe_version }}
</group>
    """

    # add data processor with run_ttp function
    nr_with_dp = nr.with_processors(
        [DataProcessor([{"fun": "run_ttp", "template": template}])]
    )

    # run task; commands for task will be dynamically populated by DataProcessor
    # run_ttp function with commands defined within TTP template inputs
    result = nr_with_dp.run(task=netmiko_send_commands)

    nr.close_connections()
    assert not result.failed, ResultSerializer(result, add_details=True)

    # serialize results to dictionary
    dict_result = ResultSerializer(result)

    pprint.pprint(dict_result)
    parsed = dict_result["csr1k-r1"]["run_ttp"][0]
    assert len(parsed) == 2
    # A fresh lab device may have an empty ARP table.
    assert parsed[0] == {} or "arp_cache" in parsed[0]
    assert parsed[1]["facts"]["version"]["ios_xe_version"]


# test_run_ttp_docs()
