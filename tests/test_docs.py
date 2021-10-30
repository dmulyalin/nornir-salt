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
    from nornir.core.task import Result

    HAS_NORNIR = True
except ImportError:
    HAS_NORNIR = False

from nornir_salt import (
    ResultSerializer, DictInventory, nr_test,
    DataProcessor, netmiko_send_commands
)

logging.basicConfig(level=logging.ERROR)
InventoryPluginRegister.register("DictInventory", DictInventory)

skip_if_no_nornir = pytest.mark.skipif(
    HAS_NORNIR == False,
    reason="Failed to import all required Nornir modules and plugins",
)

# ---------------------------------------------------
# cisco always on ios xe lab details
# ---------------------------------------------------
cisco_iosxe_always_on_router = """
hosts:
  sandbox-iosxe-recomm-1:
    hostname: "sandbox-iosxe-recomm-1.cisco.com"
    platform: ios
    username: developer
    password: C1sco12345
"""
try:
    s = socket.socket()
    s.settimeout(1)
    s.connect(("sandbox-iosxe-recomm-1.cisco.com", 22))
    has_connection_to_cisco_iosxe_always_on_router = True
except:
    has_connection_to_cisco_iosxe_always_on_router = False
    
skip_if_has_no_cisco_iosxe_always_on_router = pytest.mark.skipif(
    has_connection_to_cisco_iosxe_always_on_router == False,
    reason="Has no connection to sandbox-iosxe-recomm-1.cisco.com router",
)

cisco_iosxe_always_on_router_dict = yaml.safe_load(cisco_iosxe_always_on_router)



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

@skip_if_has_no_cisco_iosxe_always_on_router
@skip_if_no_nornir
def test_run_ttp_docs():
    nr = init(cisco_iosxe_always_on_router_dict)
    
    # define TTP template with inputs having commands attributes
    template = '''
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
Cisco IOS XE Software, Version {{ iose_xe_version }}
</group>    
    '''
    
    # add data processor with run_ttp function
    nr_with_dp = nr.with_processors([DataProcessor(
        [{"fun": "run_ttp", "template": template}]
    )]) 
    
    # run task; commands for task will be dynamically populated by DataProcessor 
    # run_ttp function with commands defined within TTP template inputs
    result = nr_with_dp.run(task=netmiko_send_commands)
    
    # serialize results to dictionary
    dict_result = ResultSerializer(result)
    
    pprint.pprint(dict_result)
    # prints:
    # {'sandbox-iosxe-recomm-1': {'run_ttp': [[{'arp_cache': [{'age': '0',
    #                                                          'interface': 'GigabitEthernet1',
    #                                                          'ip': '10.10.20.28',
    #                                                          'mac': '0050.56bf.f0be'},
    #                                                         {'age': '-',
    #                                                          'interface': 'GigabitEthernet1',
    #                                                          'ip': '10.10.20.48',
    #                                                          'mac': '0050.56bf.9379'},
    #                                                         {'age': '-',
    #                                                          'interface': 'GigabitEthernet1',
    #                                                          'ip': '10.10.20.248',
    #                                                          'mac': '0050.56bf.9379'},
    #                                                         {'age': '147',
    #                                                          'interface': 'GigabitEthernet1',
    #                                                          'ip': '10.10.20.254',
    #                                                          'mac': '0050.56bf.a3cf'},
    #                                                         {'age': '-',
    #                                                          'interface': 'GigabitEthernet2',
    #                                                          'ip': '10.255.255.1',
    #                                                          'mac': '0050.56bf.ea76'},
    #                                                         {'age': '-',
    #                                                          'interface': 'GigabitEthernet2',
    #                                                          'ip': '172.16.255.1',
    #                                                          'mac': '0050.56bf.ea76'}]},
    #                                          {'facts': {'version': {'iose_xe_version': '16.09.03'}}}]]}}
    assert "arp_cache" in dict_result['sandbox-iosxe-recomm-1']["run_ttp"][0][0]
    assert "facts" in dict_result['sandbox-iosxe-recomm-1']["run_ttp"][0][1]
    assert len(dict_result['sandbox-iosxe-recomm-1']["run_ttp"][0][0]["arp_cache"]) > 0
    
test_run_ttp_docs()