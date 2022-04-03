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
from nornir_salt.plugins.functions import InventoryFun

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
    connection_options:
      ncclient:
        port: 830
        extras:
          allow_agent: False
          hostkey_verify: False
          device_params:
            name: iosxe      
  eu:
    data:
      asn: 65100
  bma:
    groups:
        - eu
        - global

defaults:
  data:
    location: earth
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


# ----------------------------------------------------------------------
# tests that need Nornir
# ----------------------------------------------------------------------


@skip_if_no_nornir
def test_InventoryFun_create_host():
    nr = init(lab_inventory_dict)
    host_data = {
        "name": "IOL3",
        "hostname": "192.168.217.99",
        "platform": "ios",
        "groups": ["lab", "bma"],
        "connection_options": {
            "napalm": {
                "port": 2022,
                "extras": {
                    "foo": "bar"
                }
            }
        }
    }
    
    res = InventoryFun(nr, "create_host", **host_data)

    assert res == True
    # check data
    assert nr.inventory.hosts["IOL3"].platform == "ios"
    assert nr.inventory.hosts["IOL3"].hostname == "192.168.217.99"
    assert nr.inventory.hosts["IOL3"].get("domain") == "global.local"
    assert nr.inventory.hosts["IOL3"].get("asn") == 65100
    # check connection options
    assert nr.inventory.hosts["IOL3"].get_connection_parameters("ncclient").extras == {
        'allow_agent': False, 'hostkey_verify': False, 'device_params': {'name': 'iosxe'}
    }
    assert nr.inventory.hosts["IOL3"].get_connection_parameters("napalm").port == 2022
    assert nr.inventory.hosts["IOL3"].get_connection_parameters("napalm").extras == {"foo": "bar"}
    # check defaults
    assert nr.inventory.hosts["IOL3"].get("location") == "earth"
    
# test_InventoryFun_add_host()


@skip_if_no_nornir
def test_InventoryFun_delete_host():
    nr = init(lab_inventory_dict)
    res = InventoryFun(nr, "delete_host", name="IOL2")
    assert res == True
    assert "IOL2" not in nr.inventory.hosts
    assert "IOL1" in nr.inventory.hosts
    
# test_InventoryFun_delete_host()

@skip_if_no_nornir
def test_InventoryFun_delete_hosts():
    nr = init(lab_inventory_dict)
    res = InventoryFun(nr, "delete_host", name=["IOL2", "IOL1"])
    assert res == True
    assert "IOL2" not in nr.inventory.hosts
    assert "IOL1" not in nr.inventory.hosts
    
# test_InventoryFun_delete_hosts()

@skip_if_no_nornir
def test_InventoryFun_update_host_groups_append():
    nr = init(lab_inventory_dict)
    host_data = {
        "name": "IOL2",
        "hostname": "192.168.217.99",
        "platform": "ios_xe",
        "username": "new_username",
        "password": "new_password",
        "port": 123,
        "groups": ["lab", "bma"],
        "data": {
            "made_by": "humans",
        },
        "connection_options": {
            "napalm": {
                "port": 2022,
                "extras": {
                    "foo": "bar1"
                }
            }
        }
    }
    
    res = InventoryFun(nr, "update_host", groups_action="append", **host_data)
    
    assert res == True
    # check data
    assert nr.inventory.hosts["IOL2"].platform == "ios_xe"
    assert nr.inventory.hosts["IOL2"].hostname == "192.168.217.99"
    assert nr.inventory.hosts["IOL2"].username == "new_username"
    assert nr.inventory.hosts["IOL2"].password == "new_password"
    assert nr.inventory.hosts["IOL2"].port == 123
    assert nr.inventory.hosts["IOL2"].get("domain") == "global.local"
    assert nr.inventory.hosts["IOL2"].get("asn") == 65100
    assert nr.inventory.hosts["IOL2"].get("made_by") == "humans"
    # check connection options
    assert nr.inventory.hosts["IOL2"].get_connection_parameters("ncclient").extras == {
        'allow_agent': False, 'hostkey_verify': False, 'device_params': {'name': 'iosxe'}
    }
    assert nr.inventory.hosts["IOL2"].get_connection_parameters("napalm").port == 2022
    assert nr.inventory.hosts["IOL2"].get_connection_parameters("napalm").extras == {"foo": "bar1"}
    # check defaults
    assert nr.inventory.hosts["IOL2"].get("location") == "earth"    
    
# test_InventoryFun_update_host_groups_append()

@skip_if_no_nornir
def test_InventoryFun_update_host_groups_insert():
    nr = init(lab_inventory_dict)
    host_data = {
        "name": "IOL2",
        "groups": ["bma"],
        "groups_action": "insert"
    }
    res = InventoryFun(nr, "update_host", **host_data)
    assert res == True
    assert nr.inventory.groups["bma"] == nr.inventory.hosts["IOL2"].groups[0]
    
# test_InventoryFun_update_host_groups_insert()

@skip_if_no_nornir
def test_InventoryFun_update_host_groups_remove():
    nr = init(lab_inventory_dict)
    host_data = {
        "name": "IOL2",
        "groups": ["bma", "lab"],
        "groups_action": "remove"
    }
    res = InventoryFun(nr, "update_host", **host_data)
    assert res == True
    assert nr.inventory.groups["bma"] not in nr.inventory.hosts["IOL2"].groups
    assert nr.inventory.groups["lab"] not in nr.inventory.hosts["IOL2"].groups
    assert nr.inventory.groups["eu"] in nr.inventory.hosts["IOL2"].groups
    
# test_InventoryFun_update_host_groups_remove()

def test_InventoryFun_load():
    nr = init(lab_inventory_dict)
    data = [
        {
            "call": "create_host",
            "name": "IOL3",
            "hostname": "192.168.217.99",
            "platform": "ios",
            "groups": ["lab", "bma"],
        },
        {
            "call": "delete_host",
            "name": "IOL2",
        },   
        {
            "call": "update_host",
            "name": "IOL1",
            "hostname": "1.2.3.4",
            "platform": "ios_xe",
            "groups": ["bma"],
            "groups_action": "remove"
        },
        {
            "call": "create",
            "name": "IOL4",
            "hostname": "192.168.217.4",
            "platform": "iosxr",
            "groups": ["lab"],
        },        
    ]
    
    res = InventoryFun(nr, "load", data=data)
    
    assert res == True
    # check hosts deleted/created
    assert "IOL2" not in nr.inventory.hosts
    assert "IOL3" in nr.inventory.hosts
    assert "IOL4" in nr.inventory.hosts
    # check IOL3
    assert nr.inventory.hosts["IOL3"].platform == "ios"
    assert nr.inventory.hosts["IOL3"].hostname == "192.168.217.99"
    assert nr.inventory.hosts["IOL3"].get("domain") == "global.local"
    assert nr.inventory.hosts["IOL3"].get("asn") == 65100
    # check IOL4
    assert nr.inventory.hosts["IOL4"].platform == "iosxr"
    assert nr.inventory.hosts["IOL4"].hostname == "192.168.217.4"
    assert nr.inventory.hosts["IOL4"].username == "cisco"
    assert nr.inventory.hosts["IOL4"].password == "cisco"
    # check IOL1
    assert nr.inventory.hosts["IOL1"].platform == "ios_xe"
    assert nr.inventory.hosts["IOL1"].hostname == "1.2.3.4"
    assert nr.inventory.groups["bma"] not in nr.inventory.hosts["IOL1"].groups
    assert nr.inventory.hosts["IOL1"].get("domain") != "global.local"
    
# test_InventoryFun_load()

def test_InventoryFun_read_host():
    nr = init(lab_inventory_dict)
    res = InventoryFun(nr, "read", FB="IOL[13]")
    # pprint.pprint(res)
    assert "IOL1" in res
    assert "IOL2" not in res
    
# test_InventoryFun_read_host()


def test_InventoryFun_read_inventory():
    nr = init(lab_inventory_dict)
    res = InventoryFun(nr, "read_inventory", FB="IOL1")
    pprint.pprint(res)
    assert "hosts" in res
    assert "IOL1" in res["hosts"]
    assert "IOL2" not in res["hosts"]
    assert "defaults" in res
    assert "groups" in res
    
# test_InventoryFun_read_inventory()


def test_InventoryFun_list_hosts():
    nr = init(lab_inventory_dict)
    res = InventoryFun(nr, "list_hosts", FB="*")
    assert isinstance(res, list)
    assert "IOL1" in res
    assert "IOL2" in res
    assert len(res) == 2
    
# test_InventoryFun_list_hosts()