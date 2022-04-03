import sys
import os
import pprint
import logging
import yaml
import pytest
import time
import requests

sys.path.insert(0, "..")

try:
    from nornir import InitNornir
    from nornir.core.plugins.inventory import InventoryPluginRegister
    from nornir.core.plugins.connections import ConnectionPluginRegister
    from nornir.core.task import Result

    HAS_NORNIR = True
except ImportError:
    HAS_NORNIR = False

from nornir_salt.plugins.functions import ResultSerializer
from nornir_salt.plugins.inventory import DictInventory
from nornir_salt.plugins.tasks import http_call
from nornir_salt.plugins.connections import HTTPPlugin

logging.basicConfig(level=logging.ERROR)


google_query = requests.get("https://google.com")
skip_if_no_internet = pytest.mark.skipif(
    google_query.ok == False,
    reason="Have no Internet access",
)

always_on_query = requests.get("https://sandbox-iosxe-latest-1.cisco.com/restconf/", verify=False, auth=("developer", "C1sco12345"))
skip_if_no_always_on_access = pytest.mark.skipif(
    always_on_query.ok == False,
    reason="Have no access to Cisco IOS XE always on lab",
)

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
    connection_options:
      http:
        port: 8080
        extras:
          verify: False

defaults: {}
"""
lab_inventory_dict = yaml.safe_load(lab_inventory)

cisco_always_on_sandpox = """
hosts:
  sandbox-iosxe-recomm-1:
    hostname: sandbox-iosxe-latest-1.cisco.com
    platform: ios
    groups: [lab]

groups:
  lab:
    username: developer
    password: C1sco12345
    connection_options:
      http:
        port: 443
        extras:
          transport: https
          base_url: "https://sandbox-iosxe-latest-1.cisco.com/restconf/"
          verify: False
    """
cisco_always_on_sandpox_inventory = yaml.safe_load(cisco_always_on_sandpox)

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


InventoryPluginRegister.register("DictInventory", DictInventory)
ConnectionPluginRegister.register("http", HTTPPlugin)

nr = init(lab_inventory_dict)
always_on_nr = init(cisco_always_on_sandpox_inventory)


def clean_up_folder():
    # remove previous files and folder
    if os.path.exists("./tofile_outputs/"):
        for filen in os.listdir("./tofile_outputs/"):
            os.remove("./tofile_outputs/" + filen)
        os.rmdir("./tofile_outputs/")


# ----------------------------------------------------------------------
# tests that need Nornir
# ----------------------------------------------------------------------

@skip_if_no_nornir
def task_open_http_connection(task):
    http_conn = task.host.get_connection("http", task.nornir.config)

    return Result(task.host, result=http_conn)

@skip_if_no_nornir
def test_http_connection_open():

    http_conn = ResultSerializer(nr.run(task=task_open_http_connection))
    # pprint.pprint(res)

    assert 'configuration' in http_conn["IOL1"]["task_open_http_connection"]
    assert http_conn["IOL1"]["task_open_http_connection"]['extras'] == {'verify': False}
    assert http_conn["IOL1"]["task_open_http_connection"]['hostname'] ==  '192.168.217.10'
    assert http_conn["IOL1"]["task_open_http_connection"]['password'] ==  'cisco'
    assert http_conn["IOL1"]["task_open_http_connection"]['platform'] ==  'ios'
    assert http_conn["IOL1"]["task_open_http_connection"]['port'] == 8080
    assert http_conn["IOL1"]["task_open_http_connection"]['username'] ==  'cisco'

    assert 'configuration' in http_conn["IOL2"]["task_open_http_connection"]
    assert http_conn["IOL2"]["task_open_http_connection"]['extras'] == {'verify': False}
    assert http_conn["IOL2"]["task_open_http_connection"]['hostname'] ==  '192.168.217.7'
    assert http_conn["IOL2"]["task_open_http_connection"]['password'] ==  'cisco'
    assert http_conn["IOL2"]["task_open_http_connection"]['platform'] ==  'ios'
    assert http_conn["IOL2"]["task_open_http_connection"]['port'] == 8080
    assert http_conn["IOL2"]["task_open_http_connection"]['username'] ==  'cisco'

# test_http_connection_open()

# ----------------------------------------------------------------------
# tests that need Nornir and Internet access
# ----------------------------------------------------------------------

@skip_if_no_internet
@skip_if_no_nornir
def test_http_connection_get_google():

    res = ResultSerializer(
        nr.run(
            task=http_call,
            method="get",
            url="https://google.com",
        ),
        add_details=True
    )
    # pprint.pprint(res)

    assert len(res["IOL1"]["get"]["result"]) > 100
    assert len(res["IOL2"]["get"]["result"]) > 100
    assert res["IOL1"]["get"]["failed"] == False
    assert res["IOL2"]["get"]["failed"] == False

# test_http_connection_get_google()

# ----------------------------------------------------------------------
# tests that need Nornir and Cisco Always ON Cisco IOS XE lab access
# ----------------------------------------------------------------------


@skip_if_no_always_on_access
@skip_if_no_nornir
def test_http_get_ios_always_on_lab_base_url():
    res = ResultSerializer(
        always_on_nr.run(
            task=http_call,
            method="get"
        ),
        add_details=True
    )
    # pprint.pprint(res)

    assert res["sandbox-iosxe-recomm-1"]["get"]["failed"] == False
    assert "ietf-restconf:restconf" in res["sandbox-iosxe-recomm-1"]["get"]["result"]

# test_http_get_ios_always_on_lab_base_url()

@skip_if_no_always_on_access
@skip_if_no_nornir
def test_http_get_ios_always_on_lab_ietf_intefaces():
    res = ResultSerializer(
        always_on_nr.run(
            task=http_call,
            method="get",
            url="/data/ietf-interfaces:interfaces"
        ),
        add_details=True
    )
    # pprint.pprint(res)

    assert res["sandbox-iosxe-recomm-1"]["get"]["failed"] == False
    assert "ietf-interfaces:interfaces" in res["sandbox-iosxe-recomm-1"]["get"]["result"]
    assert len(res["sandbox-iosxe-recomm-1"]["get"]["result"]["ietf-interfaces:interfaces"]["interface"]) > 0

# test_http_get_ios_always_on_lab_ietf_intefaces()
