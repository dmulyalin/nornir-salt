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

from nornir_salt.plugins.functions import ResultSerializer
from nornir_salt.plugins.inventory import DictInventory
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


lab_inventory_no_hosts = """
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
lab_inventory_dict_no_hosts = yaml.safe_load(lab_inventory_no_hosts)


def init(opts):
    """
    Initiate nornir by calling InitNornir()
    """
    global skip_if_no_lab

    options = {}
    if "hosts" in opts:
        options["hosts"] = opts["hosts"]
    if "groups" in opts:
        options["groups"] = opts["groups"]
    if "defaults" in opts:
        options["defaults"] = opts["defaults"]
        
    nr = InitNornir(
        logging={"enabled": False},
        runner={"plugin": "serial"},
        inventory={
            "plugin": "DictInventory",
            "options": options
        },
    )

    return nr


InventoryPluginRegister.register("DictInventory", DictInventory)



# ----------------------------------------------------------------------
# tests that need Nornir
# ----------------------------------------------------------------------


@skip_if_no_nornir
def test_DictInvetnory_nested_groups():
    nr = init(lab_inventory_dict)
    assert nr.inventory.hosts["IOL1"].get("asn") == 65100
    assert nr.inventory.hosts["IOL1"].get("domain") == "global.local"
    assert nr.inventory.hosts["IOL2"].get("asn") == 65100
    assert nr.inventory.hosts["IOL2"].get("domain") is None

#test_DictInvetnory_nested_groups()

@skip_if_no_nornir
def test_DictInvetnory_no_hosts():
    nr = init(lab_inventory_dict_no_hosts)
    # import ipdb; ipdb.set_trace()
    inventory = nr.inventory.dict()
    assert inventory["hosts"] == {}
    assert len(inventory["groups"]) > 0
    assert len(inventory["defaults"]) > 0
    
# test_DictInvetnory_no_hosts()

@skip_if_no_nornir
def test_DictInvetnory_empty_inventory():
    nr = init({})
    # import ipdb; ipdb.set_trace()
    inventory = nr.inventory.dict()
    assert inventory["hosts"] == {}
    assert inventory["groups"] == {}
    assert all(v in [None, {}] for v in inventory["defaults"].values())
    
# test_DictInvetnory_empty_inventory()

@skip_if_no_nornir
def test_DictInvetnory_hosts_are_none():
    inventory_data = yaml.safe_load(lab_inventory_no_hosts)
    inventory_data["hosts"] = None
    nr = init(inventory_data)
    # import ipdb; ipdb.set_trace()
    inventory = nr.inventory.dict()
    assert inventory["hosts"] == {}
    assert len(inventory["groups"]) > 0
    assert len(inventory["defaults"]) > 0
    
# test_DictInvetnory_empty_inventory()