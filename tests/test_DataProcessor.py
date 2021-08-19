import sys
import pprint
import logging
import yaml
import pytest

sys.path.insert(0, "..")

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
from nornir_salt.plugins.processors.DataProcessor import DataProcessor


logging.basicConfig(level=logging.ERROR)


xml_ntp_data = """
<rpc-reply xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="urn:uuid:2412b1be-e949-4ebc-93e4-9fb3a20134c6">
  <data time-modified="2021-07-15T19:54:35.034953141Z">
    <system xmlns="http://openconfig.net/yang/system">
      <ntp>
        <config>
          <enable-ntp-auth>false</enable-ntp-auth>
          <enabled>true</enabled>
        </config>
        <servers>
          <server>
            <address>1.1.1.10</address>
            <config>
              <address>1.1.1.10</address>
              <iburst>false</iburst>
              <prefer>false</prefer>
              <version>4</version>
            </config>
          </server>
          <server>
            <address>1.1.1.11</address>
            <config>
              <address>1.1.1.11</address>
              <iburst>false</iburst>
              <prefer>false</prefer>
              <version>4</version>
            </config>
          </server>
        </servers>
      </ntp>
    </system>
  </data>
</rpc-reply>
"""

json_ntp_data = """
{
    "rpc-reply": {
        "@message-id": "urn:uuid:2412b1be-e949-4ebc-93e4-9fb3a20134c6",
        "@xmlns": "urn:ietf:params:xml:ns:netconf:base:1.0",
        "data": {
            "@time-modified": "2021-07-15T19:54:35.034953141Z",
            "system": {
                "@xmlns": "http://openconfig.net/yang/system",
                "ntp": {
                    "config": {
                        "enable-ntp-auth": "false",
                        "enabled": "true"
                    },
                    "servers": {
                        "server": [
                            {
                                "address": "1.1.1.10",
                                "config": {
                                    "address": "1.1.1.10",
                                    "iburst": "false",
                                    "prefer": "false",
                                    "version": "4"
                                }
                            },
                            {
                                "address": "1.1.1.11",
                                "config": {
                                    "address": "1.1.1.11",
                                    "iburst": "false",
                                    "prefer": "false",
                                    "version": "4"
                                }
                            }
                        ]
                    }
                }
            }
        }
    }
}
"""

dict_ntp_data = {'rpc-reply': {'@message-id': 'urn:uuid:2412b1be-e949-4ebc-93e4-9fb3a20134c6',
                               '@xmlns': 'urn:ietf:params:xml:ns:netconf:base:1.0',
                               'data': {'@time-modified': '2021-07-15T19:54:35.034953141Z',
                                        'system': {'@xmlns': 'http://openconfig.net/yang/system',
                                                   'ntp': {'config': {'enable-ntp-auth': 'false',
                                                                      'enabled': 'true'},
                                                           'servers': {'server': [{'address': '1.1.1.10',
                                                                                   'config': {'address': '1.1.1.10',
                                                                                              'iburst': 'false',
                                                                                              'prefer': 'false',
                                                                                              'version': '4'}},
                                                                                  {'address': '1.1.1.11',
                                                                                   'config': {'address': '1.1.1.11',
                                                                                              'iburst': 'false',
                                                                                              'prefer': 'false',
                                                                                              'version': '4'}}]}}}}}}
                                                                                              

dict_ntp_data_flattened = {'rpc-reply.@message-id': 'urn:uuid:2412b1be-e949-4ebc-93e4-9fb3a20134c6',
                           'rpc-reply.@xmlns': 'urn:ietf:params:xml:ns:netconf:base:1.0',
                           'rpc-reply.data.@time-modified': '2021-07-15T19:54:35.034953141Z',
                           'rpc-reply.data.system.@xmlns': 'http://openconfig.net/yang/system',
                           'rpc-reply.data.system.ntp.config.enable-ntp-auth': 'false',
                           'rpc-reply.data.system.ntp.config.enabled': 'true',
                           'rpc-reply.data.system.ntp.servers.server.0.address': '1.1.1.10',
                           'rpc-reply.data.system.ntp.servers.server.0.config.address': '1.1.1.10',
                           'rpc-reply.data.system.ntp.servers.server.0.config.iburst': 'false',
                           'rpc-reply.data.system.ntp.servers.server.0.config.prefer': 'false',
                           'rpc-reply.data.system.ntp.servers.server.0.config.version': '4',
                           'rpc-reply.data.system.ntp.servers.server.1.address': '1.1.1.11',
                           'rpc-reply.data.system.ntp.servers.server.1.config.address': '1.1.1.11',
                           'rpc-reply.data.system.ntp.servers.server.1.config.iburst': 'false',
                           'rpc-reply.data.system.ntp.servers.server.1.config.prefer': 'false',
                           'rpc-reply.data.system.ntp.servers.server.1.config.version': '4'}
                                                      
                                                      
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
def test_struct_to_json():
    """ results are dictionaries convert it to json string """
    nr_with_dp = nr.with_processors([DataProcessor([
        "to_json"
    ])])
    output = nr_with_dp.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": {"a": 1, "b": 2},
            "IOL2": {"c": 3, "d": 4},
        },
        name="show run | inc ntp",
    )
    result = ResultSerializer(output, to_dict=True)
    # pprint.pprint(result)
    assert result == {'IOL1': {'show run | inc ntp': '{\n    "a": 1,\n    "b": 2\n}'},
                      'IOL2': {'show run | inc ntp': '{\n    "c": 3,\n    "d": 4\n}'}}
# test_struct_to_json()


@skip_if_no_nornir
def test_struct_to_json_kwargs():
    """ results are dictionaries convert it to json string """
    nr_with_dp = nr.with_processors([DataProcessor(
        to_json={"indent": 2}
    )])
    output = nr_with_dp.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": {"a": 1, "b": 2},
            "IOL2": {"c": 3, "d": 4},
        },
        name="show run | inc ntp",
    )
    result = ResultSerializer(output, to_dict=True)
    # pprint.pprint(result)
    assert result == {'IOL1': {'show run | inc ntp': '{\n  "a": 1,\n  "b": 2\n}'},
                      'IOL2': {'show run | inc ntp': '{\n  "c": 3,\n  "d": 4\n}'}}
                      
# test_struct_to_json_kwargs()


@skip_if_no_nornir
def test_struct_to_json_list_kwargs():
    """ results are dictionaries convert it to json string """
    nr_with_dp = nr.with_processors([DataProcessor(
        ["to_json"], to_json={"indent": 2}
    )])
    output = nr_with_dp.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": {"a": 1, "b": 2},
            "IOL2": {"c": 3, "d": 4},
        },
        name="show run | inc ntp",
    )
    result = ResultSerializer(output, to_dict=True)
    # pprint.pprint(result)
    assert result == {'IOL1': {'show run | inc ntp': '{\n  "a": 1,\n  "b": 2\n}'},
                      'IOL2': {'show run | inc ntp': '{\n  "c": 3,\n  "d": 4\n}'}}
                      
# test_struct_to_json_list_kwargs()


@skip_if_no_nornir
def test_struct_to_yaml():
    """ results are dictionaries convert it to yaml string """
    nr_with_dp = nr.with_processors([DataProcessor([
        "to_yaml"
    ])])
    output = nr_with_dp.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": {"a": 1, "b": 2},
            "IOL2": {"c": 3, "d": 4},
        },
        name="show run | inc ntp",
    )
    result = ResultSerializer(output, to_dict=True)
    # pprint.pprint(result)
    assert result == {'IOL1': {'show run | inc ntp': 'a: 1\nb: 2\n'},
                      'IOL2': {'show run | inc ntp': 'c: 3\nd: 4\n'}}
# test_struct_to_yaml()


@skip_if_no_nornir
def test_struct_to_str():
    """ results are dictionaries convert it to string """
    nr_with_dp = nr.with_processors([DataProcessor([
        "to_str"
    ])])
    output = nr_with_dp.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": {"a": 1, "b": 2},
            "IOL2": {"c": 3, "d": 4},
        },
        name="show run | inc ntp",
    )
    result = ResultSerializer(output, to_dict=True)
    # pprint.pprint(result)
    assert result == {'IOL1': {'show run | inc ntp': "{'a': 1, 'b': 2}"},
                      'IOL2': {'show run | inc ntp': "{'c': 3, 'd': 4}"}}
# test_struct_to_str()


@skip_if_no_nornir
def test_xml_string_load_to_dict():
    """ results are XML string convert it dictionary """
    nr_with_dp = nr.with_processors([DataProcessor([
        "load_xml"
    ])])
    output = nr_with_dp.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": xml_ntp_data,
            "IOL2": xml_ntp_data,
        },
        name="show run | inc ntp",
    )
    result = ResultSerializer(output, to_dict=True)
    # pprint.pprint(result, width=150, indent=1)
    assert result == {'IOL1': {'show run | inc ntp': {'rpc-reply': {'@message-id': 'urn:uuid:2412b1be-e949-4ebc-93e4-9fb3a20134c6',
                                                                    '@xmlns': 'urn:ietf:params:xml:ns:netconf:base:1.0',
                                                                    'data': {'@time-modified': '2021-07-15T19:54:35.034953141Z',
                                                                             'system': {'@xmlns': 'http://openconfig.net/yang/system',
                                                                                        'ntp': {'config': {'enable-ntp-auth': 'false', 'enabled': 'true'},
                                                                                                'servers': {'server': [{'address': '1.1.1.10',
                                                                                                                        'config': {'address': '1.1.1.10',
                                                                                                                                   'iburst': 'false',
                                                                                                                                   'prefer': 'false',
                                                                                                                                   'version': '4'}},
                                                                                                                       {'address': '1.1.1.11',
                                                                                                                        'config': {'address': '1.1.1.11',
                                                                                                                                   'iburst': 'false',
                                                                                                                                   'prefer': 'false',
                                                                                                                                   'version': '4'}}]}}}}}}},
                      'IOL2': {'show run | inc ntp': {'rpc-reply': {'@message-id': 'urn:uuid:2412b1be-e949-4ebc-93e4-9fb3a20134c6',
                                                                    '@xmlns': 'urn:ietf:params:xml:ns:netconf:base:1.0',
                                                                    'data': {'@time-modified': '2021-07-15T19:54:35.034953141Z',
                                                                             'system': {'@xmlns': 'http://openconfig.net/yang/system',
                                                                                        'ntp': {'config': {'enable-ntp-auth': 'false', 'enabled': 'true'},
                                                                                                'servers': {'server': [{'address': '1.1.1.10',
                                                                                                                        'config': {'address': '1.1.1.10',
                                                                                                                                   'iburst': 'false',
                                                                                                                                   'prefer': 'false',
                                                                                                                                   'version': '4'}},
                                                                                                                       {'address': '1.1.1.11',
                                                                                                                        'config': {'address': '1.1.1.11',
                                                                                                                                   'iburst': 'false',
                                                                                                                                   'prefer': 'false',
                                                                                                                                   'version': '4'}}]}}}}}}}}
# test_xml_string_load_to_dict()

@skip_if_no_nornir
def test_json_string_load_to_struct():
    """ results are JSON string convert it to structure """
    nr_with_dp = nr.with_processors([DataProcessor([
        "load_json"
    ])])
    output = nr_with_dp.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": json_ntp_data,
            "IOL2": json_ntp_data,
        },
        name="show run | inc ntp",
    )
    result = ResultSerializer(output, to_dict=True)
    # pprint.pprint(result)
    assert result == {'IOL1': {'show run | inc ntp': {'rpc-reply': {'@message-id': 'urn:uuid:2412b1be-e949-4ebc-93e4-9fb3a20134c6',
                                                                    '@xmlns': 'urn:ietf:params:xml:ns:netconf:base:1.0',
                                                                    'data': {'@time-modified': '2021-07-15T19:54:35.034953141Z',
                                                                             'system': {'@xmlns': 'http://openconfig.net/yang/system',
                                                                                        'ntp': {'config': {'enable-ntp-auth': 'false',
                                                                                                           'enabled': 'true'},
                                                                                                'servers': {'server': [{'address': '1.1.1.10',
                                                                                                                        'config': {'address': '1.1.1.10',
                                                                                                                                   'iburst': 'false',
                                                                                                                                   'prefer': 'false',
                                                                                                                                   'version': '4'}},
                                                                                                                       {'address': '1.1.1.11',
                                                                                                                        'config': {'address': '1.1.1.11',
                                                                                                                                   'iburst': 'false',
                                                                                                                                   'prefer': 'false',
                                                                                                                                   'version': '4'}}]}}}}}}},
                      'IOL2': {'show run | inc ntp': {'rpc-reply': {'@message-id': 'urn:uuid:2412b1be-e949-4ebc-93e4-9fb3a20134c6',
                                                                    '@xmlns': 'urn:ietf:params:xml:ns:netconf:base:1.0',
                                                                    'data': {'@time-modified': '2021-07-15T19:54:35.034953141Z',
                                                                             'system': {'@xmlns': 'http://openconfig.net/yang/system',
                                                                                        'ntp': {'config': {'enable-ntp-auth': 'false',
                                                                                                           'enabled': 'true'},
                                                                                                'servers': {'server': [{'address': '1.1.1.10',
                                                                                                                        'config': {'address': '1.1.1.10',
                                                                                                                                   'iburst': 'false',
                                                                                                                                   'prefer': 'false',
                                                                                                                                   'version': '4'}},
                                                                                                                       {'address': '1.1.1.11',
                                                                                                                        'config': {'address': '1.1.1.11',
                                                                                                                                   'iburst': 'false',
                                                                                                                                   'prefer': 'false',
                                                                                                                                   'version': '4'}}]}}}}}}}}
# test_json_string_load_to_struct()


@skip_if_no_nornir
def test_struct_to_flatten_dict():
    """ results are JSON string convert it to structure """
    nr_with_dp = nr.with_processors([DataProcessor([
        "flatten"
    ])])
    output = nr_with_dp.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": dict_ntp_data,
            "IOL2": dict_ntp_data,
        },
        name="show run | inc ntp",
    )
    result = ResultSerializer(output, to_dict=True)
    # pprint.pprint(result)
    assert result["IOL1"]["show run | inc ntp"] == dict_ntp_data_flattened
    assert result["IOL2"]["show run | inc ntp"] == dict_ntp_data_flattened
    
# test_struct_to_flatten_dict()


@skip_if_no_nornir
def test_struct_to_unflatten_dict():
    """ results are JSON string convert it to structure """
    nr_with_dp = nr.with_processors([DataProcessor([
        "unflatten"
    ])])
    output = nr_with_dp.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": dict_ntp_data_flattened,
            "IOL2": dict_ntp_data_flattened,
        },
        name="show run | inc ntp",
    )
    result = ResultSerializer(output, to_dict=True)
    # pprint.pprint(result)
    assert result["IOL1"]["show run | inc ntp"] == dict_ntp_data
    assert result["IOL2"]["show run | inc ntp"] == dict_ntp_data
    
# test_struct_to_unflatten_dict()


@skip_if_no_nornir
def test_struct_to_unflatten_list():
    """ results are JSON string convert it to structure """
    nr_with_dp = nr.with_processors([DataProcessor([
        "unflatten"
    ])])
    output = nr_with_dp.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": {
                "0.a.b.0.c": 1,
                "0.a.b.1.c": 2,
                "1.a.b.0.c": 3,
                "1.a.b.1": 4,
            },
            "IOL2": {
                "0.a.b.0.c": 1,
                "0.a.b.1.c": 2,
                "1.a.b.0.c": 3,
                "1.a.b.1": 4,
            },
        },
        name="show run | inc ntp",
    )
    result = ResultSerializer(output, to_dict=True)
    # pprint.pprint(result)
    assert result == {'IOL1': {'show run | inc ntp': [{'a': {'b': [{'c': 1}, {'c': 2}]}},
                                                      {'a': {'b': [{'c': 3}, 4]}}]},
                      'IOL2': {'show run | inc ntp': [{'a': {'b': [{'c': 1}, {'c': 2}]}},
                                                      {'a': {'b': [{'c': 3}, 4]}}]}}
                                 
# test_struct_to_unflatten_list()


@skip_if_no_nornir
def test_struct_to_unflatten_list_first_non_0_index():
    """ results are JSON string convert it to structure """
    nr_with_dp = nr.with_processors([DataProcessor([
        "unflatten"
    ])])
    output = nr_with_dp.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": {
                "5.a.b.0.c": 1,
                "5.a.b.1.c": 2,
                "10.a.b.0.c": 3,
                "10.a.b.1": 4,
            },
            "IOL2": {
                "5.a.b.0.c": 1,
                "5.a.b.1.c": 2,
                "10.a.b.0.c": 3,
                "10.a.b.1": 4,
            },
        },
        name="show run | inc ntp",
    )
    result = ResultSerializer(output, to_dict=True)
    pprint.pprint(result)
                                 
# test_struct_to_unflatten_list_first_non_0_index()


@skip_if_no_nornir
def test_xml_xpath_with_namespaces():
    """ results are XML filtered using XPATH """
    nr_with_dp = nr.with_processors([DataProcessor(
        xpath={"expr": "//a:config", "namespaces": {"a": "http://openconfig.net/yang/system"}}
    )])
    output = nr_with_dp.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": xml_ntp_data,
            "IOL2": xml_ntp_data,
        },
        name="show run | inc ntp",
    )
    result = ResultSerializer(output, to_dict=True)
    pprint.pprint(result, width=200)
    assert result == {'IOL1': {'show run | inc ntp': '<config xmlns="http://openconfig.net/yang/system">\n'
                                                     '          <enable-ntp-auth>false</enable-ntp-auth>\n'
                                                     '          <enabled>true</enabled>\n'
                                                     '        </config>\n'
                                                     '        \n'
                                                     '\n'
                                                     '<config xmlns="http://openconfig.net/yang/system">\n'
                                                     '              <address>1.1.1.10</address>\n'
                                                     '              <iburst>false</iburst>\n'
                                                     '              <prefer>false</prefer>\n'
                                                     '              <version>4</version>\n'
                                                     '            </config>\n'
                                                     '          \n'
                                                     '\n'
                                                     '<config xmlns="http://openconfig.net/yang/system">\n'
                                                     '              <address>1.1.1.11</address>\n'
                                                     '              <iburst>false</iburst>\n'
                                                     '              <prefer>false</prefer>\n'
                                                     '              <version>4</version>\n'
                                                     '            </config>\n'
                                                     '          \n'},
                      'IOL2': {'show run | inc ntp': '<config xmlns="http://openconfig.net/yang/system">\n'
                                                     '          <enable-ntp-auth>false</enable-ntp-auth>\n'
                                                     '          <enabled>true</enabled>\n'
                                                     '        </config>\n'
                                                     '        \n'
                                                     '\n'
                                                     '<config xmlns="http://openconfig.net/yang/system">\n'
                                                     '              <address>1.1.1.10</address>\n'
                                                     '              <iburst>false</iburst>\n'
                                                     '              <prefer>false</prefer>\n'
                                                     '              <version>4</version>\n'
                                                     '            </config>\n'
                                                     '          \n'
                                                     '\n'
                                                     '<config xmlns="http://openconfig.net/yang/system">\n'
                                                     '              <address>1.1.1.11</address>\n'
                                                     '              <iburst>false</iburst>\n'
                                                     '              <prefer>false</prefer>\n'
                                                     '              <version>4</version>\n'
                                                     '            </config>\n'
                                                     '          \n'}}
# test_xml_xpath_with_namespaces()


@skip_if_no_nornir
def test_xml_xpath_elem_by_value():
    """ results are XML filtered using XPATH """
    nr_with_dp = nr.with_processors([DataProcessor(
        xpath={"expr": '//a:config/a:address[text()="1.1.1.11"]', "namespaces": {"a": "http://openconfig.net/yang/system"}}
    )])
    output = nr_with_dp.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": xml_ntp_data,
            "IOL2": xml_ntp_data,
        },
        name="show run | inc ntp",
    )
    result = ResultSerializer(output, to_dict=True)
    # pprint.pprint(result, width=200)
    assert result == {'IOL1': {'show run | inc ntp': '<address xmlns="http://openconfig.net/yang/system">1.1.1.11</address>\n              \n'},
                      'IOL2': {'show run | inc ntp': '<address xmlns="http://openconfig.net/yang/system">1.1.1.11</address>\n              \n'}}
# test_xml_xpath_elem_by_value()


@skip_if_no_nornir
def test_xml_xpath_smart_string_false():
    """ results are XML filtered using XPATH 
    Test that smart_string=False works for ethree.xpath
    """
    nr_with_dp = nr.with_processors([DataProcessor(
        xpath={"expr": "//text()"}
    )])
    output = nr_with_dp.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": xml_ntp_data,
            "IOL2": xml_ntp_data,
        },
        name="show run | inc ntp",
    )
    result = ResultSerializer(output, to_dict=True)
    # pprint.pprint(result, width=200)
    assert isinstance(result["IOL1"]["show run | inc ntp"], str)
# test_xml_xpath_smart_string_false()


@skip_if_no_nornir
def test_xml_xpath_ignore_namespaces():
    """ results are XML filtered using XPATH """
    nr_with_dp = nr.with_processors([DataProcessor(
        xpath={"expr": "//*[local-name() = 'config']"}
    )])
    output = nr_with_dp.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": xml_ntp_data,
            "IOL2": xml_ntp_data,
        },
        name="show run | inc ntp",
    )
    result = ResultSerializer(output, to_dict=True)
    # pprint.pprint(result, width=200)
    assert result == {'IOL1': {'show run | inc ntp': '<config xmlns="http://openconfig.net/yang/system">\n'
                                '          <enable-ntp-auth>false</enable-ntp-auth>\n'
                                '          <enabled>true</enabled>\n'
                                '        </config>\n'
                                '        \n'
                                '\n'
                                '<config xmlns="http://openconfig.net/yang/system">\n'
                                '              <address>1.1.1.10</address>\n'
                                '              <iburst>false</iburst>\n'
                                '              <prefer>false</prefer>\n'
                                '              <version>4</version>\n'
                                '            </config>\n'
                                '          \n'
                                '\n'
                                '<config xmlns="http://openconfig.net/yang/system">\n'
                                '              <address>1.1.1.11</address>\n'
                                '              <iburst>false</iburst>\n'
                                '              <prefer>false</prefer>\n'
                                '              <version>4</version>\n'
                                '            </config>\n'
                                '          \n'},
 'IOL2': {'show run | inc ntp': '<config xmlns="http://openconfig.net/yang/system">\n'
                                '          <enable-ntp-auth>false</enable-ntp-auth>\n'
                                '          <enabled>true</enabled>\n'
                                '        </config>\n'
                                '        \n'
                                '\n'
                                '<config xmlns="http://openconfig.net/yang/system">\n'
                                '              <address>1.1.1.10</address>\n'
                                '              <iburst>false</iburst>\n'
                                '              <prefer>false</prefer>\n'
                                '              <version>4</version>\n'
                                '            </config>\n'
                                '          \n'
                                '\n'
                                '<config xmlns="http://openconfig.net/yang/system">\n'
                                '              <address>1.1.1.11</address>\n'
                                '              <iburst>false</iburst>\n'
                                '              <prefer>false</prefer>\n'
                                '              <version>4</version>\n'
                                '            </config>\n'
                                '          \n'}}
# test_xml_xpath_ignore_namespaces()


@skip_if_no_nornir
def test_xml_xpath_on_error():
    """ results are XML filtered using XPATH """
    nr_with_dp = nr.with_processors([DataProcessor(
        xpath={"expr": "//"}, on_error="except"
    )])
    output = nr_with_dp.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": xml_ntp_data,
            "IOL2": xml_ntp_data,
        },
        name="show run | inc ntp",
    )
    result = ResultSerializer(output, to_dict=True, add_details=True)
    pprint.pprint(result, width=200)
    assert "lxml.etree.XPathEvalError: Invalid expression" in result["IOL1"]["show run | inc ntp"]["exception"]
# test_xml_xpath_on_error()