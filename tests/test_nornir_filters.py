"""
Notes:

1. Below tests will not pass for nornir 3.0.0; should pass for nornir 3.1.0 and above
de to this PR - https://github.com/nornir-automation/nornir/pull/623
"""

import sys
import yaml
import pprint
sys.path.insert(0,'..')

from nornir import InitNornir

# these libs imported from nornir_salt dir
from nornir_salt.plugins.functions import FFun

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

NornirObj = InitNornir(
    runner={
        "plugin": "RetryRunner",
        "options": {
            "num_workers": 100,
            "num_connectors": 10,
            "connect_retry": 3,
            "connect_backoff": 1000,
            "connect_splay": 100,
            "task_retry": 3,
            "task_backoff": 1000,
            "task_splay": 100
        }
    },
    inventory={
        "plugin": "DictInventory",
        "options": {
            "hosts": inventory_dict["hosts"],
            "groups": inventory_dict["groups"],
            "defaults": inventory_dict.get("defaults", {})
        }
    },
)

def test_FB():
    res = FFun(NornirObj, FB="R[12]")
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
                                 'username': None}}

# import ipdb; ipdb.set_trace()
# test_FB()

def test_FO_list_of_dict():
    res = FFun(NornirObj, FO=[{"role": "agg", "platform": "ios"}, {"site": "B3"}])
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

# test_FO_list_of_dict()

def test_FO_dict():
    res = FFun(NornirObj, FO={"role": "agg", "platform": "ios"})
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

# test_FO_dict()

def test_FG():
    res = FFun(NornirObj, FG="pod1")
    res_dict = res.dict()
    hosts_dict = res_dict.get("inventory", {}).get("hosts")
    # pprint.pprint(hosts_dict)
    assert hosts_dict == {'SW1': {'connection_options': {},
                          'data': {'role': 'access', 'site': 'B3'},
                          'groups': ['lab', 'pod1'],
                          'hostname': '192.168.2.144',
                          'name': 'SW1',
                          'password': None,
                          'platform': 'nxos_ssh',
                          'port': None,
                          'username': None}}

# test_FG()

def test_FP():
    res = FFun(NornirObj, FP="192.168.1.0/24, 192.168.2.144/31")
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

# test_FP()

def test_FL():
    res = FFun(NornirObj, FL="R1, SW1")
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

# test_FL()

def test_FB_FG_FP_FO():
    res = FFun(NornirObj, FB="R*", FG="lab", FP="192.168.1.0/24", FO={"role": "core"})
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
                                 'username': None}}

# test_FB_FG_FP_FO()