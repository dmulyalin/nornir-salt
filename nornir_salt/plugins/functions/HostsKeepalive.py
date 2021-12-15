"""
HostsKeepalive
##############

Function to iterate over Nornir hosts' connections and check if connection
still alive. If connection not responding, ``HostsKeepalive`` function deletes
it.

In general case, running ``HostsKeepalive`` function will keep connection with host
open, preventing it from timeout due to inactivity.

``HostsKeepalive`` function supports these connection types:

- netmiko - uses ``is_alive()`` method to check connection
- paramiko channel - uses connection ``conn_obj.active`` attribute to check connection status
- napalm - uses ``is_alive()`` method to check connection
- scrapli - uses ``isalive()`` method to check connection
- ncclient - uses ``connected`` attribute of connection manager to check connection status
- http - HTTP connections non-persistent hence ``HostsKeepalive`` does nothing
- pyats - uses ``is_connected`` method

For other connection types ``HostsKeepalive`` logs warning message about connection
type being unknown and keeps connection intact.

.. note:: HostsKeepalive only checks previously established connections, it
  does not creates new connections to hosts or tries to reopen dead connections.

HostsKeepalive Sample Usage
===========================

Sample code to invoke ``HostsKeepalive`` function::

    from nornir import InitNornir
    from nornir_salt.plugins.functions import HostsKeepalive

    nr = InitNornir(config_file="config.yaml")

    stats = HostsKeepalive(nr)

HostsKeepalive reference
========================

.. autofunction:: nornir_salt.plugins.functions.HostsKeepalive.HostsKeepalive
"""

import logging
import traceback

log = logging.getLogger(__name__)


def HostsKeepalive(nr):
    """
    :param nr: Nornir object
    :returns: stats dictionary with statistics about ``HostsKeepalive`` execution

    Return ``stats`` dictionary keys description:

    - ``dead_connections_cleaned`` - contains overall number of connections cleaned
    """
    stats = {"dead_connections_cleaned": 0}

    for host_name, host_obj in nr.inventory.hosts.items():
        # to avoid "RuntimeError: dictionary changed size during iteration" error
        # going to iterate over a copy of dictionary keys
        for conn_name in list(host_obj.connections.keys()):
            conn_obj = host_obj.connections[conn_name]
            is_alive = True
            try:
                if "netmiko" in str(type(conn_obj)).lower():
                    is_alive = conn_obj.connection.is_alive()
                elif "paramiko.channel.channel" in str(type(conn_obj)).lower():
                    is_alive = conn_obj.active
                elif "paramiko.client.sshclient" in str(type(conn_obj)).lower():
                    pass
                elif "napalm" in str(type(conn_obj)).lower():
                    is_alive = conn_obj.connection.is_alive()["is_alive"]
                elif "scrapli" in str(type(conn_obj)).lower():
                    is_alive = conn_obj.connection.isalive()
                elif "ncclient" in str(type(conn_obj)).lower():
                    is_alive = conn_obj.connection.connected
                elif "http" in str(type(conn_obj)).lower():
                    is_alive = True
                elif "pygnmi" in str(type(conn_obj)).lower():
                    is_alive = True
                elif "pyats" in str(type(conn_obj)).lower():
                    is_alive = all(
                        [d.is_connected() for d in conn_obj.connection.devices.values()]
                    )
                else:
                    log.debug(
                        "nornir_salt:HostsKeepalive - uncknown connection '{}', type: '{}'".format(
                            conn_name, str(type(conn_obj)).lower()
                        )
                    )
            except:
                is_alive = False
                tb = traceback.format_exc()
                log.info(
                    "nornir_salt:HostsKeepalive - '{}' connection keepalive error: {}".format(
                        conn_name, tb
                    )
                )
            # close connection if not alive
            if not is_alive:
                host_obj.close_connection(conn_name)
                _ = host_obj.connections.pop(conn_name, None)
                stats["dead_connections_cleaned"] += 1
                log.info(
                    "nornir_salt:HostsKeepalive, removed dead '{}' connection, host '{}'".format(
                        conn_name, host_name
                    )
                )

    return stats
