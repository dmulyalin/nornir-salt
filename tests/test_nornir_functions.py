import sys
import pprint
sys.path.insert(0,'..')

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