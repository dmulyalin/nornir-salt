import sys
import pprint
import logging
import yaml
import pytest
sys.path.insert(0,'..')

try:
    from nornir import InitNornir
    from nornir.core.task import Result, Task
    from nornir_netmiko import netmiko_send_command, netmiko_send_config
    from nornir.core.plugins.inventory import InventoryPluginRegister
    HAS_NORNIR = True
except ImportError:
    HAS_NORNIR = False

from nornir_salt import FindString
from nornir_salt import ResultSerializer
from nornir_salt import DictInventory
from nornir_salt import ContainsTest, ContainsLinesTest, EqualTest, RunTestSuite, CustomFunctionTest, CerberusTest
from nornir_salt import tcp_ping
from nornir_salt import nr_test

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

    ping_check = ResultSerializer(nr.run(tcp_ping))
    HAS_LAB = True
    for hostname, result in ping_check.items():
        if result['tcp_ping'][22] == False:
            HAS_LAB = False

    skip_if_no_lab = pytest.mark.skipif(
        HAS_LAB == False,
        reason="Failed connect to LAB"
    )

    return nr

InventoryPluginRegister.register("DictInventory", DictInventory)

nr = init(lab_inventory_dict)


# ----------------------------------------------------------------------
# tests that need Nornir
# ----------------------------------------------------------------------

@skip_if_no_nornir
def test_contains_check():
    output = nr.run(
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
        name="check ntp config"
    )
    check_result = ContainsTest(
        output,
        task="check ntp config",
        test_name="Test NTP config",
        pattern="ntp server 7.7.7.8"
    )
    # pprint.pprint(check_result)
    assert check_result == [{'criteria': 'ntp server 7.7.7.8',
                             'error': None,
                             'host': 'IOL1',
                             'result': 'PASS',
                             'success': True,
                             'task': 'check ntp config',
                             'test_name': 'Test NTP config',
                             'test_type': 'contains'},
                            {'criteria': 'ntp server 7.7.7.8',
                             'error': 'Criteria pattern not in output',
                             'host': 'IOL2',
                             'result': 'FAIL',
                             'success': False,
                             'task': 'check ntp config',
                             'test_name': 'Test NTP config',
                             'test_type': 'contains'}]

# test_contains_check()

@skip_if_no_nornir
def test_contains_check_tabulate():
    output = nr.run(
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
        name="check ntp config"
    )
    check_result = ContainsTest(
        output,
        task="check ntp config",
        test_name="Test NTP config",
        pattern="ntp server 7.7.7.8",
        tabulate=True
    )
    # print(check_result)
    assert check_result == """host    test_name        task              result    success    error                           test_type    criteria
------  ---------------  ----------------  --------  ---------  ------------------------------  -----------  ------------------
IOL1    Test NTP config  check ntp config  PASS      True                                       contains     ntp server 7.7.7.8
IOL2    Test NTP config  check ntp config  FAIL      False      Criteria pattern not in output  contains     ntp server 7.7.7.8"""

# test_contains_check_nr_test_tabulate()


@skip_if_no_nornir
def test_contains_check_tabulate_with_headers():
    output = nr.run(
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
        name="check ntp config"
    )
    check_result = ContainsTest(
        output,
        test_name="check ntp config",
        task="check ntp config",
        pattern="ntp server 7.7.7.8",
        tabulate={
            "headers": ["host", "test_name", "result"]
        }
    )
    # print(check_result)
    assert check_result == """host    test_name         result
------  ----------------  --------
IOL1    check ntp config  PASS
IOL2    check ntp config  FAIL"""

# test_contains_check_tabulate_with_headers()


@skip_if_no_nornir
def test_not_contains_check():
    output = nr.run(
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
        name="check ntp config"
    )
    check_result = ContainsTest(
        output,
        task="check ntp config",
        test_name="Test NTP config",
        pattern="ntp server 7.7.7.8",
        revert=True
    )
    # pprint.pprint(check_result)
    assert check_result == [{'criteria': 'ntp server 7.7.7.8',
                             'error': 'Criteria pattern in output',
                             'host': 'IOL1',
                             'result': 'FAIL',
                             'success': False,
                             'task': 'check ntp config',
                             'test_name': 'Test NTP config',
                             'test_type': 'not contains'},
                            {'criteria': 'ntp server 7.7.7.8',
                             'error': None,
                             'host': 'IOL2',
                             'result': 'PASS',
                             'success': True,
                             'task': 'check ntp config',
                             'test_name': 'Test NTP config',
                             'test_type': 'not contains'}]

# test_not_contains_check()


@skip_if_no_nornir
def test_contains_lines_check():
    output = nr.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": """
ntp server 7.7.7.8
ntp server 7.7.7.7
ntp server 8.8.8.8
        """,
            "IOL2": """
ntp server 7.7.7.7
        """
        },
        name="check ntp config"
    )
    check_result = ContainsLinesTest(
        output,
        test_name="check ntp config",
        pattern="ntp server 7.7.7.8\nntp server 7.7.7.7\nntp server 8.8.8.8"
    )
    # pprint.pprint(check_result)
    assert check_result == [{'criteria': '',
                             'error': None,
                             'host': 'IOL1',
                             'result': 'PASS',
                             'success': True,
                             'task': -1,
                             'test_name': 'check ntp config',
                             'test_type': 'contains lines'},
                            {'criteria': 'ntp server 7.7.7.8',
                             'error': 'Line not in output',
                             'host': 'IOL2',
                             'result': 'FAIL',
                             'success': False,
                             'task': -1,
                             'test_name': 'check ntp config',
                             'test_type': 'contains lines'}]

# test_contains_lines_check()


@skip_if_no_nornir
def test_not_contains_lines_check():
    output = nr.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": """
ntp server 7.7.7.8
ntp server 7.7.7.7
        """,
            "IOL2": """
ntp server 7.7.7.7
ntp server 3.3.3.3
        """
        },
        name="check ntp config"
    )
    check_result = ContainsLinesTest(
        output,
        test_name="check ntp config",
        pattern="ntp server 1.1.1.2\nntp server 3.3.3.3",
        revert=True
    )
    # pprint.pprint(check_result)
    assert check_result == [{'criteria': '',
                             'error': None,
                             'host': 'IOL1',
                             'result': 'PASS',
                             'success': True,
                             'task': -1,
                             'test_name': 'check ntp config',
                             'test_type': 'not contains lines'},
                            {'criteria': 'ntp server 3.3.3.3',
                             'error': 'Line in output',
                             'host': 'IOL2',
                             'result': 'FAIL',
                             'success': False,
                             'task': -1,
                             'test_name': 'check ntp config',
                             'test_type': 'not contains lines'}]

# test_not_contains_lines_check()


@skip_if_no_nornir
def test_equal_check():
    output = nr.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": """ntp server 7.7.7.8
ntp server 7.7.7.7""",
            "IOL2": """
ntp server 7.7.7.7
        """
        },
        name="check ntp config"
    )
    check_result = EqualTest(
        output,
        test_name="check ntp config",
        pattern="""ntp server 7.7.7.8
ntp server 7.7.7.7"""
    )
    # pprint.pprint(check_result)
    assert check_result == [{'criteria': 'ntp server 7.7.7.8\\nntp s',
                             'error': None,
                             'host': 'IOL1',
                             'result': 'PASS',
                             'success': True,
                             'task': -1,
                             'test_name': 'check ntp config',
                             'test_type': 'equal'},
                            {'criteria': 'ntp server 7.7.7.8\\nntp s',
                             'error': 'Criteria pattern and output not equal',
                             'host': 'IOL2',
                             'result': 'FAIL',
                             'success': False,
                             'task': -1,
                             'test_name': 'check ntp config',
                             'test_type': 'equal'}]

# test_equal_check()

@skip_if_no_nornir
def test_not_equal_check():
    output = nr.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": """ntp server 7.7.7.8
ntp server 7.7.7.7""",
            "IOL2": """
ntp server 7.7.7.7
        """
        },
        name="check ntp config"
    )
    check_result = EqualTest(
        output,
        test_name="check ntp config",
        pattern="""ntp server 7.7.7.8
ntp server 7.7.7.7""",
        revert=True
    )
    # pprint.pprint(check_result)
    assert check_result == [{'criteria': 'ntp server 7.7.7.8\\nntp s',
                             'error': 'Criteria pattern and output are equal',
                             'host': 'IOL1',
                             'result': 'FAIL',
                             'success': False,
                             'task': -1,
                             'test_name': 'check ntp config',
                             'test_type': 'not equal'},
                            {'criteria': 'ntp server 7.7.7.8\\nntp s',
                             'error': None,
                             'host': 'IOL2',
                             'result': 'PASS',
                             'success': True,
                             'task': -1,
                             'test_name': 'check ntp config',
                             'test_type': 'not equal'}]

# test_not_equal_check()

def fun_1(result):
    ret =[]

    if "7.7.7.8" not in result.result:
        ret.append({
            "error": "Server 7.7.7.8 not in config",
            "result": "FAIL",
            "success": False
        })

    return ret

@skip_if_no_nornir
def test_custom_function_call():
    output = nr.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": """ntp server 7.7.7.8
ntp server 7.7.7.7""",
            "IOL2": """
ntp server 7.7.7.7
        """
        },
        name="check ntp config"
    )
    check_result = CustomFunctionTest(
        output,
        function_call=fun_1,
        task="check ntp config",
        test_name="Check NTP cfg using custom fun"
    )
    # pprint.pprint(check_result)
    assert check_result == [{'criteria': None,
                             'error': None,
                             'host': 'IOL1',
                             'result': 'PASS',
                             'success': True,
                             'task': 'check ntp config',
                             'test_name': 'Check NTP cfg using custom fun',
                             'test_type': 'custom'},
                            {'criteria': None,
                             'error': 'Server 7.7.7.8 not in config',
                             'host': 'IOL2',
                             'result': 'FAIL',
                             'success': False,
                             'task': 'check ntp config',
                             'test_name': 'Check NTP cfg using custom fun',
                             'test_type': 'custom'}]

# test_custom_function_call()


fun_1_text = """
def fun_1(result):
    ret =[]

    if "7.7.7.8" not in result.result:
        ret.append({
            "error": "Server 7.7.7.8 not in config",
            "result": "FAIL",
            "success": False
        })

    return ret
"""

@skip_if_no_nornir
def test_custom_function_text():
    output = nr.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": """ntp server 7.7.7.8
ntp server 7.7.7.7""",
            "IOL2": """
ntp server 7.7.7.7
        """
        },
        name="check ntp config"
    )
    check_result = CustomFunctionTest(
        output,
        function_text=fun_1_text,
        function_name="fun_1",
        task="check ntp config",
        test_name="Check NTP cfg using custom fun"
    )
    # pprint.pprint(check_result)
    assert check_result == [{'criteria': None,
                             'error': None,
                             'host': 'IOL1',
                             'result': 'PASS',
                             'success': True,
                             'task': 'check ntp config',
                             'test_name': 'Check NTP cfg using custom fun',
                             'test_type': 'custom'},
                            {'criteria': None,
                             'error': 'Server 7.7.7.8 not in config',
                             'host': 'IOL2',
                             'result': 'FAIL',
                             'success': False,
                             'task': 'check ntp config',
                             'test_name': 'Check NTP cfg using custom fun',
                             'test_type': 'custom'}]

# test_custom_function_text()

@skip_if_no_nornir
def test_custom_function_file():
    output = nr.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": """ntp server 7.7.7.8
ntp server 7.7.7.7""",
            "IOL2": """
ntp server 7.7.7.7
        """
        },
        name="check ntp config"
    )
    check_result = CustomFunctionTest(
        output,
        function_file="./assets/custom_check_function_fun_1.txt",
        function_name="fun_1",
        task="check ntp config",
        test_name="Check NTP cfg using custom fun"
    )
    # pprint.pprint(check_result)
    assert check_result == [{'criteria': None,
                             'error': None,
                             'host': 'IOL1',
                             'result': 'PASS',
                             'success': True,
                             'task': 'check ntp config',
                             'test_name': 'Check NTP cfg using custom fun',
                             'test_type': 'custom'},
                            {'criteria': None,
                             'error': 'Server 7.7.7.8 not in config',
                             'host': 'IOL2',
                             'result': 'FAIL',
                             'success': False,
                             'task': 'check ntp config',
                             'test_name': 'Check NTP cfg using custom fun',
                             'test_type': 'custom'}]

# test_custom_function_file()

@skip_if_no_nornir
def test_run_test_suite():
    main_output = nr.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": """ntp server 7.7.7.8
ntp server 7.7.7.7""",
            "IOL2": """
ntp server 7.7.7.7
        """
        },
        name="check ntp config"
    )
    output_2 = nr.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": """
logging host 1.1.1.1
logging host 2.2.2.2
            """,
            "IOL2": """
logging host 3.3.3.3
        """
        },
        name="check syslog config"
    )

    test_suite = [
    {
        "test": "contains",
        "test_name": "check configuration of NTP",
        "pattern": "7.7.7.8"
    },
    {
        "test": "contains_re",
        "test_name": "check configuration of NTP using RE",
        "pattern": "7\\.7\\.7.+",
        "task": "check ntp config"
    },
    {
        "test": "contains_lines",
        "test_name": "check configuration of logging",
        "pattern": ["1.1.1.1", "2.2.2.2"],
        "task": "check syslog config",
        "result": output_2
    },
    {
        "test": "custom",
        "test_name": "check NTP cfg custom fun",
        "function_file": "./assets/custom_check_function_fun_1.txt",
        "function_name": "fun_1",
        "result": main_output
    }
    ]
    check_result = RunTestSuite(main_output, test_suite)
    # pprint.pprint(check_result, width=250)
    assert check_result == [
 {'criteria': '7.7.7.8', 'error': None, 'host': 'IOL1', 'result': 'PASS', 'success': True, 'task': -1, 'test_name': 'check configuration of NTP', 'test_type': 'contains'},
 {'criteria': '7.7.7.8', 'error': 'Criteria pattern not in output', 'host': 'IOL2', 'result': 'FAIL', 'success': False, 'task': -1, 'test_name': 'check configuration of NTP', 'test_type': 'contains'},
 {'criteria': '7\\.7\\.7.+', 'error': None, 'host': 'IOL1', 'result': 'PASS', 'success': True, 'task': 'check ntp config', 'test_name': 'check configuration of NTP using RE', 'test_type': 'contains'},
 {'criteria': '7\\.7\\.7.+', 'error': None, 'host': 'IOL2', 'result': 'PASS', 'success': True, 'task': 'check ntp config', 'test_name': 'check configuration of NTP using RE', 'test_type': 'contains'},
 {'criteria': '', 'error': None, 'host': 'IOL1', 'result': 'PASS', 'success': True, 'task': 'check syslog config', 'test_name': 'check configuration of logging', 'test_type': 'contains lines'},
 {'criteria': '1.1.1.1', 'error': 'Line not in output', 'host': 'IOL2', 'result': 'FAIL', 'success': False, 'task': 'check syslog config', 'test_name': 'check configuration of logging', 'test_type': 'contains lines'},
 {'criteria': None, 'error': None, 'host': 'IOL1', 'result': 'PASS', 'success': True, 'task': -1, 'test_name': 'check NTP cfg custom fun', 'test_type': 'custom'},
 {'criteria': None, 'error': 'Server 7.7.7.8 not in config', 'host': 'IOL2', 'result': 'FAIL', 'success': False, 'task': -1, 'test_name': 'check NTP cfg custom fun', 'test_type': 'custom'}
]

# test_run_test_suite()


def test_cerberus_dict():
    output = nr.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": {
                "mtu": 1200
            },
            "IOL2": {
                "mtu": 1500
            }
        },
        name="interfaces MTU"
    )
    test_schema = {
        "mtu": {"type": "integer", "allowed": [1500]}
    }
    check_result = CerberusTest(
        output,
        schema=test_schema,
        task="interfaces MTU",
        test_name="check MTU using cerberus"
    )
    # pprint.pprint(check_result)
    assert check_result == [{'criteria': None,
                             'error': {'mtu': ['unallowed value 1200']},
                             'host': 'IOL1',
                             'result': 'FAIL',
                             'success': False,
                             'task': 'interfaces MTU',
                             'test_name': 'check MTU using cerberus',
                             'test_type': 'cerberus'},
                            {'criteria': None,
                             'error': None,
                             'host': 'IOL2',
                             'result': 'PASS',
                             'success': True,
                             'task': 'interfaces MTU',
                             'test_name': 'check MTU using cerberus',
                             'test_type': 'cerberus'}]

# test_cerberus_dict()

def test_cerberus_list_of_dict():
    output = nr.run(
        task=nr_test,
        ret_data_per_host={
            "IOL1": [
                {"interface": "Gi1", "mtu": 1200},
                {"interface": "Gi2", "mtu": 1500},
                {"interface": "Gi2", "mtu": 1505}
            ],
            "IOL2": [
                {"interface": "Gi6", "mtu": 9600}
            ]
        },
        name="interfaces MTU"
    )
    test_schema = {
        "mtu": {"type": "integer", "allowed": [1500]}
    }
    check_result = CerberusTest(
        output,
        schema=test_schema,
        task="interfaces MTU",
        test_name="check MTU using cerberus"
    )
    # pprint.pprint(check_result)
    assert check_result == [{'criteria': None,
                             'error': {'mtu': ['unallowed value 1200']},
                             'host': 'IOL1',
                             'result': 'FAIL',
                             'success': False,
                             'task': 'interfaces MTU',
                             'test_name': 'check MTU using cerberus',
                             'test_type': 'cerberus'},
                            {'criteria': None,
                             'error': {'mtu': ['unallowed value 1505']},
                             'host': 'IOL1',
                             'result': 'FAIL',
                             'success': False,
                             'task': 'interfaces MTU',
                             'test_name': 'check MTU using cerberus',
                             'test_type': 'cerberus'},
                            {'criteria': None,
                             'error': {'mtu': ['unallowed value 9600']},
                             'host': 'IOL2',
                             'result': 'FAIL',
                             'success': False,
                             'task': 'interfaces MTU',
                             'test_name': 'check MTU using cerberus',
                             'test_type': 'cerberus'}]

# test_cerberus_list_of_dict()

# ----------------------------------------------------------------------
# tests that do not need LAB or Nornir
# ----------------------------------------------------------------------

def test_find_string_function():
    from nornir_salt import FindString

    data = {
    "router-1": {
            "show run": """
interface Loopback0
 description Routing Loopback
 ip address 10.0.0.10 255.255.255.255
 ip ospf 1 area 0
 ipv6 address 2001::10/128
interface Loopback100
 ip address 1.1.1.100 255.255.255.255
interface Ethernet0/0
 description Main Interface for L3 features testing
 no ip address
 duplex auto
interface Ethernet0/0.102
 description to_vIOS1_Gi0/0.102
 encapsulation dot1Q 102
 ip address 10.1.102.10 255.255.255.0
 ipv6 address 2001:102::10/64
interface Ethernet0/0.107
 description to_IOL2_Eth0/0.107
 encapsulation dot1Q 107
 ip address 10.1.107.10 255.255.255.0
 ip ospf network point-to-point
 ip ospf 1 area 0
 ipv6 address 2001:107::10/64
interface Ethernet0/0.2000
 encapsulation dot1Q 2000
 vrf forwarding MGMT
 ip address 192.168.217.10 255.255.255.0
            """,
            "show ip int brief": """
Interface                  IP-Address      OK? Method Status                Protocol
Ethernet0/0                unassigned      YES NVRAM  up                    up
Ethernet0/0.102            10.1.102.10     YES NVRAM  up                    up
Ethernet0/0.107            10.1.107.10     YES NVRAM  up                    up
Ethernet0/0.2000           192.168.217.10  YES NVRAM  up                    up
Ethernet0/1                unassigned      YES NVRAM  up                    up
Ethernet0/2                unassigned      YES NVRAM  up                    up
Ethernet0/3                unassigned      YES NVRAM  administratively down down
Loopback0                  10.0.0.10       YES NVRAM  up                    up
Loopback100                1.1.1.100       YES NVRAM  up                    up
            """
        },
    "router-2": {
            "show run": """
interface Loopback0
 description Routing Loopback
 ip address 10.0.0.7 255.255.255.255
 ip ospf 1 area 0
 ipv6 address 2001::7/128
interface Ethernet0/0
 description Main Interface for L3 features testing
 no ip address
 duplex auto
interface Ethernet0/0.27
 description to_vIOS1_Gi0/0.27
 encapsulation dot1Q 27
 ip address 10.1.27.7 255.255.255.0
 ipv6 address 2001:27::7/64
interface Ethernet0/0.37
 description to_CSR1_Gig2.37
 encapsulation dot1Q 37
 ip address 10.1.37.7 255.255.255.0
 ip ospf network point-to-point
 ip ospf 1 area 0
 ipv6 address 2001:37::7/64
interface Ethernet0/0.107
 description to_IOL1_Eth0/0.107
 encapsulation dot1Q 107
 ip address 10.1.107.7 255.255.255.0
 ip ospf network point-to-point
 ip ospf 1 area 0
 ipv6 address 2001:107::7/64
interface Ethernet0/0.117
 description to_IOL3_Eth0/0.117
 encapsulation dot1Q 117
 ip address 10.1.117.7 255.255.255.0
 ip ospf network point-to-point
 ip ospf 1 area 0
 ipv6 address 2001:117::7/64
interface Ethernet0/0.2000
 description Inband Management
 encapsulation dot1Q 2000
 vrf forwarding MGMT
 ip address 192.168.217.7 255.255.255.0
            """,
            "show ip int brief": """
Interface                  IP-Address      OK? Method Status                Protocol
Ethernet0/0                unassigned      YES NVRAM  up                    up
Ethernet0/0.27             10.1.27.7       YES NVRAM  up                    up
Ethernet0/0.37             10.1.37.7       YES NVRAM  up                    up
Ethernet0/0.107            10.1.107.7      YES NVRAM  up                    up
Ethernet0/0.117            10.1.117.7      YES NVRAM  up                    up
Ethernet0/0.2000           192.168.217.7   YES NVRAM  up                    up
Ethernet0/1                unassigned      YES NVRAM  administratively down down
Ethernet0/2                unassigned      YES NVRAM  administratively down down
Ethernet0/3                unassigned      YES NVRAM  administratively down down
Loopback0                  10.0.0.7        YES NVRAM  up                    up
            """
        },
    }

    res = FindString(data, pattern="192.168.*")
    # pprint.pprint(res, width=150)
    assert res == {'router-1': {'show ip int brief': 'Ethernet0/0.2000           192.168.217.10  YES NVRAM  up                    up',
                                             'show run': ' ip address 192.168.217.10 255.255.255.0'},
                                'router-2': {'show ip int brief': 'Ethernet0/0.2000           192.168.217.7   YES NVRAM  up                    up',
                                             'show run': ' ip address 192.168.217.7 255.255.255.0'}}

# test_find_string_function()

def test_find_string_function_before_1():
    from nornir_salt import FindString

    data = {
    "router-1": {
            "show run": """
interface Loopback0
 description Routing Loopback
 ip address 10.0.0.10 255.255.255.255
 ip ospf 1 area 0
 ipv6 address 2001::10/128
interface Loopback100
 ip address 1.1.1.100 255.255.255.255
interface Ethernet0/0
 description Main Interface for L3 features testing
 no ip address
 duplex auto
interface Ethernet0/0.102
 description to_vIOS1_Gi0/0.102
 encapsulation dot1Q 102
 ip address 10.1.102.10 255.255.255.0
 ipv6 address 2001:102::10/64
interface Ethernet0/0.107
 description to_IOL2_Eth0/0.107
 encapsulation dot1Q 107
 ip address 10.1.107.10 255.255.255.0
 ip ospf network point-to-point
 ip ospf 1 area 0
 ipv6 address 2001:107::10/64
interface Ethernet0/0.2000
 encapsulation dot1Q 2000
 vrf forwarding MGMT
 ip address 192.168.217.10 255.255.255.0
            """,
            "show ip int brief": """
Interface                  IP-Address      OK? Method Status                Protocol
Ethernet0/0                unassigned      YES NVRAM  up                    up
Ethernet0/0.102            10.1.102.10     YES NVRAM  up                    up
Ethernet0/0.107            10.1.107.10     YES NVRAM  up                    up
Ethernet0/0.2000           192.168.217.10  YES NVRAM  up                    up
Ethernet0/1                unassigned      YES NVRAM  up                    up
Ethernet0/2                unassigned      YES NVRAM  up                    up
Ethernet0/3                unassigned      YES NVRAM  administratively down down
Loopback0                  10.0.0.10       YES NVRAM  up                    up
Loopback100                1.1.1.100       YES NVRAM  up                    up
            """
        },
    "router-2": {
            "show run": """
interface Loopback0
 description Routing Loopback
 ip address 10.0.0.7 255.255.255.255
 ip ospf 1 area 0
 ipv6 address 2001::7/128
interface Ethernet0/0
 description Main Interface for L3 features testing
 no ip address
 duplex auto
interface Ethernet0/0.27
 description to_vIOS1_Gi0/0.27
 encapsulation dot1Q 27
 ip address 10.1.27.7 255.255.255.0
 ipv6 address 2001:27::7/64
interface Ethernet0/0.37
 description to_CSR1_Gig2.37
 encapsulation dot1Q 37
 ip address 10.1.37.7 255.255.255.0
 ip ospf network point-to-point
 ip ospf 1 area 0
 ipv6 address 2001:37::7/64
interface Ethernet0/0.107
 description to_IOL1_Eth0/0.107
 encapsulation dot1Q 107
 ip address 10.1.107.7 255.255.255.0
 ip ospf network point-to-point
 ip ospf 1 area 0
 ipv6 address 2001:107::7/64
interface Ethernet0/0.117
 description to_IOL3_Eth0/0.117
 encapsulation dot1Q 117
 ip address 10.1.117.7 255.255.255.0
 ip ospf network point-to-point
 ip ospf 1 area 0
 ipv6 address 2001:117::7/64
interface Ethernet0/0.2000
 description Inband Management
 encapsulation dot1Q 2000
 vrf forwarding MGMT
 ip address 192.168.217.7 255.255.255.0
            """,
            "show ip int brief": """
Interface                  IP-Address      OK? Method Status                Protocol
Ethernet0/0                unassigned      YES NVRAM  up                    up
Ethernet0/0.27             10.1.27.7       YES NVRAM  up                    up
Ethernet0/0.37             10.1.37.7       YES NVRAM  up                    up
Ethernet0/0.107            10.1.107.7      YES NVRAM  up                    up
Ethernet0/0.117            10.1.117.7      YES NVRAM  up                    up
Ethernet0/0.2000           192.168.217.7   YES NVRAM  up                    up
Ethernet0/1                unassigned      YES NVRAM  administratively down down
Ethernet0/2                unassigned      YES NVRAM  administratively down down
Ethernet0/3                unassigned      YES NVRAM  administratively down down
Loopback0                  10.0.0.7        YES NVRAM  up                    up
            """
        },
    }

    res = FindString(data, pattern="192.168.*", before=1)
    # pprint.pprint(res, width=150)
    assert res == {'router-1': {'show ip int brief': '--\n'
                                                     'Ethernet0/0.107            10.1.107.10     YES NVRAM  up                    up\n'
                                                     'Ethernet0/0.2000           192.168.217.10  YES NVRAM  up                    up',
                                'show run': '--\n vrf forwarding MGMT\n ip address 192.168.217.10 255.255.255.0'},
                   'router-2': {'show ip int brief': '--\n'
                                                     'Ethernet0/0.117            10.1.117.7      YES NVRAM  up                    up\n'
                                                     'Ethernet0/0.2000           192.168.217.7   YES NVRAM  up                    up',
                                'show run': '--\n vrf forwarding MGMT\n ip address 192.168.217.7 255.255.255.0'}}

# test_find_string_function_before_1()

@skip_if_no_nornir
def test_result_serializer_to_dict_with_details():
    output = nr.run(
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
        name="check ntp config"
    )
    serialized_output = ResultSerializer(output, add_details=True)
    assert serialized_output == {'IOL1': {'check ntp config': {'changed': False,
                                                    'diff': '',
                                                    'exception': None,
                                                    'failed': False,
                                                    'result': '\n'
                                                              'ntp server 7.7.7.8\n'
                                                              'ntp server 7.7.7.7\n'
                                                              '        '}},
                      'IOL2': {'check ntp config': {'changed': False,
                                                    'diff': '',
                                                    'exception': None,
                                                    'failed': False,
                                                    'result': '\nntp server 7.7.7.7\n        '}}}

# test_result_serializer_to_dict_with_details()

@skip_if_no_nornir
def test_result_serializer_to_dict_no_details():
    output = nr.run(
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
        name="check ntp config"
    )
    serialized_output = ResultSerializer(output, add_details=False)
    assert serialized_output == {'IOL1': {'check ntp config': '\n'
                                                   'ntp server 7.7.7.8\n'
                                                   'ntp server 7.7.7.7\n'
                                                   '        '},
                      'IOL2': {'check ntp config': '\nntp server 7.7.7.7\n        '}}

# test_result_serializer_to_dict_no_details()

@skip_if_no_nornir
def test_result_serializer_to_list_with_details():
    output = nr.run(
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
        name="check ntp config"
    )
    serialized_output = ResultSerializer(output, add_details=True, to_dict=False)
    # pprint.pprint(serialized_output)
    assert serialized_output == [{'changed': False,
                                 'diff': '',
                                 'exception': None,
                                 'failed': False,
                                 'host': 'IOL1',
                                 'name': 'check ntp config',
                                 'result': '\nntp server 7.7.7.8\nntp server 7.7.7.7\n        '},
                                {'changed': False,
                                 'diff': '',
                                 'exception': None,
                                 'failed': False,
                                 'host': 'IOL2',
                                 'name': 'check ntp config',
                                 'result': '\nntp server 7.7.7.7\n        '}]

# test_result_serializer_to_list_with_details()

@skip_if_no_nornir
def test_result_serializer_to_list_no_details():
    output = nr.run(
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
        name="check ntp config"
    )
    serialized_output = ResultSerializer(output, add_details=False, to_dict=False)
    # pprint.pprint(serialized_output)
    assert serialized_output == [{'host': 'IOL1',
                                  'name': 'check ntp config',
                                  'result': '\nntp server 7.7.7.8\nntp server 7.7.7.7\n        '},
                                 {'host': 'IOL2',
                                  'name': 'check ntp config',
                                  'result': '\nntp server 7.7.7.7\n        '}]

# test_result_serializer_to_list_no_details()