import sys
import pprint
import logging
import yaml
import pytest

sys.path.insert(0, "..")

try:
    from nornir import InitNornir
    from nornir.core.plugins.inventory import InventoryPluginRegister

    HAS_NORNIR = True
except ImportError:
    HAS_NORNIR = False

from nornir_salt import ResultSerializer
from nornir_salt import DictInventory
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
    groups: [lab, bma]
  IOL2:
    hostname: 192.168.217.7
    platform: ios
    groups: [lab, eu]
    
groups: 
  lab:
    username: cisco
    password: cisco
  global:
    data:
      domain: global.local
      asn: 1
  eu:
    data:
      asn: 65100
  bma:
    groups:
        - eu
        - global
        
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
def test_DictInvetnory_nested_groups():
    assert nr.inventory.hosts["IOL1"].get("asn") == 65100
    assert nr.inventory.hosts["IOL1"].get("domain") == "global.local"
    assert nr.inventory.hosts["IOL2"].get("asn") == 65100
    assert nr.inventory.hosts["IOL2"].get("domain") is None

# test_DictInvetnory_nested_groups()