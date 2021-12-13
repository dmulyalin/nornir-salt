"""
FFun
####

Nornir interacts with many devices and has it's own inventory. FFun is an extension
that uses Nornir's built-in filtering capabilities to narrow down tasks execution
to certain hosts/devices.

Filtering order::

    FO -> FB -> FC -> FR -> FG -> FP -> FL -> FN

.. note:: If multiple filters provided, hosts must pass all checks - ``AND`` logic - to succeed.


FFun filters overview
=====================

FO - Filter Object
------------------

Filter using `Nornir Filter Object <https://nornir.readthedocs.io/en/latest/tutorial/inventory.html#Filter-Object>`_

Examples::

    # Platform ios and hostname 192.168.217.7:
    filtered_hosts = FFun(NornirObj, FO={"platform": "ios", "hostname": "192.168.217.7"})

    # Host with name R1 or R2:
    filtered_hosts = FFun(NornirObj, FO={"name__any": ["R1", "R2"])

    # Location B1 or location B2:
    filtered_hosts = FFun(NornirObj, FO=[{"location": "B1"}, {"location": "B2"}])

    # Location B1 and platform ios or any host at location B2:
    filtered_hosts = FFun(NornirObj, FO=[{"location": "B1", "platform": "ios"}, {"location": "B2"}])

FB - Filter gloB
----------------

Filter hosts by name using Glob Patterns matching `fnmatchcase <https://docs.python.org/3.4/library/fnmatch.html#fnmatch.fnmatchcase>`_ module::

    # Match R1, R2, R# hostnames but not R11 or R4:
    filtered_hosts = FFun(NornirObj, FB="R[123]")

    # Match R1, R2, and SW1 but not R11 or R4 or eSW1 using list of patterns:
    filtered_hosts = FFun(NornirObj, FB=["R[12]", "SW*"])

    # Match R1, R2, and SW1 but not R11 or R4 or eSW1 using comma separated list of patterns:
    filtered_hosts = FFun(NornirObj, FB="R[12], SW*")

If list of patterns provided, host matching at least one pattern will pass this check.

FC - Filter Contains Any
------------------------

Filter hosts by checking if their name contains any of the string patterns::

    # Match core-switch-1 but not switch-1:
    filtered_hosts = FFun(NornirObj, FC="core-switch")

    # Match R1, R2, and SW1 but not ER33 or CR4 using list of patterns:
    filtered_hosts = FFun(NornirObj, FC=["R1", "R2", "SW"])

    # Match R1, R2, and SW1 but not ER33 or CR4 using comma separated list of patterns:
    filtered_hosts = FFun(NornirObj, FC="R1, R2, SW")

If list of patterns provided, host matching at least one pattern will pass this check.

FR - Filter Regex
-----------------

Filter hosts by checking if their name contains any of regular expression patterns::

    # Match core-switch-1 but not switch-1:
    filtered_hosts = FFun(NornirObj, FR=".+core-switch.+")

    # Match R1, R2, and SW1 but not ER33 or CR4 using list of patterns:
    filtered_hosts = FFun(NornirObj, FR=["^R1$", "^R2$", "^SW$"])

If list of patterns provided, host matching at least one pattern will pass this check.

FG - Filter Group
-----------------

Filter hosts by group returning all hosts that belongs to given group::

    # return hosts that belong to 'lab' group only
    filtered_hosts = FFun(NornirObj, FG="lab")

FP - Filter Prefix
------------------

Filter hosts by checking if hosts hostname is part of at least one of given IP Prefixes::

    # return hosts with hostnames in 192.168.217.0/29, 192.168.2.0/24 ranges
    filtered_hosts = FFun(NornirObj, FP="192.168.217.0/29, 192.168.2.0/24")

If host's inventory hostname is IP, will use it as is, if it is FQDN, will
attempt to resolve it to obtain IP address, if DNS resolution fails, host
fails the check.

FL - Filter List
----------------

Match only hosts with names in provided list::

    filtered_hosts = FFun(NornirObj, FL="R1, R2")

FN - Filter Negate
------------------

Negate matching results if ``FN`` argument set to ``True``::

    # will match all hosts except R1 and R2
    filtered_hosts = FFun(NornirObj, FL="R1, R2", FN=True)

FFun passes through all the ``Fx`` functions filtering hosts normally, ``FN``
function called at the end to form a set of non matched hosts, that set used
with ``FL`` function to provide final match result.

FFun sample usage
=================

Example how to invoke FFun filtering::

    import pprint
    import yaml
    from nornir import InitNornir
    from nornir_netmiko import netmiko_send_command
    from nornir_salt.plugins.functions import FFun

    inventory_data = '''
    hosts:
      R1:
        hostname: 192.168.1.151
        platform: ios
        groups: [lab]
        data:
          role: core
          site: B1
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
    '''

    inventory_dict = yaml.safe_load(inventory_data)

    NornirObj = InitNornir(config_file="config.yaml")

    filtered_hosts = FFun(NornirObj, FB="R*", FG="lab", FP="192.168.1.0/24", FO={"role": "core"})

    pprint.pprint(filtered_hosts.dict()["inventory"]["hosts"])

    # should print:
    # {'R1': {'connection_options': {},
    #         'data': {'role': 'core', 'site': 'B1'},
    #         'groups': ['lab'],
    #         'hostname': '192.168.1.151',
    #         'name': 'R1',
    #         'password': 'cisco',
    #         'platform': 'ios',
    #         'port': None,
    #         'username': 'cisco'}}

    result = filtered_hosts.run(
        task=netmiko_send_command,
        command_string="show clock"
    )

FFun return
===========

Nornir object with filtered hosts to further execute tasks against.

FFun reference
==============

.. autofunction:: nornir_salt.plugins.functions.FFun.FFun
"""

import logging
from fnmatch import fnmatchcase
from nornir.core.filter import F


log = logging.getLogger(__name__)


def FFun(nr, check_if_has_filter=False, **kwargs):
    """
    Inventory filters dispatcher function.

    :param nr: Nornir object
    :param kwargs: Dictionary with filtering parameters e.g. {"FB": "host1*", "FL": ["host1", "host2"]}
    :param check_if_has_filter: (bool) default is False, if True, returns tuple ``(filtered_hosts, has_filter)``,
        where ``has_filter`` is boolean set to True if any of ``Fx`` filters provided
    :param FO: (str) Nornir Filter object dictionary
    :param FB: (str or list) glob pattern or comma separate list of patterns to filter based on hosts' names
    :param FC: (str or list) pattern or comma separate list of patterns to check for containment in hostname
    :param FR: (str or list) regex pattern or list of patterns to filter based on hosts' names
    :param FG: (str) Name of inventory group to return only hosts that part of it
    :param FP: (str) string, comma separated list of IPv4 or IPv6 prefixes e.g. 102.168.1.0/24
    :param FL: (str) string, comma separated list of hosts' names to return
    :param FN: (bool) default is False, if True, will negate match results to opposite
        set of hosts
    """
    ret = nr
    has_filter = False
    # check if kwargs argument given, usually
    # supplied by SALT nornir-proxy, that required for pop to modify
    # Nornir proxy original kwargs by removing all Fx arguments
    if kwargs.get("kwargs"):
        kwargs = kwargs["kwargs"]
    if kwargs.get("FO"):
        ret = _filter_FO(ret, kwargs.pop("FO"))
        has_filter = True
    if kwargs.get("FB"):
        ret = _filter_FB(ret, kwargs.pop("FB"))
        has_filter = True
    if kwargs.get("FC"):
        ret = _filter_FC(ret, kwargs.pop("FC"))
        has_filter = True
    if kwargs.get("FR"):
        ret = _filter_FR(ret, kwargs.pop("FR"))
        has_filter = True
    if kwargs.get("FG"):
        ret = _filter_FG(ret, kwargs.pop("FG"))
        has_filter = True
    if kwargs.get("FP"):
        ret = _filter_FP(ret, kwargs.pop("FP"))
        has_filter = True
    if "FL" in kwargs:
        ret = _filter_FL(ret, kwargs.pop("FL"))
        has_filter = True
    if "FN" in kwargs:
        ret = _filter_FN(ret, nr, kwargs.pop("FN"))
    return (ret, has_filter) if check_if_has_filter else ret


def _filter_FO(nr, filter_data):
    """
    Function to filter hosts using Filter Object
    """
    ret = nr
    if isinstance(filter_data, dict):
        ret = ret.filter(F(**filter_data))
    elif isinstance(filter_data, list):
        ret = ret.filter(F(**filter_data[0]))
        for item in filter_data[1:]:
            filtered_hosts = nr.filter(F(**item))
            ret.inventory.hosts.update(filtered_hosts.inventory.hosts)
    return ret


def _filter_FB(ret, pattern):
    """
    Function to filter hosts by name using glob patterns
    """
    # check if comma separated list of patterns given
    if isinstance(pattern, str) and "," in pattern:
        pattern = [i.strip() for i in pattern.split(",")]
    # run filtering
    if isinstance(pattern, list):
        return ret.filter(
            filter_func=lambda h: any([fnmatchcase(h.name, str(p)) for p in pattern])
        )
    else:
        return ret.filter(filter_func=lambda h: fnmatchcase(h.name, str(pattern)))


def _filter_FC(ret, pattern):
    """
    Function to filter hosts by name using pattern containment check
    """
    # check if comma separated list of patterns given
    if isinstance(pattern, str) and "," in pattern:
        pattern = [i.strip() for i in pattern.split(",")]
    # run filtering
    if isinstance(pattern, list):
        return ret.filter(
            filter_func=lambda h: any([str(p) in h.name for p in pattern])
        )
    else:
        return ret.filter(filter_func=lambda h: str(pattern) in h.name)


def _filter_FR(ret, pattern):
    """
    Function to filter hosts by name using regex pattern search
    """
    import re

    # run filtering
    if isinstance(pattern, list):
        return ret.filter(
            filter_func=lambda h: any([re.search(str(p), h.name) for p in pattern])
        )
    else:
        return ret.filter(
            filter_func=lambda h: True if re.search(str(pattern), h.name) else False
        )


def _filter_FG(ret, group):
    """
    Function to filter hosts using Groups
    """
    return ret.filter(filter_func=lambda h: h.has_parent_group(group))


def _filter_FP(ret, pfx):
    """
    Function to filter hosts based on IP Prefixes
    """
    import ipaddress
    import socket

    socket.setdefaulttimeout(1)

    def _filter_net(host):
        # convert host's ip to ip address object
        try:
            ip_addr = ipaddress.ip_address(host.hostname)
        except ValueError:
            # try to resolve hostname using DNS
            try:
                ip_str = socket.gethostbyname(host.hostname)
                ip_addr = ipaddress.ip_address(ip_str)
            except Exception as e:
                log.error(
                    "FP failed to convert host IP '{}', error '{}'".format(host.name, e)
                )
                return False
        # run filtering
        for net in networks:
            if ip_addr in net:
                return True
        return False

    # make a list of network objects
    prefixes = [i.strip() for i in pfx.split(",")] if isinstance(pfx, str) else pfx
    networks = []
    for prefix in prefixes:
        try:
            networks.append(ipaddress.ip_network(prefix))
        except Exception as e:
            log.error("FP failed to convert prefix '{}', error '{}'".format(prefix, e))
    # filter hosts
    return ret.filter(filter_func=_filter_net)


def _filter_FL(ret, names_list):
    """
    Function to filter hosts names based on list of names
    """
    names_list = (
        [i.strip() for i in names_list.split(",")]
        if isinstance(names_list, str)
        else names_list
    )
    if "_all_" in names_list:
        return ret
    else:
        return ret.filter(filter_func=lambda h: h.name in names_list)


def _filter_FN(ret, nr, FN):
    """
    Function to negate hosts' match results
    """
    if FN is not True:
        return ret
    all_hosts = set(nr.inventory.hosts.keys())
    matched_hosts = set(ret.inventory.hosts.keys())
    FNed_hosts = all_hosts.difference(matched_hosts)
    return _filter_FL(nr, list(FNed_hosts))
