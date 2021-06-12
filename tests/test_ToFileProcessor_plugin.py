import sys
import pprint
import logging
import yaml
import pytest
sys.path.insert(0,'..')

try:
    from nornir import InitNornir
    from nornir.core.plugins.inventory import InventoryPluginRegister
    from nornir.core.task import Result

    HAS_NORNIR = True
except ImportError:
    HAS_NORNIR = False
    
from nornir_salt import ResultSerializer
from nornir_salt import DictInventory
from nornir_salt import nr_test
from nornir_salt.plugins.processors.TestsProcessor import ToFileProcessor


logging.basicConfig(level=logging.ERROR)


# ----------------------------------------------------------------------
# Initialize Nornir
# ----------------------------------------------------------------------


skip_if_no_nornir = pytest.mark.skipif(
    HAS_NORNIR == False, 
    reason="Failed to import all required Nornir modules and plugins"
)
skip_if_no_lab = None

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
        runner={
            "plugin": "serial"
        },
        inventory={
            "plugin": "DictInventory",
            "options": {
                "hosts": opts["hosts"],
                "groups": opts.get("groups", {}),
                "defaults": opts.get("defaults", {}),
            }
        },
    )
    
    return nr
    
InventoryPluginRegister.register("DictInventory", DictInventory)

nr = init(lab_inventory_dict)


# ----------------------------------------------------------------------
# tests that need Nornir
# ----------------------------------------------------------------------

@skip_if_no_nornir
def test_to_file():
    nr_with_tests =nr.with_processors([
        ToFileProcessor(tf="config", base_url="./tofile_outputs/")   
    ])
    output = nr_with_tests.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": """
ntp server 7.7.7.8
ntp server 7.7.7.7
        """,
            "IOL2": """
ntp server 7.7.7.7
        """
        },
        name="show run | inc ntp"
    )
	
test_to_file()