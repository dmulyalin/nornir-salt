"""
Notes:

1. Below tests will not pass for nornir 3.0.0; should pass for nornir 3.1.0 and above
de to this PR - https://github.com/nornir-automation/nornir/pull/623
"""

import sys
import yaml
import pprint

sys.path.insert(0, "..")

from nornir import InitNornir
from nornir.core.plugins.inventory import InventoryPluginRegister
    
# these libs imported from nornir_salt dir
from nornir_salt.plugins.functions import FFun, FFun_functions
from nornir_salt.plugins.inventory import DictInventory
    
inventory_data = """
hosts:
  R1:
    hostname: 192.168.1.151
    platform: ios
    groups: [lab]
    data:
      role: core
      site: B1
  R2:
    hostname: 192.168.1.153
    platform: ios
    groups: [lab]
    data:
      role: agg
      site: B2
  R3:
    hostname: 192.168.2.154
    platform: ios
    groups: [lab]
    data:
      role: agg
      site: B3
  SW1:
    hostname: 192.168.2.144
    platform: nxos_ssh
    groups: [lab, pod1]
    data:
      role: access
      site: B3

groups:
  lab:
    username: cisco
    password: cisco
  pod1:
    username: cisco@
    password: cisco
"""

inventory_dict = yaml.safe_load(inventory_data)
InventoryPluginRegister.register("DictInventory", DictInventory)

NornirObj = InitNornir(
    runner={"plugin": "serial"},
    inventory={
        "plugin": "DictInventory",
        "options": {
            "hosts": inventory_dict["hosts"],
            "groups": inventory_dict["groups"],
            "defaults": inventory_dict.get("defaults", {}),
        },
    },
)


def test_FB():
    res = FFun(NornirObj, FB="R[12]")
    res_dict = res.dict()
    hosts_dict = res_dict.get("inventory", {}).get("hosts")
    # pprint.pprint(hosts_dict)
    assert hosts_dict == {
        "R1": {
            "connection_options": {},
            "data": {"role": "core", "site": "B1"},
            "groups": ["lab"],
            "hostname": "192.168.1.151",
            "name": "R1",
            "password": None,
            "platform": "ios",
            "port": None,
            "username": None,
        },
        "R2": {
            "connection_options": {},
            "data": {"role": "agg", "site": "B2"},
            "groups": ["lab"],
            "hostname": "192.168.1.153",
            "name": "R2",
            "password": None,
            "platform": "ios",
            "port": None,
            "username": None,
        },
    }

def test_FB_list():
    res = FFun(NornirObj, FB=["R[12]", "SW*"])
    res_dict = res.dict()
    hosts_dict = res_dict.get("inventory", {}).get("hosts")
    # pprint.pprint(hosts_dict)
    assert hosts_dict == {'R1': {'connection_options': {},
                                 'data': {'role': 'core', 'site': 'B1'},
                                 'groups': ['lab'],
                                 'hostname': '192.168.1.151',
                                 'name': 'R1',
                                 'password': None,
                                 'platform': 'ios',
                                 'port': None,
                                 'username': None},
                         'R2': {'connection_options': {},
                                 'data': {'role': 'agg', 'site': 'B2'},
                                 'groups': ['lab'],
                                 'hostname': '192.168.1.153',
                                 'name': 'R2',
                                 'password': None,
                                 'platform': 'ios',
                                 'port': None,
                                 'username': None},
                         'SW1': {'connection_options': {},
                                 'data': {'role': 'access', 'site': 'B3'},
                                 'groups': ['lab', 'pod1'],
                                 'hostname': '192.168.2.144',
                                 'name': 'SW1',
                                 'password': None,
                                 'platform': 'nxos_ssh',
                                 'port': None,
                                 'username': None}}
# test_FB_list()


def test_FB_comma_separated_list():
    res = FFun(NornirObj, FB="R[12], SW*")
    res_dict = res.dict()
    hosts_dict = res_dict.get("inventory", {}).get("hosts")
    # pprint.pprint(hosts_dict)
    assert hosts_dict == {'R1': {'connection_options': {},
                                 'data': {'role': 'core', 'site': 'B1'},
                                 'groups': ['lab'],
                                 'hostname': '192.168.1.151',
                                 'name': 'R1',
                                 'password': None,
                                 'platform': 'ios',
                                 'port': None,
                                 'username': None},
                         'R2': {'connection_options': {},
                                 'data': {'role': 'agg', 'site': 'B2'},
                                 'groups': ['lab'],
                                 'hostname': '192.168.1.153',
                                 'name': 'R2',
                                 'password': None,
                                 'platform': 'ios',
                                 'port': None,
                                 'username': None},
                         'SW1': {'connection_options': {},
                                 'data': {'role': 'access', 'site': 'B3'},
                                 'groups': ['lab', 'pod1'],
                                 'hostname': '192.168.2.144',
                                 'name': 'SW1',
                                 'password': None,
                                 'platform': 'nxos_ssh',
                                 'port': None,
                                 'username': None}}
# test_FB_comma_separated_list()


def test_FC():
    res = FFun(NornirObj, FC="R1")
    res_dict = res.dict()
    hosts_dict = res_dict.get("inventory", {}).get("hosts")
    # pprint.pprint(hosts_dict)
    assert hosts_dict == {
        "R1": {
            "connection_options": {},
            "data": {"role": "core", "site": "B1"},
            "groups": ["lab"],
            "hostname": "192.168.1.151",
            "name": "R1",
            "password": None,
            "platform": "ios",
            "port": None,
            "username": None,
        }
    }

def test_FC_list():
    res = FFun(NornirObj, FC=["R1", "SW"])
    res_dict = res.dict()
    hosts_dict = res_dict.get("inventory", {}).get("hosts")
    # pprint.pprint(hosts_dict)
    assert hosts_dict == {'R1': {'connection_options': {},
                                 'data': {'role': 'core', 'site': 'B1'},
                                 'groups': ['lab'],
                                 'hostname': '192.168.1.151',
                                 'name': 'R1',
                                 'password': None,
                                 'platform': 'ios',
                                 'port': None,
                                 'username': None},
                         'SW1': {'connection_options': {},
                                 'data': {'role': 'access', 'site': 'B3'},
                                 'groups': ['lab', 'pod1'],
                                 'hostname': '192.168.2.144',
                                 'name': 'SW1',
                                 'password': None,
                                 'platform': 'nxos_ssh',
                                 'port': None,
                                 'username': None}}
# test_FC_list()


def test_FC_comma_separated_list():
    res = FFun(NornirObj, FC="R1, SW")
    res_dict = res.dict()
    hosts_dict = res_dict.get("inventory", {}).get("hosts")
    # pprint.pprint(hosts_dict)
    assert hosts_dict == {'R1': {'connection_options': {},
                                 'data': {'role': 'core', 'site': 'B1'},
                                 'groups': ['lab'],
                                 'hostname': '192.168.1.151',
                                 'name': 'R1',
                                 'password': None,
                                 'platform': 'ios',
                                 'port': None,
                                 'username': None},
                         'SW1': {'connection_options': {},
                                 'data': {'role': 'access', 'site': 'B3'},
                                 'groups': ['lab', 'pod1'],
                                 'hostname': '192.168.2.144',
                                 'name': 'SW1',
                                 'password': None,
                                 'platform': 'nxos_ssh',
                                 'port': None,
                                 'username': None}}
# test_FC_comma_separated_list()


def test_FR():
    res = FFun(NornirObj, FR="R\d")
    res_dict = res.dict()
    hosts_dict = res_dict.get("inventory", {}).get("hosts")
    # pprint.pprint(hosts_dict)
    assert hosts_dict == {'R1': {'connection_options': {},
                                 'data': {'role': 'core', 'site': 'B1'},
                                 'groups': ['lab'],
                                 'hostname': '192.168.1.151',
                                 'name': 'R1',
                                 'password': None,
                                 'platform': 'ios',
                                 'port': None,
                                 'username': None},
                          'R2': {'connection_options': {},
                                 'data': {'role': 'agg', 'site': 'B2'},
                                 'groups': ['lab'],
                                 'hostname': '192.168.1.153',
                                 'name': 'R2',
                                 'password': None,
                                 'platform': 'ios',
                                 'port': None,
                                 'username': None},
                          'R3': {'connection_options': {},
                                 'data': {'role': 'agg', 'site': 'B3'},
                                 'groups': ['lab'],
                                 'hostname': '192.168.2.154',
                                 'name': 'R3',
                                 'password': None,
                                 'platform': 'ios',
                                 'port': None,
                                 'username': None}}
# test_FR()


def test_FR_list():
    res = FFun(NornirObj, FR=["R[12]", "SW\d"])
    res_dict = res.dict()
    hosts_dict = res_dict.get("inventory", {}).get("hosts")
    # pprint.pprint(hosts_dict)
    assert hosts_dict == {'R1': {'connection_options': {},
                                'data': {'role': 'core', 'site': 'B1'},
                                'groups': ['lab'],
                                'hostname': '192.168.1.151',
                                'name': 'R1',
                                'password': None,
                                'platform': 'ios',
                                'port': None,
                                'username': None},
                         'R2': {'connection_options': {},
                                'data': {'role': 'agg', 'site': 'B2'},
                                'groups': ['lab'],
                                'hostname': '192.168.1.153',
                                'name': 'R2',
                                'password': None,
                                'platform': 'ios',
                                'port': None,
                                'username': None},
                         'SW1': {'connection_options': {},
                                 'data': {'role': 'access', 'site': 'B3'},
                                 'groups': ['lab', 'pod1'],
                                 'hostname': '192.168.2.144',
                                 'name': 'SW1',
                                 'password': None,
                                 'platform': 'nxos_ssh',
                                 'port': None,
                                 'username': None}}
# test_FR_list()

def test_FO_list_of_dict():
    res = FFun(NornirObj, FO=[{"role": "agg", "platform": "ios"}, {"site": "B3"}])
    res_dict = res.dict()
    hosts_dict = res_dict.get("inventory", {}).get("hosts")
    # pprint.pprint(hosts_dict)
    assert hosts_dict == {
        "R2": {
            "connection_options": {},
            "data": {"role": "agg", "site": "B2"},
            "groups": ["lab"],
            "hostname": "192.168.1.153",
            "name": "R2",
            "password": None,
            "platform": "ios",
            "port": None,
            "username": None,
        },
        "R3": {
            "connection_options": {},
            "data": {"role": "agg", "site": "B3"},
            "groups": ["lab"],
            "hostname": "192.168.2.154",
            "name": "R3",
            "password": None,
            "platform": "ios",
            "port": None,
            "username": None,
        },
        "SW1": {
            "connection_options": {},
            "data": {"role": "access", "site": "B3"},
            "groups": ["lab", "pod1"],
            "hostname": "192.168.2.144",
            "name": "SW1",
            "password": None,
            "platform": "nxos_ssh",
            "port": None,
            "username": None,
        },
    }


# test_FO_list_of_dict()


def test_FO_dict():
    res = FFun(NornirObj, FO={"role": "agg", "platform": "ios"})
    res_dict = res.dict()
    hosts_dict = res_dict.get("inventory", {}).get("hosts")
    # pprint.pprint(hosts_dict)
    assert hosts_dict == {
        "R2": {
            "connection_options": {},
            "data": {"role": "agg", "site": "B2"},
            "groups": ["lab"],
            "hostname": "192.168.1.153",
            "name": "R2",
            "password": None,
            "platform": "ios",
            "port": None,
            "username": None,
        },
        "R3": {
            "connection_options": {},
            "data": {"role": "agg", "site": "B3"},
            "groups": ["lab"],
            "hostname": "192.168.2.154",
            "name": "R3",
            "password": None,
            "platform": "ios",
            "port": None,
            "username": None,
        },
    }


# test_FO_dict()


def test_FG():
    res = FFun(NornirObj, FG="pod1")
    res_dict = res.dict()
    hosts_dict = res_dict.get("inventory", {}).get("hosts")
    # pprint.pprint(hosts_dict)
    assert hosts_dict == {
        "SW1": {
            "connection_options": {},
            "data": {"role": "access", "site": "B3"},
            "groups": ["lab", "pod1"],
            "hostname": "192.168.2.144",
            "name": "SW1",
            "password": None,
            "platform": "nxos_ssh",
            "port": None,
            "username": None,
        }
    }


# test_FG()


def test_FP():
    res = FFun(NornirObj, FP="192.168.1.0/24, 192.168.2.144/31")
    res_dict = res.dict()
    hosts_dict = res_dict.get("inventory", {}).get("hosts")
    # pprint.pprint(hosts_dict)
    assert hosts_dict == {
        "R1": {
            "connection_options": {},
            "data": {"role": "core", "site": "B1"},
            "groups": ["lab"],
            "hostname": "192.168.1.151",
            "name": "R1",
            "password": None,
            "platform": "ios",
            "port": None,
            "username": None,
        },
        "R2": {
            "connection_options": {},
            "data": {"role": "agg", "site": "B2"},
            "groups": ["lab"],
            "hostname": "192.168.1.153",
            "name": "R2",
            "password": None,
            "platform": "ios",
            "port": None,
            "username": None,
        },
        "SW1": {
            "connection_options": {},
            "data": {"role": "access", "site": "B3"},
            "groups": ["lab", "pod1"],
            "hostname": "192.168.2.144",
            "name": "SW1",
            "password": None,
            "platform": "nxos_ssh",
            "port": None,
            "username": None,
        },
    }


# test_FP()


def test_FL():
    res = FFun(NornirObj, FL="R1, SW1")
    res_dict = res.dict()
    hosts_dict = res_dict.get("inventory", {}).get("hosts")
    # pprint.pprint(hosts_dict)
    assert hosts_dict == {
        "R1": {
            "connection_options": {},
            "data": {"role": "core", "site": "B1"},
            "groups": ["lab"],
            "hostname": "192.168.1.151",
            "name": "R1",
            "password": None,
            "platform": "ios",
            "port": None,
            "username": None,
        },
        "SW1": {
            "connection_options": {},
            "data": {"role": "access", "site": "B3"},
            "groups": ["lab", "pod1"],
            "hostname": "192.168.2.144",
            "name": "SW1",
            "password": None,
            "platform": "nxos_ssh",
            "port": None,
            "username": None,
        },
    }


# test_FL()


def test_FB_FG_FP_FO():
    res = FFun(NornirObj, FB="R*", FG="lab", FP="192.168.1.0/24", FO={"role": "core"})
    res_dict = res.dict()
    hosts_dict = res_dict.get("inventory", {}).get("hosts")
    # pprint.pprint(hosts_dict)
    assert hosts_dict == {
        "R1": {
            "connection_options": {},
            "data": {"role": "core", "site": "B1"},
            "groups": ["lab"],
            "hostname": "192.168.1.151",
            "name": "R1",
            "password": None,
            "platform": "ios",
            "port": None,
            "username": None,
        }
    }


# test_FB_FG_FP_FO()


def test_FB_with_FN():
    res = FFun(NornirObj, FB="R[12]", FN=True)
    res_dict = res.dict()
    hosts_dict = res_dict.get("inventory", {}).get("hosts")
    pprint.pprint(hosts_dict)
    assert hosts_dict == {'R3': {'connection_options': {},
                                 'data': {'role': 'agg', 'site': 'B3'},
                                 'groups': ['lab'],
                                 'hostname': '192.168.2.154',
                                 'name': 'R3',
                                 'password': None,
                                 'platform': 'ios',
                                 'port': None,
                                 'username': None},
                          'SW1': {'connection_options': {},
                                  'data': {'role': 'access', 'site': 'B3'},
                                  'groups': ['lab', 'pod1'],
                                  'hostname': '192.168.2.144',
                                  'name': 'SW1',
                                  'password': None,
                                  'platform': 'nxos_ssh',
                                  'port': None,
                                  'username': None}}

# test_FB_with_FN()


def test_FB_FG_FP_FO_FN():
    """ Should match all except R1 """
    res = FFun(NornirObj, FB="R*", FG="lab", FP="192.168.1.0/24", FO={"role": "core"}, FN=True)
    res_dict = res.dict()
    hosts_dict = res_dict.get("inventory", {}).get("hosts")
    # pprint.pprint(hosts_dict)
    assert hosts_dict == {'R2': {'connection_options': {},
                                 'data': {'role': 'agg', 'site': 'B2'},
                                 'groups': ['lab'],
                                 'hostname': '192.168.1.153',
                                 'name': 'R2',
                                 'password': None,
                                 'platform': 'ios',
                                 'port': None,
                                 'username': None},
                          'R3': {'connection_options': {},
                                 'data': {'role': 'agg', 'site': 'B3'},
                                 'groups': ['lab'],
                                 'hostname': '192.168.2.154',
                                 'name': 'R3',
                                 'password': None,
                                 'platform': 'ios',
                                 'port': None,
                                 'username': None},
                          'SW1': {'connection_options': {},
                                  'data': {'role': 'access', 'site': 'B3'},
                                  'groups': ['lab', 'pod1'],
                                  'hostname': '192.168.2.144',
                                  'name': 'SW1',
                                  'password': None,
                                  'platform': 'nxos_ssh',
                                  'port': None,
                                  'username': None}}

# test_FB_FG_FP_FO_FN()


def test_FL_with_FN():
    res = FFun(NornirObj, FL="R1, SW1", FN=True)
    res_dict = res.dict()
    hosts_dict = res_dict.get("inventory", {}).get("hosts")
    # pprint.pprint(hosts_dict)
    assert hosts_dict == {'R2': {'connection_options': {},
                                 'data': {'role': 'agg', 'site': 'B2'},
                                 'groups': ['lab'],
                                 'hostname': '192.168.1.153',
                                 'name': 'R2',
                                 'password': None,
                                 'platform': 'ios',
                                 'port': None,
                                 'username': None},
                          'R3': {'connection_options': {},
                                 'data': {'role': 'agg', 'site': 'B3'},
                                 'groups': ['lab'],
                                 'hostname': '192.168.2.154',
                                 'name': 'R3',
                                 'password': None,
                                 'platform': 'ios',
                                 'port': None,
                                 'username': None}}


# test_FL_with_FN()

def test_FM_with_single_pattern():
    res = FFun(NornirObj, FM="ios")
    res_dict = res.dict()
    hosts_dict = res_dict.get("inventory", {}).get("hosts")
    pprint.pprint(hosts_dict)
    assert len(hosts_dict) == 3
    assert "R1" in hosts_dict
    assert "R2" in hosts_dict
    assert "R3" in hosts_dict

# test_FM_with_single_pattern()

def test_FM_with_comma_separated_patterns():
    res = FFun(NornirObj, FM="io*, nxos*")
    res_dict = res.dict()
    hosts_dict = res_dict.get("inventory", {}).get("hosts")
    pprint.pprint(hosts_dict)
    assert len(hosts_dict) == 4
    assert "R1" in hosts_dict
    assert "R2" in hosts_dict
    assert "R3" in hosts_dict
    assert "SW1" in hosts_dict
    
# test_FM_with_comma_separated_patterns()

def test_FM_with_patterns_list():
    res = FFun(NornirObj, FM=["io*", "nxos*"])
    res_dict = res.dict()
    hosts_dict = res_dict.get("inventory", {}).get("hosts")
    pprint.pprint(hosts_dict)
    assert len(hosts_dict) == 4
    assert "R1" in hosts_dict
    assert "R2" in hosts_dict
    assert "R3" in hosts_dict
    assert "SW1" in hosts_dict
    
# test_FM_with_patterns_list()

def test_FM_matches_nothing():
    res = FFun(NornirObj, FM=["foobar"])
    res_dict = res.dict()
    hosts_dict = res_dict.get("inventory", {}).get("hosts")
    pprint.pprint(hosts_dict)
    assert len(hosts_dict) == 0
    
# test_FM_matches_nothing()

def test_FFun_functions_imported():
    assert len(FFun_functions) > 0
    assert isinstance(FFun_functions, list)

# test_FFun_functions_imported()

def test_FH():
    res = FFun(NornirObj, FH="192.168.1.15[13]")
    res_dict = res.dict()
    hosts_dict = res_dict.get("inventory", {}).get("hosts")
    pprint.pprint(hosts_dict)
    assert hosts_dict == {
        "R1": {
            "connection_options": {},
            "data": {"role": "core", "site": "B1"},
            "groups": ["lab"],
            "hostname": "192.168.1.151",
            "name": "R1",
            "password": None,
            "platform": "ios",
            "port": None,
            "username": None,
        },
        "R2": {
            "connection_options": {},
            "data": {"role": "agg", "site": "B2"},
            "groups": ["lab"],
            "hostname": "192.168.1.153",
            "name": "R2",
            "password": None,
            "platform": "ios",
            "port": None,
            "username": None,
        },
    }
    
def test_FH_list():
    res = FFun(NornirObj, FH=["192.168.1.15[13]", "192.168.2.14*"])
    res_dict = res.dict()
    hosts_dict = res_dict.get("inventory", {}).get("hosts")
    pprint.pprint(hosts_dict)
    assert hosts_dict == {'R1': {'connection_options': {},
                                 'data': {'role': 'core', 'site': 'B1'},
                                 'groups': ['lab'],
                                 'hostname': '192.168.1.151',
                                 'name': 'R1',
                                 'password': None,
                                 'platform': 'ios',
                                 'port': None,
                                 'username': None},
                         'R2': {'connection_options': {},
                                 'data': {'role': 'agg', 'site': 'B2'},
                                 'groups': ['lab'],
                                 'hostname': '192.168.1.153',
                                 'name': 'R2',
                                 'password': None,
                                 'platform': 'ios',
                                 'port': None,
                                 'username': None},
                         'SW1': {'connection_options': {},
                                 'data': {'role': 'access', 'site': 'B3'},
                                 'groups': ['lab', 'pod1'],
                                 'hostname': '192.168.2.144',
                                 'name': 'SW1',
                                 'password': None,
                                 'platform': 'nxos_ssh',
                                 'port': None,
                                 'username': None}}
                                 

def test_FH_comma_separated_list():
    res = FFun(NornirObj, FH="192.168.1.15[13], 192.168.2.14*")
    res_dict = res.dict()
    hosts_dict = res_dict.get("inventory", {}).get("hosts")
    pprint.pprint(hosts_dict)
    assert hosts_dict == {'R1': {'connection_options': {},
                                 'data': {'role': 'core', 'site': 'B1'},
                                 'groups': ['lab'],
                                 'hostname': '192.168.1.151',
                                 'name': 'R1',
                                 'password': None,
                                 'platform': 'ios',
                                 'port': None,
                                 'username': None},
                         'R2': {'connection_options': {},
                                 'data': {'role': 'agg', 'site': 'B2'},
                                 'groups': ['lab'],
                                 'hostname': '192.168.1.153',
                                 'name': 'R2',
                                 'password': None,
                                 'platform': 'ios',
                                 'port': None,
                                 'username': None},
                         'SW1': {'connection_options': {},
                                 'data': {'role': 'access', 'site': 'B3'},
                                 'groups': ['lab', 'pod1'],
                                 'hostname': '192.168.2.144',
                                 'name': 'SW1',
                                 'password': None,
                                 'platform': 'nxos_ssh',
                                 'port': None,
                                 'username': None}}
                                 
def test_FX():
    res = FFun(NornirObj, FX="R[13]")
    res_dict = res.dict()
    hosts_dict = res_dict.get("inventory", {}).get("hosts")
    pprint.pprint(hosts_dict)
    assert hosts_dict ==  {'R2': {'connection_options': {},
                                 'data': {'role': 'agg', 'site': 'B2'},
                                 'groups': ['lab'],
                                 'hostname': '192.168.1.153',
                                 'name': 'R2',
                                 'password': None,
                                 'platform': 'ios',
                                 'port': None,
                                 'username': None},
                          'SW1': {'connection_options': {},
                                  'data': {'role': 'access', 'site': 'B3'},
                                  'groups': ['lab', 'pod1'],
                                  'hostname': '192.168.2.144',
                                  'name': 'SW1',
                                  'password': None,
                                  'platform': 'nxos_ssh',
                                  'port': None,
                                  'username': None}}
                                  
def test_FX_comma_list():
    res = FFun(NornirObj, FX="R[13], R2")
    res_dict = res.dict()
    hosts_dict = res_dict.get("inventory", {}).get("hosts")
    pprint.pprint(hosts_dict)
    assert hosts_dict ==  {'SW1': {'connection_options': {},
                                  'data': {'role': 'access', 'site': 'B3'},
                                  'groups': ['lab', 'pod1'],
                                  'hostname': '192.168.2.144',
                                  'name': 'SW1',
                                  'password': None,
                                  'platform': 'nxos_ssh',
                                  'port': None,
                                  'username': None}}
								  
def test_FX_list():
    res = FFun(NornirObj, FX=["R[13]", "R2"])
    res_dict = res.dict()
    hosts_dict = res_dict.get("inventory", {}).get("hosts")
    pprint.pprint(hosts_dict)
    assert hosts_dict ==  {'SW1': {'connection_options': {},
                                  'data': {'role': 'access', 'site': 'B3'},
                                  'groups': ['lab', 'pod1'],
                                  'hostname': '192.168.2.144',
                                  'name': 'SW1',
                                  'password': None,
                                  'platform': 'nxos_ssh',
                                  'port': None,
                                  'username': None}}