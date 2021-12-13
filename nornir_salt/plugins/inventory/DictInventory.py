"""
DictInventory plugin
####################

DictInventory is an inventory plugin that loads data from Python dictionaries.

DictInventory sample usage
==========================

Need to instruct Nornir to use DictInventory plugin on instantiation::

    import yaml
    from nornir import InitNornir

    inventory_data = '''
    hosts:
      R1:
        hostname: 192.168.1.151
        platform: ios
        groups: [lab]
      R2:
        hostname: 192.168.1.153
        platform: ios
        groups: [lab]
      R3:
        hostname: 192.168.1.154
        platform: ios
        groups: [lab]

    groups:
      lab:
        username: cisco
        password: cisco
    '''

    inventory_dict = yaml.safe_load(inventory_data)

    NornirObj = InitNornir(
        inventory={
            "plugin": "DictInventory",
            "options": {
                "hosts": inventory_dict["hosts"],
                "groups": inventory_dict["groups"],
                "defaults": inventory_dict.get("defaults", {})
            }
        }
    )

DictInventory reference
=======================

.. autoclass:: nornir_salt.plugins.inventory.DictInventory.DictInventory
"""
import logging
from typing import Any, Dict, Type

from nornir.core.inventory import (
    Inventory,
    Group,
    Host,
    Defaults,
    ConnectionOptions,
    HostOrGroup,
    ParentGroups,
)

__version__ = "0.0.1"

logger = logging.getLogger(__name__)


def _get_connection_options(data: Dict[str, Any]) -> Dict[str, ConnectionOptions]:
    cp = {}
    for cn, c in data.items():
        cp[cn] = ConnectionOptions(
            hostname=c.get("hostname"),
            port=c.get("port"),
            username=c.get("username"),
            password=c.get("password"),
            platform=c.get("platform"),
            extras=c.get("extras"),
        )
    return cp


def _get_defaults(data: Dict[str, Any]) -> Defaults:
    return Defaults(
        hostname=data.get("hostname"),
        port=data.get("port"),
        username=data.get("username"),
        password=data.get("password"),
        platform=data.get("platform"),
        data=data.get("data"),
        connection_options=_get_connection_options(data.get("connection_options", {})),
    )


def _get_inventory_element(
    typ: Type[HostOrGroup], data: Dict[str, Any], name: str, defaults: Defaults
) -> HostOrGroup:
    return typ(
        name=name,
        hostname=data.get("hostname"),
        port=data.get("port"),
        username=data.get("username"),
        password=data.get("password"),
        platform=data.get("platform"),
        data=data.get("data"),
        groups=data.get(
            "groups"
        ),  # this is a hack, we will convert it later to the correct type
        defaults=defaults,
        connection_options=_get_connection_options(data.get("connection_options", {})),
    )


class DictInventory:
    """
    DictInventory class to instantiate inventory plugin from.

    :param hosts: dictionary with hosts data
    :param groups: dictionary with groups data
    :param defaults: dictionary with defaults data
    """

    def __init__(self, hosts: Dict, groups: Dict, defaults: Dict) -> None:
        self.hosts = hosts
        self.groups = groups
        self.defaults = defaults

    def load(self) -> Inventory:
        nr_defaults = _get_defaults(self.defaults)

        nr_hosts = {
            n: _get_inventory_element(Host, h, n, nr_defaults)
            for n, h in self.hosts.items()
        }

        nr_groups = {
            n: _get_inventory_element(Group, g, n, nr_defaults)
            for n, g in self.groups.items()
        }

        for h in nr_hosts.values():
            h.groups = ParentGroups([nr_groups[g] for g in h.groups])
        for g in nr_groups.values():
            g.groups = ParentGroups([nr_groups[g] for g in g.groups])
        return Inventory(hosts=nr_hosts, groups=nr_groups, defaults=nr_defaults)
