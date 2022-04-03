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
from nornir_salt.plugins.runners import QueueRunner

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
        runner={"plugin": "QueueRunner"},
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

nr = init(lab_inventory_dict)


# ----------------------------------------------------------------------
# tests that need Nornir
# ----------------------------------------------------------------------


@skip_if_no_nornir
def test_nr_runner_QueueRunner_with_connection_name():
    output = nr.run(
        task=nr_test,
        name="check ntp config",
		connection_name="netmiko",
    )
    result = ResultSerializer(output)
    pprint.pprint(result)
	# verify output does not contains connection_name k/v pair
    assert result == {'IOL1': {'check ntp config': {}}, 'IOL2': {'check ntp config': {}}}

# test_nr_runner_QueueRunner_with_connection_name()